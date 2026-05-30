from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass(frozen=True)
class GitHubWorkflowTriggerIsolationConfig:
    repository: str
    default_branch: str
    apple_workflow_name: str
    apple_workflow_file: str
    apple_workflow_path: str
    main_ci_workflow_name: str
    main_ci_workflow_file: str
    main_ci_workflow_path: str
    expected_semver_tag_pattern: str
    recent_runs_limit: int
    ui_timeout_seconds: int

    @classmethod
    def from_file(cls, path: Path) -> "GitHubWorkflowTriggerIsolationConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-709 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if runtime_inputs and not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-709 config runtime_inputs must deserialize to a mapping: {path}"
            )

        return cls(
            repository=_read_string(
                runtime_inputs,
                env_key="TS709_REPOSITORY",
                payload_key="repository",
                default="IstiN/trackstate",
            ),
            default_branch=_read_string(
                runtime_inputs,
                env_key="TS709_DEFAULT_BRANCH",
                payload_key="default_branch",
                default="main",
            ),
            apple_workflow_name=_read_string(
                runtime_inputs,
                env_key="TS709_APPLE_WORKFLOW_NAME",
                payload_key="apple_workflow_name",
                default="Apple Release Builds",
            ),
            apple_workflow_file=_read_string(
                runtime_inputs,
                env_key="TS709_APPLE_WORKFLOW_FILE",
                payload_key="apple_workflow_file",
                default="build-native.yml",
            ),
            apple_workflow_path=_read_string(
                runtime_inputs,
                env_key="TS709_APPLE_WORKFLOW_PATH",
                payload_key="apple_workflow_path",
                default=".github/workflows/build-native.yml",
            ),
            main_ci_workflow_name=_read_string(
                runtime_inputs,
                env_key="TS709_MAIN_CI_WORKFLOW_NAME",
                payload_key="main_ci_workflow_name",
                default="Flutter CI",
            ),
            main_ci_workflow_file=_read_string(
                runtime_inputs,
                env_key="TS709_MAIN_CI_WORKFLOW_FILE",
                payload_key="main_ci_workflow_file",
                default="flutter-ci.yml",
            ),
            main_ci_workflow_path=_read_string(
                runtime_inputs,
                env_key="TS709_MAIN_CI_WORKFLOW_PATH",
                payload_key="main_ci_workflow_path",
                default=".github/workflows/flutter-ci.yml",
            ),
            expected_semver_tag_pattern=_read_string(
                runtime_inputs,
                env_key="TS709_EXPECTED_SEMVER_TAG_PATTERN",
                payload_key="expected_semver_tag_pattern",
                default="v*",
            ),
            recent_runs_limit=_read_int(
                runtime_inputs,
                env_key="TS709_RECENT_RUNS_LIMIT",
                payload_key="recent_runs_limit",
                default=30,
            ),
            ui_timeout_seconds=_read_int(
                runtime_inputs,
                env_key="TS709_UI_TIMEOUT_SECONDS",
                payload_key="ui_timeout_seconds",
                default=60,
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


def _read_int(
    payload: dict[str, Any],
    *,
    env_key: str,
    payload_key: str,
    default: int,
) -> int:
    value = os.getenv(env_key)
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip())
        except ValueError:
            pass

    raw_value = payload.get(payload_key)
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, str) and raw_value.strip():
        try:
            return int(raw_value.strip())
        except ValueError:
            pass

    return default
