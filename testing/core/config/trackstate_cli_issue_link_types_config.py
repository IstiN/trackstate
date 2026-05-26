from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IssueLinkTypeFixture:
    id: str
    name: str
    outward: str
    inward: str

    def to_payload(self) -> dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "outward": self.outward,
            "inward": self.inward,
        }


@dataclass(frozen=True)
class TrackStateCliIssueLinkTypesConfig:
    project_key: str
    project_name: str
    ticket_command: tuple[str, ...]
    canonical_command: tuple[str, ...]
    expected_link_types: tuple[IssueLinkTypeFixture, ...]

    @classmethod
    def from_defaults(cls) -> "TrackStateCliIssueLinkTypesConfig":
        return cls(
            project_key="TRACK",
            project_name="TrackState Issue Link Types Test Project",
            ticket_command=("trackstate", "read", "issue-link-types"),
            canonical_command=("trackstate", "read", "link-types"),
            expected_link_types=(
                IssueLinkTypeFixture(
                    id="blocks",
                    name="Blocks",
                    outward="blocks",
                    inward="is blocked by",
                ),
                IssueLinkTypeFixture(
                    id="relates-to",
                    name="Relates",
                    outward="relates to",
                    inward="relates to",
                ),
                IssueLinkTypeFixture(
                    id="duplicates",
                    name="Duplicates",
                    outward="duplicates",
                    inward="is duplicated by",
                ),
                IssueLinkTypeFixture(
                    id="clones",
                    name="Clones",
                    outward="clones",
                    inward="is cloned by",
                ),
            ),
        )
