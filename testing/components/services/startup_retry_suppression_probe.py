from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from testing.components.pages.trackstate_live_app_page import TrackStateLiveAppPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


class BootstrapRequestMonitor(Protocol):
    @property
    def bootstrap_request_count(self) -> int: ...

    @property
    def blocked_request_count(self) -> int: ...

    @property
    def blocked_target_url(self) -> str: ...

    @property
    def bootstrap_urls(self) -> Sequence[str]: ...

    @property
    def blocked_urls(self) -> Sequence[str]: ...


@dataclass(frozen=True)
class RetrySuppressionCheckpoint:
    name: str
    bootstrap_request_count: int
    blocked_request_count: int
    body_text: str


@dataclass(frozen=True)
class RetrySuppressionObservation:
    recovery_controls: tuple[str, ...]
    initial_recovery: RetrySuppressionCheckpoint
    after_network_reconnect: RetrySuppressionCheckpoint
    after_focus_regain: RetrySuppressionCheckpoint
    after_rate_limit_window: RetrySuppressionCheckpoint
    blocked_target_url: str
    bootstrap_urls: tuple[str, ...]
    blocked_urls: tuple[str, ...]


class StartupRetrySuppressionProbe:
    def __init__(
        self,
        *,
        event_settle_ms: int = 2_000,
        rate_limit_window_ms: int = 12_000,
    ) -> None:
        self._event_settle_ms = event_settle_ms
        self._rate_limit_window_ms = rate_limit_window_ms

    def observe(
        self,
        *,
        live_page: TrackStateLiveAppPage,
        request_monitor: BootstrapRequestMonitor,
    ) -> RetrySuppressionObservation:
        live_page.open()
        self._wait_for_recovery_controls(live_page)
        self._wait_for_blocked_bootstrap_request(live_page, request_monitor)

        initial_recovery = self._checkpoint(
            "initial recovery",
            live_page=live_page,
            request_monitor=request_monitor,
        )

        network_started_at = live_page.session.evaluate(
            """
            () => {
                window.dispatchEvent(new Event('offline'));
                window.dispatchEvent(new Event('online'));
                return performance.now();
            }
            """,
        )
        self._wait_elapsed(
            live_page=live_page,
            started_at=network_started_at,
            duration_ms=self._event_settle_ms,
            failure_step=2,
            failure_action="network reconnect",
        )
        after_network_reconnect = self._checkpoint(
            "after network reconnect",
            live_page=live_page,
            request_monitor=request_monitor,
        )

        focus_started_at = live_page.session.evaluate(
            """
            () => {
                window.dispatchEvent(new Event('blur'));
                window.dispatchEvent(new Event('focus'));
                document.dispatchEvent(new Event('visibilitychange'));
                return performance.now();
            }
            """,
        )
        self._wait_elapsed(
            live_page=live_page,
            started_at=focus_started_at,
            duration_ms=self._event_settle_ms,
            failure_step=3,
            failure_action="window focus regain",
        )
        after_focus_regain = self._checkpoint(
            "after window focus regain",
            live_page=live_page,
            request_monitor=request_monitor,
        )

        timer_started_at = live_page.session.evaluate("() => performance.now()")
        self._wait_elapsed(
            live_page=live_page,
            started_at=timer_started_at,
            duration_ms=self._rate_limit_window_ms,
            failure_step=4,
            failure_action="the rate-limit reset window",
        )
        after_rate_limit_window = self._checkpoint(
            "after rate-limit window",
            live_page=live_page,
            request_monitor=request_monitor,
        )

        return RetrySuppressionObservation(
            recovery_controls=("Retry", "Connect GitHub"),
            initial_recovery=initial_recovery,
            after_network_reconnect=after_network_reconnect,
            after_focus_regain=after_focus_regain,
            after_rate_limit_window=after_rate_limit_window,
            blocked_target_url=request_monitor.blocked_target_url,
            bootstrap_urls=tuple(request_monitor.bootstrap_urls),
            blocked_urls=tuple(request_monitor.blocked_urls),
        )

    def _checkpoint(
        self,
        name: str,
        *,
        live_page: TrackStateLiveAppPage,
        request_monitor: BootstrapRequestMonitor,
    ) -> RetrySuppressionCheckpoint:
        body_text = live_page.body_text()
        self._assert_recovery_controls_visible(body_text=body_text)
        return RetrySuppressionCheckpoint(
            name=name,
            bootstrap_request_count=request_monitor.bootstrap_request_count,
            blocked_request_count=request_monitor.blocked_request_count,
            body_text=body_text,
        )

    def _wait_for_recovery_controls(self, live_page: TrackStateLiveAppPage) -> None:
        try:
            live_page.session.wait_for_function(
                """
                (expectedTexts) => {
                    const bodyText = document.body?.innerText ?? '';
                    return expectedTexts.every((text) => bodyText.includes(text));
                }
                """,
                arg=["Retry", "Connect GitHub"],
                timeout_ms=120_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 1 failed: the deployed app never reached the unauthenticated "
                "rate-limit recovery state.\n"
                f"Observed body text:\n{live_page.body_text()}",
            ) from error

    def _wait_for_blocked_bootstrap_request(
        self,
        live_page: TrackStateLiveAppPage,
        request_monitor: BootstrapRequestMonitor,
    ) -> None:
        try:
            live_page.session.wait_for_function(
                """
                ({ expectedTexts, expectedBlockedRequestCount }) => {
                    const bodyText = document.body?.innerText ?? '';
                    return expectedTexts.every((text) => bodyText.includes(text))
                        && expectedBlockedRequestCount >= 1;
                }
                """,
                arg={
                    "expectedTexts": ["Retry", "Connect GitHub"],
                    "expectedBlockedRequestCount": request_monitor.blocked_request_count,
                },
                timeout_ms=5_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                "Step 1 failed: the recovery screen became visible before the blocked "
                "bootstrap request could be observed.\n"
                f"Blocked target URL: {request_monitor.blocked_target_url}\n"
                f"Observed bootstrap request count: {request_monitor.bootstrap_request_count}\n"
                f"Observed blocked request count: {request_monitor.blocked_request_count}\n"
                f"Observed body text:\n{live_page.body_text()}",
            ) from error

    def _wait_elapsed(
        self,
        *,
        live_page: TrackStateLiveAppPage,
        started_at: object,
        duration_ms: int,
        failure_step: int,
        failure_action: str,
    ) -> None:
        try:
            live_page.session.wait_for_function(
                """
                ({ startedAt, durationMs }) =>
                    typeof startedAt === 'number'
                    && performance.now() - startedAt >= durationMs
                """,
                arg={"startedAt": started_at, "durationMs": duration_ms},
                timeout_ms=duration_ms + 5_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f"Step {failure_step} failed: the browser test did not finish waiting "
                f"for {failure_action} within the expected observation window.\n"
                f"Observed body text:\n{live_page.body_text()}",
            ) from error

    @staticmethod
    def _assert_recovery_controls_visible(*, body_text: str) -> None:
        missing_controls = [
            label for label in ("Retry", "Connect GitHub") if label not in body_text
        ]
        if missing_controls:
            raise AssertionError(
                "Human-style verification failed: the unauthenticated recovery screen "
                "did not keep the expected visible controls on screen.\n"
                f"Missing controls: {missing_controls}\n"
                f"Observed body text:\n{body_text}",
            )
