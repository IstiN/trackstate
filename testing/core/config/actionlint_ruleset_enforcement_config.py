from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ActionlintRulesetEnforcementConfig:
    repository: str
    base_branch: str
    expected_actionlint_context: str = "actionlint"
    minimum_protected_branch_count: int = 1

    @classmethod
    def from_file(cls, path: Path) -> "ActionlintRulesetEnforcementConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "Actionlint ruleset enforcement config must deserialize to a mapping: "
                f"{path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "Actionlint ruleset enforcement config runtime_inputs must "
                f"deserialize to a mapping: {path}"
            )

        return cls(
            repository=cls._require_string(runtime_inputs, "repository", path),
            base_branch=cls._require_string(runtime_inputs, "base_branch", path),
            expected_actionlint_context=cls._require_string(
                runtime_inputs,
                "expected_actionlint_context",
                path,
            ),
            minimum_protected_branch_count=cls._require_positive_int(
                runtime_inputs,
                "minimum_protected_branch_count",
                path,
                default=1,
            ),
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "Actionlint ruleset enforcement config is missing "
                f"runtime_inputs.{key} in {path}."
            )
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
                "Actionlint ruleset enforcement config runtime_inputs."
                f"{key} must be a positive integer in {path}."
            )
        return value
