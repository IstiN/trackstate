from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ReleaseWorkflowStaticConfig:
    """Static validation configuration for release-on-main.yml and related workflows."""

    test_id: str
    repository_root: Path
    workflow_path: Path
    required_triggers: list[str] = field(default_factory=list)
    required_jobs: list[str] = field(default_factory=list)
    forbidden_jobs: list[str] = field(default_factory=list)
    required_job_dependencies: dict[str, list[str]] = field(default_factory=dict)
    required_steps_by_job: dict[str, list[str]] = field(default_factory=dict)
    required_uses_by_job: dict[str, list[str]] = field(default_factory=dict)
    required_outputs_by_job: dict[str, list[str]] = field(default_factory=dict)
    required_env_vars: list[str] = field(default_factory=list)
    required_markers_in_job: dict[str, list[str]] = field(default_factory=dict)
    required_literal_markers_in_job: dict[str, list[str]] = field(default_factory=dict)
    required_call_inputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    required_source_files: list[Path] = field(default_factory=list)
    script_tool_path: Path | None = None
    script_args: list[str] = field(default_factory=list)
    script_expected_outputs: dict[str, str] = field(default_factory=dict)
    semver_tag_pattern: str = r"^v\d+\.\d+\.\d+$"
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path, repository_root: Path | None = None) -> "ReleaseWorkflowStaticConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"Config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(f"Config runtime_inputs must deserialize to a mapping: {path}")

        if repository_root is None:
            repository_root = path.resolve().parents[3]

        workflow_relative = runtime_inputs.get("workflow_path", ".github/workflows/release-on-main.yml")
        script_tool_path = runtime_inputs.get("script_tool_path")

        source_files = runtime_inputs.get("required_source_files", []) or []

        return cls(
            test_id=payload.get("test_id", path.parent.name),
            repository_root=repository_root,
            workflow_path=repository_root / workflow_relative,
            required_triggers=runtime_inputs.get("required_triggers", []),
            required_jobs=runtime_inputs.get("required_jobs", []),
            forbidden_jobs=runtime_inputs.get("forbidden_jobs", []),
            required_job_dependencies=runtime_inputs.get("required_job_dependencies", {}),
            required_steps_by_job=runtime_inputs.get("required_steps_by_job", {}),
            required_uses_by_job=runtime_inputs.get("required_uses_by_job", {}),
            required_outputs_by_job=runtime_inputs.get("required_outputs_by_job", {}),
            required_env_vars=runtime_inputs.get("required_env_vars", []),
            required_markers_in_job=runtime_inputs.get("required_markers_in_job", {}),
            required_literal_markers_in_job=runtime_inputs.get("required_literal_markers_in_job", {}),
            required_call_inputs=runtime_inputs.get("required_call_inputs", {}),
            required_source_files=[repository_root / Path(p) for p in source_files],
            script_tool_path=repository_root / script_tool_path if script_tool_path else None,
            script_args=runtime_inputs.get("script_args", []),
            script_expected_outputs=runtime_inputs.get("script_expected_outputs", {}),
            semver_tag_pattern=runtime_inputs.get("semver_tag_pattern", r"^v\d+\.\d+\.\d+$"),
            notes=payload.get("notes", []),
        )
