from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_root_links_json_exclusivity_result import (
    TrackStateCliRootLinksJsonExclusivityObservation,
)


@dataclass(frozen=True)
class TrackStateCliLegacyLocalLinksJsonPurgeObservation(
    TrackStateCliRootLinksJsonExclusivityObservation
):
    legacy_links_json_relative_path: str
    legacy_links_json_content_before_link: str | None
    legacy_links_json_payload_before_link: object | None
    issue_a_directory_entries_before_link: tuple[str, ...]


@dataclass(frozen=True)
class TrackStateCliLegacyLocalLinksJsonPurgeValidationResult:
    observation: TrackStateCliLegacyLocalLinksJsonPurgeObservation
