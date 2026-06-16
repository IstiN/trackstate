#!/usr/bin/env bash
# TrackState CLI installer for Linux and macOS.
#
# Usage:
#   curl -fsSL https://github.com/__REPO_PLACEHOLDER__/releases/latest/download/install.sh | bash
#   curl -fsSL https://github.com/__REPO_PLACEHOLDER__/releases/download/v1.2.3/install.sh | bash -s -- v1.2.3
#
# The script installs the TrackState CLI into a user-local directory and
# appends that directory to the user's shell profile when it is not already
# on PATH. No administrator privileges are required.
set -euo pipefail

REPO="__REPO_PLACEHOLDER__"
INSTALL_DIR="${HOME}/.trackstate/bin"

FORCE=0

print_usage() {
  cat <<EOF
Usage: $0 [OPTIONS] [VERSION]

Install or update the TrackState CLI.

Options:
  --force   Install even when a conflicting trackstate binary is already
            present on PATH.

Arguments:
  VERSION   Release tag to install (e.g., v1.2.3). Defaults to the latest
            release published on GitHub.

Examples:
  $0                 # install the latest release
  $0 v1.2.3          # install a pinned release
  $0 --force         # install even if trackstate is already on PATH
EOF
}

log() {
  echo "--> $*" >&2
}

error() {
  echo "ERROR: $*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -*)
      error "Unknown option: $1"
      ;;
    *)
      if [[ -n "${REQUESTED_VERSION:-}" ]]; then
        error "Unexpected argument: $1"
      fi
      REQUESTED_VERSION="$1"
      shift
      ;;
  esac
done

REQUESTED_VERSION="${REQUESTED_VERSION:-latest}"

check_existing_trackstate() {
  local existing
  existing="$(type -P trackstate || true)"
  if [[ -n "$existing" && "$existing" != "${INSTALL_DIR}/trackstate" ]]; then
    if [[ "$FORCE" -eq 1 ]]; then
      log "Warning: an existing trackstate binary was found at ${existing}; continuing because --force was passed."
    else
      error "A conflicting trackstate binary already exists on PATH at ${existing}. Use --force to override."
    fi
  fi
}

resolve_release_tag() {
  local version="$1"
  if [[ "$version" != "latest" ]]; then
    echo "$version"
    return
  fi

  local release_json
  release_json="$(curl -sSL --fail "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null)" ||
    error "Unable to resolve the latest release from the GitHub API."

  local tag
  tag="$(printf '%s' "$release_json" | sed -n 's/.*"tag_name": "\([^"]*\)".*/\1/p' | head -n 1)"
  if [[ -z "$tag" ]]; then
    error "Unable to parse the latest release tag from the GitHub API response."
  fi
  echo "$tag"
}

detect_platform() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"

  case "$os" in
    Linux)
      case "$arch" in
        x86_64|amd64)
          echo "linux-x64"
          ;;
        *)
          error "Unsupported architecture on Linux: $arch. Supported: x86_64."
          ;;
      esac
      ;;
    Darwin)
      case "$arch" in
        arm64|aarch64)
          echo "macos-arm64"
          ;;
        *)
          error "Unsupported architecture on macOS: $arch. Supported: arm64."
          ;;
      esac
      ;;
    *)
      error "Unsupported operating system: $os. Supported: Linux, Darwin."
      ;;
  esac
}

download() {
  local url="$1"
  local out="$2"
  curl -sSL --fail "$url" -o "$out" || error "Download failed: $url"
}

sha256_hash() {
  local file_path="$1"
  case "$(uname -s)" in
    Darwin)
      shasum -a 256 "$file_path" | awk '{ print $1 }'
      ;;
    *)
      sha256sum "$file_path" | awk '{ print $1 }'
      ;;
  esac
}

check_existing_trackstate

RELEASE_TAG="$(resolve_release_tag "$REQUESTED_VERSION")"
PLATFORM="$(detect_platform)"
ARCHIVE_NAME="trackstate-cli-${PLATFORM}-${RELEASE_TAG}.tar.gz"
CHECKSUM_NAME="trackstate-${RELEASE_TAG}.sha256"
DOWNLOAD_BASE="https://github.com/${REPO}/releases/download/${RELEASE_TAG}"

log "Installing TrackState CLI ${RELEASE_TAG} for ${PLATFORM}..."

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

ARCHIVE_PATH="${TMP_DIR}/${ARCHIVE_NAME}"
CHECKSUM_PATH="${TMP_DIR}/${CHECKSUM_NAME}"

download "${DOWNLOAD_BASE}/${ARCHIVE_NAME}" "$ARCHIVE_PATH"
download "${DOWNLOAD_BASE}/${CHECKSUM_NAME}" "$CHECKSUM_PATH"

EXPECTED_HASH="$(awk -v file="$ARCHIVE_NAME" '$2 == file { print $1 }' "$CHECKSUM_PATH")"
if [[ -z "$EXPECTED_HASH" ]]; then
  error "Unable to find checksum entry for ${ARCHIVE_NAME} in ${CHECKSUM_NAME}."
fi

ACTUAL_HASH="$(sha256_hash "$ARCHIVE_PATH")"
if [[ "$EXPECTED_HASH" != "$ACTUAL_HASH" ]]; then
  error "Checksum mismatch for ${ARCHIVE_NAME}. Expected: ${EXPECTED_HASH}, got: ${ACTUAL_HASH}."
fi

mkdir -p "$INSTALL_DIR"
tar -xzf "$ARCHIVE_PATH" -C "$TMP_DIR"

# The archive contains a single executable named "trackstate" (Linux/macOS).
EXTRACTED_BIN="${TMP_DIR}/trackstate"
if [[ ! -f "$EXTRACTED_BIN" ]]; then
  error "Expected executable 'trackstate' was not found in the downloaded archive."
fi

install -m 755 "$EXTRACTED_BIN" "${INSTALL_DIR}/trackstate"

if [[ ":${PATH}:" != *":${INSTALL_DIR}:"* ]]; then
  SHELL_NAME="${SHELL:-}"
  PROFILE_FILE=""
  case "$(basename "$SHELL_NAME")" in
    zsh)
      PROFILE_FILE="${HOME}/.zshrc"
      ;;
    bash)
      PROFILE_FILE="${HOME}/.bashrc"
      ;;
    *)
      if [[ -f "${HOME}/.bashrc" ]]; then
        PROFILE_FILE="${HOME}/.bashrc"
      elif [[ -f "${HOME}/.zshrc" ]]; then
        PROFILE_FILE="${HOME}/.zshrc"
      elif [[ -f "${HOME}/.profile" ]]; then
        PROFILE_FILE="${HOME}/.profile"
      fi
      ;;
  esac

  if [[ -n "$PROFILE_FILE" ]]; then
    printf '\n# TrackState CLI\nexport PATH="%s:$PATH"\n' "$INSTALL_DIR" >> "$PROFILE_FILE"
    log "Added ${INSTALL_DIR} to PATH in ${PROFILE_FILE}."
    log "Run 'source ${PROFILE_FILE}' or open a new terminal to use the 'trackstate' command."
  else
    log "Could not detect a shell profile. Please add ${INSTALL_DIR} to your PATH manually."
  fi
else
  log "${INSTALL_DIR} is already on PATH."
fi

log "TrackState CLI ${RELEASE_TAG} installed to ${INSTALL_DIR}/trackstate"
"${INSTALL_DIR}/trackstate" --version 2>/dev/null || true
