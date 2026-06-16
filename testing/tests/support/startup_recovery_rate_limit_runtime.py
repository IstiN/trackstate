from __future__ import annotations

from contextlib import AbstractContextManager
import json
import time
from dataclasses import dataclass, field
from threading import Lock
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Browser, BrowserContext, Page, Request, Route, sync_playwright

from testing.frameworks.python.playwright_web_app_session import PlaywrightWebAppSession


@dataclass(frozen=True)
class StartupRecoveryObservedEvent:
    observed_order: int
    observed_at_monotonic: float


@dataclass(frozen=True)
class StartupRecoveryBlockedRequestObservation(StartupRecoveryObservedEvent):
    url: str
    request_observed_at_performance_ms: float
    body_text_snapshot: str
    visible_navigation_labels: tuple[str, ...]
    settings_selected: bool
    settings_heading_visible: bool
    topbar_title_visible: bool
    shell_ready_observed_before_request: bool
    shell_ready_observed_order: int | None
    shell_ready_observed_at_performance_ms: float | None
    shell_ready_body_text_snapshot: str
    shell_ready_visible_navigation_labels: tuple[str, ...]
    shell_ready_visible_button_labels: tuple[str, ...]
    shell_ready_workspace_switcher_visible: bool
    shell_ready_add_workspace_visible: bool


@dataclass
class StartupRecoveryRateLimitObservation:
    blocked_repository_path: str
    blocked_requests: list[StartupRecoveryBlockedRequestObservation] = field(
        default_factory=list,
    )
    shell_ready_event: StartupRecoveryObservedEvent | None = None
    _next_observed_order: int = field(default=1, init=False, repr=False)
    _event_lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def record_blocked_request(
        self,
        url: str,
        *,
        request_observed_at_performance_ms: float,
        body_text_snapshot: str,
        visible_navigation_labels: tuple[str, ...],
        settings_selected: bool,
        settings_heading_visible: bool,
        topbar_title_visible: bool,
        shell_ready_observed_before_request: bool,
        shell_ready_observed_order: int | None,
        shell_ready_observed_at_performance_ms: float | None,
        shell_ready_body_text_snapshot: str,
        shell_ready_visible_navigation_labels: tuple[str, ...],
        shell_ready_visible_button_labels: tuple[str, ...],
        shell_ready_workspace_switcher_visible: bool,
        shell_ready_add_workspace_visible: bool,
    ) -> StartupRecoveryBlockedRequestObservation:
        observation = StartupRecoveryBlockedRequestObservation(
            url=url,
            request_observed_at_performance_ms=request_observed_at_performance_ms,
            body_text_snapshot=body_text_snapshot,
            visible_navigation_labels=visible_navigation_labels,
            settings_selected=settings_selected,
            settings_heading_visible=settings_heading_visible,
            topbar_title_visible=topbar_title_visible,
            shell_ready_observed_before_request=shell_ready_observed_before_request,
            shell_ready_observed_order=shell_ready_observed_order,
            shell_ready_observed_at_performance_ms=shell_ready_observed_at_performance_ms,
            shell_ready_body_text_snapshot=shell_ready_body_text_snapshot,
            shell_ready_visible_navigation_labels=shell_ready_visible_navigation_labels,
            shell_ready_visible_button_labels=shell_ready_visible_button_labels,
            shell_ready_workspace_switcher_visible=shell_ready_workspace_switcher_visible,
            shell_ready_add_workspace_visible=shell_ready_add_workspace_visible,
            **self._reserve_event_payload(),
        )
        self.blocked_requests.append(observation)
        return observation

    def record_shell_ready(self) -> StartupRecoveryObservedEvent:
        if self.shell_ready_event is not None:
            return self.shell_ready_event
        self.shell_ready_event = StartupRecoveryObservedEvent(
            **self._reserve_event_payload(),
        )
        return self.shell_ready_event

    def _reserve_event_payload(self) -> dict[str, float | int]:
        with self._event_lock:
            observed_order = self._next_observed_order
            self._next_observed_order += 1
        return {
            "observed_order": observed_order,
            "observed_at_monotonic": time.monotonic(),
        }

    @property
    def blocked_was_exercised(self) -> bool:
        return len(self.blocked_requests) > 0

    @property
    def blocked_urls(self) -> list[str]:
        return [request.url for request in self.blocked_requests]


