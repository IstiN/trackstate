from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass(frozen=True)
class GitHubActionsPreflightGateConfig:
    repository: str
    default_branch: str
    workflow_name: str
    workflow_file: str
    workflow_path: str
    preflight_job_name: str
    downstream_job_name: str
    expected_preflight_runner: str
    expected_runner_labels: list[str]
    expected_failure_markers: list[str]
    recent_runs_limit: int
    poll_interval_seconds: int
    run_timeout_seconds: int
    ui_timeout_seconds: int

    @classmethod
    def from_file(cls, path: Path) -> "GitHubActionsPreflightGateConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-706 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if runtime_inputs and not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-706 config runtime_inputs must deserialize to a mapping: {path}"
            )

        return cls(
            repository=_read_string(
                runtime_inputs,
                env_key="TS706_REPOSITORY",
                payload_key="repository",
                default="IstiN/trackstate",
            ),
            default_branch=_read_string(
                runtime_inputs,
                env_key="TS706_DEFAULT_BRANCH",
                payload_key="default_branch",
                default="main",
            ),
            workflow_name=_read_string(
                runtime_inputs,
                env_key="TS706_WORKFLOW_NAME",
                payload_key="workflow_name",
                default="Apple Release Builds",
            ),
            workflow_file=_read_string(
                runtime_inputs,
                env_key="TS706_WORKFLOW_FILE",
                payload_key="workflow_file",
                default="build-native.yml",
            ),
            workflow_path=_read_string(
                runtime_inputs,
                env_key="TS706_WORKFLOW_PATH",
                payload_key="workflow_path",
                default=".github/workflows/build-native.yml",
            ),
            preflight_job_name=_read_string(
                runtime_inputs,
                env_key="TS706_PREFLIGHT_JOB_NAME",
                payload_key="preflight_job_name",
                default="Verify macOS runner availability",
            ),
            downstream_job_name=_read_string(
                runtime_inputs,
                env_key="TS706_DOWNSTREAM_JOB_NAME",
                payload_key="downstream_job_name",
                default="Build macOS desktop and CLI artifacts",
            ),
            expected_preflight_runner=_read_string(
                runtime_inputs,
                env_key="TS706_EXPECTED_PREFLIGHT_RUNNER",
                payload_key="expected_preflight_runner",
                default="ubuntu-latest",
            ),
            expected_runner_labels=_read_string_list(
                runtime_inputs,
                env_key="TS706_EXPECTED_RUNNER_LABELS",
                payload_key="expected_runner_labels",
                default=["self-hosted", "macOS", "trackstate-release", "ARM64"],
            ),
            expected_failure_markers=_read_string_list(
                runtime_inputs,
                env_key="TS706_EXPECTED_FAILURE_MARKERS",
                payload_key="expected_failure_markers",
                default=[
                    "No runner registered for",
                    "none are online",
                ],
            ),
            recent_runs_limit=_read_int(
                runtime_inputs,
                env_key="TS706_RECENT_RUNS_LIMIT",
                payload_key="recent_runs_limit",
                default=20,
            ),
            poll_interval_seconds=_read_int(
                runtime_inputs,
                env_key="TS706_POLL_INTERVAL_SECONDS",
                payload_key="poll_interval_seconds",
                default=5,
            ),
            run_timeout_seconds=_read_int(
                runtime_inputs,
                env_key="TS706_RUN_TIMEOUT_SECONDS",
                payload_key="run_timeout_seconds",
                default=240,
            ),
            ui_timeout_seconds=_read_int(
                runtime_inputs,
                env_key="TS706_UI_TIMEOUT_SECONDS",
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


def _read_string_list(
    payload: dict[str, Any],
    *,
    env_key: str,
    payload_key: str,
    default: list[str],
) -> list[str]:
    value = os.getenv(env_key)
    if isinstance(value, str) and value.strip():
        parsed = [item.strip() for item in value.split(",") if item.strip()]
        if parsed:
            return parsed

    raw_value = payload.get(payload_key)
    if isinstance(raw_value, list):
        parsed = [str(item).strip() for item in raw_value if str(item).strip()]
        if parsed:
            return parsed
    if isinstance(raw_value, str) and raw_value.strip():
        parsed = [item.strip() for item in raw_value.split(",") if item.strip()]
        if parsed:
            return parsed

    return list(default)


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
