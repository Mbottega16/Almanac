# Almanac — house rules

A searchable, aggregated database of teaching resources for teachers,
organized to make **UDL (Universal Design for Learning)** planning
easier. Backed by FastAPI + SQLAlchemy + SQLite, with a Vite + React +
TypeScript frontend. Deliberately the same stack and shape as **Atlas**
(the personal link/tool library) — Almanac is "Atlas for teaching
content." See `README.md` for the quickstart.

## What it's for

A teacher searches a **theme** and immediately gets content for it:
lessons, readings, videos, simulations, activities — sourced from many
sites, gathered into one collective library. For any theme, the app
shows **UDL coverage**: how many matching resources support each of the
three principles (Engagement / Representation / Action & Expression) and
in which formats, so gaps are obvious and a multi-modal lesson is fast
to assemble.

## Current state (2026-08-28)

- **Deployed & live: https://almanac-api.vercel.app** — one Vercel Python
  service (project `almanac-api`, CheggaWeb team) serves the built SPA at
  `/` and the API at `/api/*`. `scripts/build_frontend.py` builds the
  frontend into `backend/static/`; `app.main` mounts it via `StaticFiles`.
  On Vercel `DATABASE_URL` is `/tmp` and the DB is wiped on every cold
  start. **Cold-start seeding fix (2026-08-28):** re-inserting the 289 JSON
  seed rows row-by-row took ~8s and was intermittently tripping the
  serverless function timeout (504s / "backend failures"). Now `app.main`
  first calls `db.seed.ensure_seed_db_file()`, which copies a committed
  pre-built `backend/seed/almanac-seed.db` into `/tmp` (milliseconds); cold
  import is ~1.8s. Rebuild that file with `scripts/build_seed_db.py`
  whenever `almanac-seed.json` changes. The JSON path is still the fallback
  (`load_seed_rows`, now one transaction). Favorites/visits still don't
  survive a cold start — a persistent host (Render — `render.yaml` is
  ready — or Vercel Postgres) is the real fix. Only the canonical `almanac-api.vercel.app` is public;
  custom aliases 302 behind the team's Deployment Protection (disable it
  or rename the project for a nicer URL). The old standalone `almanac`
  Vercel project is superseded and can be deleted.
- **Auth gate** (`app/auth.py` + `routes/auth.py`): built, **dormant** —
  set `ADMIN_PASSWORD` (env var) to activate; the frontend then shows a
  login screen. `itsdangerous`-signed cookie, `SameSite=None; Secure`.
- **Live Claude-assisted capture** (`services/capture_service.py` + `POST
  /api/capture/research`): built, **dormant** — 503s until
  `ANTHROPIC_API_KEY` is set. Returns draft, unsaved resources; the
  Capture page grows a paste-box + review UI when `GET
  /api/capture/enabled` is true. Runs on the operator's key — off by
  default on purpose.
- **Backend**: `resources` model (Atlas's `Entry` fields plus
  `subject`, `grade_band`, `resource_type`, `scope`, `publisher`,
  `cost` (free/paid/freemium), `price_note`, `source_site`, `license`,
  `standards`, `description_source`), real many-to-many `tags` **and** a
  fixed 3-row `udl_principles` join. Full CRUD, search/filter
  (`q`/`subject`/`grade_band`/`resource_type`/`scope`/`publisher`/`cost`/`source_site`/`udl`/`tag`/`age`/`favorite`),
  `random`, `visit`, `favorite`, batch-upsert on `link`
  (`POST /api/resources/batch`), faceted-count endpoints (incl.
  `/api/scopes` and `/api/publishers`), and `GET /api/udl-coverage`.
  22 passing pytest tests (in-memory SQLite).
- **Frontend**: Browse page (theme search, Free/Paid toggle, a
  **scope toggle** — Single lessons / Units / Full courses / Curricula —
  subject chips, grade/format/theme selects, three UDL-principle
  toggles, grid/list/large view modes persisted in `localStorage`), a
  **UDL coverage strip** shown for any theme search, resource cards with
  cost badge + **scope badge** + publisher line + UDL pills, a "My
  Collection" slide-in panel, and a read-only Capture page. The Guided
  discovery flow asks a "how much are you planning?" (scope) step.
  Type-checks and builds clean.
- **Seed**: **291 curated resources** at `backend/seed/almanac-seed.json`
  (idempotent load via `scripts/import_seed.py`). One-off lessons grew
  from 91 via four subject-cluster research passes; a 2026-08-29 pass
  added **31 full courses / commercial curricula** (Illustrative
  Mathematics, OpenSciEd, EL Education, Amplify, Great Minds / Eureka /
  Wit & Wisdom, Zearn, Fishtank, Open Up Resources, CommonLit 360,
  Carnegie Learning, Bridges, PLTW, iCivics, Code.org courses, Khan
  Academy courses, MIT OCW, Crash Course, TERC, Bootstrap) with `scope`
  and `publisher` set.
- **Link-validation pass (2026-08-30):** added `scripts/check_links.py`
  (ported from Atlas — reads `Resource.link`, flags 4xx/5xx, off-host
  redirects, and deep-links that bounce to a homepage; 403/405/429/999
  treated as anti-bot noise). First run flagged 132/320: fixed 64 URLs
  (a systemic `phet.colorado.edu/en/simulations/html/<sim>` →
  `/simulations/<sim>` bug across all PhET rows; provider reorgs at PBS
  LearningMedia, NatGeo Education, NASA, OpenSciEd, SPLC/Learning for
  Justice, iCivics, Kendall Hunt IM, SHEG→Inquiry Group) and dropped 29
  dead rows (retired products, sites where only a homepage remained, and
  a few fabricated entries) → 320 → 291. ~40 rows still flag as
  `URLError`/timeout but are **live sites the build environment's DNS
  can't resolve** (achievethecore.org, mindfulschools.org, scijinks,
  crf-usa.org …) — re-run `check_links.py` from a normal network to
  confirm those.