class StartupRecoveryRateLimitRuntime(
    AbstractContextManager[PlaywrightWebAppSession],
):
    def __init__(
        self,
        *,
        observation: StartupRecoveryRateLimitObservation,
        failure_message: str,
        retry_after_seconds: int = 60,
    ) -> None:
        self._observation = observation
        self._failure_message = failure_message
        self._retry_after_seconds = retry_after_seconds
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def __enter__(self) -> PlaywrightWebAppSession:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(viewport={"width": 1440, "height": 1200})
        self._context.add_init_script(
            """
            (() => {
              const requiredNavigationLabels = [
                'Dashboard',
                'Board',
                'JQL Search',
                'Hierarchy',
                'Settings',
              ];
              const shellReadyMarkers = ['Workspace switcher', 'Add workspace'];
              const normalize = (value) => (value ?? '').replace(/\\s+/g, ' ').trim();
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
              const nextOrder = () => {
                const nextValue = Number(window.__ts444ObservedOrderCounter ?? 0) + 1;
                window.__ts444ObservedOrderCounter = nextValue;
                return nextValue;
              };
              const collectShellReadySnapshot = () => {
                const bodyText = document.body?.innerText ?? '';
                const visibleButtonLabels = Array.from(
                  document.querySelectorAll('flt-semantics[role="button"]'),
                )
                  .filter(isVisible)
                  .map((candidate) => normalize(candidate.innerText))
                  .filter((label) => label.length > 0);
                const visibleNavigationLabels = requiredNavigationLabels.filter(
                  (label) => bodyText.includes(label),
                );
                const workspaceSwitcherVisible = bodyText.includes('Workspace switcher')
                  || visibleButtonLabels.includes('Workspace switcher');
                const addWorkspaceVisible = bodyText.includes('Add workspace')
                  || visibleButtonLabels.includes('Add workspace');
                return {
                  bodyText,
                  visibleButtonLabels,
                  visibleNavigationLabels,
                  workspaceSwitcherVisible,
                  addWorkspaceVisible,
                  shellReady: requiredNavigationLabels.every((label) => bodyText.includes(label))
                    && (workspaceSwitcherVisible || addWorkspaceVisible),
                };
              };
              const recordShellReadyIfVisible = () => {
                if (window.__ts444ShellReadyInfo) {
                  return;
                }
                const snapshot = collectShellReadySnapshot();
                if (!snapshot.shellReady) {
                  return;
                }
                window.__ts444ShellReadyInfo = {
                  observedOrder: nextOrder(),
                  observedAtPerformanceMs: performance.now(),
                  bodyText: snapshot.bodyText,
                  visibleNavigationLabels: snapshot.visibleNavigationLabels,
                  visibleButtonLabels: snapshot.visibleButtonLabels,
                  workspaceSwitcherVisible: snapshot.workspaceSwitcherVisible,
                  addWorkspaceVisible: snapshot.addWorkspaceVisible,
                };
              };
              const installObserver = () => {
                if (window.__ts444ShellReadyObserverInstalled) {
                  recordShellReadyIfVisible();
                  return;
                }
                window.__ts444ShellReadyObserverInstalled = true;
                recordShellReadyIfVisible();
                const root = document.documentElement;
                if (root) {
                  const observer = new MutationObserver(() => recordShellReadyIfVisible());
                  observer.observe(root, {
                    subtree: true,
                    childList: true,
                    characterData: true,
                    attributes: true,
                  });
                }
                document.addEventListener('readystatechange', () => recordShellReadyIfVisible());
                window.addEventListener('load', () => recordShellReadyIfVisible());
                window.requestAnimationFrame(() => recordShellReadyIfVisible());
                window.setTimeout(() => recordShellReadyIfVisible(), 0);
              };
              if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', installObserver, { once: true });
              } else {
                installObserver();
              }
            })();
            """,
        )
        self._context.route("https://api.github.com/**", self._handle_github_api_route)
        self._page = self._context.new_page()
        self._page.on("request", self._handle_page_request)
        return PlaywrightWebAppSession(self._page)

    def _handle_github_api_route(self, route: Route) -> None:
        url = route.request.url
        if self._is_blocked_request(url):
            route.fulfill(
                status=403,
                content_type="application/json",
                body=json.dumps(
                    {
                        "message": self._failure_message,
                        "documentation_url": (
                            "https://docs.github.com/rest/overview/resources-in-the-rest-api"
                            "#rate-limiting"
                        ),
                    },
                ),
                headers={
                    "x-ratelimit-remaining": "0",
                    "retry-after": str(self._retry_after_seconds),
                },
            )
            return
        route.fallback()

    def _handle_page_request(self, request: Request) -> None:
        url = request.url
        if not self._is_blocked_request(url):
            return
        snapshot = self._capture_ui_snapshot()
        self._observation.record_blocked_request(
            url,
            request_observed_at_performance_ms=float(
                snapshot["request_observed_at_performance_ms"],
            ),
            body_text_snapshot=str(snapshot["body_text"]),
            visible_navigation_labels=tuple(snapshot["visible_navigation_labels"]),
            settings_selected=bool(snapshot["settings_selected"]),
            settings_heading_visible=bool(snapshot["settings_heading_visible"]),
            topbar_title_visible=bool(snapshot["topbar_title_visible"]),
            shell_ready_observed_before_request=bool(
                snapshot["shell_ready_observed_before_request"],
            ),
            shell_ready_observed_order=(
                int(snapshot["shell_ready_observed_order"])
                if snapshot["shell_ready_observed_order"] is not None
                else None
            ),
            shell_ready_observed_at_performance_ms=(
                float(snapshot["shell_ready_observed_at_performance_ms"])
                if snapshot["shell_ready_observed_at_performance_ms"] is not None
                else None
            ),
            shell_ready_body_text_snapshot=str(snapshot["shell_ready_body_text_snapshot"]),
            shell_ready_visible_navigation_labels=tuple(
                snapshot["shell_ready_visible_navigation_labels"],
            ),
            shell_ready_visible_button_labels=tuple(
                snapshot["shell_ready_visible_button_labels"],
            ),
            shell_ready_workspace_switcher_visible=bool(
                snapshot["shell_ready_workspace_switcher_visible"],
            ),
            shell_ready_add_workspace_visible=bool(
                snapshot["shell_ready_add_workspace_visible"],
            ),
        )

    def _capture_ui_snapshot(self) -> dict[str, object]:
        if self._page is None:
            return {
                "request_observed_at_performance_ms": 0.0,
                "body_text": "",
                "visible_navigation_labels": [],
                "settings_selected": False,
                "settings_heading_visible": False,
                "topbar_title_visible": False,
                "shell_ready_observed_before_request": False,
                "shell_ready_observed_order": None,
                "shell_ready_observed_at_performance_ms": None,
                "shell_ready_body_text_snapshot": "",
                "shell_ready_visible_navigation_labels": [],
                "shell_ready_visible_button_labels": [],
                "shell_ready_workspace_switcher_visible": False,
                "shell_ready_add_workspace_visible": False,
            }
        try:
            body_text = self._page.locator("body").inner_text(timeout=2_000)
        except Exception:
            body_text = ""
        try:
            payload = self._page.evaluate(
                """
                () => {
                  const selectedLabels = Array.from(
                    document.querySelectorAll('flt-semantics[role="button"][aria-current="true"]'),
                  )
                    .map((candidate) => (candidate.innerText ?? '').trim())
                    .filter((label) => label.length > 0);
                  return {
                    request_observed_at_performance_ms: performance.now(),
                    settings_selected: selectedLabels.includes('Settings'),
                    shell_ready_info: window.__ts444ShellReadyInfo ?? null,
                  };
                }
                """,
            )
        except Exception:
            payload = None
        if not isinstance(payload, dict):
            return {
                "request_observed_at_performance_ms": 0.0,
                "body_text": body_text,
                "visible_navigation_labels": self._visible_navigation_labels(body_text),
                "settings_selected": False,
                "settings_heading_visible": "Project settings administration" in body_text,
                "topbar_title_visible": "Project Settings" in body_text,
                "shell_ready_observed_before_request": False,
                "shell_ready_observed_order": None,
                "shell_ready_observed_at_performance_ms": None,
                "shell_ready_body_text_snapshot": "",
                "shell_ready_visible_navigation_labels": [],
                "shell_ready_visible_button_labels": [],
                "shell_ready_workspace_switcher_visible": False,
                "shell_ready_add_workspace_visible": False,
            }
        shell_ready_info = (
            payload["shell_ready_info"]
            if isinstance(payload.get("shell_ready_info"), dict)
            else None
        )
        request_observed_at_performance_ms = float(
            payload.get("request_observed_at_performance_ms", 0.0),
        )
        shell_ready_observed_at_performance_ms = (
            float(shell_ready_info.get("observedAtPerformanceMs"))
            if shell_ready_info
            and shell_ready_info.get("observedAtPerformanceMs") is not None
            else None
        )
        return {
            "request_observed_at_performance_ms": request_observed_at_performance_ms,
            "body_text": body_text,
            "visible_navigation_labels": self._visible_navigation_labels(body_text),
            "settings_selected": bool(payload.get("settings_selected", False)),
            "settings_heading_visible": "Project settings administration" in body_text,
            "topbar_title_visible": "Project Settings" in body_text,
            "shell_ready_observed_before_request": (
                shell_ready_observed_at_performance_ms is not None
                and shell_ready_observed_at_performance_ms
                < request_observed_at_performance_ms
            ),
            "shell_ready_observed_order": (
                int(shell_ready_info.get("observedOrder"))
                if shell_ready_info and shell_ready_info.get("observedOrder") is not None
                else None
            ),
            "shell_ready_observed_at_performance_ms": shell_ready_observed_at_performance_ms,
            "shell_ready_body_text_snapshot": (
                str(shell_ready_info.get("bodyText", "")) if shell_ready_info else ""
            ),
            "shell_ready_visible_navigation_labels": (
                [
                    str(item)
                    for item in shell_ready_info.get("visibleNavigationLabels", [])
                ]
                if shell_ready_info
                else []
            ),
            "shell_ready_visible_button_labels": (
                [str(item) for item in shell_ready_info.get("visibleButtonLabels", [])]
                if shell_ready_info
                else []
            ),
            "shell_ready_workspace_switcher_visible": (
                bool(shell_ready_info.get("workspaceSwitcherVisible"))
                if shell_ready_info
                else False
            ),
            "shell_ready_add_workspace_visible": (
                bool(shell_ready_info.get("addWorkspaceVisible"))
                if shell_ready_info
                else False
            ),
        }

    @staticmethod
    def _visible_navigation_labels(body_text: str) -> list[str]:
        return [
            label
            for label in ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
            if label in body_text
        ]

    def _is_blocked_request(self, url: str) -> bool:
        parsed_url = urlsplit(url)
        expected_path_suffix = f"/contents/{self._observation.blocked_repository_path}"
        return (
            parsed_url.scheme == "https"
            and parsed_url.netloc == "api.github.com"
            and parsed_url.path.endswith(expected_path_suffix)
            and bool(parse_qs(parsed_url.query).get("ref"))
        )

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        return None
