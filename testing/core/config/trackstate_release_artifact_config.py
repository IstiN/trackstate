from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any
import os

import yaml


@dataclass(frozen=True)
class TrackStateReleaseArtifactConfig:
    repository: str
    default_branch: str
    release_tag: str
    release_tag_pattern: str
    expected_architecture_fragment: str
    archive_extensions: tuple[str, ...]
    checksum_extensions: tuple[str, ...]
    forbidden_extensions: tuple[str, ...]

    @property
    def releases_api_endpoint(self) -> str:
        return f"/repos/{self.repository}/releases?per_page=50"

    @property
    def releases_page_url(self) -> str:
        return f"https://github.com/{self.repository}/releases"

    def release_page_url(self, tag_name: str) -> str:
        return f"https://github.com/{self.repository}/releases/tag/{tag_name}"

    @classmethod
    def from_file(cls, path: Path) -> "TrackStateReleaseArtifactConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-708 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if runtime_inputs and not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-708 config runtime_inputs must deserialize to a mapping: {path}"
            )

        release_tag_pattern = _read_string(
            runtime_inputs,
            env_key="TS708_RELEASE_TAG_PATTERN",
            payload_key="release_tag_pattern",
            default=r"^v\d+\.\d+\.\d+$",
        )
        return cls(
            repository=_read_string(
                runtime_inputs,
                env_key="TS708_REPOSITORY",
                payload_key="repository",
                default="IstiN/trackstate",
            ),
            default_branch=_read_string(
                runtime_inputs,
                env_key="TS708_DEFAULT_BRANCH",
                payload_key="default_branch",
                default="main",
            ),
            release_tag=_read_required_release_tag(
                runtime_inputs,
                env_key="TS708_RELEASE_TAG",
                payload_key="release_tag",
                pattern=release_tag_pattern,
            ),
            release_tag_pattern=release_tag_pattern,
            expected_architecture_fragment=_read_string(
                runtime_inputs,
                env_key="TS708_EXPECTED_ARCHITECTURE_FRAGMENT",
                payload_key="expected_architecture_fragment",
                default="Mach-O 64-bit executable arm64",
            ),
            archive_extensions=_read_string_list(
                runtime_inputs,
                env_key="TS708_ARCHIVE_EXTENSIONS",
                payload_key="archive_extensions",
                default=(".zip", ".tar.gz", ".tgz", ".tar"),
            ),
            checksum_extensions=_read_string_list(
                runtime_inputs,
                env_key="TS708_CHECKSUM_EXTENSIONS",
                payload_key="checksum_extensions",
                default=(".sha256",),
            ),
            forbidden_extensions=_read_string_list(
                runtime_inputs,
                env_key="TS708_FORBIDDEN_EXTENSIONS",
                payload_key="forbidden_extensions",
                default=(".dmg", ".pkg"),
            ),
        )


def _read_string(
    payload: dict[str, Any],
    *,
    env_key: str,
    payload_key: str,
    default: str,
) -> str:
    value = os.getenv(env_key)
    if isinstance(value, str) and value.strip():
        return value.strip()

    raw_value = payload.get(payload_key)
    if isinstance(raw_value, str) and raw_value.strip():
        return raw_value.strip()

    return default


def _read_optional_string(
    payload: dict[str, Any],
    *,
    env_key: str,
    payload_key: str,
) -> str | None:
    value = os.getenv(env_key)
    if isinstance(value, str) and value.strip():
        return value.strip()

    raw_value = payload.get(payload_key)
    if isinstance(raw_value, str) and raw_value.strip():
        return raw_value.strip()

    return None


def _read_required_release_tag(
    payload: dict[str, Any],
    *,
    env_key: str,
    payload_key: str,
    pattern: str,
) -> str:
    compiled_pattern = re.compile(pattern)
    value = _read_optional_string(payload, env_key=env_key, payload_key=payload_key)
    if value is None:
        value = _read_release_tag_from_ci_metadata(compiled_pattern)
    if value is None:
        raise ValueError(
            "TS-708 requires an explicit release tag. Set TS708_RELEASE_TAG, add "
            "runtime_inputs.release_tag to testing/tests/TS-708/config.yaml, or run in "
            "GitHub Actions with CI metadata that resolves the version tag under test."
        )
    if compiled_pattern.fullmatch(value) is None:
        raise ValueError(
            "TS-708 release tag must match the configured semantic-version pattern.\n"
            f"Observed tag: {value}\n"
            f"Pattern: {pattern}"
        )
    return value


def _read_release_tag_from_ci_metadata(pattern: re.Pattern[str]) -> str | None:
    github_ref_name = os.getenv("GITHUB_REF_NAME")
    if isinstance(github_ref_name, str):
        candidate = github_ref_name.strip()
        if candidate and pattern.fullmatch(candidate) is not None:
            return candidate

    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not isinstance(event_path, str) or not event_path.strip():
        return None

    try:
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None

    inputs = payload.get("inputs")
    release = payload.get("release")
    release_tag = _first_matching_ci_tag(
        pattern,
        (
            _payload_string(inputs.get("release_ref")) if isinstance(inputs, dict) else None,
            _tag_from_ref(_payload_string(payload.get("ref"))),
            _payload_string(release.get("tag_name")) if isinstance(release, dict) else None,
        ),
    )
    return release_tag


def _first_matching_ci_tag(
    pattern: re.Pattern[str],
    values: tuple[str | None, ...],
) -> str | None:
    for value in values:
        if value is not None and pattern.fullmatch(value) is not None:
            return value
    return None


def _payload_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _tag_from_ref(ref: str | None) -> str | None:
    if ref is None:
        return None
    if ref.startswith("refs/tags/"):
        return ref.removeprefix("refs/tags/").strip() or None
    return None


def _read_string_list(
    payload: dict[str, Any],
    *,
    env_key: str,
    payload_key: str,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = os.getenv(env_key)
    if isinstance(value, str) and value.strip():
        return tuple(
            entry.strip()
            for entry in value.split(",")
            if isinstance(entry, str) and entry.strip()
        )

    raw_value = payload.get(payload_key)
    if isinstance(raw_value, list):
        return tuple(
            str(entry).strip()
            for entry in raw_value
            if str(entry).strip()
        )

    return default
