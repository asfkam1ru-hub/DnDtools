#!/usr/bin/env bash
# Create an isolated feature branch from an up-to-date main.
# Usage: ./scripts/start_feature.sh 3.9 agent-service
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <STEP> <SLUG>" >&2
  echo "Example: $0 3.9 agent-service" >&2
  exit 1
fi

STEP="$1"
SLUG="$2"

if [[ ! "$STEP" =~ ^[0-9]+\.[0-9]+$ ]]; then
  echo "Invalid STEP '$STEP'. Expected form N.N (e.g. 3.9)." >&2
  exit 1
fi

if [[ ! "$SLUG" =~ ^[a-z0-9-]+$ ]]; then
  echo "Invalid SLUG '$SLUG'. Expected [a-z0-9-]+." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is not clean. Commit or stash changes first." >&2
  git status --short >&2
  exit 1
fi

BRANCH="feat/${STEP}-${SLUG}"

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "Branch already exists locally: ${BRANCH}" >&2
  exit 1
fi

if git show-ref --verify --quiet "refs/remotes/origin/${BRANCH}"; then
  echo "Branch already exists on origin: ${BRANCH}" >&2
  exit 1
fi

echo "Fetching origin..."
git fetch origin

if ! git show-ref --verify --quiet refs/heads/main; then
  echo "Local main branch is missing." >&2
  exit 1
fi

if ! git show-ref --verify --quiet refs/remotes/origin/main; then
  echo "origin/main is missing after fetch." >&2
  exit 1
fi

LOCAL_MAIN="$(git rev-parse main)"
ORIGIN_MAIN="$(git rev-parse origin/main)"
if [[ "$LOCAL_MAIN" != "$ORIGIN_MAIN" ]]; then
  echo "Local main is not aligned with origin/main." >&2
  echo "  main:        $LOCAL_MAIN" >&2
  echo "  origin/main: $ORIGIN_MAIN" >&2
  echo "Update main before creating a feature branch." >&2
  exit 1
fi

git checkout main
git checkout -b "$BRANCH"
echo "Created and checked out ${BRANCH}"
