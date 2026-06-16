from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ReleaseNotesInstructionsConfig:
    """Static validation configuration for release-note launch instructions."""

    test_id: str
    repository_root: Path
    workflow_path: Path
    publish_release_step_name: str = "Publish release"
    unsigned_warning_markers: list[str] = field(
        default_factory=lambda: ["unsigned", "unnotarized"]
    )
    macos_guidance_markers: list[str] = field(
        default_factory=lambda: ["right-click", "Open"]
    )
    windows_guidance_markers: list[str] = field(
        default_factory=lambda: ["More info", "Run anyway"]
    )
    heading_pattern: str = r"^#{2,3}\s+"
    heading_max_lines_before_guidance: int = 3
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_file(
        cls, path: Path, repository_root: Path | None = None
    ) -> "ReleaseNotesInstructionsConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"Config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"Config runtime_inputs must deserialize to a mapping: {path}"
            )

        if repository_root is None:
            repository_root = path.resolve().parents[3]

        workflow_relative = runtime_inputs.get(
            "workflow_path", ".github/workflows/release-on-main.yml"
        )

        return cls(
            test_id=payload.get("test_id", path.parent.name),
            repository_root=repository_root,
            workflow_path=repository_root / workflow_relative,
            publish_release_step_name=runtime_inputs.get(
                "publish_release_step_name", "Publish release"
            ),
            unsigned_warning_markers=runtime_inputs.get(
                "unsigned_warning_markers", ["unsigned", "unnotarized"]
            ),
            macos_guidance_markers=runtime_inputs.get(
                "macos_guidance_markers", ["right-click", "Open"]
            ),
            windows_guidance_markers=runtime_inputs.get(
                "windows_guidance_markers", ["More info", "Run anyway"]
            ),
            heading_pattern=runtime_inputs.get(
                "heading_pattern", r"^#{2,3}\s+"
            ),
            heading_max_lines_before_guidance=runtime_inputs.get(
                "heading_max_lines_before_guidance", 3
            ),
            notes=payload.get("notes", []),
        )
