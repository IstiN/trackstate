from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliTicketShowHelpConfig:
    requested_command: tuple[str, ...]
    required_actions_header: str
    required_action_name: str
    required_action_description: str
    required_example: str
    forbidden_fragments: tuple[str, ...]

    @property
    def required_action_line(self) -> str:
        return (
            f"{self.required_action_name}"
            f"               {self.required_action_description}"
        )

    @classmethod
    def from_defaults(cls) -> "TrackStateCliTicketShowHelpConfig":
        return cls(
            requested_command=("trackstate", "ticket", "--help"),
            required_actions_header="Actions:",
            required_action_name="show",
            required_action_description=(
                "Display one ticket with TrackState-native detail payload."
            ),
            required_example="trackstate ticket show --target local --key TRACK-1",
            forbidden_fragments=(
                'Unknown ticket action "show"',
                "Unknown ticket action 'show'",
            ),
        )
