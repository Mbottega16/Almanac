# Almanac — rules & map (read this first)

A searchable, aggregated database of teaching resources for teachers,
organized to make **UDL (Universal Design for Learning)** planning
easier. Backed by FastAPI + SQLAlchemy + SQLite, with a Vite + React +
TypeScript frontend. Deliberately the same stack and shape as **Atlas**
(the personal link/tool library) — Almanac is "Atlas for teaching
content." See `README.md` for the quickstart.

**History:** [`HISTORY.md`](HISTORY.md), newest first — the build record from 2026-08-28 on.
Read it when a task touches past work. **Business side:** the owner's my-brain vault,
`projects/almanac/context.md`. **Repo:** `Mbottega16/Almanac` (**public**; the old
`EduSystems-Code` URL redirects) — PC `~/OneDrive/Desktop/Almanac`, Mac `projects/almanac/app`.

**Warning:** Render uses `rootDir: backend`. A push that changes files under `backend/` redeploys the live site. Other pushes do not. Ask the owner before you push a `backend/` change.

## What this is

- **What:** a teacher searches a **theme** and immediately gets content for it:
  lessons, readings, videos, simulations, activities — sourced from many
  sites, gathered into one collective library. For any theme, the app
  shows **UDL coverage**: how many matching resources support each of the
  three principles (Engagement / Representation / Action & Expression) and
  in which formats, so gaps are obvious and a multi-modal lesson is fast
  to assemble.
- **For:** teachers building UDL-aligned lessons. The owner is the first user.
- **Platform:** one Render web service on the free plan, <https://almanac-0uue.onrender.com>,
  behind the `ADMIN_PASSWORD` gate. Free; no API spend.
