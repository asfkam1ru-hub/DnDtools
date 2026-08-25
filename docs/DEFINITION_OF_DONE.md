# Definition of Done

A roadmap step is **not** complete because an AI agent said “done”.
It is complete when the checklist below is satisfied and verified.

## Implementation

- [ ] Requested behavior exists
- [ ] Scope boundaries preserved
- [ ] No unrelated changes

## Tests

- [ ] New behavior tested
- [ ] Full suite passes (`make test` / `make check`)
- [ ] No network unless explicitly required by the task

## Static checks

- [ ] Compile passes (`make compile`)
- [ ] Architecture passes (`make architecture`)
- [ ] `git diff --check` passes

## Review

- [ ] Diff inspected
- [ ] Status inspected
- [ ] No secrets
- [ ] Roadmap completion reflects reality

## Git

- [ ] Isolated commit on a feature/chore branch
- [ ] CI passes
- [ ] Pushed branch
- [ ] Reviewed / merged
- [ ] Clean `main` afterwards

## Notes

- Use `make audit` as the default local verification command after implementation.
- Use the matching `tasks/...` file as the execution contract for the step.
- Numbered ROADMAP checkboxes are updated only after human confirmation.
