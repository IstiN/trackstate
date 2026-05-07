from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class GitHubPagesWorkflowProbeConfig:
    upstream_repository: str
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
            workflow_file=cls._require_string(runtime_inputs, "workflow_file", path),
            workflow_ref=cls._require_string(runtime_inputs, "workflow_ref", path),
            trackstate_ref=cls._require_string(runtime_inputs, "trackstate_ref", path),
        )

    def requested_repository_for(self, authenticated_login: str) -> str:
        login = authenticated_login.strip()
        if not login:
            raise ValueError(
                "TS-69 requires an authenticated GitHub login to derive the fork repository."
            )

        upstream_owner, repository_name = self._split_repository(self.upstream_repository)
        if login.lower() == upstream_owner.lower():
            raise ValueError(
                "TS-69 requires validating a forked repository, but the "
                f"authenticated login {login} owns the upstream repository "
                f"{self.upstream_repository}. Authenticate as a different GitHub "
                "user so the test can validate a fork."
            )
        return f"{login}/{repository_name}"

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

    @staticmethod
    def _split_repository(repository: str) -> tuple[str, str]:
        owner, separator, name = repository.partition("/")
        owner = owner.strip()
        name = name.strip()
        if not owner or separator != "/" or not name:
            raise ValueError(
                "TS-69 repository values must use the GitHub owner/name format: "
                f"{repository!r}"
            )
        return owner, name
