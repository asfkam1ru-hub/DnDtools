# Development Workflow

Automation-first lifecycle for DnDpetProject.

## Lifecycle

```
main
  ↓
feature branch
  ↓
task spec
  ↓
AI implementation
  ↓
make audit
  ↓
human architecture review
  ↓
commit
  ↓
push
  ↓
GitHub CI
  ↓
PR
  ↓
merge
  ↓
clean main
```

## Branch conventions

| Prefix | Use |
| --- | --- |
| `feat/<step>-<slug>` | Numbered roadmap feature work |
| `fix/<slug>` | Bug fixes |
| `chore/<slug>` | Engineering / docs / automation |

Examples:

- `feat/3.9-agent-service`
- `feat/4.1-campaign-model`
- `chore/dev-automation-foundation`

Create feature branches with:

```bash
make feature STEP=3.9 SLUG=agent-service
# or
./scripts/start_feature.sh 3.9 agent-service
```

Requirements: clean working tree, local `main` aligned with `origin/main`.

## Daily quality commands

```bash
make test
make compile
make architecture
make check
make audit
make progress
make ci
```

Install repository-local hooks once per clone:

```bash
make hooks
```

Hooks:

- **pre-commit** — `git diff --check --cached`, compile, architecture
- **pre-push** — `make ci`

## Rules

- Do not land feature changes directly on `main`.
- Do not mark numbered ROADMAP steps complete without verification.
- Do not commit or push unless explicitly requested.
- Prefer task specs under `tasks/` as the AI execution contract.
