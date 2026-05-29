from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RepositoryReleaseTagsObservation:
    repository: str
    releases_api_url: str
    tags_api_url: str
    releases_status_code: int | None
    tags_status_code: int | None
    release_tag_names: list[str]
    tag_names: list[str]
    stable_release_versions: list[str]
    stable_tag_versions: list[str]
    common_stable_versions: list[str]
    latest_common_stable_version: str | None
    releases_page_url: str
    tags_page_url: str
    releases_page_text: str
    tags_page_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RepositoryReleaseTagsProbe(Protocol):
    def validate(self) -> RepositoryReleaseTagsObservation: ...
