# DnD AI Game Platform

AI-native platform for running tabletop role-playing games online.

Players and game masters will manage campaigns, characters, NPCs, story scenes,
dialogs, maps, tokens, and inventory. An AI agent will be able to change objects
inside the platform (not only reply with text).

## How the AI agent differs from a chat box

A normal chat returns text. Our agent will use **tools**: structured actions
such as "create NPC", "update character HP", or "move token on the map".
The backend applies those actions to real app data. That is the core product idea.

## Current status

**Stage 1 — foundation only.** Minimal FastAPI backend skeleton. No database,
auth, frontend UI, maps, or AI agent yet.

## Stack (planned / partial)

| Layer | Technology |
| --- | --- |
| Backend | Python, FastAPI, Uvicorn |
| Frontend | React / Next.js (later) |
| Database | TBD (later) |
| AI | LLM API + tool calling (later) |
| Realtime | WebSocket (later) |

## What exists now

- Project docs (`README.md`, `ROADMAP.md`, `docs/architecture.md`)
- Safe env template (`.env.example`)
- Backend app with `GET /` and `GET /health`
- Placeholder folders for frontend and tests

## Local run (Mac, Apple Silicon) — do this later

Do **not** run these yet if you are still on Stage 1 setup instructions that
forbid installs. When you are ready:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
```

Then open:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs
