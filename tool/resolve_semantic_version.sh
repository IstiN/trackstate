#!/usr/bin/env bash
set -euo pipefail

# Resolve the next semantic release tag and the Git ref to build from.
#
# Usage:
#   ./tool/resolve_semantic_version.sh [--release-ref <tag|auto>] [--sha <commit-sha>]
#
# Outputs (one key=value per line, suitable for appending to GITHUB_OUTPUT):
#   release_tag=<semantic-version-tag>
#   release_checkout_ref=<sha-or-tag>
#   build_number=<commit-count>
#
# Behavior:
# * When --release-ref is a semantic version tag (e.g. v1.2.3), that tag is used
#   as both the release_tag and the release_checkout_ref.
# * When --release-ref is "auto" (the default), the script checks whether the
#   current commit already has a semantic version tag. If so, that tag is used.
#   Otherwise the latest semantic version tag is patch-bumped and the current
#   commit is used as the checkout ref.
# * If no semantic version tags exist and --release-ref is "auto", the first
#   release is v0.0.1.

release_ref="${RELEASE_REF:-auto}"
current_sha="${CURRENT_SHA:-${GITHUB_SHA:-}}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --release-ref)
      release_ref="$2"
      shift 2
      ;;
    --sha)
      current_sha="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$current_sha" ]]; then
  echo "::error::CURRENT_SHA or GITHUB_SHA must be set." >&2
  exit 1
fi

# Ensure tags are available locally. Try the caller's origin first; fall back to
# a bare fetch if the remote is not reachable (e.g. local dry-runs).
if ! git fetch --force --tags origin >/dev/null 2>&1; then
  git fetch --force --tags >/dev/null 2>&1 || true
fi

if [[ -n "$release_ref" && "$release_ref" != "auto" ]]; then
  if [[ ! "$release_ref" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "::error::Release ref '$release_ref' is not a semantic version tag such as v1.2.3." >&2
    exit 1
  fi

  release_tag="$release_ref"
  release_checkout_ref="$release_ref"
else
  existing_head_tag="$(
    git tag --points-at "$current_sha" |
      grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' |
      sort -V |
      tail -n 1 || true
  )"

  if [[ -n "$existing_head_tag" ]]; then
    release_tag="$existing_head_tag"
    release_checkout_ref="$existing_head_tag"
  else
    latest_tag="$(
      git tag --list |
        grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' |
        sort -V |
        tail -n 1 || true
    )"

    if [[ -z "$latest_tag" ]]; then
      release_tag="v0.0.1"
    else
      version_part="${latest_tag#v}"
      IFS='.' read -r major minor patch <<< "$version_part"
      # Force decimal interpretation so leading-zero patch components (e.g. 08)
      # are not treated as invalid octal values by bash arithmetic.
      release_tag="v${major}.${minor}.$((10#$patch + 1))"
    fi

    release_checkout_ref="$current_sha"
  fi
fi

if ! git rev-parse "$release_checkout_ref" >/dev/null 2>&1; then
  echo "::error::Resolved checkout ref '$release_checkout_ref' does not exist in the repository." >&2
  exit 1
fi

build_number="$(git rev-list --count "$release_checkout_ref")"

echo "release_tag=$release_tag"
echo "release_checkout_ref=$release_checkout_ref"
echo "build_number=$build_number"
