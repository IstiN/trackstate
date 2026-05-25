from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError


@dataclass(frozen=True)
class ProjectSettingsUiObservation:
    settings_text: str
    status_dialog_text: str
    status_list_text: str
    workflow_dialog_text: str
    workflow_tab_text: str
    post_save_text: str


class LiveProjectSettingsPage:
    _button_selector = 'flt-semantics[role="button"]'
    _tab_selector = 'flt-semantics[role="tab"]'
    _connect_label = "Connect GitHub"
    _connect_submit_label = "Connect token"
    _close_label = "Close"
    _save_settings_label = "Save settings"
    _token_input_selector = 'input[aria-label="Fine-grained token"]'
    _settings_nav_selector = 'flt-semantics[role="button"]'
    _settings_heading = "Project Settings"
    _settings_admin_heading = "Project settings administration"
    _status_id_selector = 'input[aria-label="ID"]'
    _status_name_selector = 'input[aria-label="Name"]'
    _transition_name_selector = 'input[aria-label="Transition name"]'
    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def ensure_connected(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
        timeout_seconds: int = 240,
    ) -> str:
        connected_banner = TrackStateTrackerPage.CONNECTED_BANNER_TEMPLATE.format(
            user_login=user_login,
            repository=repository,
        )
        connected_banner_short = f"Connected as {user_login} to {repository}."
        current_body = self.body_text()
        if connected_banner in current_body or connected_banner_short in current_body:
            return current_body

        if self._session.count(self._button_selector, has_text=self._connect_label) == 0:
            raise AssertionError(
                "Step 2 failed: the hosted runtime did not expose the Connect GitHub "
                "action needed to enter the writable Settings flow.\n"
                f"Observed body text:\n{current_body}",
            )

        for attempt in range(2):
            if self._session.count(self._token_input_selector) == 0:
                self._mouse_click_button(self._connect_label)
            self._session.wait_for_selector(self._token_input_selector, timeout_ms=30_000)
            self._session.fill(self._token_input_selector, token, timeout_ms=30_000)
            self._session.press(self._token_input_selector, "Tab", timeout_ms=30_000)
            self._mouse_click_button(self._connect_submit_label)

            try:
                wait_match = self._session.wait_for_any_text(
                    [
                        connected_banner,
                        connected_banner_short,
                        "GitHub connection failed:",
                    ],
                    timeout_ms=timeout_seconds * 1_000,
                )
            except WebAppTimeoutError:
                current_body = self.body_text()
                if connected_banner in current_body or connected_banner_short in current_body:
                    return current_body
                if attempt == 0:
                    continue
                raise AssertionError(
                    "Step 2 failed: submitting the fine-grained token never reached a "
                    "connected hosted session.\n"
                    f"Observed body text:\n{current_body}",
                ) from None

            if wait_match.matched_text == "GitHub connection failed:":
                raise AssertionError(
                    "Step 2 failed: submitting the fine-grained token did not reach a "
                    "connected hosted session.\n"
                    f"Observed body text:\n{wait_match.body_text}",
                )
            return wait_match.body_text

        raise AssertionError(
            "Step 2 failed: the hosted token connect flow could not complete.",
        )

    def dismiss_connection_banner(self) -> None:
        if self._session.count(self._button_selector, has_text=self._close_label) == 0:
            return
        self._mouse_click_button(self._close_label)

    def open_settings(self) -> str:
        self._session.click(
            self._settings_nav_selector,
            has_text="Settings",
            timeout_ms=30_000,
        )
        return self._session.wait_for_text(self._settings_heading, timeout_ms=60_000)

    def add_status(
        self,
        *,
        status_id: str,
        status_name: str,
    ) -> tuple[str, str]:
        self._session.click('flt-semantics[aria-label="Add status"]', timeout_ms=30_000)
        self._session.wait_for_selector(self._status_id_selector, timeout_ms=30_000)
        self._session.fill(self._status_id_selector, status_id, timeout_ms=30_000)
        self._session.fill(self._status_name_selector, status_name, timeout_ms=30_000)
        status_dialog_text = self.body_text()
        self._session.click(self._button_selector, has_text="Save", timeout_ms=30_000)
        self._session.wait_for_selector(
            self._status_id_selector,
            state="hidden",
            timeout_ms=60_000,
        )
        self._session.wait_for_selector(
            self._button_selector,
            has_text=self._save_settings_label,
            timeout_ms=30_000,
        )
        status_list_text = self.body_text()
        return status_dialog_text, status_list_text

    def open_workflows_tab(self) -> str:
        self._session.click(
            'flt-semantics[role="tab"][aria-label="Workflows"]',
            timeout_ms=30_000,
        )
        self._session.wait_for_selector(
            'flt-semantics[aria-label*="Delivery Workflow"]',
            timeout_ms=30_000,
        )
        return self.body_text()

    def update_workflow_transition_name(
        self,
        *,
        workflow_name: str,
        transition_index: int,
        transition_name: str,
    ) -> tuple[str, str]:
        self._session.click(
            f'flt-semantics[aria-label="Edit workflow {self._escape(workflow_name)}"]',
            timeout_ms=30_000,
        )
        self._session.wait_for_selector(
            self._transition_name_selector,
            timeout_ms=30_000,
        )
        self._session.fill(
            self._transition_name_selector,
            transition_name,
            index=transition_index,
            timeout_ms=30_000,
        )
        workflow_dialog_text = self.body_text()
        self._session.click(self._button_selector, has_text="Save", timeout_ms=30_000)
        self._session.wait_for_selector(
            self._button_selector,
            has_text=self._save_settings_label,
            timeout_ms=30_000,
        )
        workflow_tab_text = self.body_text()
        return workflow_dialog_text, workflow_tab_text

    def save_settings(self) -> str:
        self._mouse_click_button(self._save_settings_label)
        self._session.wait_for_text(self._settings_admin_heading, timeout_ms=120_000)
        return self.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def body_text(self) -> str:
        return self._tracker_page.body_text()

    def observe_saved_configuration(
        self,
        *,
        status_name: str,
        workflow_name: str,
        transition_name: str,
        transition_index: int,
    ) -> ProjectSettingsUiObservation:
        settings_text = self.open_settings()
        status_dialog_text, status_list_text = self.add_status(
            status_id=f"{status_name.lower().replace(' ', '-')}",
            status_name=status_name,
        )
        workflow_tab_text = self.open_workflows_tab()
        workflow_dialog_text, workflow_tab_text = self.update_workflow_transition_name(
            workflow_name=workflow_name,
            transition_index=transition_index,
            transition_name=transition_name,
        )
        post_save_text = self.save_settings()
        return ProjectSettingsUiObservation(
            settings_text=settings_text,
            status_dialog_text=status_dialog_text,
            status_list_text=status_list_text,
            workflow_dialog_text=workflow_dialog_text,
            workflow_tab_text=workflow_tab_text,
            post_save_text=post_save_text,
        )

    def _wait_for_visible_text(self, text: str, *, timeout_seconds: int) -> str:
        try:
            return self._session.wait_for_text(text, timeout_ms=timeout_seconds * 1_000)
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'Human-style verification failed: the live Settings surface never '
                f'showed "{text}" after saving the dialog.\n'
                f"Observed body text:\n{self.body_text()}",
            ) from error

    def _wait_for_semantics_text(self, text: str, *, timeout_seconds: int) -> str:
        try:
            self._session.wait_for_function(
                """
                (expectedText) => Array.from(document.querySelectorAll("flt-semantics"))
                  .some((element) => {
                    const aria = element.getAttribute("aria-label") ?? "";
                    const innerText = element.innerText ?? "";
                    return aria.includes(expectedText) || innerText.includes(expectedText);
                  })
                """,
                arg=text,
                timeout_ms=timeout_seconds * 1_000,
            )
        except WebAppTimeoutError as error:
            raise AssertionError(
                f'Human-style verification failed: the live Settings semantics never '
                f'exposed "{text}" after saving the dialog.\n'
                f"Observed body text:\n{self.body_text()}",
            ) from error
        return self.body_text()

    def _mouse_click_button(self, label: str, *, index: int = 0) -> None:
        rect = self._session.bounding_box(
            self._button_selector,
            has_text=label,
            index=index,
            timeout_ms=30_000,
        )
        self._session.mouse_click(rect.x + (rect.width / 2), rect.y + (rect.height / 2))

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
