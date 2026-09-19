"""Keyword search over the library.

A teacher types a few loose words ("cheetah themed pre-K SEL kinesthetic
activities") and expects the library to understand them. Three things make
that work:

1. Every term is matched on its own, across every field, and a resource is
   ranked first by how many of the terms it covers — so several keywords
   narrow the results instead of having to appear together verbatim.
2. Rare terms count for more than common ones (BM25). "free", "lesson" and
   "activity" match most of the library; the word carrying the teacher's
   intent is usually the rare one.
3. A term the library has nothing for is reported, not silently ignored. If
   that leaves the query too narrow to answer well, broad programs are
   favoured — they're the likeliest place for the missing specific thing —
   so a micro question still gets a macro answer.

Matching runs on an SQLite FTS5 index (an inverted index): query cost tracks
how many rows *match*, not how many exist, which is what lets the library
grow into the tens of thousands. The earlier approach re-read every row in
Python per query — ~90 ms at 385 rows, ~2 s at 8,000. It survives below as
the fallback for a database without FTS5 (e.g. a future move to Postgres,
where tsvector would replace this module's index).
"""
import re
import sqlite3
import weakref

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from app.models.resource import Resource

# Multi-word forms collapsed before tokenizing, applied identically to the
# query and to indexed text so both sides land on the same token.
_PHRASES = (
    ("pre-kindergarten", "prek"),
    ("prekindergarten", "prek"),
    ("pre-k", "prek"),
    ("pre k", "prek"),
    ("early childhood", "prek"),
    ("social-emotional", "sel"),
    ("social emotional", "sel"),
    ("self-regulation", "selfregulation"),
    ("self regulation", "selfregulation"),
    ("hands-on", "handson"),
    ("hands on", "handson"),
    ("gross motor", "grossmotor"),
    ("fine motor", "finemotor"),
    ("read-aloud", "readaloud"),
    ("read aloud", "readaloud"),
    ("english language learner", "ell"),
    ("english learner", "ell"),
    ("special education", "sped"),
    ("professional development", "pd"),
    ("professional learning", "pd"),
    ("continuing education", "ceu"),
)

# Function words, plus filler that would otherwise match nearly every row.
# "students"/"will"/"able" are here because every learning outcome begins
# "Students will be able to" — left in, they match the whole library.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "of", "to", "in", "on", "with",
    "by", "about", "is", "are", "be", "that", "this", "it", "as", "at",
    "from", "my", "me", "i", "we", "you", "your", "their", "our", "its",
    "some", "any", "need", "needs", "want", "wants", "looking", "look",
    "find", "show", "give", "something", "anything", "students", "student",
    "kids", "kid", "child", "children", "teacher", "teachers", "class",
    "classroom", "grade", "grades", "level", "levels", "based", "using",
    "use", "themed", "theme", "themes", "idea", "ideas", "best", "good",
    "great", "fun", "will", "able", "can", "how", "what", "where", "which",
    "do", "does", "make", "get", "new", "more", "most", "other", "into",
}

# Teacher vocabulary that should find resources filed under another word.
# Written in the normalized space; scored below a direct hit.
_SYNONYMS = {
    "kinesthetic": ("movement", "grossmotor", "physical", "dance", "active", "handson"),
    "movement": ("kinesthetic", "grossmotor", "physical", "dance"),
    "handson": ("kinesthetic", "tactile", "manipulative", "experiment", "build"),
    "sel": ("emotion", "feeling", "kindness", "mindfulness", "selfregulation"),
    "prek": ("preschool", "kindergarten", "toddler"),
    "preschool": ("prek", "kindergarten", "toddler"),
    "printable": ("worksheet", "handout", "pdf"),
    "worksheet": ("printable", "handout"),
    "ell": ("esl", "multilingual", "bilingual"),
    "sped": ("accommodation", "differentiation", "iep", "inclusive", "inclusion"),
    "reading": ("literacy", "phonic", "ela"),
    "literacy": ("reading", "phonic", "ela"),
    "writing": ("ela", "composition", "narrative"),
    "coding": ("code", "programming", "computational", "algorithm"),
    "programming": ("coding", "code", "computational", "algorithm"),
    "experiment": ("lab", "investigation", "handson"),
    "space": ("astronomy", "planet", "solar", "nasa"),
    "animal": ("wildlife", "zoo", "habitat", "creature"),
    "puzzle": ("logic", "brain", "challenge"),
    "pd": ("educator", "training", "webinar", "ceu", "certificate"),
    "ceu": ("pd", "credit", "certificate"),
    "training": ("pd", "course", "webinar"),
}
_SYNONYM_FACTOR = 0.7

