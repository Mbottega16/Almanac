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

## Where it stands (2026-08-28)

**Live at https://almanac-api.vercel.app** — one Vercel Python service
serves the SPA + API. Auth gate and live Claude-assisted capture are both
built but dormant (flip on with `ADMIN_PASSWORD` / `ANTHROPIC_API_KEY`
env vars). On Vercel the DB is `/tmp` + auto-seeded, so favorites don't
persist across cold starts — a persistent host (Render/`render.yaml` is
ready) is the follow-up. Scaffolded, tested (17 pytest), and seeded:
- Backend: `resources` + `tags` + fixed 3-row `udl_principles` model;
  full CRUD, faceted search, `random`, `visit`, `favorite`,
  batch-upsert on `link`, `GET /api/udl-coverage`. 15 passing pytest
  tests.
- Frontend: Browse (theme search, Free/Paid toggle, subject chips,
  grade/format/theme filters, UDL-principle toggles, view modes), a UDL
  coverage strip for theme searches, resource cards with cost badge +
  UDL pills, "My Collection" panel, read-only Capture page. Builds
  clean.
- First curated seed batch imported (well-known free/OER + notable paid
  repositories). The DB and `Almanac/CLAUDE.md` are authoritative for
  the live count — not kept live here.
- Not yet built: auth gate, deployment, live Claude-assisted capture.

## Decisions already made

- Same stack/shape as Atlas on purpose; divergences are the
  teaching-specific columns (`subject`, `grade_band`, `resource_type`,
  `cost` free/paid/freemium, `source_site`, `license`, `standards`,
  `description_source`), the `udl_principles` join, and the
  `udl-coverage` endpoint + strip.
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
3. More capture passes — start with the thin subjects (Arts, World
   Languages, SEL, PreK).
4. Delete the superseded standalone `almanac` Vercel project.

## Why this file exists

So a session opened in this vault can answer "where does Almanac stand?"
without re-reading its own `CLAUDE.md`. For real work on the app,
`Almanac/CLAUDE.md` is authoritative — this is a summary.
