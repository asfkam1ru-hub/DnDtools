# Stage 4 — Existing Core Alignment

**Phase 1 — Core Platform Foundation** (approved roadmap)

Stages 1–3 (Foundation, Characters, AI Tools) are completed historical work.
Do not rewrite their completion state.

Stage 4 aligns the already-implemented Character stack and AI-tool integration
with the new multi-system product model:

```
GenericCharacter (system-independent identity / lifecycle / ownership)
  + 0..N CharacterSystemProfile (platform relation per game_system_id)
    + system-specific mechanics (DndCharacterProfile today)
```

## Approved sub-steps (dependency order)

| Step | Task spec | Goal |
| --- | --- | --- |
| 4.1 | [4.1-current-core-delta-audit.md](4.1-current-core-delta-audit.md) | Formal audit: current core vs target invariants |
| 4.2 | [4.2-base-character-domain-refactor.md](4.2-base-character-domain-refactor.md) | System-independent base Character domain |
| 4.3 | [4.3-dnd-character-profile-extraction.md](4.3-dnd-character-profile-extraction.md) | D&D mechanics in system-specific profile |
| 4.4 | [4.4-character-persistence-refactor.md](4.4-character-persistence-refactor.md) | Split persistence + profile uniqueness |
| 4.5 | [4.5-character-api-schemas-alignment.md](4.5-character-api-schemas-alignment.md) | HTTP/schemas alignment |
| 4.6 | [4.6-character-tools-alignment.md](4.6-character-tools-alignment.md) | CharacterTools → profile boundary |
| 4.7 | [4.7-character-lifecycle-alignment.md](4.7-character-lifecycle-alignment.md) | ACTIVE / ARCHIVED end-to-end |
| 4.8 | [4.8-character-import-export.md](4.8-character-import-export.md) | Versioned import / export foundation |
| 4.9 | [4.9-existing-character-tests-migration.md](4.9-existing-character-tests-migration.md) | Migrate character tests; retire legacy monolith |
| 4.10 | [4.10-core-alignment-integration-tests.md](4.10-core-alignment-integration-tests.md) | End-to-end alignment + architecture guards |

## Explicitly deferred (not in current roadmap)

Campaign, CampaignSystem, CampaignMembership, CampaignCharacter, User
persistence, roles authorization, permissions, GameContext, GameRuntime,
Pathfinder, maps, multiplayer, SaaS.

## Partial work already in worktree

Uncommitted domain-boundary code (`backend/app/domain/*`,
`backend/app/game_systems/dnd/*`, `tests/test_character_domain_boundaries.py`)
predates this numbering. See **4.1 audit** for mapping to 4.2 / 4.3 / 4.7.
Do not mark those steps complete until human review after full scope is done.

## Workflow

1. One sub-step per branch when possible.
2. `make audit` before claiming done.
3. Human architecture review before marking any ROADMAP checkbox complete.