- **Lesson format** (the "categorizer"): each resource also carries
  `age_min`/`age_max`, `duration_minutes`, `materials`, and
  `learning_outcomes` (list of "Students will be able to …"). Age
  back-fills from `grade_band` via `resource_service.GRADE_TO_AGE` so the
  `age` query param works library-wide; `q` also searches outcomes +
  materials; the live-capture prompt extracts all of it.
  `scripts/migrate_add_lesson_fields.py` is ready for a persistent DB.
- **Lesson scope / commercial curriculum** (2026-08-29): every resource
  carries `scope` — `lesson` (a single class period / one-off, the
  default and all 289 original rows), `unit` (a multi-lesson module),
  `course` (a semester or year of one subject), or `curriculum` (a
  publisher's complete multi-grade program) — plus a `publisher` string
  for the program behind a course/curriculum. Both are filterable
  (`?scope=`, `?publisher=`), faceted (`/api/scopes`, `/api/publishers`),
  and `publisher` is covered by `q` search. `course`/`curriculum` rows
  are the commercial (and free-OER) full programs; a card shows a scope
  badge and the publisher name in place of `source_site`.
  `scripts/migrate_add_curriculum_fields.py` is ready for a persistent DB.
  22 passing pytest tests.
- **Still to do**: re-run `scripts/check_links.py` from a real network
  and clear the ~40 DNS-unreachable flags; activate the auth gate +
  capture (set the env vars), move to a persistent DB, deepen the
  portal-only links, delete the dead standalone `almanac` Vercel project.

## Decisions already made

- **Same stack/shape as Atlas on purpose** — mirror its file layout,
  service patterns, and two-phase capture. Divergences: the
  teaching-specific columns above, the `udl_principles` join, and the
  `GET /api/udl-coverage` endpoint + coverage strip.
- **`link` is UNIQUE**; the batch endpoint upserts on it, so
  re-importing updates instead of duplicating.
- **UDL principles are a fixed lookup table + join**, not a CSV column —
  filtering "show me Representation resources for fractions" is
  first-class, same reasoning Atlas used for tags. Unknown principle
  names are dropped, never created.
- **`cost` is `free` | `paid` | `freemium`.** `freemium` is real and
  common for teacher platforms; don't collapse it into paid.
- **`scope` is `lesson` | `unit` | `course` | `curriculum`**, separate
  from `resource_type` (which is the *format* — video, worksheet, sim…).
  Scope answers "how much of a plan is this?" A one-off lesson is
  `lesson` (the default); a publisher's whole program is `curriculum`.
  Commercial curriculum is deliberately in scope for the library — link
  the program's landing page, set `publisher` + `scope`, and set
  `cost` honestly (`free` for OER programs like IM / OpenSciEd,
  `freemium` where core is free, `paid` otherwise). Still a pointer
  index — never mirror the program's materials.
- **Quick-capture is two-phase**, exactly like Atlas:
  - *Now:* a Claude Code session rooted here researches pasted links /
    named sites via `WebFetch`/`WebSearch` and saves via
    `POST /api/resources/batch`. No API key, no spend. `CapturePage.tsx`
    is a read-only "recently added" view.
  - *Later (needs explicit sign-off + a real `ANTHROPIC_API_KEY`):* a
    `POST /api/capture/research` endpoint does live research and returns
    **draft, unsaved** resources; a second explicit action commits them
    via the batch endpoint. Mirrors Chegga's `coaching_service.py`
    guard — the key stays blank in `.env` until you say otherwise.
- **Deployment: Render (backend) + Vercel (frontend), free tiers** —
  the split Atlas ended up shipping. **Needs explicit user sign-off
  before it goes live**, going public is the gate, not the cost.
- **Auth gate before deploy**: single `ADMIN_PASSWORD` +
  `itsdangerous`-signed session cookie gating the whole app, mirroring
  Atlas / LittleSprout-Rewards. Not built yet.

## Content / copyright guardrail (do not cross)

Almanac is a **pointer index**, not a content mirror. For each resource
store only: the `link`, a `title`, a **short** factual description (a
brief attributed excerpt *or* a generated summary — set
`description_source` accordingly), and metadata. Always link back to the
source. **Never** store a resource's full body (worksheet text, full
lesson plan, video transcript). Record `license` when known. For paid
marketplaces (Teachers Pay Teachers, etc.), link the listing/category
page and set `cost=paid`. **No bulk scraping** — hand-curation +
user-supplied sources + session-assisted research only, the lesson Atlas
learned when several scrape sources didn't pan out.

## Phases

1–4. ✅ Scaffold, data model, browse/capture UI, session-assisted
   capture, first seed batch.
5. ✅ Auth gate built (dormant — set `ADMIN_PASSWORD` to turn on).
6. ✅ Deployed — one Vercel service at https://almanac-api.vercel.app
   (user signed off 2026-08-28). Follow-up: persistent DB.
7. ✅ Live Claude-assisted capture built (dormant — set
   `ANTHROPIC_API_KEY` to turn on; spend is the operator's).

## Why this file exists

So a session opened in this repo has the real plan and constraints
without re-deriving them — mirrors `Atlas/CLAUDE.md`. The vault-side
`projects/almanac/context.md` in `my-brain` is a shorter cross-project
summary; this file is authoritative for Almanac's own code.
