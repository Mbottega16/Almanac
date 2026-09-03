"""Live Claude-assisted capture (Phase 7).

Dormant until ANTHROPIC_API_KEY is set — every entry point raises until then,
same guard pattern as Chegga's coaching_service. When a key is present, given
a list of URLs this asks Claude to return draft, unsaved Resource records
(subject / grade band / format / cost / UDL principles / a short generated
description). The caller reviews them and commits via POST /api/resources/batch.

Cost note: these calls run on whoever's key is in ANTHROPIC_API_KEY — the
site operator's, unless the deployment is changed to take a per-user key.
That's why it stays off until explicitly switched on.
"""
import json

from app.config import settings
from app.models.udl import UDL_PRINCIPLES
from app.schemas.resource import ResourceCreate

MODEL = "claude-sonnet-5"

_SUBJECTS = [
    "Math", "ELA / Reading", "Science", "Social Studies", "Arts", "SEL",
    "World Languages", "CS / STEM", "PE / Health", "Other",
]
_GRADE_BANDS = ["PreK", "K-2", "3-5", "6-8", "9-12", "HigherEd/Adult", "All"]
_TYPES = [
    "lesson plan", "unit", "worksheet/printable", "video", "interactive/sim",
    "slides", "activity", "assessment", "project", "game", "article/text",
]

_SYSTEM = f"""You catalog teaching resources for a UDL-focused library.
For each URL you are given, produce one JSON object with keys:
link, title,
description (1-2 factual sentences you write yourself),
description_source (always "generated"),
subject (one of {_SUBJECTS}),
grade_band (one of {_GRADE_BANDS}),
age_min (integer or null — youngest typical age),
age_max (integer or null),
resource_type (one of {_TYPES}),
scope (one of "lesson" | "unit" | "course" | "curriculum" — a single
  class period is "lesson"; a multi-lesson topic module is "unit"; a
  full semester/year of one subject is "course"; a publisher's complete
  multi-grade program is "curriculum"),
publisher (the program or publisher name for a course/curriculum, e.g.
  "Illustrative Mathematics", "OpenSciEd"; "" for a one-off lesson),
granularity ("specific" if the URL is one lesson/activity/video a teacher
  can use as-is; "collection" if it is a browse/portal/library page),
duration_minutes (integer or null — how long the lesson/activity runs),
materials (string, "" if digital-only / nothing needed),
learning_outcomes (array of 1-4 short strings, each phrased
  "Students will be able to ..."),
cost ("free" | "paid" | "freemium"),
price_note (short, "" if free),
source_site, license, standards ("" unless a real CCSS/NGSS/C3 code is clear),
evidence (ONE sentence quoted verbatim from the page, <= 200 chars, in
  quotation marks — proof the page is real; "" only if the fetch failed),
udl_rationale (one short line per assigned principle saying why it applies,
  e.g. "representation: captions + transcript + diagrams; engagement: ..."),
tags (2-5 lowercase theme strings),
udl_principles (1-3 of {list(UDL_PRINCIPLES)}).
Reply with ONLY a JSON array, no prose."""


def _require_key() -> str:
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set — live capture is disabled. "
            "Set it in the environment to enable POST /api/capture/research."
        )
    return settings.anthropic_api_key


def research_links(links: list[str], notes: str | None = None) -> list[ResourceCreate]:
    key = _require_key()
    from anthropic import Anthropic  # imported lazily so the dep is optional

    client = Anthropic(api_key=key)
    user = "URLs:\n" + "\n".join(links)
    if notes:
        user += f"\n\nExtra context from the librarian:\n{notes}"

    msg = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in msg.content if block.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()
    rows = json.loads(text)
    return [ResourceCreate(**row) for row in rows]
