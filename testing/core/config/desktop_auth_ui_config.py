from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class DesktopAuthUIConfig:
    """Static validation configuration for desktop authentication UI scope."""

    test_id: str
    repository_root: Path
    workflow_path: Path
    desktop_build_job_names: list[str] = field(
        default_factory=lambda: ["build-linux", "build-windows", "build-macos"]
    )
    web_build_step_name: str = "Build GitHub Pages web app"
    oauth_dart_defines: list[str] = field(
        default_factory=lambda: [
            "TRACKSTATE_GITHUB_APP_CLIENT_ID",
            "TRACKSTATE_GITHUB_AUTH_PROXY_URL",
        ]
    )
    auth_source_relative_path: str = (
        "lib/ui/features/tracker/views/trackstate_app_widgets_workspace.dart"
    )
    localization_file_relative_path: str = "lib/l10n/app_en.arb"
    conditional_flag: str = "widget.viewModel.isGitHubAppAuthAvailable"
    github_app_button_label_key: str = "continueWithGitHubApp"
    pat_input_label_key: str = "fineGrainedToken"
    connect_button_label_key: str = "connectToken"
    required_label_keys: list[str] = field(
        default_factory=lambda: [
            "fineGrainedToken",
            "fineGrainedTokenHelper",
            "connectToken",
            "continueWithGitHubApp",
        ]
    )
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_file(
        cls, path: Path, repository_root: Path | None = None
    ) -> "DesktopAuthUIConfig":
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
            desktop_build_job_names=runtime_inputs.get(
                "desktop_build_job_names",
                ["build-linux", "build-windows", "build-macos"],
            ),
            web_build_step_name=runtime_inputs.get(
                "web_build_step_name", "Build GitHub Pages web app"
            ),
            oauth_dart_defines=runtime_inputs.get(
                "oauth_dart_defines",
                [
                    "TRACKSTATE_GITHUB_APP_CLIENT_ID",
                    "TRACKSTATE_GITHUB_AUTH_PROXY_URL",
                ],
            ),
            auth_source_relative_path=runtime_inputs.get(
                "auth_source_relative_path",
                "lib/ui/features/tracker/views/trackstate_app_widgets_workspace.dart",
            ),
            localization_file_relative_path=runtime_inputs.get(
                "localization_file_relative_path", "lib/l10n/app_en.arb"
            ),
            conditional_flag=runtime_inputs.get(
                "conditional_flag", "widget.viewModel.isGitHubAppAuthAvailable"
            ),
            github_app_button_label_key=runtime_inputs.get(
                "github_app_button_label_key", "continueWithGitHubApp"
            ),
            pat_input_label_key=runtime_inputs.get(
                "pat_input_label_key", "fineGrainedToken"
            ),
            connect_button_label_key=runtime_inputs.get(
                "connect_button_label_key", "connectToken"
            ),
            required_label_keys=runtime_inputs.get(
                "required_label_keys",
                [
                    "fineGrainedToken",
                    "fineGrainedTokenHelper",
                    "connectToken",
                    "continueWithGitHubApp",
                ],
            ),
            notes=payload.get("notes", []),
        )
