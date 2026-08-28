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
  On Vercel `DATABASE_URL` is `/tmp` and the app auto-seeds from
  `backend/seed/almanac-seed.json` on an empty DB — so cold starts are
  never blank, but favorites/visits don't survive a cold start. A
  persistent host (Render — `render.yaml` is ready — or Vercel Postgres)
  is the real fix. Only the canonical `almanac-api.vercel.app` is public;
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
  `subject`, `grade_band`, `resource_type`, `cost` (free/paid/freemium),
  `price_note`, `source_site`, `license`, `standards`,
  `description_source`), real many-to-many `tags` **and** a fixed
  3-row `udl_principles` join. Full CRUD, search/filter
  (`q`/`subject`/`grade_band`/`resource_type`/`cost`/`source_site`/`udl`/`tag`/`favorite`),
  `random`, `visit`, `favorite`, batch-upsert on `link`
  (`POST /api/resources/batch`), faceted-count endpoints, and
  `GET /api/udl-coverage`. 15 passing pytest tests (in-memory SQLite).
- **Frontend**: Browse page (theme search, Free/Paid toggle, subject
  chips, grade/format/theme selects, three UDL-principle toggles,
  grid/list/large view modes persisted in `localStorage`), a **UDL
  coverage strip** shown for any theme search, resource cards with cost
  badge + UDL pills, a "My Collection" slide-in panel, and a read-only
  Capture page. Type-checks and builds clean.
- **Seed**: a first curated batch imported from well-known free/OER +
  notable paid repositories (CommonLit, PhET, ReadWorks, Khan Academy,
  PBS LearningMedia, Illustrative Mathematics, EngageNY, Code.org,
  Smithsonian, Library of Congress, NASA, CAST UDL Guidelines, Goalbook,
  Facing History, Learning for Justice, Zinn Education Project, TpT
  (paid), BrainPOP (paid), etc.). 17 passing pytest tests.
- **Still to do**: activate the auth gate + capture (set the env vars),
  move to a persistent DB, top up thin subjects (Arts, World Languages,
  SEL, PreK), delete the dead `almanac` Vercel project.

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