# Indexed fields and their weights. The FTS table's columns are exactly
# these, in this order, so bm25() weights line up by position.
_FIELDS = (
    ("title", 6.0),
    ("tags", 5.0),
    ("subject", 3.0),
    ("grade_band", 3.0),
    ("resource_type", 3.0),
    ("audience", 3.0),
    ("description", 2.5),
    ("publisher", 2.0),
    ("source_site", 2.0),
    ("learning_outcomes", 2.0),
    ("udl_principles", 2.0),
    ("credit", 2.0),
    ("scope", 1.5),
    ("materials", 1.5),
    ("standards", 1.5),
    ("udl_rationale", 1.5),
    ("granularity", 1.0),
)

# Ranking. Coverage (how many query terms a row answers) decides first; BM25
# orders rows within a coverage level; the granularity bonus breaks near-ties
# toward what the query seems to want.
_COVERAGE_WEIGHT = 1000.0
_BM25_WEIGHT = 10.0
_GRANULARITY_BONUS = 60.0
# Below this share of terms answered by the best row, the query is too narrow
# and broad programs are preferred.
_BROADEN_COVERAGE = 0.6
# Rows covering less than this share of the best row's coverage are dropped,
# so the result count means "relevant", not "touched one common word".
_RELEVANCE_SHARE = 0.5

_TABLE = "resources_fts"
_WORD_RE = re.compile(r"[a-z0-9]+")


def _normalize(text_: str) -> str:
    text_ = text_.lower()
    for phrase, token in _PHRASES:
        text_ = text_.replace(phrase, token)
    return text_


def _words(text_: str) -> list[str]:
    return _WORD_RE.findall(text_)


def _stem(word: str) -> str:
    """Crude plural stripper for query terms and the fallback scorer. The FTS
    index stems with Porter on both sides, so this only has to agree with
    itself — Porter re-stemming an already-trimmed plural lands in the same
    place."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("es") and word[:-2].endswith(("s", "x", "z", "ch", "sh")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def tokenize(query: str) -> list[str]:
    """Query text -> deduped, stemmed, stopword-free terms."""
    out: list[str] = []
    for word in _words(_normalize(query)):
        if word in _STOPWORDS or len(word) < 2:
            continue
        stem = _stem(word)
        if stem not in out:
            out.append(stem)
    return out


# Extra words indexed alongside a coded value, so "ceu" or "professional
# development" finds a resource whose column just says 'ceu' / 'educators'.
_AUDIENCE_WORDS = {
    "students": "students",
    "educators": "educators educator pd training professional",
}
_CREDIT_WORDS = {
    "ceu": "ceu credit continuing",
    "pd_hours": "pd hours clock credit",
    "certificate": "certificate",
    "graduate_credit": "graduate credit",
}


def _field_text(resource: Resource) -> dict[str, str]:
    credit = _CREDIT_WORDS.get(resource.credit_type or "", "")
    if resource.credit_note:
        credit = f"{credit} {resource.credit_note}"
    return {
        "title": resource.title or "",
        "tags": " ".join(t.name for t in resource.tags),
        "subject": resource.subject or "",
        "grade_band": resource.grade_band or "",
        "resource_type": resource.resource_type or "",
        "audience": _AUDIENCE_WORDS.get(resource.audience or "students", ""),
        "description": resource.description or "",
        "publisher": resource.publisher or "",
        "source_site": resource.source_site or "",
        "learning_outcomes": resource.learning_outcomes or "",
        "udl_principles": " ".join(p.name.replace("_", " ") for p in resource.udl_principles),
        "credit": credit,
        "scope": resource.scope or "",
        "materials": resource.materials or "",
        "standards": resource.standards or "",
        "udl_rationale": resource.udl_rationale or "",
        "granularity": resource.granularity or "",
    }


# --- FTS5 index -----------------------------------------------------------


def _fts5_compiled() -> bool:
    """Whether this Python's SQLite has FTS5 + Porter built in. Checked on a
    throwaway connection: module support is a property of the linked
    library, and probing the app's own session could roll back its work."""
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE probe USING fts5(a, tokenize='porter unicode61')")
        conn.close()
        return True
    except sqlite3.OperationalError:
        return False


