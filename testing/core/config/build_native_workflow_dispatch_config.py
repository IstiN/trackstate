from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass(frozen=True)
class BuildNativeWorkflowDispatchConfig:
    repository: str
    default_branch: str
    workflow_path: str
    workflow_file: str
    reusable_workflow_path: str
    build_macos_job_name: str
    required_runner_labels: tuple[str, ...]
    release_ref: str
    run_timeout_seconds: int
    poll_interval_seconds: int

    @classmethod
    def from_file(cls, path: Path) -> "BuildNativeWorkflowDispatchConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"Config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(f"Config runtime_inputs must deserialize to a mapping: {path}")

        dispatch_inputs = runtime_inputs.get("dispatch_inputs") or {}
        if not isinstance(dispatch_inputs, dict):
            raise ValueError(f"Config dispatch_inputs must deserialize to a mapping: {path}")

        runner_labels = dispatch_inputs.get("required_runner_labels", [])
        if isinstance(runner_labels, str):
            runner_labels = [label.strip() for label in runner_labels.split(",") if label.strip()]
        elif not isinstance(runner_labels, list):
            runner_labels = []

        return cls(
            repository=_read_string(
                runtime_inputs,
                env_key="TS1346_REPOSITORY",
                payload_key="repository",
                default="IstiN/trackstate",
            ),
            default_branch=_read_string(
                runtime_inputs,
                env_key="TS1346_DEFAULT_BRANCH",
                payload_key="default_branch",
                default="main",
            ),
            workflow_path=_read_string(
                runtime_inputs,
                env_key="TS1346_WORKFLOW_PATH",
                payload_key="workflow_path",
                default=".github/workflows/build-native.yml",
            ),
            workflow_file=_read_string(
                runtime_inputs,
                env_key="TS1346_WORKFLOW_FILE",
                payload_key="workflow_file",
                default="build-native.yml",
            ),
            reusable_workflow_path=_read_string(
                dispatch_inputs,
                env_key="TS1346_REUSABLE_WORKFLOW_PATH",
                payload_key="reusable_workflow_path",
                default=".github/workflows/build-macos-reusable.yml",
            ),
            build_macos_job_name=_read_string(
                dispatch_inputs,
                env_key="TS1346_BUILD_MACOS_JOB_NAME",
                payload_key="build_macos_job_name",
                default="Build macOS release artifacts",
            ),
            required_runner_labels=tuple(runner_labels),
            release_ref=_read_string(
                dispatch_inputs,
                env_key="TS1346_RELEASE_REF",
                payload_key="release_ref",
                default="auto",
            ),
            run_timeout_seconds=_read_int(
                dispatch_inputs,
                env_key="TS1346_RUN_TIMEOUT_SECONDS",
                payload_key="run_timeout_seconds",
                default=1800,
            ),
            poll_interval_seconds=_read_int(
                dispatch_inputs,
                env_key="TS1346_POLL_INTERVAL_SECONDS",
                payload_key="poll_interval_seconds",
                default=15,
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
