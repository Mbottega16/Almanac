# Almanac — current state

*Snapshot, not a live link. Refresh manually as the project moves — it
will go stale otherwise. Created 2026-08-27.*

## What it is

Almanac is a searchable, aggregated database of teaching resources for
teachers, organized to make UDL planning easier. It is "Atlas for
teaching content": the same FastAPI + SQLAlchemy + SQLite / Vite + React
+ TS stack and shape as the Atlas link library, with a
teaching-specific data model.

A teacher searches a theme and gets content for it — lessons, readings,
videos, sims, activities — from many sources in one place, with a
per-theme **UDL coverage** readout so a multi-modal lesson is fast to
build.

Repo: `EduSystems-Code/Almanac` (private), cloned at `Desktop\Almanac`
(bare Desktop, same convention as Atlas/Chegga).

## Who it's for

Teachers building UDL-aligned lessons. (First user: the user, dogfooding
it the way Atlas is a personal tool.)

## Where it stands (2026-08-29)

**Live at https://almanac-api.vercel.app** — one Vercel Python service
serves the SPA + API. Auth gate and live Claude-assisted capture are both
built but dormant (flip on with `ADMIN_PASSWORD` / `ANTHROPIC_API_KEY`
env vars). On Vercel the DB is `/tmp` + auto-seeded from a committed
pre-built `almanac-seed.db`, so favorites don't persist across cold
starts — a persistent host (Render/`render.yaml` is ready) is the
follow-up. Scaffolded, tested (22 pytest), and seeded:
- Backend: `resources` + `tags` + fixed 3-row `udl_principles` model;
  full CRUD, faceted search
  (`q`/`subject`/`grade_band`/`resource_type`/`scope`/`publisher`/`cost`/`source_site`/`udl`/`tag`/`age`/`favorite`),
  `random`, `visit`, `favorite`, batch-upsert on `link`, faceted-count
  endpoints, `GET /api/udl-coverage`. 22 passing pytest tests.
- Frontend: Guided discovery swipe flow + Browse (theme search,
  Free/Paid toggle, **scope toggle** — Single lessons / Units / Full
  courses / Curricula — subject chips, grade/format/theme/age filters,
  UDL-principle toggles, view modes), a UDL coverage strip for theme
  searches, resource cards with cost badge + **scope badge** + publisher
  line + UDL pills + learning outcomes, "My Collection" panel, read-only
  Capture page. Builds clean.
- **Seed: 320 resources.** 289 one-off lessons + a 2026-08-29 pass of
  **31 full courses / commercial curricula** (Illustrative Mathematics,
  OpenSciEd, EL Education, Amplify, Great Minds, Zearn, Fishtank, Open
  Up Resources, CommonLit 360, Carnegie Learning, Bridges, PLTW,
  iCivics, Code.org / Khan Academy courses, MIT OCW, Crash Course, TERC,
  Bootstrap), each with `scope` + `publisher`. `Almanac/CLAUDE.md` is
  authoritative for live counts.
- **Lesson vs. curriculum (2026-08-29):** `scope` column —
  `lesson` (default) / `unit` / `course` / `curriculum` — plus a
  `publisher` string. Lets a teacher ask for a one-off lesson or a whole
  program to run from. Commercial curriculum is in scope for the
  library; still a pointer index (link the landing page, never mirror
  materials).

## Decisions already made

- Same stack/shape as Atlas on purpose; divergences are the
  teaching-specific columns (`subject`, `grade_band`, `resource_type`,
  `scope`, `publisher`, `cost` free/paid/freemium, `source_site`,
  `license`, `standards`, `description_source`), the `udl_principles`
  join, and the `udl-coverage` endpoint + strip.
- `scope` (`lesson`/`unit`/`course`/`curriculum`) is separate from
  `resource_type` (the format). Commercial curriculum is intentionally
  in scope — set `publisher`, `scope`, and an honest `cost`.
- Content guardrail: pointer index, not a content mirror — store link +
  title + short (attributed or generated) description + metadata, always
  link back, never the full resource body. No bulk scraping.
- Two-phase capture, identical to Atlas: session-assisted now, live
  Anthropic API later (gated on key + sign-off).
- Deploy target: Render (backend) + Vercel (frontend), free tiers —
  **needs explicit sign-off**, going public is the gate.
- Auth gate (shared `ADMIN_PASSWORD` + signed cookie) built before any
  deploy.

## What happens next

1. Move to a persistent database (Render or Vercel Postgres) so
   favorites/visits survive cold starts.
2. Turn on the auth gate / live capture by setting `ADMIN_PASSWORD` /
   `ANTHROPIC_API_KEY` env vars, when wanted.
3. More capture passes — thin subjects (Arts, World Languages, SEL,
   PreK) and more `course`/`curriculum` entries (state-adopted lists,
   subject-specific programs).
4. Deepen the ~112 portal-only lesson links (real page-fetching pass).
5. Delete the superseded standalone `almanac` Vercel project.

## Why this file exists

So a session opened in this vault can answer "where does Almanac stand?"
without re-reading its own `CLAUDE.md`. For real work on the app,
`Almanac/CLAUDE.md` is authoritative — this is a summary.
