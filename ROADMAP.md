# Roadmap — DnD AI Game Platform

Sequential stages. Finish one before starting the next.

## 1. Foundation

- Project structure, docs, config templates
- Minimal FastAPI backend (`/`, `/health`)
- Local run workflow, basic tests, coding conventions

## 2. Characters

- Character model and CRUD API
- Stats, inventory hooks, persistence
- Simple validation and error handling

## 3. AI tools

- LLM client behind a service layer
- Tool definitions the agent can call (create/update game objects)
- Safe execution path: model proposes action → backend validates → data changes

## 4. Story and dialogs

- Campaigns, scenes, NPC dialogs
- Message history tied to scenes
- Agent-assisted narration that still writes structured state

## 5. Maps and tokens

- Map entities and token positions
- Movement and visibility rules (basic)
- Link tokens to characters / NPCs

## 6. Multiplayer

- Sessions for multiple players
- WebSocket updates for shared state
- Roles: GM vs player permissions

## 7. SaaS and monetization

- Auth, orgs/workspaces, billing hooks
- Usage limits for AI calls
- Deploy, monitoring, and product packaging
