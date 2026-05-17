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
    quick_start_expected_focus_order: list[GitHubReleaseFocusObservation]
    assets: list[GitHubReleaseAssetObservation]
    digests: list[GitHubReleaseDigestObservation]
    asset_expected_focus_order: list[GitHubReleaseFocusObservation]
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
        asset_focus_order = self._observe_focus_order(
            group="asset",
            stop_count=len(snapshot.asset_expected_focus_order),
        )
        quick_start_focus_order = self._observe_focus_order(
            group="quick-start",
            stop_count=len(snapshot.quick_start_expected_focus_order),
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
            quick_start_focus_labels=[step.label or "" for step in quick_start_focus_order],
            quick_start_expected_focus_order=snapshot.quick_start_expected_focus_order,
            quick_start_focus_order=quick_start_focus_order,
            assets=snapshot.assets,
            digests=snapshot.digests,
            asset_expected_focus_order=snapshot.asset_expected_focus_order,
            asset_focus_order=asset_focus_order,
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
                const focusableSelector =
                    'summary, a[href], button, input, select, textarea, [tabindex], clipboard-copy';
                const isKeyboardFocusable = (node) => {
                    if (!(node instanceof HTMLElement)) {
                        return false;
                    }
                    if (node.hasAttribute('disabled') || node.closest('[hidden], [inert]')) {
                        return false;
                    }
                    const tabindex = node.getAttribute('tabindex');
                    if (tabindex === '-1') {
                        return false;
                    }
                    if (node.tagName === 'A') {
                        return node.hasAttribute('href');
                    }
                    if (node.tagName === 'SUMMARY' || node.tagName === 'CLIPBOARD-COPY') {
                        return true;
                    }
                    return ['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'].includes(node.tagName)
                        || node.hasAttribute('tabindex');
                };
                const accessibleLabel = (node) =>
                    normalize(node.getAttribute('aria-label')) || normalize(node.textContent);
                const toFocusObservation = (node) => ({
                    tagName: node.tagName,
                    role: node.getAttribute('role'),
                    label: accessibleLabel(node),
                    href: node.getAttribute('href') || null,
                });
                const collectFocusableDescendants = (root, excludedNodes = []) => {
                    const excluded = new Set(excludedNodes);
                    return Array.from(root.querySelectorAll(focusableSelector)).filter(
                        (node) => !excluded.has(node) && isKeyboardFocusable(node),
                    );
                };
                const markFocusGroup = (nodes, group) => {
                    nodes.forEach((node, index) => {
                        node.setAttribute('data-ts710-focus-group', group);
                        node.setAttribute('data-ts710-focus-index', String(index));
                    });
                };
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
                let quickStartFocusNodes = [];
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

                    quickStartFocusNodes = sectionNodes.flatMap((node) =>
                        collectFocusableDescendants(node),
                    );
                }

                const assetsSummary = Array.from(document.querySelectorAll('summary')).find(
                    (node) => normalize(node.textContent).includes('Assets'),
                );
                const assetContainer = assetsSummary?.closest('details') || null;
                const assetFocusNodes = assetsSummary
                    ? [
                        assetsSummary,
                        ...(
                            assetContainer
                                ? collectFocusableDescendants(assetContainer, [assetsSummary])
                                : []
                        ),
                    ]
                    : [];
                markFocusGroup(assetFocusNodes, 'asset');
                markFocusGroup(quickStartFocusNodes, 'quick-start');
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
                    quickStartExpectedFocusOrder: quickStartFocusNodes.map(toFocusObservation),
                    assets: assetLinks,
                    digests: digestControls,
                    assetExpectedFocusOrder: assetFocusNodes.map(toFocusObservation),
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
        asset_expected_focus_order = self._parse_focus_observations(
            payload.get("assetExpectedFocusOrder", []),
        )
        quick_start_expected_focus_order = self._parse_focus_observations(
            payload.get("quickStartExpectedFocusOrder", []),
        )

        return _ReleasePageSnapshot(
            release_title=str(payload.get("releaseTitle", "")),
            asset_section_label=str(payload.get("assetSectionLabel", "")),
            headings=headings,
            quick_start_heading_present=bool(payload.get("quickStartHeadingPresent")),
            quick_start_heading_is_logical=bool(
                payload.get("quickStartHeadingIsLogical", True),
            ),
            quick_start_expected_focus_order=quick_start_expected_focus_order,
            assets=assets,
            digests=digests,
            asset_expected_focus_order=asset_expected_focus_order,
            release_note_text_color=self._parse_rgb(
                str(payload.get("releaseNoteTextColor", "rgb(0, 0, 0)")),
            ),
            release_note_background_color=self._parse_rgb(
                str(payload.get("releaseNoteBackgroundColor", "rgb(255, 255, 255)")),
            ),
        )

    def _observe_focus_order(
        self,
        *,
        group: str,
        stop_count: int,
    ) -> list[GitHubReleaseFocusObservation]:
        if stop_count <= 0:
            return []
        self._session.focus(
            f'[data-ts710-focus-group="{group}"][data-ts710-focus-index="0"]',
        )
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
                            || normalize(active.textContent),
                        href: active.getAttribute('href'),
                    };
                }
                """,
            )
            if not isinstance(payload, dict):
                raise AssertionError(
                    "Could not observe keyboard focus while traversing the live GitHub "
                    f"release page focus group: {group}.",
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

    @staticmethod
    def _parse_focus_observations(items: object) -> list[GitHubReleaseFocusObservation]:
        if not isinstance(items, list):
            return []
        return [
            GitHubReleaseFocusObservation(
                tag_name=str(item.get("tagName", "")),
                role=str(item["role"]) if item.get("role") is not None else None,
                label=str(item["label"]) if item.get("label") is not None else None,
                href=str(item["href"]) if item.get("href") is not None else None,
            )
            for item in items
            if isinstance(item, dict)
        ]

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
