#!/usr/bin/env bash
# Install repository-local git hooks (does not touch global git config).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HOOKS_DIR=".githooks"

if [[ ! -d "$HOOKS_DIR" ]]; then
  echo "Missing hooks directory: $HOOKS_DIR" >&2
  exit 1
fi

for hook in pre-commit pre-push; do
  path="${HOOKS_DIR}/${hook}"
  if [[ ! -f "$path" ]]; then
    echo "Missing hook file: $path" >&2
    exit 1
  fi
  if [[ ! -x "$path" ]]; then
    echo "Hook is not executable: $path" >&2
    exit 1
  fi
done

git config core.hooksPath "$HOOKS_DIR"
echo "Installed repository-local hooksPath=${HOOKS_DIR}"
git config --get core.hooksPath
