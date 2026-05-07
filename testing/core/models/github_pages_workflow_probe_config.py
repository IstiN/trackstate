from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class GitHubPagesWorkflowProbeConfig:
    upstream_repository: str
    requested_repository: str
    workflow_file: str
    workflow_ref: str
    trackstate_ref: str

    @classmethod
    def from_file(cls, path: Path) -> "GitHubPagesWorkflowProbeConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-69 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-69 config runtime_inputs must deserialize to a mapping: {path}"
            )

        return cls(
            upstream_repository=cls._require_string(
                runtime_inputs,
                "upstream_repository",
                path,
            ),
            requested_repository=cls._require_string(
                runtime_inputs,
                "requested_repository",
                path,
            ),
            workflow_file=cls._require_string(runtime_inputs, "workflow_file", path),
            workflow_ref=cls._require_string(runtime_inputs, "workflow_ref", path),
            trackstate_ref=cls._require_string(runtime_inputs, "trackstate_ref", path),
        )

    @staticmethod
    def _require_string(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"TS-69 config is missing runtime_inputs.{key} in {path}."
            )
        return value.strip()
