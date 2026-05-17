from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliLinkFormatterWarningConfig:
    probe_link_payload: dict[str, str]
    expected_warning_fragments: tuple[str, ...]
    required_visible_fragments: tuple[str, ...]

    @classmethod
    def from_defaults(cls) -> "TrackStateCliLinkFormatterWarningConfig":
        return cls(
            probe_link_payload={
                "type": "blocks",
                "target": "TS-2",
                "direction": "inward",
            },
            expected_warning_fragments=(
                "warning",
                "blocks",
                "inward",
                "outward",
            ),
            required_visible_fragments=(
                '"type": "blocks"',
                '"direction": "inward"',
                "Link: blocks inward TS-2",
            ),
        )
