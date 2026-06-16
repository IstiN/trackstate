#!/usr/bin/env bash
set -euo pipefail

# Verify that the inline macOS thinning fallback in the reusable macOS release
# workflow stays identical to tool/thin_macos_app_bundle.sh. The fallback is
# intentionally inlined so historical tags that predate the helper script can
# still be rebuilt; this check catches drift between the two copies.

workflow_file=".github/workflows/build-macos-reusable.yml"
helper_file="tool/thin_macos_app_bundle.sh"

functions=(read_file_mode preserve_file_mode thin_macho_to_arm64 thin_app_bundle_to_arm64)

extract_functions() {
  local source_file="$1"
  for func in "${functions[@]}"; do
    awk -v fname="$func" '
      $0 ~ "^[[:space:]]*" fname "\\(\\) \\{" { found = 1 }
      found {
        gsub(/^[[:space:]]+/, "")
        print
        if ($0 ~ "^\\}$") { found = 0 }
      }
    ' "$source_file"
  done
}

workflow_functions="$(mktemp)"
helper_functions="$(mktemp)"
trap 'rm -f "$workflow_functions" "$helper_functions"' EXIT

extract_functions "$workflow_file" > "$workflow_functions"
extract_functions "$helper_file" > "$helper_functions"

if ! diff -u "$helper_functions" "$workflow_functions"; then
  echo "::error::Inline thinning fallback in $workflow_file is out of sync with $helper_file."
  exit 1
fi

echo "Inline macOS thinning fallback is in sync with $helper_file."
