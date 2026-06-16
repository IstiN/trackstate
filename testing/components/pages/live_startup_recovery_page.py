from __future__ import annotations

from dataclasses import dataclass
import time

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.utils.polling import poll_until


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


@dataclass(frozen=True)
class StartupRecoveryStateObservation:
    body_text: str
    surface_text: str
    visible_button_labels: tuple[str, ...]
    visible_action_label: str | None
    visible_navigation_labels: tuple[str, ...]
    connect_github_visible: bool
    recovery_markers: tuple[str, ...]
    disallowed_visible_text: tuple[str, ...]


@dataclass(frozen=True)
class StartupRecoveryStateWindowObservation:
    samples: tuple[StartupRecoveryStateObservation, ...]
    failure_messages: tuple[str, ...]

    @property
    def final_snapshot(self) -> StartupRecoveryStateObservation:
        return self.samples[-1]


@dataclass(frozen=True)
class StartupRecoveryShellReadyObservation:
    body_text: str
    location_href: str
    location_hash: str
    location_pathname: str
    visible_navigation_labels: tuple[str, ...]
    visible_button_labels: tuple[str, ...]
    workspace_switcher_visible: bool
    add_workspace_visible: bool


class LiveStartupRecoveryPage:
    _required_navigation_labels = (
        "Dashboard",
        "Board",
        "JQL Search",
        "Hierarchy",
        "Settings",
    )
    _shell_ready_markers = ("Workspace switcher", "Add workspace")
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

    def wait_for_shell_ready(
        self,
        *,
        timeout_ms: int = 120_000,
    ) -> StartupRecoveryShellReadyObservation:
        self._session.wait_for_function(
            r"""
            ({ requiredNavigationLabels, shellReadyMarkers }) => {
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
              const visibleButtonLabels = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .filter(isVisible)
                .map((candidate) => normalize(candidate.innerText))
                .filter((label) => label.length > 0);
              return requiredNavigationLabels.every((label) => bodyText.includes(label))
                && shellReadyMarkers.some(
                  (marker) => bodyText.includes(marker) || visibleButtonLabels.includes(marker),
                );
            }
            """,
            arg={
                "requiredNavigationLabels": list(self._required_navigation_labels),
                "shellReadyMarkers": list(self._shell_ready_markers),
            },
            timeout_ms=timeout_ms,
        )
        return self.observe_shell_ready()

    def observe_shell_ready(self) -> StartupRecoveryShellReadyObservation:
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
                visibleNavigationLabels: requiredNavigationLabels.filter(
                  (label) => bodyText.includes(label),
                ),
                visibleButtonLabels,
                workspaceSwitcherVisible: bodyText.includes('Workspace switcher')
                  || visibleButtonLabels.includes('Workspace switcher'),
                addWorkspaceVisible: bodyText.includes('Add workspace')
                  || visibleButtonLabels.includes('Add workspace'),
              };
            }
            """,
            arg=list(self._required_navigation_labels),
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The startup recovery page did not expose a readable shell-ready snapshot.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return StartupRecoveryShellReadyObservation(
            body_text=str(payload["bodyText"]),
            location_href=str(payload["locationHref"]),
            location_hash=str(payload["locationHash"]),
            location_pathname=str(payload["locationPathname"]),
            visible_navigation_labels=tuple(
                str(item) for item in payload["visibleNavigationLabels"]
            ),
            visible_button_labels=tuple(str(item) for item in payload["visibleButtonLabels"]),
            workspace_switcher_visible=bool(payload["workspaceSwitcherVisible"]),
            add_workspace_visible=bool(payload["addWorkspaceVisible"]),
        )

    def wait_for_shell_routed_to_settings(
        self,
        *,
        timeout_ms: int = 120_000,
        require_retry_action: bool = True,
        require_settings_heading: bool = True,
        required_body_fragments: tuple[str, ...] = (),
    ) -> StartupRecoveryShellObservation:
        self._session.wait_for_function(
            r"""
            ({
              requiredNavigationLabels,
              settingsHeading,
              topbarTitle,
              requireRetryAction,
              requireSettingsHeading,
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
                && (!requireSettingsHeading || bodyText.includes(settingsHeading))
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
                "requireSettingsHeading": require_settings_heading,
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

    def observe_recovery_state(
        self,
        *,
        accepted_action_labels: tuple[str, ...] = ("Retry", "Sync issue"),
        recovery_markers: tuple[str, ...] = ("Retry", "Sync issue", "Connect GitHub"),
        disallowed_visible_text: tuple[str, ...] = (),
    ) -> StartupRecoveryStateObservation:
        payload = self._session.evaluate(
            r"""
            ({ acceptedActionLabels, recoveryMarkers, navigationLabels }) => {
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
              const buttonSelector = 'flt-semantics[role="button"],button,[role="button"]';
              const visibleButtons = Array.from(document.querySelectorAll(buttonSelector))
                .filter(isVisible)
                .map((candidate) => normalize(
                  candidate.getAttribute?.('aria-label')
                    || candidate.innerText
                    || candidate.textContent
                    || '',
                ))
                .filter((label) => label.length > 0);
              const bodyText = normalize(document.body?.innerText ?? '');
              const visibleNavigationLabels = navigationLabels.filter((label) => bodyText.includes(label));
              const visibleActionLabel =
                acceptedActionLabels.find((label) => visibleButtons.includes(label)) ?? null;
              const visibleElements = [document.body, ...Array.from(document.body?.querySelectorAll('*') ?? [])]
                .filter((element) => !!element && isVisible(element));
              const candidates = visibleElements
                .map((element) => {
                  const text = normalize(element.innerText || element.textContent || '');
                  const buttons = [element, ...Array.from(element.querySelectorAll(buttonSelector))]
                    .filter(isVisible)
                    .map((candidate) => normalize(
                      candidate.getAttribute?.('aria-label')
                        || candidate.innerText
                        || candidate.textContent
                        || '',
                    ))
                    .filter((label) => label.length > 0);
                  const connectGitHubVisible =
                    buttons.includes('Connect GitHub') || text.includes('Connect GitHub');
                  const matchingActionLabel =
                    acceptedActionLabels.find((label) => buttons.includes(label)) ?? null;
                  if (!connectGitHubVisible) {
                    return null;
                  }
                  const rect = element.getBoundingClientRect();
                  return {
                    text,
                    area: rect.width * rect.height,
                    bodyPenalty: element === document.body ? 1 : 0,
                    connectGitHubVisible,
                    matchingActionLabel,
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
                surfaceText: best?.text ?? bodyText,
                visibleButtonLabels: visibleButtons,
                visibleActionLabel: visibleActionLabel ?? best?.matchingActionLabel ?? null,
                visibleNavigationLabels,
                connectGitHubVisible: best?.connectGitHubVisible ?? bodyText.includes('Connect GitHub'),
                recoveryMarkers: recoveryMarkers.filter(
                  (marker) => bodyText.includes(marker) || visibleButtons.includes(marker),
                ),
              };
            }
            """,
            arg={
                "acceptedActionLabels": list(accepted_action_labels),
                "recoveryMarkers": list(recovery_markers),
                "navigationLabels": list(self._required_navigation_labels),
            },
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The startup recovery page did not expose a readable recovery-state snapshot.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        body_text = str(payload.get("bodyText", ""))
        return StartupRecoveryStateObservation(
            body_text=body_text,
            surface_text=str(payload.get("surfaceText", body_text)),
            visible_button_labels=tuple(
                str(item) for item in payload.get("visibleButtonLabels", [])
            ),
            visible_action_label=(
                str(payload["visibleActionLabel"])
                if payload.get("visibleActionLabel") is not None
                else None
            ),
            visible_navigation_labels=tuple(
                str(item) for item in payload.get("visibleNavigationLabels", [])
            ),
            connect_github_visible=bool(payload.get("connectGitHubVisible")),
            recovery_markers=tuple(str(item) for item in payload.get("recoveryMarkers", [])),
            disallowed_visible_text=tuple(
                text for text in disallowed_visible_text if text in body_text
            ),
        )

    def recovery_state_failures(
        self,
        observation: StartupRecoveryStateObservation,
        *,
        phase: str,
    ) -> tuple[str, ...]:
        failures: list[str] = []
        if not observation.recovery_markers:
            failures.append(
                f"{phase}: the visible page stopped exposing recovery copy or controls.\n"
                f"Snapshot:\n{observation!r}"
            )
        if observation.visible_navigation_labels:
            failures.append(
                f"{phase}: the shell navigation became visible even though the startup "
                "recovery state should still own the screen.\n"
                f"Visible navigation labels: {list(observation.visible_navigation_labels)!r}\n"
                f"Snapshot:\n{observation!r}"
            )
        if observation.disallowed_visible_text:
            failures.append(
                f"{phase}: the recovery view exposed forbidden workspace text.\n"
                f"Forbidden text: {list(observation.disallowed_visible_text)!r}\n"
                f"Snapshot:\n{observation!r}"
            )
        return tuple(failures)

    def monitor_recovery_state(
        self,
        *,
        duration_seconds: float,
        interval_seconds: float,
        phase: str,
        accepted_action_labels: tuple[str, ...] = ("Retry", "Sync issue"),
        recovery_markers: tuple[str, ...] = ("Retry", "Sync issue", "Connect GitHub"),
        disallowed_visible_text: tuple[str, ...] = (),
    ) -> StartupRecoveryStateWindowObservation:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than zero.")
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero.")

        deadline = time.monotonic() + duration_seconds
        samples: list[StartupRecoveryStateObservation] = []

        _, observation = poll_until(
            probe=lambda: self._monitor_recovery_probe(
                samples=samples,
                deadline=deadline,
                accepted_action_labels=accepted_action_labels,
                recovery_markers=recovery_markers,
                disallowed_visible_text=disallowed_visible_text,
                phase=phase,
            ),
            is_satisfied=lambda observation: bool(observation["failures"])
            or float(observation["remaining_seconds"]) <= 0,
            timeout_seconds=duration_seconds + interval_seconds + 1,
            interval_seconds=interval_seconds,
        )
        failures = tuple(str(message) for message in observation["failures"])
        return StartupRecoveryStateWindowObservation(
            samples=tuple(samples),
            failure_messages=failures,
        )

    def _monitor_recovery_probe(
        self,
        *,
        samples: list[StartupRecoveryStateObservation],
        deadline: float,
        accepted_action_labels: tuple[str, ...],
        recovery_markers: tuple[str, ...],
        disallowed_visible_text: tuple[str, ...],
        phase: str,
    ) -> dict[str, object]:
        snapshot = self.observe_recovery_state(
            accepted_action_labels=accepted_action_labels,
            recovery_markers=recovery_markers,
            disallowed_visible_text=disallowed_visible_text,
        )
        samples.append(snapshot)
        failures = self.recovery_state_failures(
            snapshot,
            phase=f"{phase} sample {len(samples)}",
        )
        return {
            "failures": list(failures),
            "remaining_seconds": deadline - time.monotonic(),
        }

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def tap_retry(self) -> None:
        self._session.click(self._button_selector, has_text="Retry", timeout_ms=30_000)

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)
