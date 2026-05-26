from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml


@dataclass(frozen=True)
class NonDefaultBranchReleaseConfig:
    repository: str
    default_branch: str
    probe_file_path: str
    branch_prefix: str
    pull_request_title: str
    pull_request_body: str
    semver_tag_pattern: str
    poll_interval_seconds: int = 10
    pull_request_timeout_seconds: int = 180
    quiet_period_seconds: int = 900
    releases_lookup_limit: int = 30
    tags_lookup_limit: int = 50

    @property
    def releases_page_url(self) -> str:
        return f"https://github.com/{self.repository}/releases"

    @property
    def tags_page_url(self) -> str:
        return f"https://github.com/{self.repository}/tags"

    @classmethod
    def from_file(cls, path: Path) -> "NonDefaultBranchReleaseConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-252 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-252 config runtime_inputs must deserialize to a mapping: {path}"
            )

        instance = cls(
            repository=cls._require_string(runtime_inputs, "repository", path),
            default_branch=cls._require_string(runtime_inputs, "default_branch", path),
            probe_file_path=cls._require_string(runtime_inputs, "probe_file_path", path),
            branch_prefix=cls._require_string(runtime_inputs, "branch_prefix", path),
            pull_request_title=cls._require_string(
                runtime_inputs,
                "pull_request_title",
                path,
            ),
            pull_request_body=cls._require_string(
                runtime_inputs,
                "pull_request_body",
                path,
            ),
            semver_tag_pattern=cls._require_string(
                runtime_inputs,
                "semver_tag_pattern",
                path,
            ),
            poll_interval_seconds=cls._require_positive_int(
                runtime_inputs,
                "poll_interval_seconds",
                path,
                default=10,
            ),
            pull_request_timeout_seconds=cls._require_positive_int(
                runtime_inputs,
                "pull_request_timeout_seconds",
                path,
                default=180,
            ),
            quiet_period_seconds=cls._require_positive_int(
                runtime_inputs,
                "quiet_period_seconds",
                path,
                default=900,
            ),
            releases_lookup_limit=cls._require_positive_int(
                runtime_inputs,
                "releases_lookup_limit",
                path,
                default=30,
            ),
            tags_lookup_limit=cls._require_positive_int(
                runtime_inputs,
                "tags_lookup_limit",
                path,
                default=50,
            ),
        )
        re.compile(instance.semver_tag_pattern)
        return instance

    @staticmethod
    def _require_string(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"TS-252 config is missing runtime_inputs.{key} in {path}.")
        return value.strip()

    @staticmethod
    def _require_positive_int(
        payload: dict[str, Any],
        key: str,
        path: Path,
        *,
        default: int,
    ) -> int:
        value = payload.get(key, default)
        if not isinstance(value, int) or value <= 0:
            raise ValueError(
                f"TS-252 config runtime_inputs.{key} must be a positive integer in {path}."
            )
        return value
