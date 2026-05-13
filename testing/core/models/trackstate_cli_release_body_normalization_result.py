from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseBodyNormalizationSeededRelease:
    id: int
    tag_name: str
    name: str
    body: str
    draft: bool
    prerelease: bool


@dataclass(frozen=True)
class TrackStateCliReleaseBodyNormalizationRepositoryState:
    issue_main_exists: bool
    source_file_exists: bool
    manifest_exists: bool
    manifest_text: str | None
    git_status_lines: tuple[str, ...]
    remote_origin_url: str | None


@dataclass(frozen=True)
class TrackStateCliReleaseBodyNormalizationValidationResult:
    release_tag_prefix: str
    release_tag: str
    remote_origin_url: str
    compiled_binary_path: str
    seeded_release: TrackStateCliReleaseBodyNormalizationSeededRelease
    initial_state: TrackStateCliReleaseBodyNormalizationRepositoryState
    observation: TrackStateCliCommandObservation
    final_state: TrackStateCliReleaseBodyNormalizationRepositoryState
    manifest_observation: dict[str, object]
    release_observation: dict[str, object]
    gh_release_view: dict[str, object]
    cleanup: dict[str, object]
