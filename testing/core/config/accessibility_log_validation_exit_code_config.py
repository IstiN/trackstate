from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AccessibilityLogValidationExitCodeConfig:
    requested_command: tuple[str, ...]
    workflow_relative_path: str
    node_test_relative_path: str
    validator_relative_path: str
    log_validation_step_name: str
    expected_missing_step_message: str
    expected_failing_subtest: str
    expected_pass_exit_code: int
    expected_fail_exit_code: int

    @classmethod
    def from_file(cls, path: Path) -> "AccessibilityLogValidationExitCodeConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-968 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-968 config runtime_inputs must deserialize to a mapping: {path}"
            )

        return cls(
            requested_command=cls._require_string_list(
                runtime_inputs,
                "requested_command",
                path,
            ),
            workflow_relative_path=cls._require_string(
                runtime_inputs,
                "workflow_relative_path",
                path,
            ),
            node_test_relative_path=cls._require_string(
                runtime_inputs,
                "node_test_relative_path",
                path,
            ),
            validator_relative_path=cls._require_string(
                runtime_inputs,
                "validator_relative_path",
                path,
            ),
            log_validation_step_name=cls._require_string(
                runtime_inputs,
                "log_validation_step_name",
                path,
            ),
            expected_missing_step_message=cls._require_string(
                runtime_inputs,
                "expected_missing_step_message",
                path,
            ),
            expected_failing_subtest=cls._require_string(
                runtime_inputs,
                "expected_failing_subtest",
                path,
            ),
            expected_pass_exit_code=cls._require_int(
                runtime_inputs,
                "expected_pass_exit_code",
                path,
            ),
            expected_fail_exit_code=cls._require_int(
                runtime_inputs,
                "expected_fail_exit_code",
                path,
            ),
        )

    @staticmethod
    def _require_string(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"TS-968 config runtime_inputs.{key} must be a non-empty string in {path}."
            )
        return value

    @staticmethod
    def _require_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(
                f"TS-968 config runtime_inputs.{key} must be a non-empty list in {path}."
            )

        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-968 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}."
                )
            items.append(item)
        return tuple(items)

    @staticmethod
    def _require_int(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> int:
        value = payload.get(key)
        if not isinstance(value, int):
            raise ValueError(
                f"TS-968 config runtime_inputs.{key} must be an integer in {path}."
            )
        return value
