from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass(frozen=True)
class RepositoryReleaseTagsConfig:
    repository: str
    expected_stable_version: str | None

    @property
    def releases_api_url(self) -> str:
        return f"https://api.github.com/repos/{self.repository}/releases"

    @property
    def tags_api_url(self) -> str:
        return f"https://api.github.com/repos/{self.repository}/tags"

    @property
    def releases_page_url(self) -> str:
        return f"https://github.com/{self.repository}/releases"

    @property
    def tags_page_url(self) -> str:
        return f"https://github.com/{self.repository}/tags"

    @classmethod
    def from_file(cls, path: Path) -> "RepositoryReleaseTagsConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-229 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if runtime_inputs and not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-229 config runtime_inputs must deserialize to a mapping: {path}"
            )

        repository = _read_string(
            runtime_inputs,
            env_key="TRACKSTATE_RELEASE_TAG_REPOSITORY",
            payload_key="repository",
            default="IstiN/trackstate-setup",
        )
        expected_stable_version = _read_optional_string(
            runtime_inputs,
            env_key="TRACKSTATE_EXPECTED_STABLE_VERSION",
            payload_key="expected_stable_version",
        )

        return cls(
            repository=repository,
            expected_stable_version=expected_stable_version,
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