_FTS5 = _fts5_compiled()
# Engines whose database already has the FTS table. Weak, not id()-keyed:
# ids are reused after garbage collection, so a fresh database (every test
# gets one) could otherwise inherit a stale "already created".
_ensured: "weakref.WeakSet[Engine]" = weakref.WeakSet()


def backend_name(db: Session) -> str:
    return "fts5" if _uses_fts(db) else "python"


def _uses_fts(db: Session) -> bool:
    return _FTS5 and db.get_bind().dialect.name == "sqlite"


def ensure_index(db: Session) -> bool:
    """Create the FTS table if missing. True when the FTS path is usable."""
    if not _uses_fts(db):
        return False
    engine = db.get_bind()
    if engine not in _ensured:
        columns = ", ".join(name for name, _ in _FIELDS)
        db.execute(
            text(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS {_TABLE} "
                f"USING fts5({columns}, tokenize='porter unicode61')"
            )
        )
        _ensured.add(engine)
    return True


def _index_params(resource: Resource) -> dict:
    fields = _field_text(resource)
    params = {name: _normalize(fields[name]) for name, _ in _FIELDS}
    params["rid"] = resource.id
    return params


_INSERT = (
    f"INSERT INTO {_TABLE}(rowid, {', '.join(n for n, _ in _FIELDS)}) "
    f"VALUES (:rid, {', '.join(':' + n for n, _ in _FIELDS)})"
)


def index_resource(db: Session, resource: Resource) -> None:
    """(Re)index one resource. Call after a flush, so the row has an id."""
    if not ensure_index(db):
        return
    db.execute(text(f"DELETE FROM {_TABLE} WHERE rowid = :rid"), {"rid": resource.id})
    db.execute(text(_INSERT), _index_params(resource))


def remove_resource(db: Session, resource_id: int) -> None:
    if ensure_index(db):
        db.execute(text(f"DELETE FROM {_TABLE} WHERE rowid = :rid"), {"rid": resource_id})


def index_size(db: Session) -> int:
    if not ensure_index(db):
        return 0
    return db.execute(text(f"SELECT count(*) FROM {_TABLE}")).scalar_one()


def rebuild_index(db: Session) -> int:
    """Reindex every resource from scratch. Used when an existing database
    predates the index, and after bulk imports."""
    if not ensure_index(db):
        return 0
    db.execute(text(f"DELETE FROM {_TABLE}"))
    rows = (
        db.execute(
            select(Resource).options(
                selectinload(Resource.tags), selectinload(Resource.udl_principles)
            )
        )
        .scalars()
        .all()
    )
    if rows:
        db.execute(text(_INSERT), [_index_params(r) for r in rows])
    db.commit()
    return len(rows)


def _quote(term: str) -> str:
    # Terms are [a-z0-9]+ after tokenizing; quoting stops FTS reading a term
    # like "or"/"not"/"near" as an operator.
    return f'"{term}"'


def _match_ids(db: Session, expression: str) -> set[int]:
    return set(
        db.execute(
            text(f"SELECT rowid FROM {_TABLE} WHERE {_TABLE} MATCH :q"), {"q": expression}
        ).scalars()
    )


