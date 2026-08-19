# Roadmap — DnD AI Game Platform

Sequential stages. Finish one before starting the next.

## 1. Foundation

This phase establishes the backend structure, configuration, observability, error boundaries, tests, and development standards. After completion, the project has a reliable FastAPI foundation on which every product feature can be built.

- [ ] 1.1 Audit проекта
- [ ] 1.2 Virtual Environment
- [ ] 1.3 Dependencies
- [ ] 1.4 FastAPI
- [ ] 1.5 Configuration
- [ ] 1.6 Application Structure
- [ ] 1.7 Logging
- [ ] 1.8 Error Handling
- [ ] 1.9 Basic Tests
- [ ] 1.10 Documentation and Standards

## 2. Characters

This phase defines the character domain and connects it to validated API and persistence layers. After completion, clients can reliably create, read, update, delete, and test persistent characters.

- [x] 2.1 Character Domain Model
- [x] 2.2 Ability Scores
- [x] 2.3 Health
- [x] 2.4 Inventory
- [x] 2.5 Skills
- [ ] 2.6 Character API Schemas
- [ ] 2.7 Character CRUD API
- [ ] 2.8 Persistence
- [ ] 2.9 Validation and Error Handling
- [ ] 2.10 Character Tests

## 3. AI Tools

This phase isolates LLM providers behind services and creates a validated pipeline for structured tool execution. After completion, the AI agent can safely propose and perform approved changes to game objects.

- [ ] 3.1 LLM Configuration
- [ ] 3.2 LLM Service
- [ ] 3.3 AI Provider Abstraction
- [ ] 3.4 Tool Schema
- [ ] 3.5 Character Tools
- [ ] 3.6 Game Object Tools
- [ ] 3.7 Tool Validation
- [ ] 3.8 Safe Execution Pipeline
- [ ] 3.9 Agent Service
- [ ] 3.10 AI Integration Tests

## 4. Story and Dialogs

This phase introduces persistent story entities, conversations, and structured narrative state. After completion, campaigns can contain scenes, NPCs, dialog history, and AI-assisted narration.

- [ ] 4.1 Campaign Model
- [ ] 4.2 Scene Model
- [ ] 4.3 NPC Model
- [ ] 4.4 Message Model
- [ ] 4.5 Conversation History
- [ ] 4.6 Scene API
- [ ] 4.7 Dialog API
- [ ] 4.8 Structured State Updates
- [ ] 4.9 Agent Narration
- [ ] 4.10 Story and Dialog Tests

## 5. Maps and Tokens

This phase models spatial game state and exposes controlled map operations through backend and frontend interfaces. After completion, users can place linked tokens, move them according to rules, and share map state.

- [ ] 5.1 Map Model
- [ ] 5.2 Map API
- [ ] 5.3 Token Model
- [ ] 5.4 Token Positions
- [ ] 5.5 Character/NPC Token Links
- [ ] 5.6 Movement Rules
- [ ] 5.7 Visibility Rules
- [ ] 5.8 Map State API
- [ ] 5.9 Frontend Map Integration
- [ ] 5.10 Map and Token Tests

## 6. Multiplayer

This phase adds realtime sessions, synchronized state, recovery, and role-based game permissions. After completion, a GM and multiple players can participate safely in the same live game.

- [ ] 6.1 Game Session Model
- [ ] 6.2 Player Model
- [ ] 6.3 Session API
- [ ] 6.4 WebSocket Infrastructure
- [ ] 6.5 State Synchronization
- [ ] 6.6 Player Roles
- [ ] 6.7 GM Permissions
- [ ] 6.8 Player Permissions
- [ ] 6.9 Reconnection and Session Recovery
- [ ] 6.10 Multiplayer Tests

## 7. SaaS and Monetization

This phase adds identity, authorization, tenancy, billing, usage controls, and production operations around the application. After completion, the platform can be deployed, monitored, packaged, and offered as a controlled SaaS product.

- [ ] 7.1 Authentication
- [ ] 7.2 Users
- [ ] 7.3 Organizations / Workspaces
- [ ] 7.4 Authorization
- [ ] 7.5 Subscription Model
- [ ] 7.6 Billing Integration
- [ ] 7.7 AI Usage Tracking
- [ ] 7.8 Usage Limits
- [ ] 7.9 Deployment and Monitoring
- [ ] 7.10 Product Packaging
