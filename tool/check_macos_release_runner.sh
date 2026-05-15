#!/usr/bin/env bash
set -euo pipefail

required_flutter_version="${TRACKSTATE_EXPECTED_FLUTTER_VERSION:-3.35.3}"
required_dart_version="${TRACKSTATE_EXPECTED_DART_VERSION:-3.9.2}"
minimum_xcode_major="${TRACKSTATE_MIN_XCODE_MAJOR:-16}"
runner_os="${TRACKSTATE_UNAME_S:-$(uname -s)}"
runner_arch="${TRACKSTATE_UNAME_M:-$(uname -m)}"
required_tools=(
  flutter
  dart
  xcodebuild
  zip
  ditto
  tar
  shasum
  bash
)

fail() {
  echo "::error::$1"
  exit 1
}

read_matching_line() {
  local __result_var="$1"
  local pattern="$2"
  shift
  shift

  local output=""
  if ! output="$("$@" 2>&1)"; then
    fail "Failed to run '$*': $output"
  fi

  local matching_line=""
  while IFS= read -r line; do
    if [[ "$line" =~ $pattern ]]; then
      matching_line="$line"
      break
    fi
  done <<< "$output"

  printf -v "$__result_var" '%s' "$matching_line"
}

if [[ "$runner_os" != "Darwin" ]]; then
  fail "TrackState Apple release jobs require a macOS runner; found '$runner_os'."
fi

if [[ "$runner_arch" != "arm64" ]]; then
  fail "TrackState Apple release jobs require an Apple Silicon ARM64 runner; found '$runner_arch'."
fi

for tool in "${required_tools[@]}"; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    fail "Required tool '$tool' is missing from PATH."
  fi
done

read_matching_line flutter_version_line '^Flutter[[:space:]]+[0-9]+' flutter --version
if [[ "$flutter_version_line" != "Flutter $required_flutter_version"* ]]; then
  fail "Flutter $required_flutter_version is required; found '$flutter_version_line'."
fi

dart_version_line="$(dart --version 2>&1)"
if [[ "$dart_version_line" != "Dart SDK version: $required_dart_version"* ]]; then
  fail "Dart $required_dart_version is required; found '$dart_version_line'."
fi

read_matching_line xcode_version_line '^Xcode[[:space:]]+' xcodebuild -version
if [[ ! "$xcode_version_line" =~ ^Xcode[[:space:]]+([0-9]+)(\.[0-9]+)? ]]; then
  fail "Unable to determine the Xcode version from '$xcode_version_line'."
fi

xcode_major="${BASH_REMATCH[1]}"
if (( xcode_major < minimum_xcode_major )); then
  fail "Xcode $minimum_xcode_major or newer is required; found '$xcode_version_line'."
fi

read_matching_line bash_version_line 'version[[:space:]]+[0-9]+\.[0-9]+' bash --version
if [[ ! "$bash_version_line" =~ version[[:space:]]+([0-9]+)\.([0-9]+) ]]; then
  fail "Unable to determine the Bash version from '$bash_version_line'."
fi

bash_major="${BASH_REMATCH[1]}"
bash_minor="${BASH_REMATCH[2]}"
if (( bash_major < 3 || (bash_major == 3 && bash_minor < 2) )); then
  fail "Bash 3.2 or newer is required; found '$bash_version_line'."
fi

echo "Runner readiness verified for Flutter $required_flutter_version, Dart $required_dart_version, and $xcode_version_line."
