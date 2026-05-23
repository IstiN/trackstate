#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 '<command>'" >&2
  exit 2
fi

command_to_run="$1"

detect_changed_files() {
  local base
  if git rev-parse --verify origin/main >/dev/null 2>&1; then
    base="$(git merge-base HEAD origin/main)"
    git diff --name-only --diff-filter=ACMRTUXB "$base"...HEAD
    return
  fi

  if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
    git diff --name-only --diff-filter=ACMRTUXB HEAD~1...HEAD
    return
  fi

  git ls-files
}

changed_files="$(detect_changed_files || true)"

if [[ -z "$changed_files" ]]; then
  echo "[a11y-gate] No changed files detected; skipping heavy accessibility command."
  exit 0
fi

if echo "$changed_files" | grep -Eq '^(lib/|web/|test/|testing/accessibility/|playwright\.config\.js|package(-lock)?\.json|pubspec\.(yaml|lock)|l10n\.yaml|\.github/workflows/unit-tests\.yml)'; then
  echo "[a11y-gate] Accessibility-relevant changes detected; running: $command_to_run"
  bash -lc "$command_to_run"
else
  echo "[a11y-gate] No accessibility-relevant changes; skipping: $command_to_run"
fi
