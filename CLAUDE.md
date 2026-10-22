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

## How the library ships (2026-10-22)

- **The library is `backend/seed/almanac-seed.json`** (409 resources). Git
  tracks it. The database is a build artifact.
- **The deploy builds the database.** `render.yaml`'s `buildCommand` runs
  `scripts/build_seed_db.py`, which writes `backend/seed/almanac-seed.db`
  (git-ignored). On start, `app.db.seed.ensure_seed_db_file()` copies that
  file into place. If it is missing, the app loads the JSON (about 6 s at 409
  rows). Build time grows with the library: about 13 ms per row.
- **Link health runs itself.** `.github/workflows/link-check.yml` runs
  `scripts/check_links.py --seed --write-status` every Monday. It writes
  `backend/seed/link-status.json` (consecutive real-4xx failures per link)
  and sets `link_status` on the seed rows. A link is `dead` only after two
  failures in a row. The Action keeps one open "Dead links" issue.
- **Tests:** `cd backend && .venv/Scripts/python -m pytest` (47 pass).

## Historical state (2026-08-28 to 2026-09-16)

Older notes below. Some counts and deploy details are superseded by the
section above.

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
  `granularity`, `cost` (free/paid/freemium), `price_note`, `source_site`,
  `license`, `standards`, `evidence`, `udl_rationale`, `link_status`,
  `description_source`), many-to-many `tags`, `standards` (parsed codes),
  **and** a fixed 3-row `udl_principles` join. Full CRUD, search/filter
  (`q`/`subject`/`grade_band`/`resource_type`/`scope`/`publisher`/`granularity`/`cost`/`source_site`/`udl`/`tag`/`standard`/`age`/`favorite`),
  `random`, `visit`, `favorite`, batch-upsert on `link`
  (`POST /api/resources/batch`), faceted-count endpoints
  (`/api/subjects|grade-bands|resource-types|scopes|publishers|sources|tags|standards`),
  `GET /api/udl-coverage`, and `GET /api/stats` (library-wide gap map).
  Links are canonicalized on write (`services/links.py`) so http/https/www
  variants can't dupe. 27 passing pytest tests (in-memory SQLite).
