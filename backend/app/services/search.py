"""Keyword search over the library.

The old search was a single SQL LIKE across a handful of columns, so the
whole query had to appear verbatim as one substring. A real teacher query
("cheetah themed pre-K SEL kinesthetic activities") matched nothing, and
tags — where the most specific words live — weren't searched at all.

This scores each resource against the query's individual terms across every
field, weighted by where the term hit. Two behaviours matter most:

1. Coverage dominates. A resource matching four of five terms beats one
   matching a single term repeatedly, so multi-keyword queries narrow.
2. A narrow query still answers. When some terms match nothing in the
   library ("cheetah"), the search retries with only the terms that did
   match and says so — a micro question gets a macro answer instead of an
   empty page, and broad programs are favoured on that retry because
   they're the ones likely to contain the missing specific thing.
"""
import math
import re

from sqlalchemy.orm import Session, selectinload

from app.models.resource import Resource

# Multi-word forms collapsed before tokenizing, applied identically to the
# query and to resource text so both sides normalize to the same token.
_PHRASES = (
    ("pre-kindergarten", "prek"),
    ("prekindergarten", "prek"),
    ("pre-k", "prek"),
    ("pre k", "prek"),
    ("social-emotional", "sel"),
    ("social emotional", "sel"),
    ("hands-on", "handson"),
    ("hands on", "handson"),
    ("gross motor", "grossmotor"),
    ("fine motor", "finemotor"),
    ("read-aloud", "readaloud"),
    ("read aloud", "readaloud"),
    ("english language learner", "ell"),
    ("english learner", "ell"),
    ("special education", "sped"),
    ("early childhood", "prek"),
)

# Function words plus filler that would otherwise match nearly every row.
# "students"/"will"/"able" are here because every learning outcome starts
# with "Students will be able to" — left in, they match the whole library.
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

# (field name, weight). Title and tags carry the most signal: tags are where
# the concrete topical words live ("cheetah", "moon phases", "kinesthetic").
_FIELD_WEIGHTS = (
    ("title", 6.0),
    ("tags", 5.0),
    ("subject", 3.0),
    ("grade_band", 3.0),
    ("resource_type", 3.0),
    ("description", 2.5),
    ("publisher", 2.0),
    ("source_site", 2.0),
    ("learning_outcomes", 2.0),
    ("udl_principles", 2.0),
    ("scope", 1.5),
    ("materials", 1.5),
    ("standards", 1.5),
    ("udl_rationale", 1.5),
    ("granularity", 1.0),
)

# Teacher vocabulary that should find resources filed under a different word.
# Written in the same normalized/stemmed space the documents are, and scored
# below a direct hit so precision survives.
_SYNONYMS = {
    "kinesthetic": ("movement", "grossmotor", "physical", "dance", "active", "handson"),
    "movement": ("kinesthetic", "grossmotor", "physical", "dance"),
    "handson": ("kinesthetic", "tactile", "manipulative", "experiment", "build"),
    "sel": ("emotion", "feeling", "kindness", "mindfulness", "selfregulation"),
    "prek": ("preschool", "kindergarten", "toddler", "earli"),
    "preschool": ("prek", "kindergarten", "toddler"),
    "printable": ("worksheet", "handout", "pdf"),
    "worksheet": ("printable", "handout"),
    "ell": ("esl", "multilingual", "bilingual"),
    "sped": ("accommodation", "differentiation", "iep", "inclusive"),
    "reading": ("literacy", "phonic", "ela"),
    "literacy": ("reading", "phonic", "ela"),
    "writing": ("ela", "composition", "narrative"),
    "coding": ("code", "programming", "computational", "algorithm"),
    "programming": ("coding", "code", "computational", "algorithm"),
    "experiment": ("lab", "investigation", "handson"),
    "space": ("astronomy", "planet", "solar", "nasa"),
    "animal": ("wildlife", "zoo", "habitat", "creature"),
    "puzzle": ("logic", "brain", "challenge"),
}
_SYNONYM_FACTOR = 0.7

# Added to a term's field weight so that matching another distinct term always
# beats matching the same one somewhere better.
_COVERAGE_BONUS = 8.0
# Multiplied in after scoring: a specific query wants one class-ready thing;
# a broadened one wants the big program that might contain the missing piece.
_SPECIFIC_NUDGE = 1.06
_COLLECTION_NUDGE = 1.15
# Below this share of terms matched, the query is treated as too narrow and
# retried without its dead terms.
_BROADEN_COVERAGE = 0.6
# Results scoring below this share of the best hit are dropped, so the result
# count means "relevant" rather than "touched one common word".
_RELEVANCE_FLOOR = 0.38

_WORD_RE = re.compile(r"[a-z0-9]+")


def _normalize(text: str) -> str:
    text = text.lower()
    for phrase, token in _PHRASES:
        text = text.replace(phrase, token)
    return text


