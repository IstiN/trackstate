from __future__ import annotations

from dataclasses import dataclass

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


@dataclass(frozen=True)
class SettingsFieldRowObservation:
    field_name: str
    aria_label: str
    action_button_count: int
    delete_action_visible: bool


@dataclass(frozen=True)
class TextInputObservation:
    aria_label: str
    value: str
    disabled: bool
    read_only: bool


@dataclass(frozen=True)
class TypeControlObservation:
    text: str
    role: str | None
    disabled: str | None


@dataclass(frozen=True)
class IssueTypeChipObservation:
    text: str
    selected: str | None


@dataclass(frozen=True)
class FieldEditorObservation:
    body_text: str
    id_input: TextInputObservation | None
    name_input: TextInputObservation | None
    default_value_input: TextInputObservation | None
    options_input: TextInputObservation | None
    type_control: TypeControlObservation | None
    issue_type_chips: list[IssueTypeChipObservation]


class LiveSettingsFieldsPage:
    _button_selector = 'flt-semantics[role="button"]'
    _tab_selector = 'flt-semantics[role="tab"]'
    _settings_admin_heading = "Project settings administration"
    _fields_tab_label = "Fields"
    _editor_title = "Edit field"

    def __init__(self, tracker_page: TrackStateTrackerPage) -> None:
        self._tracker_page = tracker_page
        self._session = tracker_page.session

    def open_settings_admin(self) -> str:
        self._session.click(
            self._button_selector,
            has_text="Settings",
            timeout_ms=30_000,
        )
        return self._session.wait_for_text(
            self._settings_admin_heading,
            timeout_ms=60_000,
        )

    def open_fields_tab(self) -> str:
        selector = self._fields_tab_selector()
        self._scroll_into_view(selector)
        rect = self._session.bounding_box(selector, timeout_ms=30_000)
        self._session.mouse_click(rect.x + (rect.width / 2), rect.y + (rect.height / 2))
        self._session.wait_for_function(
            """
            ({ tabSelector, rowSelector }) => {
              const tab = document.querySelector(tabSelector);
              return (
                !!tab &&
                tab.getAttribute('aria-selected') === 'true' &&
                document.querySelectorAll(rowSelector).length > 0
              );
            }
            """,
            arg={
                "tabSelector": selector,
                "rowSelector": self._field_row_selector("*"),
            },
            timeout_ms=30_000,
        )
        return self.current_body_text()

    def field_row_observation(self, field_name: str) -> SettingsFieldRowObservation:
        selector = self._field_row_selector(field_name)
        self._session.wait_for_selector(selector, timeout_ms=30_000)
        payload = self._session.evaluate(
            """
            ({ rowSelector, fieldName }) => {
              const row = document.querySelector(rowSelector);
              if (!row) {
                return null;
              }
              const deleteVisible = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              ).some((candidate) =>
                (candidate.getAttribute('aria-label') ?? '').includes(
                  `Delete field ${fieldName}`,
                ),
              );
              return {
                ariaLabel: row.getAttribute('aria-label') ?? '',
                actionButtonCount: row.querySelectorAll(
                  ':scope > flt-semantics[role="button"]',
                ).length,
                deleteActionVisible: deleteVisible,
              };
            }
            """,
            arg={"rowSelector": selector, "fieldName": field_name},
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                f'Could not locate the "{field_name}" field row in Settings > Fields.\n'
                f"Observed body text:\n{self.current_body_text()}",
            )
        return SettingsFieldRowObservation(
            field_name=field_name,
            aria_label=str(payload["ariaLabel"]),
            action_button_count=int(payload["actionButtonCount"]),
            delete_action_visible=bool(payload["deleteActionVisible"]),
        )

    def open_field_editor(self, field_name: str) -> str:
        selector = self._field_row_edit_button_selector(field_name)
        self._scroll_into_view(selector)
        rect = self._session.bounding_box(selector, timeout_ms=30_000)
        self._session.mouse_click(rect.x + (rect.width / 2), rect.y + (rect.height / 2))
        self._session.wait_for_function(
            """
            (title) => {
              const bodyText = document.body?.innerText ?? '';
              const hasEditorInputs =
                document.querySelectorAll('input[aria-label="ID"]').length > 0;
              return bodyText.includes(title) && hasEditorInputs;
            }
            """,
            arg=self._editor_title,
            timeout_ms=30_000,
        )
        return self.current_body_text()

    def read_editor_observation(self) -> FieldEditorObservation:
        payload = self._session.evaluate(
            """
            () => {
              const readInput = (label) => {
                const element = document.querySelector(`input[aria-label="${label}"]`);
                if (!element) {
                  return null;
                }
                return {
                  ariaLabel: element.getAttribute('aria-label') ?? label,
                  value: element.value ?? '',
                  disabled: !!element.disabled,
                  readOnly: !!element.readOnly,
                };
              };
              const typeControl = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .map((element) => ({
                  text: (element.innerText ?? '').trim(),
                  role: element.getAttribute('role'),
                  disabled: element.getAttribute('aria-disabled'),
                }))
                .find((candidate) => candidate.text.startsWith('Type '));
              const chipTexts = ['Epic', 'Story', 'Task', 'Sub-task', 'Bug'];
              const issueTypeChips = Array.from(
                document.querySelectorAll('flt-semantics[role="button"]'),
              )
                .map((element) => ({
                  text: (element.innerText ?? '').trim(),
                  selected: element.getAttribute('aria-current'),
                }))
                .filter((candidate) => chipTexts.includes(candidate.text));
              return {
                bodyText: document.body?.innerText ?? '',
                idInput: readInput('ID'),
                nameInput: readInput('Name'),
                defaultValueInput: readInput('Default value'),
                optionsInput: readInput('Options'),
                typeControl,
                issueTypeChips,
              };
            }
            """,
        )
        if not isinstance(payload, dict):
            raise AssertionError(
                "The field editor did not expose a readable DOM snapshot.\n"
                f"Observed body text:\n{self.current_body_text()}",
            )
        return FieldEditorObservation(
            body_text=str(payload["bodyText"]),
            id_input=_text_input_observation(payload.get("idInput")),
            name_input=_text_input_observation(payload.get("nameInput")),
            default_value_input=_text_input_observation(
                payload.get("defaultValueInput"),
            ),
            options_input=_text_input_observation(payload.get("optionsInput")),
            type_control=_type_control_observation(payload.get("typeControl")),
            issue_type_chips=_issue_type_chip_observations(payload.get("issueTypeChips")),
        )

    def cancel_editor(self) -> None:
        self._session.click(self._button_selector, has_text="Cancel", timeout_ms=30_000)
        self._session.wait_for_function(
            """
            (title) => !(document.body?.innerText ?? '').includes(title)
            """,
            arg=self._editor_title,
            timeout_ms=30_000,
        )

    def current_body_text(self) -> str:
        return self._tracker_page.body_text()

    def screenshot(self, path: str) -> None:
        self._tracker_page.screenshot(path)

    def _fields_tab_selector(self) -> str:
        return f'{self._tab_selector}[aria-label="{self._escape(self._fields_tab_label)}"]'

    def _field_row_selector(self, field_name: str) -> str:
        escaped_name = self._escape(field_name)
        return (
            f'{self._button_selector}[aria-label*="Edit field {escaped_name}"], '
            f'{self._button_selector}[aria-label*="Edit field"]'
            if field_name == "*"
            else f'{self._button_selector}[aria-label*="Edit field {escaped_name}"]'
        )

    def _field_row_edit_button_selector(self, field_name: str) -> str:
        return f'{self._field_row_selector(field_name)} > {self._button_selector}'

    def _scroll_into_view(self, selector: str) -> None:
        self._session.evaluate(
            """
            (value) => {
              document.querySelector(value)?.scrollIntoView({ block: 'center' });
            }
            """,
            arg=selector,
        )

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')


def _text_input_observation(payload: object) -> TextInputObservation | None:
    if not isinstance(payload, dict):
        return None
    return TextInputObservation(
        aria_label=str(payload["ariaLabel"]),
        value=str(payload["value"]),
        disabled=bool(payload["disabled"]),
        read_only=bool(payload["readOnly"]),
    )


def _type_control_observation(payload: object) -> TypeControlObservation | None:
    if not isinstance(payload, dict):
        return None
    return TypeControlObservation(
        text=str(payload["text"]),
        role=str(payload["role"]) if payload["role"] is not None else None,
        disabled=str(payload["disabled"]) if payload["disabled"] is not None else None,
    )


def _issue_type_chip_observations(payload: object) -> list[IssueTypeChipObservation]:
    if not isinstance(payload, list):
        return []
    observations: list[IssueTypeChipObservation] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        observations.append(
            IssueTypeChipObservation(
                text=str(item["text"]),
                selected=(
                    str(item["selected"]) if item.get("selected") is not None else None
                ),
            ),
        )
    return observations
