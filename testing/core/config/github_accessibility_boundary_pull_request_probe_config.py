from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from testing.core.config.github_accessibility_pull_request_gate_config import (
    GitHubAccessibilityPullRequestGateConfig,
)


@dataclass(frozen=True)
class GitHubAccessibilityBoundaryPullRequestProbeConfig(
    GitHubAccessibilityPullRequestGateConfig
):
    exact_contrast_ratio: float = 4.5
    contrast_tolerance: float = 0.01
    text_color: str = "rgb(50, 50, 50)"
    background_color: str = "rgb(153, 153, 153)"
    visible_text: str = "Boundary contrast sample"
    accessible_button_label: str = "Open tracker settings"

    @classmethod
    def from_file(
        cls, path: Path
    ) -> "GitHubAccessibilityBoundaryPullRequestProbeConfig":
        base = GitHubAccessibilityPullRequestGateConfig.from_file(path)
        runtime_inputs = cls._load_runtime_inputs(path)
        return cls(
            repository=base.repository,
            base_branch=base.base_branch,
            target_workflow_name=base.target_workflow_name,
            target_workflow_path=base.target_workflow_path,
            probe_path=base.probe_path,
            probe_render_host_path=base.probe_render_host_path,
            branch_prefix=base.branch_prefix,
            commit_message=base.commit_message,
            pull_request_title=base.pull_request_title,
            pull_request_body=base.pull_request_body,
            expected_accessibility_markers=base.expected_accessibility_markers,
            contrast_evidence_markers=base.contrast_evidence_markers,
            semantic_evidence_markers=base.semantic_evidence_markers,
            poll_interval_seconds=base.poll_interval_seconds,
            run_timeout_seconds=base.run_timeout_seconds,
            pull_request_timeout_seconds=base.pull_request_timeout_seconds,
            exact_contrast_ratio=cls._require_positive_number(
                runtime_inputs,
                "exact_contrast_ratio",
                path,
                default=4.5,
            ),
            contrast_tolerance=cls._require_positive_number(
                runtime_inputs,
                "contrast_tolerance",
                path,
                default=0.01,
            ),
            text_color=cls._require_string(runtime_inputs, "text_color", path),
            background_color=cls._require_string(runtime_inputs, "background_color", path),
            visible_text=cls._require_string(runtime_inputs, "visible_text", path),
            accessible_button_label=cls._require_string(
                runtime_inputs,
                "accessible_button_label",
                path,
            ),
        )

    @staticmethod
    def _load_runtime_inputs(path: Path) -> dict[str, object]:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "GitHub accessibility boundary probe config must deserialize to a "
                f"mapping: {path}"
            )
        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "GitHub accessibility boundary probe config runtime_inputs must "
                f"deserialize to a mapping: {path}"
            )
        return runtime_inputs

    @staticmethod
    def _require_positive_number(
        payload: dict[str, object],
        key: str,
        path: Path,
        *,
        default: float,
    ) -> float:
        value = payload.get(key, default)
        if not isinstance(value, (int, float)) or float(value) <= 0:
            raise ValueError(
                "GitHub accessibility boundary probe config runtime_inputs."
                f"{key} must be a positive number in {path}."
            )
        return float(value)
