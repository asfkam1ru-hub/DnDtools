#!/usr/bin/env bash
# End-of-work developer report for AI agent sessions.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export GIT_PAGER=cat

echo "=== make check ==="
make check

echo ""
echo "=== make progress ==="
make progress

echo ""
echo "=== git branch ==="
git branch --show-current

echo ""
echo "=== git status --short ==="
git status --short

echo ""
echo "=== git diff --stat ==="
git diff --stat

echo ""
echo "=== git diff --cached --stat ==="
git diff --cached --stat

echo ""
echo "=== last commit ==="
git log -1 --oneline --decorate