def _rank_fts(db: Session, terms: list[str], allowed: set[int] | None) -> dict:
    coverage: dict[int, float] = {}
    hits: dict[str, int] = {}
    for term in terms:
        direct = _match_ids(db, _quote(term))
        synonyms = [_stem(s) for s in _SYNONYMS.get(term, ())]
        via_synonym = (
            _match_ids(db, " OR ".join(_quote(s) for s in synonyms)) - direct
            if synonyms
            else set()
        )
        if allowed is not None:
            direct &= allowed
            via_synonym &= allowed
        hits[term] = len(direct) + len(via_synonym)
        for rid in direct:
            coverage[rid] = coverage.get(rid, 0.0) + 1.0
        for rid in via_synonym:
            coverage[rid] = coverage.get(rid, 0.0) + _SYNONYM_FACTOR

    live = [t for t in terms if hits[t]]
    dead = [t for t in terms if not hits[t]]
    if not coverage:
        return {"ids": [], "matched_terms": live, "unmatched_terms": dead, "broadened": False}

    best = max(coverage.values())
    broadened = bool(dead) and best < max(1.0, len(terms) * _BROADEN_COVERAGE)

    tokens: set[str] = set()
    for term in live:
        tokens.add(term)
        tokens.update(_stem(s) for s in _SYNONYMS.get(term, ()))
    weights = ", ".join(str(w) for _, w in _FIELDS)
    relevance: dict[int, float] = {}
    granularity: dict[int, str] = {}
    for rid, gran, score in db.execute(
        text(
            f"SELECT rowid, granularity, bm25({_TABLE}, {weights}) "
            f"FROM {_TABLE} WHERE {_TABLE} MATCH :q"
        ),
        {"q": " OR ".join(_quote(t) for t in tokens)},
    ):
        relevance[rid] = -score  # bm25() is negative; lower is better
        granularity[rid] = gran

    floor = best * _RELEVANCE_SHARE
    scored: list[tuple[float, int]] = []
    for rid, covered in coverage.items():
        if covered < floor:
            continue
        score = covered * _COVERAGE_WEIGHT + relevance.get(rid, 0.0) * _BM25_WEIGHT
        is_collection = granularity.get(rid) == "collection"
        if is_collection == broadened:
            score += _GRANULARITY_BONUS
        scored.append((score, rid))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return {
        "ids": [rid for _, rid in scored],
        "matched_terms": live,
        "unmatched_terms": dead,
        "broadened": broadened,
    }


# --- Fallback scorer (no FTS5) -----------------------------------------------


def _rank_python(db: Session, terms: list[str], allowed: set[int] | None) -> dict:
    stmt = select(Resource).options(
        selectinload(Resource.tags), selectinload(Resource.udl_principles)
    )
    if allowed is not None:
        stmt = stmt.where(Resource.id.in_(allowed))
    resources = db.execute(stmt).scalars().unique().all()

    weights = dict(_FIELDS)
    docs = []
    for resource in resources:
        fields = {n: {_stem(w) for w in _words(_normalize(t))} for n, t in _field_text(resource).items()}
        docs.append((resource, fields))

    coverage: dict[int, float] = {}
    relevance: dict[int, float] = {}
    hits = {t: 0 for t in terms}
    for resource, fields in docs:
        for term in terms:
            variants = [(term, 1.0)] + [(_stem(s), _SYNONYM_FACTOR) for s in _SYNONYMS.get(term, ())]
            best_factor, best_weight = 0.0, 0.0
            for variant, factor in variants:
                for name, words in fields.items():
                    if variant in words and factor * weights[name] > best_factor * best_weight:
                        best_factor, best_weight = factor, weights[name]
            if best_factor:
                hits[term] += 1
                coverage[resource.id] = coverage.get(resource.id, 0.0) + best_factor
                relevance[resource.id] = relevance.get(resource.id, 0.0) + best_weight

    live = [t for t in terms if hits[t]]
    dead = [t for t in terms if not hits[t]]
    if not coverage:
        return {"ids": [], "matched_terms": live, "unmatched_terms": dead, "broadened": False}
    best = max(coverage.values())
    broadened = bool(dead) and best < max(1.0, len(terms) * _BROADEN_COVERAGE)
    gran = {r.id: r.granularity for r, _ in docs}
    scored = []
    for rid, covered in coverage.items():
        if covered < best * _RELEVANCE_SHARE:
            continue
        score = covered * _COVERAGE_WEIGHT + relevance[rid]
        if (gran.get(rid) == "collection") == broadened:
            score += _GRANULARITY_BONUS
        scored.append((score, rid))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return {"ids": [rid for _, rid in scored], "matched_terms": live,
            "unmatched_terms": dead, "broadened": broadened}


def rank(db: Session, query: str, allowed: set[int] | None = None) -> dict | None:
    """Rank resource ids for a free-text query.

    `allowed` restricts the result to ids that passed the hard filters (None =
    no filters). Returns None when the query has no searchable words left
    after stopwords, so the caller can treat it as a plain browse.
    """
    terms = tokenize(query)
    if not terms:
        return None
    if ensure_index(db):
        return _rank_fts(db, terms, allowed)
    return _rank_python(db, terms, allowed)
