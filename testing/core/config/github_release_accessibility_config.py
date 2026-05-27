from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass(frozen=True)
class GitHubReleaseAccessibilityConfig:
    repository: str
    release_tag: str | None
    screenshot_path: str | None

    @property
    def releases_api_url(self) -> str:
        return f"https://api.github.com/repos/{self.repository}/releases?per_page=10"

    @classmethod
    def from_file(cls, path: Path) -> "GitHubReleaseAccessibilityConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-710 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if runtime_inputs and not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-710 config runtime_inputs must deserialize to a mapping: {path}",
            )

        repository = _read_string(
            runtime_inputs,
            env_key="TRACKSTATE_RELEASE_ACCESSIBILITY_REPOSITORY",
            payload_key="repository",
            default="IstiN/trackstate",
        )
        release_tag = _read_optional_string(
            runtime_inputs,
            env_key="TRACKSTATE_RELEASE_ACCESSIBILITY_TAG",
            payload_key="release_tag",
        )
        screenshot_path = _read_optional_string(
            runtime_inputs,
            env_key="TS710_SCREENSHOT_PATH",
            payload_key="screenshot_path",
        )

        return cls(
            repository=repository,
            release_tag=release_tag,
            screenshot_path=screenshot_path,
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
