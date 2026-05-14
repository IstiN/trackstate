from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from testing.core.interfaces.github_release_accessibility_probe import (
    GitHubReleaseAccessibilityObservation,
    GitHubReleaseAssetObservation,
    GitHubReleaseDigestObservation,
    GitHubReleaseDownloadObservation,
    GitHubReleaseFocusObservation,
    GitHubReleaseHeadingObservation,
)
from testing.core.interfaces.web_app_session import WebAppSession, WebAppTimeoutError
from testing.core.utils.color_contrast import RgbColor, contrast_ratio, rgb_to_hex


@dataclass(frozen=True)
class _ReleasePageSnapshot:
    release_title: str
    asset_section_label: str
    headings: list[GitHubReleaseHeadingObservation]
    quick_start_heading_present: bool
    quick_start_heading_is_logical: bool
    quick_start_focus_labels: list[str]
    assets: list[GitHubReleaseAssetObservation]
    digests: list[GitHubReleaseDigestObservation]
    release_note_text_color: RgbColor
    release_note_background_color: RgbColor


class GitHubReleasePage:
    _release_body_selector = '[data-test-selector="body-content"]'
    _asset_summary_selector = "summary"
    _asset_link_selector = (
        'a[href*="/releases/download/"], a[href*="/archive/refs/tags/"]'
    )

    def __init__(self, session: WebAppSession) -> None:
        self._session = session

    def open_release(
        self,
        *,
        repository: str,
        tag_name: str,
        timeout_seconds: int = 60,
    ) -> str:
        url = self._build_release_url(repository=repository, tag_name=tag_name)
        try:
            self._session.goto(
                url,
                wait_until="domcontentloaded",
                timeout_ms=timeout_seconds * 1_000,
            )
            self._session.wait_for_text("Assets", timeout_ms=timeout_seconds * 1_000)
            self._session.wait_for_function(
                """
                () => {
                    const assetSummary = Array.from(document.querySelectorAll('summary'))
                      .find((node) => (node.innerText || '').includes('Assets'));
                    const releaseBody = document.querySelector('[data-test-selector="body-content"]');
                    const assetLinks = document.querySelectorAll(
                      'a[href*="/releases/download/"], a[href*="/archive/refs/tags/"]',
                    );
                    return !!assetSummary && !!releaseBody && assetLinks.length > 0;
                }
                """,
                timeout_ms=timeout_seconds * 1_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Could not open the live GitHub release page for accessibility "
                f"verification.\nURL: {url}\nVisible body text:\n{self._session.body_text()}",
            ) from error
        return url

    def observe_accessibility(
        self,
        *,
        repository: str,
        tag_name: str,
        release_page_url: str,
        screenshot_path: str | None = None,
    ) -> GitHubReleaseAccessibilityObservation:
        snapshot = self._snapshot_page()
        focus_order = self._observe_asset_focus_order(
            stop_count=1 + len(snapshot.assets) + len(snapshot.digests),
        )
        downloads = self._download_assets_via_keyboard(snapshot.assets)
        captured_screenshot_path = self._capture_screenshot(screenshot_path)

        return GitHubReleaseAccessibilityObservation(
            repository=repository,
            tag_name=tag_name,
            release_page_url=release_page_url,
            release_title=snapshot.release_title,
            asset_section_label=snapshot.asset_section_label,
            headings=snapshot.headings,
            quick_start_heading_present=snapshot.quick_start_heading_present,
            quick_start_heading_is_logical=snapshot.quick_start_heading_is_logical,
            quick_start_focus_labels=snapshot.quick_start_focus_labels,
            assets=snapshot.assets,
            digests=snapshot.digests,
            asset_focus_order=focus_order,
            downloads=downloads,
            release_note_text_color_hex=rgb_to_hex(snapshot.release_note_text_color),
            release_note_background_color_hex=rgb_to_hex(
                snapshot.release_note_background_color,
            ),
            release_note_contrast_ratio=contrast_ratio(
                snapshot.release_note_text_color,
                snapshot.release_note_background_color,
            ),
            screenshot_path=captured_screenshot_path,
        )

    def _snapshot_page(self) -> _ReleasePageSnapshot:
        payload = self._session.evaluate(
            """
            () => {
                const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                const releaseBody = document.querySelector('[data-test-selector="body-content"]');
                if (!releaseBody) {
                    return null;
                }

                const headings = Array.from(
                    releaseBody.querySelectorAll('h1,h2,h3,h4,h5,h6'),
                ).map((node) => ({
                    level: Number(node.tagName.slice(1)),
                    text: normalize(node.textContent),
                }));

                const quickStartIndex = headings.findIndex((heading) =>
                    heading.text.toLowerCase().includes('quick start'),
                );
                let quickStartHeadingIsLogical = true;
                let quickStartFocusLabels = [];
                if (quickStartIndex >= 0) {
                    const sectionHeadings = Array.from(
                        releaseBody.querySelectorAll('h1,h2,h3,h4,h5,h6'),
                    );
                    const quickStartHeading = sectionHeadings[quickStartIndex];
                    const quickStartLevel = Number(quickStartHeading.tagName.slice(1));
                    const previousHeading = sectionHeadings[quickStartIndex - 1] || null;
                    if (previousHeading) {
                        const previousLevel = Number(previousHeading.tagName.slice(1));
                        quickStartHeadingIsLogical = quickStartLevel <= previousLevel + 1;
                    }

                    const isFocusable = (node) => {
                        if (!(node instanceof HTMLElement)) {
                            return false;
                        }
                        if (node.hasAttribute('disabled')) {
                            return false;
                        }
                        const tabindex = node.getAttribute('tabindex');
                        if (tabindex === '-1') {
                            return false;
                        }
                        if (node.tagName === 'A') {
                            return node.hasAttribute('href');
                        }
                        return ['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'].includes(node.tagName)
                            || node.hasAttribute('tabindex');
                    };

                    const focusableLabel = (node) =>
                        normalize(node.getAttribute('aria-label')) || normalize(node.textContent);

                    const sectionNodes = [];
                    for (
                        let node = quickStartHeading.nextElementSibling;
                        node;
                        node = node.nextElementSibling
                    ) {
                        if (
                            /^H[1-6]$/.test(node.tagName)
                            && Number(node.tagName.slice(1)) <= quickStartLevel
                        ) {
                            break;
                        }
                        sectionNodes.push(node);
                    }

                    quickStartFocusLabels = sectionNodes.flatMap((node) =>
                        Array.from(
                            node.querySelectorAll(
                                'a, button, input, select, textarea, [tabindex]',
                            ),
                        )
                            .filter(isFocusable)
                            .map(focusableLabel)
                            .filter((label) => label.length > 0),
                    );
                }

                const assetsSummary = Array.from(document.querySelectorAll('summary')).find(
                    (node) => normalize(node.textContent).includes('Assets'),
                );
                const assetLinks = Array.from(
                    document.querySelectorAll(
                        'a[href*="/releases/download/"], a[href*="/archive/refs/tags/"]',
                    ),
                ).map((node) => ({
                    label: normalize(node.textContent),
                    ariaLabel: normalize(node.getAttribute('aria-label')) || null,
                    href: node.getAttribute('href') || '',
                    tabindex: node.getAttribute('tabindex'),
                    keyboardFocusable:
                        node.getAttribute('tabindex') !== '-1'
                        && node.hasAttribute('href'),
                }));

                const digestControls = Array.from(
                    document.querySelectorAll('clipboard-copy'),
                ).map((node) => ({
                    label: normalize(node.getAttribute('aria-label')),
                    value: normalize(node.getAttribute('value')),
                }));

                const effectiveBackground = (node) => {
                    for (let current = node; current; current = current.parentElement) {
                        const backgroundColor = getComputedStyle(current).backgroundColor;
                        if (
                            backgroundColor
                            && backgroundColor !== 'rgba(0, 0, 0, 0)'
                            && backgroundColor !== 'transparent'
                        ) {
                            return backgroundColor;
                        }
                    }
                    return getComputedStyle(document.body).backgroundColor;
                };

                const noteTextNode =
                    releaseBody.querySelector('p, li, h1, h2, h3, h4, h5, h6')
                    || releaseBody;
                const noteStyle = getComputedStyle(noteTextNode);

                return {
                    releaseTitle: document.title,
                    assetSectionLabel: assetsSummary ? normalize(assetsSummary.textContent) : '',
                    headings,
                    quickStartHeadingPresent: quickStartIndex >= 0,
                    quickStartHeadingIsLogical,
                    quickStartFocusLabels,
                    assets: assetLinks,
                    digests: digestControls,
                    releaseNoteTextColor: noteStyle.color,
                    releaseNoteBackgroundColor: effectiveBackground(noteTextNode),
                };
            }
            """,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The live GitHub release page did not expose the expected release body "
                "content for accessibility verification.",
            )

        headings = [
            GitHubReleaseHeadingObservation(
                level=int(item["level"]),
                text=str(item["text"]),
            )
            for item in payload.get("headings", [])
            if isinstance(item, dict)
        ]
        assets = [
            GitHubReleaseAssetObservation(
                label=str(item["label"]),
                aria_label=(
                    str(item["ariaLabel"]) if item.get("ariaLabel") is not None else None
                ),
                href=str(item["href"]),
                tabindex=(
                    str(item["tabindex"]) if item.get("tabindex") is not None else None
                ),
                keyboard_focusable=bool(item.get("keyboardFocusable")),
            )
            for item in payload.get("assets", [])
            if isinstance(item, dict)
        ]
        digests = [
            GitHubReleaseDigestObservation(
                label=str(item["label"]),
                value=str(item["value"]),
            )
            for item in payload.get("digests", [])
            if isinstance(item, dict)
        ]

        return _ReleasePageSnapshot(
            release_title=str(payload.get("releaseTitle", "")),
            asset_section_label=str(payload.get("assetSectionLabel", "")),
            headings=headings,
            quick_start_heading_present=bool(payload.get("quickStartHeadingPresent")),
            quick_start_heading_is_logical=bool(
                payload.get("quickStartHeadingIsLogical", True),
            ),
            quick_start_focus_labels=[
                str(label)
                for label in payload.get("quickStartFocusLabels", [])
                if isinstance(label, str)
            ],
            assets=assets,
            digests=digests,
            release_note_text_color=self._parse_rgb(
                str(payload.get("releaseNoteTextColor", "rgb(0, 0, 0)")),
            ),
            release_note_background_color=self._parse_rgb(
                str(payload.get("releaseNoteBackgroundColor", "rgb(255, 255, 255)")),
            ),
        )

    def _observe_asset_focus_order(
        self,
        *,
        stop_count: int,
    ) -> list[GitHubReleaseFocusObservation]:
        self._session.focus(self._asset_summary_selector, has_text="Assets")
        observations: list[GitHubReleaseFocusObservation] = []
        for index in range(max(stop_count, 1)):
            payload = self._session.evaluate(
                """
                () => {
                    const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                    const active = document.activeElement;
                    if (!active) {
                        return {
                            tagName: '',
                            role: null,
                            label: null,
                            href: null,
                        };
                    }
                    return {
                        tagName: active.tagName,
                        role: active.getAttribute('role'),
                        label:
                            normalize(active.getAttribute('aria-label'))
                            || normalize(active.textContent)
                            || null,
                        href: active.getAttribute('href'),
                    };
                }
                """,
            )
            if not isinstance(payload, dict):
                raise AssertionError(
                    "Could not observe keyboard focus while traversing the Assets section.",
                )
            observations.append(
                GitHubReleaseFocusObservation(
                    tag_name=str(payload.get("tagName", "")),
                    role=str(payload["role"]) if payload.get("role") is not None else None,
                    label=(
                        str(payload["label"]) if payload.get("label") is not None else None
                    ),
                    href=str(payload["href"]) if payload.get("href") is not None else None,
                ),
            )
            if index < stop_count - 1:
                self._session.press_key("Tab")
        return observations

    def _download_assets_via_keyboard(
        self,
        assets: list[GitHubReleaseAssetObservation],
    ) -> list[GitHubReleaseDownloadObservation]:
        downloads: list[GitHubReleaseDownloadObservation] = []
        for index, asset in enumerate(assets):
            self._session.focus(self._asset_link_selector, index=index)
            suggested_filename = self._session.wait_for_download_after_keypress(
                "Enter",
                timeout_ms=30_000,
            )
            downloads.append(
                GitHubReleaseDownloadObservation(
                    label=asset.label or asset.aria_label or asset.href,
                    href=asset.href,
                    suggested_filename=suggested_filename,
                ),
            )
        return downloads

    def _capture_screenshot(self, screenshot_path: str | None) -> str | None:
        if screenshot_path is None:
            return None
        destination = Path(screenshot_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._session.screenshot(str(destination))
        return str(destination) if destination.exists() else None

    @staticmethod
    def _build_release_url(*, repository: str, tag_name: str) -> str:
        return f"https://github.com/{repository}/releases/tag/{quote(tag_name, safe='')}"

    @staticmethod
    def _parse_rgb(value: str) -> RgbColor:
        normalized = value.strip()
        if normalized.startswith("rgba("):
            channels = normalized[5:-1].split(",")[:3]
        elif normalized.startswith("rgb("):
            channels = normalized[4:-1].split(",")[:3]
        else:
            raise ValueError(f"Unsupported CSS color: {value}")
        return tuple(int(float(channel.strip())) for channel in channels)  # type: ignore[return-value]
