# Almanac

A searchable, aggregated database of teaching resources — lessons,
activities, worksheets, videos, sims — pulled from many sites into one
library. Search a **theme** ("fractions", "the water cycle", "the Civil
Rights Movement") and get usable content for it, with every UDL
principle (Engagement / Representation / Action & Expression) in view so
a lesson can offer multiple means of each.

Same stack and shape as Atlas: FastAPI + SQLAlchemy + SQLite backend,
Vite + React + TypeScript frontend. Full plan and phasing: see
`CLAUDE.md`, or the vault-side summary at `projects/almanac/context.md`
in the `my-brain` repo.

## Quickstart (local dev)

Backend:
```
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Frontend (separate terminal):
```
cd frontend
npm install
npm run dev
```

`vite.config.ts` proxies `/api` to `localhost:8000` in dev, so open the
Vite dev server URL directly — no CORS setup needed.

## Tests

```
cd backend
.venv\Scripts\python -m pytest
```

## Adding resources

Paste raw links — or the name of a site to pull from — into a Claude
Code session rooted in this repo. It researches and tags each one
(subject, grade band, format, free/paid, UDL principles, a short
description) and saves them via `POST /api/resources/batch`. A direct
paste-box UI arrives with Phase 7 (live Claude-assisted capture), which
is gated on an approved `ANTHROPIC_API_KEY`.
