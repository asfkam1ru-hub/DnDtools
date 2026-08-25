#!/usr/bin/env bash
# Architecture invariant checks for AI tooling layers.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

failures=0

fail_if_matches() {
  local file="$1"
  local pattern="$2"
  local description="$3"
  local matches

  matches="$(grep -nE "$pattern" "$file" || true)"
  if [[ -n "$matches" ]]; then
    echo "FAIL: $description"
    echo "  file: $file"
    echo "  pattern: $pattern"
    echo "$matches" | sed 's/^/  /'
    failures=$((failures + 1))
    return 1
  fi
  return 0
}

require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "FAIL: expected production file missing: $file"
    failures=$((failures + 1))
    return 1
  fi
  return 0
}

pass() {
  echo "PASS: $1"
}

check_section() {
  local label="$1"
  local before="$failures"
  shift
  "$@"
  if [[ "$failures" -eq "$before" ]]; then
    pass "$label"
  fi
}

check_registry() {
  local file="backend/app/tools/registry.py"
  require_file "$file" || return 0
  fail_if_matches "$file" 'CharacterTools' "registry must not import CharacterTools" || true
  fail_if_matches "$file" 'CharacterRepository' "registry must not import CharacterRepository" || true
  fail_if_matches "$file" 'OpenAI' "registry must not import OpenAI" || true
  fail_if_matches "$file" 'LLMService' "registry must not import LLMService" || true
  fail_if_matches "$file" 'FastAPI' "registry must not import FastAPI" || true
  fail_if_matches "$file" 'app\.main' "registry must not import app.main" || true
  fail_if_matches "$file" '\.handler\(' "registry must not invoke .handler(" || true
}

check_validation() {
  local file="backend/app/tools/validation.py"
  require_file "$file" || return 0
  fail_if_matches "$file" 'CharacterTools' "validation must not import CharacterTools" || true
  fail_if_matches "$file" 'CharacterRepository' "validation must not import CharacterRepository" || true
  fail_if_matches "$file" 'OpenAI' "validation must not import OpenAI" || true
  fail_if_matches "$file" 'LLMService' "validation must not import LLMService" || true
  fail_if_matches "$file" 'FastAPI' "validation must not import FastAPI" || true
  fail_if_matches "$file" 'app\.main' "validation must not import app.main" || true
  fail_if_matches "$file" '\.handler\(' "validation must not invoke .handler(" || true
  fail_if_matches "$file" '^\s*def (execute|run|invoke|call)\(' \
    "validation must not expose public execution methods" || true
}

check_execution() {
  local file="backend/app/tools/execution.py"
  require_file "$file" || return 0
  fail_if_matches "$file" 'CharacterTools' "execution must not import CharacterTools" || true
  fail_if_matches "$file" 'CharacterRepository' "execution must not import CharacterRepository" || true
  fail_if_matches "$file" 'OpenAI' "execution must not import OpenAI" || true
  fail_if_matches "$file" 'OpenAIProvider' "execution must not import OpenAIProvider" || true
  fail_if_matches "$file" 'LLMService' "execution must not import LLMService" || true
  fail_if_matches "$file" '\bSettings\b' "execution must not import Settings" || true
  fail_if_matches "$file" 'FastAPI' "execution must not import FastAPI" || true
  fail_if_matches "$file" 'app\.main' "execution must not import app.main" || true
  fail_if_matches "$file" 'getattr\(' "execution must not use getattr(" || true
  fail_if_matches "$file" 'eval\(' "execution must not use eval(" || true
  fail_if_matches "$file" 'exec\(' "execution must not use exec(" || true
  fail_if_matches "$file" 'globals\(' "execution must not use globals(" || true
  fail_if_matches "$file" 'locals\(' "execution must not use locals(" || true
  fail_if_matches "$file" 'except Exception' "execution must not catch broad Exception" || true
  fail_if_matches "$file" 'except BaseException' "execution must not catch BaseException" || true
}

echo "=== Architecture checks ==="
check_section "registry.py invariants" check_registry
check_section "validation.py invariants" check_validation
check_section "execution.py invariants" check_execution

if [[ "$failures" -ne 0 ]]; then
  echo "Architecture check failed with $failures violation(s)."
  exit 1
fi

echo "Architecture checks passed."
exit 0