- **Frontend**: Browse page (theme search, Free/Paid toggle, a
  **scope toggle**, subject chips, grade/format/theme/**standard**
  selects, a **"Class-ready only"** toggle, three UDL-principle toggles,
  grid/list/large view modes), a **UDL coverage strip** for any theme
  search, resource cards with cost + scope + **"Browse page"** +
  **"link may be broken"** badges, publisher line, and UDL pills with
  per-principle **why-this-applies tooltips**. A **Stats page**
  (subject×UDL heatmap + thinnest cells). A "My Collection" slide-in with
  a **Lesson plan** view and a `localStorage` mirror. Guided discovery
  asks a scope step and offers "undo last choice" on a dead-end.
  Read-only Capture page. Type-checks and builds clean.
- **Seed**: **274 curated resources** at `backend/seed/almanac-seed.json`
  (was 288 until the 2026-09-15 dead-link cleanup below dropped 14)
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
- **Deep-critique build (2026-08-30):** ten items off `/deep_critique almanac`.
  New columns (`migrate_add_critique_fields.py`): `granularity`
  (`specific` | `collection` — hides browse/portal pages, `?granularity=`;
  seed backfilled 185/103), `evidence` (one attributed quoted sentence,
  write-only, proof the page is real), `udl_rationale` (one line per
  principle, shown on card hover), `link_status` (`ok`/`dead`/`redirect`/
  `bounced`/`unreachable`, set by `scripts/flag_dead_links.py`; a `dead`
  row gets a warning badge). New: `standards` join table +
  `extract_standard_codes()` (CCSS/NGSS/C3) + `?standard=` +
  `/api/standards`; `GET /api/stats` + a **Stats page** (subject×UDL
  heatmap, thinnest cells); a **Lesson plan** view in My Collection
  (order by duration, union materials, combined UDL coverage) backed by a
  `localStorage` mirror so favorites survive a `/tmp` cold start; Guided
  discovery offers "undo last choice" on a zero-result dead-end;
  `scripts/check_links.py` gained `--json`/`--write`;
  `scripts/find_near_dupes.py` clusters soft duplicates for review. The
  capture prompt now asks for `granularity` / `evidence` / `udl_rationale`.
  27 passing pytest tests.
- **Render deploy + link cleanup (2026-09-15):** `scripts/check_links.py`
  had a real bug — Windows Python's `ssl` module carries no CA bundle by
  default, so any link needing real chain validation (e.g. `nysed.gov`)
  was misclassified `unreachable` instead of actually checked. Fixed by
  pointing `urlopen` at `certifi`'s bundle + a retry for transient DNS
  blips (`certifi` added to `requirements.txt`). Re-ran `flag_dead_links.py`
  and cross-checked the still-flagged rows from a second, independent
  network path: **14 confirmed-dead rows dropped** (domains that don't
  resolve from two networks — `actively.learn`, `learnzillion.com`,
  `scijinks.jpl.nasa.gov`, `estimationology.com`, `teachingchildrensbooks.com`,
  `mathedinsight.com`, `miriammatthes.com`, `ireadlightly.com`,
  `theindigebrief.org`, `culturaclassroom.org`, `pearsoneducation.com`,
  `irasscience.org`, `greatergoodinaction.org`, `sensemaking.mit.edu`) and
  **one seed typo fixed** (`openmidle.com` → `openmiddle.com`, confirmed
  live and a real match for its row's title/description). 288 → 274 rows.
  27 pytest still pass. A further ~30 rows still flag `unreachable` for
  reasons that are real but not "confirmed dead" (broken/misconfigured
  TLS, content that moved to an unrelated domain, or just flaky DNS) —
  left alone pending a real curation pass, not dropped on a guess.
  **`render.yaml` rewired for a real Render deploy** (was scaffolded but
  never wired to build the frontend): `buildCommand` now also runs
  `scripts/build_frontend.py` so the one Render web service serves the
  built SPA + API from the same origin, same shape as the Vercel deploy
  but on Render's disk instead of a serverless `/tmp` that resets every
  cold start (mirrors how Atlas deployed to Render the same week).
  Verified end-to-end locally: built the frontend, booted the app against
  a fresh `sqlite:///./data/almanac.db`-style path, confirmed the seed
  bootstraps once (288→274 rows show up via `/api/stats`), confirmed a
  restart against the same file does not re-seed or duplicate rows, and
  confirmed `/` serves the built SPA.
- **Render deploy went live (2026-09-16):** the user created the Render
  web service from this repo and set `ADMIN_PASSWORD` in its dashboard —
  **live at https://almanac-0uue.onrender.com**. To verify it worked,
  the user generated a Render personal API key (`RENDER_API_KEY` in
  `backend/.env.local`, gitignored, never in chat) so a session could
  call Render's API directly. That verification caught a real
  production bug: **`/api/auth-status` wasn't in `OPEN_PATHS`**, so it
  401'd for any unauthenticated request — but that endpoint's whole job
  is telling an *unauthenticated* frontend whether to show the login
  screen (`App.tsx` calls it before any login attempt). The 401 made
  `fetchAuthStatus()` throw before reading `gate_enabled`, and
  `App.tsx`'s catch-all set `authed = true` without ever rendering
  `LoginGate` — so the moment `ADMIN_PASSWORD` went live, the site was
  broken for anyone without a cookie: no way to log in, every real page
  silently 401ing underneath a UI that looked fine. Fixed (`app/auth.py`
  now includes `/api/auth-status` in `OPEN_PATHS`), covered by a new
  `tests/test_auth.py` (5 tests — gate dormant/active, protected-route
  blocking, login, wrong password), and `tests/conftest.py`'s shared
  `client` fixture now uses `base_url="https://testserver"` (the login
  cookie is `Secure`, which a plain-`http://` test client silently never
  resends — matches how the app is actually always served, behind TLS).
  32 pytest total. Pushed; Render auto-deployed; reconfirmed live
  end-to-end (status check open, protected routes still gated, login
  works, authenticated data returns 274 rows).
- **Still to do**: decide whether to set `ANTHROPIC_API_KEY` on the
  Render deploy to turn on live capture; delete the now-superseded
  standalone `almanac` Vercel project (the live site is Render now;
  `almanac-api.vercel.app` is still up too); deepen the portal-only
  links.

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
  Atlas / LittleSprout-Rewards. Built and live on Render (2026-09-16).

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

## Never Read / Noise Zones (Do Not Scan)

To keep search and file reads fast, **never scan or read inside**:
- `backend/.venv/` and `frontend/node_modules/` — 9,780+ vendor files.
- `backend/static/` and `frontend/dist/` — generated SPA build bundles.
- `backend/data/*.db` and `backend/seed/almanac-seed.db` — binary SQLite databases (the seed `.db` is git-ignored, built at deploy).
- `backend/seed/almanac-seed.json` — 409-row JSON seed (about 530 KB); query via Python/API or read targeted slices rather than loading the entire file into context.

## Session Handoff (Last Worked On · Current State · Next Up)

- **Last Worked On:**
  - Added the Almanac editorial library shell: clearer brand/header, welcoming UDL-focused introduction, distinct navigation, calmer responsive surfaces, and improved card/filter hierarchy (2026-10-22; frontend-only).
  - Deepened 42 portal-only seed links into specific lesson/resource links with a live page-fetching pass (`5160846`).
  - Deployed live on Render (`https://almanac-0uue.onrender.com`) with `ADMIN_PASSWORD` auth gate enabled (`2026-09-16`).
  - Fixed production auth-gate bug (`/api/auth-status` added to `OPEN_PATHS` in `backend/app/auth.py` + 5 new tests in `tests/test_auth.py`; 32 pytest tests passing).
  - Fixed Windows SSL CA bundle in `scripts/check_links.py` via `certifi` and cleaned 14 confirmed-dead seed domains (`288 -> 274` curated resources).
- **Current State (2026-10-22):**
  - Live on Render (`https://almanac-0uue.onrender.com`), 409 curated UDL teaching resources, 47 passing backend pytest tests.
  - The seed `.db` left git. The Render build now makes it from the JSON.
  - Weekly link-check GitHub Action added. First run: use `workflow_dispatch`.
- **What Needs To Be Worked On Next:**
  1. Deepen portal-only/collection links (`granularity="collection"`) into specific lesson/unit links during future `/deep_curate` passes.
  2. Delete the superseded standalone `almanac` Vercel project when convenient.
  3. Keep live Claude-assisted capture (`ANTHROPIC_API_KEY`) dormant unless the owner explicitly approves API spend.

## Why this file exists

So a session opened in this repo has the real plan and constraints
without re-deriving them — mirrors `Atlas/CLAUDE.md`. The vault-side
`projects/almanac/context.md` in `my-brain` is a shorter cross-project
summary; this file is authoritative for Almanac's own code.
