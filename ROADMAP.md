# Roadmap — DnD AI Game Platform

## Phase 1 — Core Platform Foundation

Sequential stages. Finish one before starting the next.

## 1. Foundation

This phase establishes the backend structure, configuration, observability, error boundaries, tests, and development standards. After completion, the project has a reliable FastAPI foundation on which every product feature can be built.

- [x] 1.1 Audit проекта
- [x] 1.2 Virtual Environment
- [x] 1.3 Dependencies
- [x] 1.4 FastAPI
- [x] 1.5 Configuration
- [x] 1.6 Application Structure
- [x] 1.7 Logging
- [x] 1.8 Error Handling
- [x] 1.9 Basic Tests
- [x] 1.10 Documentation and Standards

## 2. Characters

This phase defines the character domain and connects it to validated API and persistence layers. After completion, clients can reliably create, read, update, delete, and test persistent characters.

- [x] 2.1 Character Domain Model
- [x] 2.2 Ability Scores
- [x] 2.3 Health
- [x] 2.4 Inventory
- [x] 2.5 Skills
- [x] 2.6 Character API Schemas
- [x] 2.7 Character CRUD API
- [x] 2.8 Persistence
- [x] 2.9 Validation and Error Handling
- [x] 2.10 Character Tests

## 3. AI Tools

This phase isolates LLM providers behind services and creates a validated pipeline
for structured tool execution. After completion, the AI agent can safely propose
and perform approved changes to game objects.

Entity-specific tools beyond Character are added only after their corresponding
domain models and persistence exist. Phase 3 builds the shared tool infrastructure
using Character Tools as the first concrete implementation.

- [x] 3.1 LLM Configuration
- [x] 3.2 LLM Service
- [x] 3.3 AI Provider Abstraction
- [x] 3.4 Tool Schema
- [x] 3.5 Character Tools
- [x] 3.6 Tool Registry and Binding
- [x] 3.7 Tool Validation
- [x] 3.8 Safe Execution Pipeline
- [x] 3.9 Agent Service
- [x] 3.10 AI Integration Tests

## 4. Existing Core Alignment

This stage aligns the already implemented Character and AI-tool integration
with the new multi-system product model without rebuilding the completed
Stages 1–3 foundation. After completion, the existing D&D-specific character
mechanics are preserved inside a system-specific profile boundary, while the
base Character becomes system-independent and ready for future RPG systems.

- [x] 4.1 Current Core Delta Audit
- [ ] 4.2 Base Character Domain Refactor
- [ ] 4.3 D&D Character Profile Extraction
- [ ] 4.4 Character Persistence Refactor
- [ ] 4.5 Character API and Schemas Alignment
- [ ] 4.6 Character Tools Alignment
- [ ] 4.7 Character Lifecycle Alignment
- [ ] 4.8 Character Import / Export
- [ ] 4.9 Existing Character Tests Migration
- [ ] 4.10 Core Alignment Integration Tests

## Development Automation

Engineering infrastructure for quality gates, AI coding workflow, and CI.
These checklist items are **excluded** from the MVP numbered-step denominator
used by `make progress` / `scripts/project_status.py`.

- [x] Unified Makefile quality gates
- [x] Architecture checks
- [x] Repository AI rules
- [x] Automated progress reporting
- [x] Git hooks
- [x] GitHub Actions CI
- [x] Definition of Done
- [x] Feature branch workflow
- [x] Task specification workflow
