from __future__ import annotations

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


class LiveProjectSettingsAdminPage:
    BUTTON_SELECTOR = 'flt-semantics[role="button"]'
    GROUP_SELECTOR = 'flt-semantics[role="group"]'
    MENU_ITEM_SELECTOR = 'flt-semantics[role="menuitem"]'
    TAB_SELECTOR = 'flt-semantics[role="tab"]'

    SETTINGS_HEADER = "Project settings administration"
    SETTINGS_DESCRIPTION = (
        "Manage repository-backed statuses, workflows, issue types, and fields with "
        "validation before Git writes."
    )
    WORKFLOWS_TAB = "Workflows"
    ISSUE_TYPES_TAB = "Issue Types"
    BUG_WORKFLOW_NAME = "Bug Workflow"
    BUG_WORKFLOW_ID = "bug-workflow"
    BUG_ISSUE_TYPE_NAME = "Bug"
    WORKFLOW_TRANSITION_NAME = "Complete bug"

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self.session = tracker_page.session

    def ensure_connected(
        self,
        *,
        token: str,
        repository: str,
        user_login: str,
    ) -> str:
        observation = self._tracker_page.connect_with_token(
            token=token,
            repository=repository,
            user_login=user_login,
        )
        return observation.body_text

    def open_settings_admin(self) -> str:
        self._tracker_page._live_page.open_settings()
        self.session.wait_for_text(self.SETTINGS_HEADER, timeout_ms=120_000)
        self._scroll_page(y=1_200)
        self._scroll_into_view(
            f'{self.GROUP_SELECTOR}[aria-label="{self.SETTINGS_HEADER}"]',
        )
        return self.current_body_text()

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def open_tab(self, label: str) -> str:
        selector = f'{self.TAB_SELECTOR}[aria-label="{label}"]'
        self._scroll_into_view(selector)
        self.session.click(selector, timeout_ms=30_000)
        self.session.wait_for_function(
            """
            (selector) => {
              const tab = document.querySelector(selector);
              return !!tab && tab.getAttribute('aria-selected') === 'true';
            }
            """,
            arg=selector,
            timeout_ms=30_000,
        )
        return self.current_body_text()

    def workflow_exists(self, workflow_name: str) -> bool:
        return self.session.count(self._workflow_group_selector(workflow_name)) > 0

    def create_bug_workflow(self) -> str:
        self.open_tab(self.WORKFLOWS_TAB)
        add_selector = f'{self.BUTTON_SELECTOR}[aria-label="Add workflow"]'
        self._scroll_into_view(add_selector)
        self.session.click(add_selector, timeout_ms=30_000)
        self.session.wait_for_text("Add workflow", timeout_ms=30_000)

        self.session.fill('input[aria-label="ID"]', self.BUG_WORKFLOW_ID, timeout_ms=30_000)
        self._type_into_input('input[aria-label="Name"]', self.BUG_WORKFLOW_NAME)
        self._click_button_text("To Do")
        self._click_button_text("Done")
        self._click_button_text("Add transition")

        self.session.wait_for_selector('input[aria-label="Transition name"]', timeout_ms=30_000)
        self.session.fill(
            'input[aria-label="Transition name"]',
            self.WORKFLOW_TRANSITION_NAME,
            timeout_ms=30_000,
        )
        self._click_button_text("To status To Do")
        self.session.wait_for_selector(
            f'{self.MENU_ITEM_SELECTOR}[aria-label="Done"]',
            timeout_ms=30_000,
        )
        self.session.click(
            f'{self.MENU_ITEM_SELECTOR}[aria-label="Done"]',
            timeout_ms=30_000,
        )
        self.session.click(self.BUTTON_SELECTOR, has_text="Save", timeout_ms=30_000)
        self.session.wait_for_selector(
            'input[aria-label="Transition name"]',
            state="detached",
            timeout_ms=30_000,
        )
        return self.workflow_row_label(self.BUG_WORKFLOW_NAME)

    def workflow_row_label(self, workflow_name: str) -> str:
        selector = self._workflow_group_selector(workflow_name)
        self._scroll_into_view(selector)
        self.session.wait_for_selector(selector, timeout_ms=30_000)
        label = self._read_attribute(selector, "aria-label")
        if not label:
            raise AssertionError(
                f'Expected the "{workflow_name}" workflow row to expose an accessible label.',
            )
        return label

    def assign_bug_issue_type_to_bug_workflow(self) -> tuple[str, str]:
        self.open_tab(self.ISSUE_TYPES_TAB)
        edit_selector = (
            f'{self.BUTTON_SELECTOR}[aria-label="Edit issue type {self.BUG_ISSUE_TYPE_NAME}"]'
        )
        self._scroll_into_view(edit_selector)
        self.session.click(edit_selector, timeout_ms=30_000)
        self.session.wait_for_text("Edit issue type", timeout_ms=30_000)
        workflow_control_selector = self.BUTTON_SELECTOR
        self._scroll_into_view(workflow_control_selector, has_text="Workflow")
        self.session.click(
            workflow_control_selector,
            has_text="Workflow",
            timeout_ms=30_000,
        )
        self.session.wait_for_selector(
            f'{self.MENU_ITEM_SELECTOR}[aria-label="{self.BUG_WORKFLOW_NAME}"]',
            timeout_ms=30_000,
        )
        self.session.click(
            f'{self.MENU_ITEM_SELECTOR}[aria-label="{self.BUG_WORKFLOW_NAME}"]',
            timeout_ms=30_000,
        )
        dropdown_label = self._read_matching_text(
            workflow_control_selector,
            has_text="Workflow",
        )
        self.session.click(self.BUTTON_SELECTOR, has_text="Save", timeout_ms=30_000)
        self.session.wait_for_text_absence("Edit issue type", timeout_ms=30_000)
        return dropdown_label, self.issue_type_row_label(self.BUG_ISSUE_TYPE_NAME)

    def issue_type_row_label(self, issue_type_name: str) -> str:
        selector = self._issue_type_group_selector(issue_type_name)
        self._scroll_into_view(selector)
        self.session.wait_for_selector(selector, timeout_ms=30_000)
        label = self._read_attribute(selector, "aria-label")
        if not label:
            raise AssertionError(
                f'Expected the "{issue_type_name}" issue type row to expose an accessible label.',
            )
        return label

    def save_project_settings(self) -> str:
        save_selector = f'{self.BUTTON_SELECTOR}[aria-label="Save settings"]'
        self._scroll_into_view(save_selector)
        self.session.click(save_selector, timeout_ms=30_000)
        self.session.wait_for_function(
            """
            (selector) => {
              const button = document.querySelector(selector);
              return !!button && button.getAttribute('aria-disabled') !== 'true';
            }
            """,
            arg=save_selector,
            timeout_ms=120_000,
        )
        return self.current_body_text()

    def _workflow_group_selector(self, workflow_name: str) -> str:
        return f'{self.GROUP_SELECTOR}[aria-label*="{workflow_name}"]'

    def _issue_type_group_selector(self, issue_type_name: str) -> str:
        return (
            f'{self.GROUP_SELECTOR}[aria-label*="{issue_type_name}"]'
            f'[aria-label*="Workflow: {self.BUG_WORKFLOW_ID}"]'
        )

    def _click_button_text(self, text: str) -> None:
        self._scroll_into_view(self.BUTTON_SELECTOR, has_text=text)
        self.session.click(self.BUTTON_SELECTOR, has_text=text, timeout_ms=30_000)

    def _scroll_page(self, *, y: int) -> None:
        self.session.evaluate(
            "(targetY) => window.scrollTo({ top: targetY, behavior: 'instant' })",
            arg=y,
        )

    def _scroll_into_view(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
    ) -> None:
        for target_y in (0, 900, 1_400, 2_000, 2_600, 3_200):
            self._scroll_page(y=target_y)
            found = self.session.evaluate(
                """
                ({ selector, hasText, index }) => {
                  const matches = Array.from(document.querySelectorAll(selector)).filter(
                    (element) => {
                      if (!hasText) {
                        return true;
                      }
                      const text = element.innerText ?? element.textContent ?? '';
                      const ariaLabel = element.getAttribute('aria-label') ?? '';
                      return text.includes(hasText) || ariaLabel.includes(hasText);
                    }
                  );
                  const element = matches[index];
                  if (!element) {
                    return false;
                  }
                  element.scrollIntoView({ block: 'center', inline: 'nearest' });
                  return true;
                }
                """,
                arg={
                    "selector": selector,
                    "hasText": has_text,
                    "index": index,
                },
            )
            if found is True:
                return
        raise AssertionError(
            "The expected settings control was not rendered before interaction.\n"
            f"Selector: {selector}\n"
            f"Text filter: {has_text}\n"
            f"Visible body text:\n{self.current_body_text()}",
        )

    def _read_attribute(self, selector: str, attribute: str) -> str:
        value = self.session.evaluate(
            """
            ({ selector, attribute }) => {
              const element = document.querySelector(selector);
              return element ? element.getAttribute(attribute) : null;
            }
            """,
            arg={"selector": selector, "attribute": attribute},
        )
        return "" if value is None else str(value)

    def _type_into_input(self, selector: str, value: str) -> None:
        self._scroll_into_view(selector)
        self.session.type_text(
            selector,
            value,
            timeout_ms=30_000,
            delay_ms=120,
        )
        observed = self.session.read_value(selector, timeout_ms=30_000)
        if observed != value:
            raise AssertionError(
                "The hosted text field did not keep the typed value.\n"
                f"Selector: {selector}\n"
                f"Expected: {value}\n"
                f"Observed: {observed}",
            )

    def _read_matching_text(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
    ) -> str:
        value = self.session.evaluate(
            """
            ({ selector, hasText, index }) => {
              const matches = Array.from(document.querySelectorAll(selector)).filter(
                (element) => {
                  if (!hasText) {
                    return true;
                  }
                  const text = element.innerText ?? element.textContent ?? '';
                  const ariaLabel = element.getAttribute('aria-label') ?? '';
                  return text.includes(hasText) || ariaLabel.includes(hasText);
                }
              );
              const element = matches[index];
              if (!element) {
                return null;
              }
              return (element.innerText ?? element.textContent ?? '').trim();
            }
            """,
            arg={
                "selector": selector,
                "hasText": has_text,
                "index": index,
            },
        )
        return "" if value is None else str(value)
