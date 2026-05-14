from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass(frozen=True)
class TrackStateReleaseArtifactConfig:
    repository: str
    default_branch: str
    release_tag: str | None
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
            release_tag=_read_optional_string(
                runtime_inputs,
                env_key="TS708_RELEASE_TAG",
                payload_key="release_tag",
            ),
            release_tag_pattern=_read_string(
                runtime_inputs,
                env_key="TS708_RELEASE_TAG_PATTERN",
                payload_key="release_tag_pattern",
                default=r"^v\d+\.\d+\.\d+$",
            ),
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
