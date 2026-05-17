from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliNonblockingLinkFormatterWarningConfig:
    probe_link_payload: dict[str, str]
    expected_warning_fragments: tuple[str, ...]
    required_text_fragments: tuple[str, ...]

    @classmethod
    def from_defaults(
        cls,
    ) -> "TrackStateCliNonblockingLinkFormatterWarningConfig":
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
            required_text_fragments=(
                "Command: ticket-link",
                "Issue: TS-1 Issue A",
                "Link: blocks inward TS-2",
            ),
        )
