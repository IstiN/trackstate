from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass(frozen=True)
class ReleaseSourceWorkflowConfig:
    repository: str
    default_branch: str
    workflow_path: str

    @property
    def releases_api_endpoint(self) -> str:
        return f"/repos/{self.repository}/releases?per_page=1"

    @property
    def tags_api_endpoint(self) -> str:
        return f"/repos/{self.repository}/tags?per_page=1"

    @property
    def releases_page_url(self) -> str:
        return f"https://github.com/{self.repository}/releases"

    @property
    def tags_page_url(self) -> str:
        return f"https://github.com/{self.repository}/tags"


    @classmethod
    def from_file(cls, path: Path) -> "ReleaseSourceWorkflowConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-83 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if runtime_inputs and not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-83 config runtime_inputs must deserialize to a mapping: {path}"
            )

        return cls(
            repository=_read_string(
                runtime_inputs,
                env_key="TRACKSTATE_RELEASE_SOURCE_REPOSITORY",
                payload_key="repository",
                default="IstiN/trackstate-setup",
            ),
            default_branch=_read_string(
                runtime_inputs,
                env_key="TRACKSTATE_RELEASE_SOURCE_BRANCH",
                payload_key="default_branch",
                default="main",
            ),
            workflow_path=_read_string(
                runtime_inputs,
                env_key="TRACKSTATE_RELEASE_SOURCE_WORKFLOW_PATH",
                payload_key="workflow_path",
                default=".github/workflows/install-update-trackstate.yml",
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