def _stem(word: str) -> str:
    """Crude plural stripper. Applied to both sides so the two agree; real
    stemming isn't worth a dependency at this library's size."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("es") and word[:-2].endswith(("s", "x", "z", "ch", "sh")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    """Query/document text -> deduped, stemmed, stopword-free terms."""
    words = _WORD_RE.findall(_normalize(text))
    out: list[str] = []
    for word in words:
        if word in _STOPWORDS or len(word) < 2:
            continue
        stem = _stem(word)
        if stem not in out:
            out.append(stem)
    return out


def _expand(term: str) -> list[tuple[str, float]]:
    """A term plus its discounted synonyms, all in stemmed form."""
    variants = [(term, 1.0)]
    for synonym in _SYNONYMS.get(term, ()):
        variants.append((_stem(synonym), _SYNONYM_FACTOR))
    return variants


def _field_text(resource: Resource) -> dict[str, str]:
    return {
        "title": resource.title or "",
        "tags": " ".join(t.name for t in resource.tags),
        "subject": resource.subject or "",
        "grade_band": resource.grade_band or "",
        "resource_type": resource.resource_type or "",
        "description": resource.description or "",
        "publisher": resource.publisher or "",
        "source_site": resource.source_site or "",
        "learning_outcomes": resource.learning_outcomes or "",
        "udl_principles": " ".join(p.name.replace("_", " ") for p in resource.udl_principles),
        "scope": resource.scope or "",
        "materials": resource.materials or "",
        "standards": resource.standards or "",
        "udl_rationale": resource.udl_rationale or "",
        "granularity": resource.granularity or "",
    }


class _Indexed:
    """A resource plus its searchable text, prepared once per request."""

    __slots__ = ("resource", "raw", "stems")

    def __init__(self, resource: Resource):
        self.resource = resource
        raw = _field_text(resource)
        self.raw = {name: _normalize(text) for name, text in raw.items()}
        self.stems = {
            name: {_stem(w) for w in _WORD_RE.findall(text)}
            for name, text in self.raw.items()
        }

    def term_score(self, term: str) -> float:
        """Best weight this term earns anywhere in the resource, 0 if absent.
        A whole-word hit scores full weight; a substring hit scores less, so
        'art' inside 'earth' can't outrank a real match. Synonyms count too,
        discounted, so 'kinesthetic' still finds a movement activity."""
        best = 0.0
        for variant, factor in _expand(term):
            for field, weight in _FIELD_WEIGHTS:
                value = weight * factor
                if value <= best:
                    continue
                if variant in self.stems[field]:
                    best = value
                elif len(variant) >= 4 and variant in self.raw[field]:
                    best = max(best, value * 0.55)
        return best


def _score_all(
    indexed: list[_Indexed], terms: list[str], prefer_broad: bool
) -> tuple[list[tuple[float, Resource]], dict[str, int]]:
    """Score every resource against `terms`. Also returns how many resources
    each term hit, which is what tells us a term is dead in this library.

    Terms are weighted by rarity. Without it every query drowns: "free",
    "activity" and "lesson" match most of the library, so a resource hitting
    only those would outrank the one actually about the rare word that
    carried the teacher's intent.
    """
    hits: dict[str, int] = {t: 0 for t in terms}
    rows: list[dict[str, float]] = []
    for entry in indexed:
        row: dict[str, float] = {}
        for term in terms:
            value = entry.term_score(term)
            if value > 0:
                row[term] = value
                hits[term] += 1
        rows.append(row)

    count = max(1, len(indexed))
    idf = {
        term: max(0.15, math.log(count / hit) + 0.5) if hit else 0.0
        for term, hit in hits.items()
    }

    scored: list[tuple[float, Resource]] = []
    for entry, row in zip(indexed, rows):
        if not row:
            continue
        total = sum((weight + _COVERAGE_BONUS) * idf[term] for term, weight in row.items())
        is_collection = entry.resource.granularity == "collection"
        if prefer_broad and is_collection:
            total *= _COLLECTION_NUDGE
        elif not prefer_broad and not is_collection:
            total *= _SPECIFIC_NUDGE
        scored.append((total, entry.resource))

    scored.sort(key=lambda pair: (-pair[0], (pair[1].title or "").lower()))
    if scored:
        floor = scored[0][0] * _RELEVANCE_FLOOR
        scored = [pair for pair in scored if pair[0] >= floor]
    return scored, hits


def search(resources: list[Resource], q: str) -> dict:
    """Rank `resources` against the query.

    Returns the ordered resources plus what the search understood: which
    terms found nothing, and whether it had to drop them to answer at all.
    """
    terms = tokenize(q)
    if not terms:
        return {
            "items": list(resources),
            "terms": [],
            "matched_terms": [],
            "unmatched_terms": [],
            "broadened": False,
        }

    indexed = [_Indexed(r) for r in resources]
    scored, hits = _score_all(indexed, terms, prefer_broad=False)

    live = [t for t in terms if hits[t] > 0]
    dead = [t for t in terms if hits[t] == 0]

    # Narrow query: either nothing came back, or nothing covered enough of
    # what was asked. Retry on the terms that exist in this library.
    best_coverage = 0
    for entry in indexed:
        covered = sum(1 for t in terms if entry.term_score(t) > 0)
        best_coverage = max(best_coverage, covered)
    too_narrow = not scored or best_coverage < max(1, round(len(terms) * _BROADEN_COVERAGE))

    broadened = False
    if too_narrow and live and len(live) < len(terms):
        scored, _ = _score_all(indexed, live, prefer_broad=True)
        broadened = True

    return {
        "items": [r for _, r in scored],
        "terms": terms,
        "matched_terms": live,
        "unmatched_terms": dead,
        "broadened": broadened,
    }


def load_for_search(db: Session, stmt) -> list[Resource]:
    """Run a filter query with the relationships search reads eagerly, so
    scoring doesn't fire a query per row."""
    stmt = stmt.options(
        selectinload(Resource.tags),
        selectinload(Resource.udl_principles),
    )
    return list(db.execute(stmt).scalars().unique())
