from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TrackStateReleaseCandidateObservation:
    id: int
    tag_name: str
    name: str
    html_url: str
    published_at: str | None
    draft: bool
    prerelease: bool
    asset_names: tuple[str, ...]


@dataclass(frozen=True)
class TrackStateReleaseAssetObservation:
    id: int
    name: str
    size_bytes: int
    content_type: str | None
    state: str | None
    browser_download_url: str | None
    classification: str
    sha256: str | None = None
    archive_members: tuple[str, ...] = ()
    extracted_binary_relative_path: str | None = None
    file_output: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class TrackStateReleaseArtifactObservation:
    repository: str
    releases_page_url: str
    selected_release: TrackStateReleaseCandidateObservation | None
    candidate_releases: tuple[TrackStateReleaseCandidateObservation, ...]
    assets: tuple[TrackStateReleaseAssetObservation, ...]
    gh_release_view_command: tuple[str, ...]
    gh_release_view_exit_code: int
    gh_release_view_stdout: str
    gh_release_view_stderr: str
    checksum_manifest_text: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
