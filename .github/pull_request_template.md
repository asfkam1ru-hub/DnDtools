## Pull Request

**Roadmap/task step:**

**Summary:**

**Tests:**

**Architecture notes:**

---

### Checklist

#### Scope
- [ ] Change matches the stated roadmap/task step
- [ ] No unrelated refactors or drive-by edits

#### Tests
- [ ] New/changed behavior covered by tests
- [ ] Full suite green locally (`make test` / `make check`)
- [ ] No network/OpenAI calls required for CI

#### Architecture
- [ ] Layer boundaries preserved (`make architecture`)
- [ ] No forbidden imports or reflection dispatch in tool layers

#### Secrets
- [ ] No `.env`, API keys, or credentials in the diff

#### Roadmap
- [ ] Numbered step completion status updated only when truly done
- [ ] Task/DoD criteria satisfied

#### CI
- [ ] GitHub Actions CI is green on this branch

#### Manual review
- [ ] Diff and status inspected by a human before merge
