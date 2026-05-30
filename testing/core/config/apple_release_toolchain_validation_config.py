from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

import yaml


@dataclass(frozen=True)
class AppleReleaseToolchainValidationConfig:
    repository: str
    default_branch: str
    workflow_name: str
    workflow_file: str
    workflow_path: str
    verify_runner_job_name: str
    build_job_name: str
    setup_flutter_step_name: str
    validation_step_name: str
    desktop_build_step_name: str
    cli_build_step_name: str
    required_flutter_version: str
    incompatible_flutter_version: str
    ui_timeout_seconds: int
    run_timeout_seconds: int
    poll_interval_seconds: int
    log_excerpt_lines: int

    @classmethod
    def from_file(cls, path: Path) -> "AppleReleaseToolchainValidationConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-707 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if runtime_inputs and not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-707 config runtime_inputs must deserialize to a mapping: {path}"
            )

        return cls(
            repository=_read_string(
                runtime_inputs,
                env_key="TS707_REPOSITORY",
                payload_key="repository",
                default="IstiN/trackstate",
            ),
            default_branch=_read_string(
                runtime_inputs,
                env_key="TS707_DEFAULT_BRANCH",
                payload_key="default_branch",
                default="main",
            ),
            workflow_name=_read_string(
                runtime_inputs,
                env_key="TS707_WORKFLOW_NAME",
                payload_key="workflow_name",
                default="Apple Release Builds",
            ),
            workflow_file=_read_string(
                runtime_inputs,
                env_key="TS707_WORKFLOW_FILE",
                payload_key="workflow_file",
                default="build-native.yml",
            ),
            workflow_path=_read_string(
                runtime_inputs,
                env_key="TS707_WORKFLOW_PATH",
                payload_key="workflow_path",
                default=".github/workflows/build-native.yml",
            ),
            verify_runner_job_name=_read_string(
                runtime_inputs,
                env_key="TS707_VERIFY_RUNNER_JOB_NAME",
                payload_key="verify_runner_job_name",
                default="Verify macOS runner availability",
            ),
            build_job_name=_read_string(
                runtime_inputs,
                env_key="TS707_BUILD_JOB_NAME",
                payload_key="build_job_name",
                default="Build macOS desktop and CLI artifacts",
            ),
            setup_flutter_step_name=_read_string(
                runtime_inputs,
                env_key="TS707_SETUP_FLUTTER_STEP_NAME",
                payload_key="setup_flutter_step_name",
                default="Set up Flutter",
            ),
            validation_step_name=_read_string(
                runtime_inputs,
                env_key="TS707_VALIDATION_STEP_NAME",
                payload_key="validation_step_name",
                default="Verify runner toolchain",
            ),
            desktop_build_step_name=_read_string(
                runtime_inputs,
                env_key="TS707_DESKTOP_BUILD_STEP_NAME",
                payload_key="desktop_build_step_name",
                default="Build macOS desktop app",
            ),
            cli_build_step_name=_read_string(
                runtime_inputs,
                env_key="TS707_CLI_BUILD_STEP_NAME",
                payload_key="cli_build_step_name",
                default="Build macOS CLI",
            ),
            required_flutter_version=_read_string(
                runtime_inputs,
                env_key="TS707_REQUIRED_FLUTTER_VERSION",
                payload_key="required_flutter_version",
                default="3.35.3",
            ),
            incompatible_flutter_version=_read_string(
                runtime_inputs,
                env_key="TS707_INCOMPATIBLE_FLUTTER_VERSION",
                payload_key="incompatible_flutter_version",
                default="3.30.0",
            ),
            ui_timeout_seconds=_read_int(
                runtime_inputs,
                env_key="TS707_UI_TIMEOUT_SECONDS",
                payload_key="ui_timeout_seconds",
                default=60,
            ),
            run_timeout_seconds=_read_int(
                runtime_inputs,
                env_key="TS707_RUN_TIMEOUT_SECONDS",
                payload_key="run_timeout_seconds",
                default=900,
            ),
            poll_interval_seconds=_read_int(
                runtime_inputs,
                env_key="TS707_POLL_INTERVAL_SECONDS",
                payload_key="poll_interval_seconds",
                default=10,
            ),
            log_excerpt_lines=_read_int(
                runtime_inputs,
                env_key="TS707_LOG_EXCERPT_LINES",
                payload_key="log_excerpt_lines",
                default=40,
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
