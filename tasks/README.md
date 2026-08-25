# Task specifications

Task specs are the **execution contract** for an AI coding agent.

## Roles

| Artifact | Role |
| --- | --- |
| `ROADMAP.md` | Product order and numbered MVP scope |
| `tasks/...` | Implementation scope for one step |
| `.cursor/rules/` | Permanent constraints |
| `docs/DEFINITION_OF_DONE.md` | Completion checklist |

Numbered roadmap steps define *what comes next*.
A task file defines *exactly what may be implemented* for that step.

## Layout

```
tasks/
  README.md
  TEMPLATE.md
  phase-3/
    3.9-agent-service.md
```

## Usage

1. Create/update a task file from `TEMPLATE.md`.
2. Start an isolated branch (`make feature STEP=... SLUG=...`).
3. Point the coding agent at the task file + relevant rules.
4. Verify with `make audit`.
5. Update numbered ROADMAP completion only after human confirmation.
