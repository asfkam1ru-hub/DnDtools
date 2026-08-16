# Architecture (draft)

High-level components for later stages. Stage 1 only implements a thin backend.

## Frontend

React / Next.js UI for campaigns, characters, maps, and chat/agent controls.
Talks to the backend over HTTP (and later WebSocket).

## Backend

FastAPI application: REST API, validation, business rules, auth (later),
and orchestration of AI tool calls. Entry point today: `backend/app/main.py`.

## Database

Persistent store for users, campaigns, characters, scenes, inventory, maps,
and tokens. Not chosen or created in Stage 1.

## AI agent

LLM-backed agent that plans actions from player/GM input. It does not only
return prose — it proposes structured tool calls.

## Agent tools

Backend functions the agent may invoke (e.g. create NPC, update HP, move token).
Every tool runs through server-side validation before mutating data.

## WebSocket

Realtime channel so all clients in a session see state changes (moves, dialog,
agent actions) without polling.
