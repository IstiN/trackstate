from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class GitHubReleaseHeadingObservation:
    level: int
    text: str


@dataclass(frozen=True)
class GitHubReleaseAssetObservation:
    label: str
    aria_label: str | None
    href: str
    tabindex: str | None
    keyboard_focusable: bool


@dataclass(frozen=True)
class GitHubReleaseDigestObservation:
    label: str
    value: str


@dataclass(frozen=True)
class GitHubReleaseFocusObservation:
    tag_name: str
    role: str | None
    label: str | None
    href: str | None


@dataclass(frozen=True)
class GitHubReleaseDownloadObservation:
    label: str
    href: str
    suggested_filename: str


@dataclass(frozen=True)
class GitHubReleaseAccessibilityObservation:
    repository: str
    tag_name: str
    release_page_url: str
    release_title: str
    asset_section_label: str
    headings: list[GitHubReleaseHeadingObservation]
    quick_start_heading_present: bool
    quick_start_heading_is_logical: bool
    quick_start_focus_labels: list[str]
    quick_start_expected_focus_order: list[GitHubReleaseFocusObservation]
    quick_start_focus_order: list[GitHubReleaseFocusObservation]
    assets: list[GitHubReleaseAssetObservation]
    digests: list[GitHubReleaseDigestObservation]
    asset_expected_focus_order: list[GitHubReleaseFocusObservation]
    asset_focus_order: list[GitHubReleaseFocusObservation]
    downloads: list[GitHubReleaseDownloadObservation]
    release_note_text_color_hex: str
    release_note_background_color_hex: str
    release_note_contrast_ratio: float
    screenshot_path: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubReleaseAccessibilityProbe(Protocol):
    def validate(self) -> GitHubReleaseAccessibilityObservation: ...
