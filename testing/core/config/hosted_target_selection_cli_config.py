from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HostedTargetSelectionCliConfig:
    requested_arguments: tuple[str, ...]
    requested_command_text: str
    expected_provider: str
    expected_target_type: str
    expected_target_value: str
    expected_branch: str
    required_visible_fragments: tuple[str, ...]

    @classmethod
    def from_defaults(cls) -> "HostedTargetSelectionCliConfig":
        arguments = (
            "--target",
            "hosted",
            "--provider",
            "github",
            "--repository",
            "owner/repo",
            "--branch",
            "main",
        )
        return cls(
            requested_arguments=arguments,
            requested_command_text=f"trackstate {' '.join(arguments)}",
            expected_provider="github",
            expected_target_type="hosted",
            expected_target_value="owner/repo",
            expected_branch="main",
            required_visible_fragments=(
                '"provider": "github"',
                '"type": "hosted"',
                '"value": "owner/repo"',
                '"branch": "main"',
            ),
        )
