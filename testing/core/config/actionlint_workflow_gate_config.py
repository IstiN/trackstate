from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ActionlintWorkflowGateConfig:
    repository: str
    base_branch: str
    target_workflow_name: str
    target_workflow_path: str
    branch_prefix: str
    commit_message: str
    mutation_mode: str = "replace_text"
    mutation_search_text: str = ""
    mutation_replacement_text: str = ""
    created_workflow_contents: str | None = None
    expected_actionlint_marker: str = "actionlint"
    expected_log_markers: tuple[str, ...] = ()
    poll_interval_seconds: int = 5
    run_timeout_seconds: int = 60

    @classmethod
    def from_file(cls, path: Path) -> "ActionlintWorkflowGateConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                f"Actionlint workflow gate config must deserialize to a mapping: {path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "Actionlint workflow gate config runtime_inputs must deserialize "
                f"to a mapping: {path}"
            )

        return cls(
            repository=cls._require_string(runtime_inputs, "repository", path),
            base_branch=cls._require_string(runtime_inputs, "base_branch", path),
            target_workflow_name=cls._require_string(
                runtime_inputs,
                "target_workflow_name",
                path,
            ),
            target_workflow_path=cls._require_string(
                runtime_inputs,
                "target_workflow_path",
                path,
            ),
            branch_prefix=cls._require_string(runtime_inputs, "branch_prefix", path),
            commit_message=cls._require_string(runtime_inputs, "commit_message", path),
            mutation_mode=cls._read_string(
                runtime_inputs,
                "mutation_mode",
                path,
                default="replace_text",
            ),
            mutation_search_text=cls._read_string(
                runtime_inputs,
                "mutation_search_text",
                path,
                default="",
            ),
            mutation_replacement_text=cls._read_string(
                runtime_inputs,
                "mutation_replacement_text",
                path,
                default="",
            ),
            created_workflow_contents=cls._read_optional_string(
                runtime_inputs,
                "created_workflow_contents",
                path,
            ),
            expected_actionlint_marker=cls._require_string(
                runtime_inputs,
                "expected_actionlint_marker",
                path,
            ),
            expected_log_markers=cls._read_string_sequence(
                runtime_inputs,
                "expected_log_markers",
                path,
            ),
            poll_interval_seconds=cls._require_positive_int(
                runtime_inputs,
                "poll_interval_seconds",
                path,
                default=5,
            ),
            run_timeout_seconds=cls._require_positive_int(
                runtime_inputs,
                "run_timeout_seconds",
                path,
                default=60,
            ),
        )._validated(path)

    def _validated(self, path: Path) -> "ActionlintWorkflowGateConfig":
        if self.mutation_mode not in {"replace_text", "create_file"}:
            raise ValueError(
                "Actionlint workflow gate config runtime_inputs.mutation_mode must be "
                f"'replace_text' or 'create_file' in {path}."
            )
        if self.mutation_mode == "replace_text":
            if not self.mutation_search_text:
                raise ValueError(
                    "Actionlint workflow gate config is missing "
                    f"runtime_inputs.mutation_search_text in {path}."
                )
            if not self.mutation_replacement_text:
                raise ValueError(
                    "Actionlint workflow gate config is missing "
                    f"runtime_inputs.mutation_replacement_text in {path}."
                )
        if self.mutation_mode == "create_file" and not self.created_workflow_contents:
            raise ValueError(
                "Actionlint workflow gate config is missing "
                f"runtime_inputs.created_workflow_contents in {path}."
            )
        return self

    @staticmethod
    def _require_string(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> str:
        value = ActionlintWorkflowGateConfig._read_string(payload, key, path, default=None)
        if value is None:
            raise ValueError(
                f"Actionlint workflow gate config is missing runtime_inputs.{key} in {path}."
            )
        return value

    @staticmethod
    def _read_string(
        payload: dict[str, Any],
        key: str,
        path: Path,
        *,
        default: str | None,
    ) -> str | None:
        value = payload.get(key)
        if value is None:
            return default
        if not isinstance(value, str):
            raise ValueError(
                "Actionlint workflow gate config runtime_inputs."
                f"{key} must be a string in {path}."
            )
        return value.strip()

    @staticmethod
    def _read_optional_string(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> str | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "Actionlint workflow gate config runtime_inputs."
                f"{key} must be a non-empty string in {path}."
            )
        return value.rstrip("\n")

    @staticmethod
    def _read_string_sequence(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if value is None:
            return ()
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ValueError(
                "Actionlint workflow gate config runtime_inputs."
                f"{key} must be a list of non-empty strings in {path}."
            )
        return tuple(item.strip() for item in value)

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
                "Actionlint workflow gate config runtime_inputs."
                f"{key} must be a positive integer in {path}."
            )
        return value
