from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.live_issue_detail_collaboration_page import (
    LiveIssueDetailCollaborationPage,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class EditControlObservation:
    label: str | None
    text: str


class LiveMultiViewRefreshPage:
    _button_selector = 'flt-semantics[role="button"]'
    _edit_button_selector = 'flt-semantics[role="button"][aria-label="Edit"]'

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session
        self._issue_page = LiveIssueDetailCollaborationPage(tracker_page)

    def ensure_connected(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
    ) -> None:
        self._issue_page.ensure_connected(
            token=token,
            repository=repository,
            user_login=user_login,
        )

    def open_edit_dialog_for_issue(self, *, issue_key: str, issue_summary: str) -> str:
        self.navigate_to_section("JQL Search")
        self._session.wait_for_selector(
            self._issue_selector(issue_key=issue_key, issue_summary=issue_summary),
            timeout_ms=60_000,
        )
        self._session.click(
            self._issue_selector(issue_key=issue_key, issue_summary=issue_summary),
            timeout_ms=30_000,
        )
        self._session.wait_for_selector(self._edit_button_selector, timeout_ms=30_000)
        self._session.click(self._edit_button_selector, timeout_ms=30_000)
        dialog_text = self._session.wait_for_text("Edit issue", timeout_ms=30_000)
        if issue_key not in dialog_text:
            raise AssertionError(
                "Step 1 failed: opening the requested issue from JQL Search did not "
                f"lead to the edit surface for {issue_key}.\n"
                f"Expected issue key in edit dialog: {issue_key}\n"
                f"Observed dialog text:\n{dialog_text}",
            )
        return dialog_text

    def navigate_to_section(self, label: str) -> None:
        bounds = self._button_bounds_for_sidebar_label(label)
        if bounds is None:
            raise AssertionError(
                f'Step 1 failed: the hosted tracker did not expose a visible "{label}" '
                "navigation entry in the sidebar.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        self._session.mouse_click(
            bounds["x"] + (bounds["width"] / 2),
            bounds["y"] + (bounds["height"] / 2),
        )
        try:
            self._session.wait_for_function(
                """
                (label) => Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                  .some((element) =>
                    (element.innerText || '').trim() === label
                    && element.getAttribute('aria-current') === 'true')
                """,
                arg=label,
                timeout_ms=30_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'Step 1 failed: clicking the "{label}" sidebar entry did not activate '
                "that section in the hosted tracker.\n"
                f"Observed body text:\n{self.current_body_text()}",
            ) from error

    def status_control(self) -> EditControlObservation:
        observation = self._control_observation(
            """
            (button) => {
              const label = button.getAttribute('aria-label') ?? '';
              const text = (button.innerText || '').trim();
              return label.includes('Status') || text.startsWith('Status');
            }
            """,
        )
        if observation is None:
            raise AssertionError(
                "Human-style verification failed: the Edit issue surface did not show "
                "a visible Status control.\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        return observation

    def priority_control(self) -> EditControlObservation:
        observation = self._control_observation(
            """
            (button) => {
              const label = button.getAttribute('aria-label') ?? '';
              const text = (button.innerText || '').trim();
              return label.includes('Priority') || text.startsWith('Priority');
            }
            """,
        )
        if observation is None:
            raise AssertionError(
                "Human-style verification failed: the Edit issue surface did not show "
                "a visible Priority control.\n"
                f"Observed dialog text:\n{self.current_body_text()}",
            )
        return observation

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def _control_observation(
        self,
        predicate_expression: str,
    ) -> EditControlObservation | None:
        payload = self._session.evaluate(
            f"""
            (predicateSource) => {{
              const predicate = eval(predicateSource);
              const match = Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                .map((button) => ({{
                  label: button.getAttribute('aria-label'),
                  text: (button.innerText || '').trim(),
                }}))
                .find((candidate) => predicate({{
                  getAttribute: (name) => name === 'aria-label' ? candidate.label : null,
                  innerText: candidate.text,
                }}));
              return match ?? null;
            }}
            """,
            arg=predicate_expression,
        )
        if not isinstance(payload, dict):
            return None
        return EditControlObservation(
            label=str(payload["label"]) if payload["label"] is not None else None,
            text=str(payload["text"]),
        )

    def _button_bounds_for_sidebar_label(self, label: str) -> dict[str, float] | None:
        payload = self._session.evaluate(
            """
            (label) => {
              const button = Array.from(document.querySelectorAll('flt-semantics[role="button"]'))
                .find((element) => (element.innerText || '').trim() === label);
              if (!button) {
                return null;
              }
              const rect = button.getBoundingClientRect();
              return {
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height,
              };
            }
            """,
            arg=label,
        )
        if not isinstance(payload, dict):
            return None
        return {
            "x": float(payload["x"]),
            "y": float(payload["y"]),
            "width": float(payload["width"]),
            "height": float(payload["height"]),
        }

    @staticmethod
    def _issue_selector(*, issue_key: str, issue_summary: str) -> str:
        escaped_summary = issue_summary.replace("\\", "\\\\").replace('"', '\\"')
        return (
            'flt-semantics[role="button"]'
            f'[aria-label="Open {issue_key} {escaped_summary}"]'
        )