- **What "done" looks like (owner, 2026-10-24):** sort lessons by subject and age, pull
  consistent lessons and activities, and adapt a lesson with UDL moves (Lesson Studio,
  PR #5). These lesson tools are built here, not in Atlas.
- **Direction:** thousands to tens of thousands of resources, grown by the vault's intake
  engine through reviewed harvest PRs.

## Settled decisions (don't re-argue)

- **Same stack/shape as Atlas on purpose** — mirror its file layout,
  service patterns, and two-phase capture. Divergences: the
  teaching-specific columns, the `udl_principles` join, and the
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
- **Two tracks via `audience` (2026-09-19):** `students` (lesson planning) and `educators`
  (professional learning: PD courses, webinars, CEUs) — a separate axis from `scope`. PD rows
  carry `credit_type` / `credit_hours` / `credit_note`.
- **Credit claims are recorded as the page states them**, with the qualifier in
  `credit_note` (who grants it, what it costs, that a district decides renewal). Overstating
  one could cost a teacher a license renewal.
- **No SEL/mental-health content framed as treatment (owner, 2026-09-18)** — "this isn't a
  social worker's resource, it's an educator's resource." Early-childhood classroom SEL
  (feelings vocabulary, calm-down corners) is fine.
- **Search is an SQLite FTS5 index (2026-09-19)** in `app/services/search.py` — coverage of
  query terms first, BM25 within that. Moving to Postgres means replacing that one seam with
  `tsvector`.
- **Lesson and unit UDL tags are a labeled default (2026-10-24):** all three principles,
  rationale "default". A keyword rule did worse on the 151 hand-tagged lessons and units, so
  none ships. Change it in the vault engine's `UDL_BY_FORMAT`, not here, and only for a method
  that beats the default on those 151.
- **Quick-capture is two-phase**, exactly like Atlas:
  - *Now:* a Claude Code session rooted here researches pasted links /
    named sites via `WebFetch`/`WebSearch` and saves via
    `POST /api/resources/batch`. No API key, no spend. `CapturePage.tsx`
    is a read-only "recently added" view.
  - *Later (needs explicit sign-off + a real `ANTHROPIC_API_KEY`):* a
    `POST /api/capture/research` endpoint does live research and returns
    **draft, unsaved** resources; a second explicit action commits them
    via the batch endpoint. **The owner has said no API spend (2026-09-18)**, so it stays off.
- **Auth gate:** single `ADMIN_PASSWORD` + `itsdangerous`-signed session cookie
  (`SameSite=None; Secure`) gating the whole app, mirroring Atlas / LittleSprout-Rewards.
  Live on Render since 2026-09-16.
- **Favorites are cut (2026-10-24, PR #4).** A shared list needs a persistent database, and
  the owner will not pay for one. `test_favorites_are_gone` keeps them gone. Do not bring them
  back without a free way to store them.

## How it's built

- **The library is `backend/seed/almanac-seed.json`** (about 1,100 resources). Git
  tracks it. The database is a build artifact.
- **The deploy builds the database.** `render.yaml`'s `buildCommand` runs
  `scripts/build_seed_db.py`, which writes `backend/seed/almanac-seed.db`
  (git-ignored). On start, `app.db.seed.ensure_seed_db_file()` copies that
  file into place. If it is missing, the app loads the JSON (about 6 s at 409
  rows). Build time grows with the library: about 13 ms per row.
- **Backend:** a `resources` model (Atlas's `Entry` fields plus `subject`, `grade_band`,
  `age_min`/`age_max`, `resource_type`, `scope`, `publisher`, `audience`, `granularity`
  (specific/collection), `duration_minutes`, `materials`, `learning_outcomes`, `cost`,
  `price_note`, `source_site`, `license`, `standards`, `evidence` (write-only),
  `udl_rationale`, `link_status`, `description_source`), many-to-many `tags`, a `standards`
  join (parsed CCSS/NGSS/C3 codes), and the fixed 3-row `udl_principles` join. Faceted search,
  batch-upsert on `link` (canonicalized on write, `services/links.py`), `GET /api/udl-coverage`,
  `GET /api/stats`, `/api/standards`.
- **Frontend:** a discovery front door (#9, 2026-10-29): a plain-language sentence box whose
  filters show as removable chips, three doors (who / what / how much time) with live counts,
  and curated situation paths. Browse (theme search; Free/Paid, scope, subject,
  grade/format/theme/age/standard filters, UDL toggles and "Class-ready only" behind a
  "Refine" toggle, active filters as chips), the UDL coverage strip, resource cards with cost/scope/publisher/UDL
  pills and "link may be broken" badges, a Stats page (subject×UDL heatmap), and a read-only
  Capture page.
- **Link health runs itself.** `.github/workflows/link-check.yml` runs
  `scripts/check_links.py --seed --write-status` every Monday. It writes
  `backend/seed/link-status.json` (consecutive real-4xx failures per link)
  and sets `link_status` on the seed rows. A link is `dead` only after two
  failures in a row. The Action opens a `link-check/<date>` branch and keeps one open
  "Dead links" issue.
- **Growth:** the vault's `workflows/library/library.js` harvests (sitemaps, staged candidates,
  portal deepening) and opens `harvest/<date>` PRs; a person merges them.

## Commands & Verification

- **Tests:** `cd backend && .venv/Scripts/python -m pytest` (59 pass; 61 with PR #16). `cd frontend && npm run build`.
- **Rebuild the seed DB** after the JSON changes: `scripts/build_seed_db.py`.
- **Links:** `scripts/check_links.py` (`--json`/`--write`), `scripts/flag_dead_links.py`,
  `scripts/find_near_dupes.py` (soft duplicates for review).
- **Portal backlog** (from the vault): `node workflows/library/library.js portal next --n 8`,
  then follow `skills/deep_portal/SKILL.md`.

## Never Read / Noise Zones (Do Not Scan)

To keep search and file reads fast, **never scan or read inside**:
- `backend/.venv/` and `frontend/node_modules/` — 9,780+ vendor files.
- `backend/static/` and `frontend/dist/` — generated SPA build bundles.
- `backend/data/*.db` and `backend/seed/almanac-seed.db` — binary SQLite databases (the seed `.db` is git-ignored, built at deploy).
- `backend/seed/almanac-seed.json` — 1,405-row JSON seed (2,180 with PR #17; about 3 MB, 2-space indent); query via Python/API or read targeted slices rather than loading the entire file into context.

## Rules & Gotchas

**Content / copyright guardrail (do not cross).** Almanac is a **pointer index**, not a content
mirror. For each resource store only: the `link`, a `title`, a **short** factual description (a
brief attributed excerpt *or* a generated summary — set `description_source` accordingly), and
metadata. Always link back to the source. **Never** store a resource's full body (worksheet
text, full lesson plan, video transcript). Record `license` when known. For paid marketplaces
(Teachers Pay Teachers, etc.), link the listing/category page and set `cost=paid`. Harvesting
through the vault engine is allowed (owner, 2026-10-22), but robots.txt, Crawl-delay, rate
limits and pointer-only records still apply.

- **Merging is the owner's call.** A session merges a PR only on the owner's explicit go-ahead
  (`gh pr merge N --squash`, the repo's style; it worked 2026-10-25 — earlier attempts and
  2026-11-06 were blocked by the permission check). Check `git merge-tree` first. Merging
  anything under `backend/` redeploys the live site. A PR stacked on another needs
  **Create a merge commit** for the lower one, or the upper one conflicts.
- **The Vercel `backend` check can fail on new PRs. That check is noise.** Render is the live
  site; `almanac-api.vercel.app` is an old fallback.
- **Take URLs from `portal links`** (real hrefs, renders JavaScript pages). A summarizing fetch
  tool once invented a host for CommonLit — 5 dead links, caught by the page check.
- **loc.gov answers HTTP 429** (a Cloudflare challenge) after about 27 requests: retry in small
  batches a day apart. On 2026-11-06 its HTML pages answered 403 (the challenge) at once, but
  the `?fo=json` form the engine reads still answered.
- **Write the seed with a 2-space indent and a final newline** (`JSON.stringify(rows, null, 2)`,
  or `json.dumps(rows, indent=2, ensure_ascii=False)`). The engine and the link check both do.
  Any other indent rewrites the whole file in the diff. **PBS LearningMedia's bare domain has an expired TLS certificate** and
  the engine stores links without `www.`, so PBS pages are held until that is decided.
- **The URL check can't see duplicates under old slugs** (two Khan courses had older URL slugs).
- `check_links.py` uses `certifi`'s CA bundle — Windows Python's `ssl` has none, which once
  misclassified real sites as unreachable.
- After pulling the favorites cut, delete any old local `backend/data/almanac.db`; deploys
  rebuild the database from the seed.
- **This repo is public:** keep private business notes in the owner's vault, not here.

## Session Handoff (Last Worked On · Current State · Next Up)

- **Last Worked On (2026-11-06, PC):**
  - The owner dropped the lesson and unit UDL default. PR #15 clears it from 280 rows and
    puts back the seed's 2-space indent. The vault engine no longer writes the default.
  - PR #16: the weekly link check skips Almanac Originals. PR #13 had marked all 232 of them
    `unreachable`, because no web request can open an `almanac-original://` link.
  - PR #17, stacked on #15: +775 entries. ReadWorks 299, TeachEngineering 315 (lessons,
    activities, units), Math Is Fun 135, portal batch 002 (NASA and National Geographic, 10),
    and a hand-picked gap batch of 17 graded Math and Social Studies rows. One dead
    TeachEngineering row (moved link) goes in the same PR.
  - Local `master` held one unpushed crew commit (accessibility toggles, `ecef7cf`). It now
    sits on branch `crew/a11y-toggles-unpushed`, and `master` matches GitHub.
- **Current State (2026-11-06):**
  - Live on Render from `master`: 1,405 rows, with the discovery overhaul (#9) and the PreK
    Originals (#12). The live rows still carry the old lesson and unit UDL default.
  - Open PRs: #13 (link check 2026-11-02, out of date), #15, #16, #17. A session's
    `gh pr merge` was blocked by the permission check: the owner merges.
  - Tests: 59 pass on `master`, 61 with #16. The seed database builds with #17 applied
    (2,181 rows in, 2,179 stored: the 2 known LOC link pairs).
- **Next Up:**
  1. The owner merges #15 with **Create a merge commit** (a squash would conflict with #17),
     then #17, then #16. Close #13: its real findings are 2 dead Twinkl links, 5 unreachable
     links and 1 recovered link, and next Monday's run replaces it.
  2. Portal backlog: 126 to do, 6 assigned and blocked (`portal next --n 8`).
  3. LOC: 111 pages parked. HTML pages get a Cloudflare challenge; the `?fo=json` form
     answered 11 of 14 requests. Retry about 20 a day (`requeue` now keeps their titles).
  4. Thinnest graded cells after #17: Math 3-5 (22) and 9-12 (16); Social Studies K-2 (13),
     3-5 (8) and 6-8 (12); Arts and PE/Health in every band.
  5. 12 local `crew/*` branches on the PC wait for review. None is pushed.
  6. Later: the teacher upload/pull phase (not started), a keep-alive ping, and a persistent
     database before about 20,000 rows.

