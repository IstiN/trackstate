from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliCanonicalLinkFormatterConfig:
    probe_link_payload: dict[str, str]
    required_visible_fragments: tuple[str, ...]

    @classmethod
    def from_defaults(cls) -> "TrackStateCliCanonicalLinkFormatterConfig":
        return cls(
            probe_link_payload={
                "type": "blocks",
                "target": "TS-2",
                "direction": "outward",
            },
            required_visible_fragments=(
                '"type": "blocks"',
                '"direction": "outward"',
                "Link: blocks outward TS-2",
            ),
        )
