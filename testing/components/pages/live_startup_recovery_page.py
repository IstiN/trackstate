from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


@dataclass(frozen=True)
class StartupRecoveryShellObservation:
    body_text: str
    location_href: str
    location_hash: str
    location_pathname: str
    selected_button_labels: tuple[str, ...]
    visible_navigation_labels: tuple[str, ...]
    visible_button_labels: tuple[str, ...]
    retry_visible: bool
    connect_github_visible: bool
    topbar_title_visible: bool
    settings_heading_visible: bool

    @property
    def settings_selected(self) -> bool:
        return "Settings" in self.selected_button_labels


@dataclass(frozen=True)
class StartupRecoverySurfaceObservation:
    body_text: str
    surface_text: str
    visible_button_labels: tuple[str, ...]
    visible_action_label: str | None
    connect_github_visible: bool
    container_tag_name: str | None
    container_role: str | None


class LiveStartupRecoveryPage:
    _required_navigation_labels = (
        "Dashboard",
        "Board",
        "JQL Search",
        "Hierarchy",
        "Settings",
    )
    _settings_heading = "Project settings administration"
    _topbar_title = "Project Settings"
    _button_selector = 'flt-semantics[role="button"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def open(self) -> None:
        self._tracker_page.open_entrypoint()

    def open_route(self, route: str) -> str:
        return self._tracker_page.open_route(route)

    def wait_for_shell_routed_to_settings(
        self,
        *,
        timeout_ms: int = 120_000,
        require_retry_action: bool = True,
        required_body_fragments: tuple[str, ...] = (),
    ) -> StartupRecoveryShellObservation:
        self._session.wait_for_function(
            r"""
            ({
              requiredNavigationLabels,
              settingsHeading,
              topbarTitle,
              requireRetryAction,
              requiredBodyFragments,
            }) => {
              const normalize = (value) => (value ?? '').replace(/\s+/g, ' ').trim();
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0
                  && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const bodyText = document.body?.innerText ?? '';
              const selectedLabels = Array.from(
                document.querySelectorAll('flt-semantics[role="button"][aria-current="true"]'),
              )
                .map((candidate) => normalize(candidate.innerText))
                .filter((label) => label.length > 0);
              const visibleButtonLabels = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .filter(isVisible)
                .map((candidate) => normalize(candidate.innerText))
                .filter((label) => label.length > 0);
              return requiredNavigationLabels.every((label) => bodyText.includes(label))
                && bodyText.includes(settingsHeading)
                && bodyText.includes(topbarTitle)
                && (!requireRetryAction || visibleButtonLabels.includes('Retry'))
                && requiredBodyFragments.every((fragment) => bodyText.includes(fragment))
                && selectedLabels.includes('Settings');
            }
            """,
            arg={
                "requiredNavigationLabels": list(self._required_navigation_labels),
                "settingsHeading": self._settings_heading,
                "topbarTitle": self._topbar_title,
                "requireRetryAction": require_retry_action,
                "requiredBodyFragments": list(required_body_fragments),
            },
            timeout_ms=timeout_ms,
        )
        return self.observe_shell()

    def observe_shell(self) -> StartupRecoveryShellObservation:
        payload = self._session.evaluate(
            r"""
            (requiredNavigationLabels) => {
              const normalize = (value) => (value ?? '').replace(/\s+/g, ' ').trim();
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0
                  && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const bodyText = document.body?.innerText ?? '';
              const selectedButtonLabels = Array.from(
                document.querySelectorAll('flt-semantics[role="button"][aria-current="true"]'),
              )
                .map((candidate) => normalize(candidate.innerText))
                .filter((label) => label.length > 0);
              const visibleButtonLabels = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .filter(isVisible)
                .map((candidate) => normalize(candidate.innerText))
                .filter((label) => label.length > 0);
              return {
                 bodyText,
                 locationHref: window.location.href,
                 locationHash: window.location.hash,
                 locationPathname: window.location.pathname,
                 selectedButtonLabels,
                 visibleNavigationLabels: requiredNavigationLabels.filter(
                   (label) => bodyText.includes(label),
                ),
                visibleButtonLabels,
                retryVisible: visibleButtonLabels.includes('Retry'),
                connectGitHubVisible: bodyText.includes('Connect GitHub'),
                topbarTitleVisible: bodyText.includes('Project Settings'),
                settingsHeadingVisible: bodyText.includes(
                  'Project settings administration',
                ),
              };
            }
            """,
            arg=list(self._required_navigation_labels),
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The startup recovery page did not expose a readable DOM snapshot.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return StartupRecoveryShellObservation(
            body_text=str(payload["bodyText"]),
            location_href=str(payload["locationHref"]),
            location_hash=str(payload["locationHash"]),
            location_pathname=str(payload["locationPathname"]),
            selected_button_labels=tuple(str(item) for item in payload["selectedButtonLabels"]),
            visible_navigation_labels=tuple(
                str(item) for item in payload["visibleNavigationLabels"]
            ),
            visible_button_labels=tuple(str(item) for item in payload["visibleButtonLabels"]),
            retry_visible=bool(payload["retryVisible"]),
            connect_github_visible=bool(payload["connectGitHubVisible"]),
            topbar_title_visible=bool(payload["topbarTitleVisible"]),
            settings_heading_visible=bool(payload["settingsHeadingVisible"]),
        )

    def observe_recovery_surface(
        self,
        *,
        accepted_action_labels: tuple[str, ...] = ("Retry",),
    ) -> StartupRecoverySurfaceObservation:
        payload = self._session.evaluate(
            r"""
            (acceptedActionLabels) => {
              const normalize = (value) => (value ?? '').replace(/\s+/g, ' ').trim();
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0
                  && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const isButton = (element) =>
                !!element?.matches?.('flt-semantics[role="button"],button,[role="button"]');
              const labeledButtons = (root) => {
                const nodes = [];
                if (isButton(root)) {
                  nodes.push(root);
                }
                nodes.push(
                  ...Array.from(
                    root.querySelectorAll('flt-semantics[role="button"],button,[role="button"]'),
                  ),
                );
                return nodes
                  .filter(isVisible)
                  .map((element) => ({
                    element,
                    label: normalize(
                      element.getAttribute?.('aria-label')
                        || element.innerText
                        || element.textContent
                        || '',
                    ),
                  }))
                  .filter((candidate) => candidate.label.length > 0);
              };
              const bodyText = normalize(document.body?.innerText ?? '');
              const visibleElements = [document.body, ...Array.from(document.body?.querySelectorAll('*') ?? [])]
                .filter((element) => !!element && isVisible(element));
              const candidates = visibleElements
                .map((element) => {
                  const text = normalize(element.innerText || element.textContent || '');
                  const buttons = labeledButtons(element);
                  const visibleButtonLabels = buttons.map((candidate) => candidate.label);
                  const visibleActionLabel =
                    acceptedActionLabels.find((label) => visibleButtonLabels.includes(label)) ?? null;
                  const connectGitHubVisible =
                    visibleButtonLabels.includes('Connect GitHub') || text.includes('Connect GitHub');
                  if (!visibleActionLabel || !connectGitHubVisible) {
                    return null;
                  }
                  const rect = element.getBoundingClientRect();
                  return {
                    text,
                    visibleButtonLabels,
                    visibleActionLabel,
                    connectGitHubVisible,
                    containerTagName: element.tagName?.toLowerCase?.() ?? null,
                    containerRole: element.getAttribute?.('role') ?? null,
                    area: rect.width * rect.height,
                    bodyPenalty: element === document.body ? 1 : 0,
                  };
                })
                .filter((candidate) => candidate !== null)
                .sort((left, right) => {
                  if (left.bodyPenalty !== right.bodyPenalty) {
                    return left.bodyPenalty - right.bodyPenalty;
                  }
                  if (left.area !== right.area) {
                    return left.area - right.area;
                  }
                  return left.text.length - right.text.length;
                });
              const best = candidates[0] ?? null;
              return {
                bodyText,
                surfaceText: best?.text ?? '',
                visibleButtonLabels: best?.visibleButtonLabels ?? [],
                visibleActionLabel: best?.visibleActionLabel ?? null,
                connectGitHubVisible: best?.connectGitHubVisible ?? false,
                containerTagName: best?.containerTagName ?? null,
                containerRole: best?.containerRole ?? null,
              };
            }
            """,
            arg=list(accepted_action_labels),
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The startup recovery page did not expose a readable recovery surface.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return StartupRecoverySurfaceObservation(
            body_text=str(payload.get("bodyText", "")),
            surface_text=str(payload.get("surfaceText", "")),
            visible_button_labels=tuple(
                str(item) for item in payload.get("visibleButtonLabels", [])
            ),
            visible_action_label=(
                str(payload["visibleActionLabel"])
                if payload.get("visibleActionLabel") is not None
                else None
            ),
            connect_github_visible=bool(payload.get("connectGitHubVisible")),
            container_tag_name=(
                str(payload["containerTagName"])
                if payload.get("containerTagName") is not None
                else None
            ),
            container_role=(
                str(payload["containerRole"]) if payload.get("containerRole") is not None else None
            ),
        )

    def click_recovery_action(
        self,
        *,
        accepted_action_labels: tuple[str, ...] = ("Retry",),
    ) -> str:
        clicked_label = self._session.evaluate(
            r"""
            (acceptedActionLabels) => {
              const normalize = (value) => (value ?? '').replace(/\s+/g, ' ').trim();
              const isVisible = (element) => {
                if (!element) {
                  return false;
                }
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);
                return rect.width > 0
                  && rect.height > 0
                  && style.visibility !== 'hidden'
                  && style.display !== 'none';
              };
              const isButton = (element) =>
                !!element?.matches?.('flt-semantics[role="button"],button,[role="button"]');
              const labeledButtons = (root) => {
                const nodes = [];
                if (isButton(root)) {
                  nodes.push(root);
                }
                nodes.push(
                  ...Array.from(
                    root.querySelectorAll('flt-semantics[role="button"],button,[role="button"]'),
                  ),
                );
                return nodes
                  .filter(isVisible)
                  .map((element) => ({
                    element,
                    label: normalize(
                      element.getAttribute?.('aria-label')
                        || element.innerText
                        || element.textContent
                        || '',
                    ),
                  }))
                  .filter((candidate) => candidate.label.length > 0);
              };
              const visibleElements = [document.body, ...Array.from(document.body?.querySelectorAll('*') ?? [])]
                .filter((element) => !!element && isVisible(element));
              const candidates = visibleElements
                .map((element) => {
                  const text = normalize(element.innerText || element.textContent || '');
                  const buttons = labeledButtons(element);
                  const visibleButtonLabels = buttons.map((candidate) => candidate.label);
                  const visibleActionLabel =
                    acceptedActionLabels.find((label) => visibleButtonLabels.includes(label)) ?? null;
                  const connectGitHubVisible =
                    visibleButtonLabels.includes('Connect GitHub') || text.includes('Connect GitHub');
                  if (!visibleActionLabel || !connectGitHubVisible) {
                    return null;
                  }
                  const rect = element.getBoundingClientRect();
                  return {
                    buttons,
                    area: rect.width * rect.height,
                    textLength: text.length,
                    bodyPenalty: element === document.body ? 1 : 0,
                  };
                })
                .filter((candidate) => candidate !== null)
                .sort((left, right) => {
                  if (left.bodyPenalty !== right.bodyPenalty) {
                    return left.bodyPenalty - right.bodyPenalty;
                  }
                  if (left.area !== right.area) {
                    return left.area - right.area;
                  }
                  return left.textLength - right.textLength;
                });
              const best = candidates[0] ?? null;
              if (!best) {
                return null;
              }
              const button =
                best.buttons.find((candidate) => acceptedActionLabels.includes(candidate.label)) ?? null;
              if (!button) {
                return null;
              }
              button.element.click();
              return button.label;
            }
            """,
            arg=list(accepted_action_labels),
        )
        if clicked_label is None:
            raise AssertionError(
                "The startup recovery surface did not expose a clickable recovery action.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return str(clicked_label)

    def click_retry(self, *, timeout_ms: int = 30_000) -> None:
        self._session.click(
            self._button_selector,
            has_text="Retry",
            timeout_ms=timeout_ms,
        )

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def tap_retry(self) -> None:
        self._session.click(self._button_selector, has_text="Retry", timeout_ms=30_000)

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)
