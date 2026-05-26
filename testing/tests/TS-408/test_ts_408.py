from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (
    LiveIssueDetailCollaborationPage,
)
from testing.components.pages.live_settings_fields_page import (
    FieldEditorObservation,
    LiveSettingsFieldsPage,
    SettingsFieldRowObservation,
    TextInputObservation,
    TypeControlObservation,
)
from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-408"
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts408_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts408_success.png"
EXPECTED_RESERVED_FIELD_ID = "summary"
EXPECTED_RESERVED_FIELD_TYPE = "string"
CUSTOM_FIELD_ID = "environment"
CUSTOM_FIELD_NAME = "Environment"
CUSTOM_FIELD_TYPE = "option"
CUSTOM_FIELD_OPTIONS = ("Production", "Staging", "Development")
CUSTOM_FIELD_OPTIONS_TEXT = ", ".join(CUSTOM_FIELD_OPTIONS)
CUSTOM_FIELD_ISSUE_TYPES = {"Bug"}


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-408 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "expected_reserved_field_id": EXPECTED_RESERVED_FIELD_ID,
        "expected_reserved_field_type": EXPECTED_RESERVED_FIELD_TYPE,
        "steps": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            settings_page = LiveSettingsFieldsPage(tracker_page)
            collaboration_page = LiveIssueDetailCollaborationPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the field-catalog scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the hosted tracker.",
                    observed=runtime.body_text,
                )

                collaboration_page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                collaboration_page.dismiss_connection_banner()
                settings_text = settings_page.open_settings_admin()
                fields_text = settings_page.open_fields_tab()
                result["settings_body_text"] = settings_text
                result["fields_tab_body_text"] = fields_text
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Navigate to Settings > Fields in the live hosted app.",
                    observed=fields_text,
                )

                summary_row = settings_page.field_row_observation("Summary")
                result["summary_row"] = _row_payload(summary_row)
                _assert_summary_row(summary_row)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "Locate the Summary field row and verify the visible reserved "
                        "field metadata."
                    ),
                    observed=summary_row.aria_label,
                )

                if summary_row.delete_action_visible:
                    raise AssertionError(
                        "Step 4 failed: the reserved Summary field still exposed a delete "
                        "action in Settings > Fields.\n"
                        f"Observed Summary row: {summary_row.aria_label}",
                    )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Attempt to delete the Summary field.",
                    observed=(
                        "No Delete field Summary action was exposed; only the edit action "
                        "was visible on the reserved field row."
                    ),
                )

                settings_page.open_field_editor("Summary")
                editor = settings_page.read_editor_observation()
                result["summary_editor"] = _editor_payload(editor)
                _assert_reserved_field_editor(editor)
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Attempt to change the Summary field ID or Type.",
                    observed=editor.body_text,
                )

                had_existing_environment = settings_page.field_exists(CUSTOM_FIELD_NAME)
                result["environment_field_preexisting"] = had_existing_environment
                if had_existing_environment:
                    settings_page.delete_field(CUSTOM_FIELD_NAME)
                    settings_page.save_settings()
                    refreshed_fields_text = _reopen_fields_tab(
                        tracker_page=tracker_page,
                        settings_page=settings_page,
                        collaboration_page=collaboration_page,
                        token=token,
                        repository=service.repository,
                        user_login=user.login,
                    )
                    result["fields_tab_body_text_after_environment_cleanup"] = (
                        refreshed_fields_text
                    )
                    if settings_page.field_exists(CUSTOM_FIELD_NAME):
                        raise AssertionError(
                            "Precondition failed: a previous Environment custom field "
                            "could not be removed before the TS-408 create-field flow.\n"
                            f"Observed body text:\n{refreshed_fields_text}",
                        )

                settings_page.open_add_field_editor()
                settings_page.fill_editor_input("ID", CUSTOM_FIELD_ID)
                settings_page.fill_editor_input("Name", CUSTOM_FIELD_NAME)
                settings_page.select_field_type(CUSTOM_FIELD_TYPE)
                settings_page.fill_editor_input("Options", CUSTOM_FIELD_OPTIONS_TEXT)
                settings_page.set_applicable_issue_types(CUSTOM_FIELD_ISSUE_TYPES)
                environment_editor_draft = settings_page.read_editor_observation()
                result["environment_editor_before_save"] = _editor_payload(
                    environment_editor_draft,
                )
                _assert_environment_field_editor(
                    environment_editor_draft,
                    step=6,
                    action_description=(
                        "creating the Environment field before saving settings"
                    ),
                )
                settings_page.save_field_editor(field_name=CUSTOM_FIELD_NAME)
                environment_row_before_save = settings_page.field_row_observation(
                    CUSTOM_FIELD_NAME,
                )
                result["environment_row_before_save_settings"] = _row_payload(
                    environment_row_before_save,
                )
                _assert_custom_field_row(environment_row_before_save)
                settings_page.save_settings()
                refreshed_fields_text = _reopen_fields_tab(
                    tracker_page=tracker_page,
                    settings_page=settings_page,
                    collaboration_page=collaboration_page,
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                result["fields_tab_body_text_after_environment_save"] = refreshed_fields_text
                environment_row = settings_page.field_row_observation(CUSTOM_FIELD_NAME)
                result["environment_row"] = _row_payload(environment_row)
                _assert_custom_field_row(environment_row)
                _record_step(
                    result,
                    step=6,
                    status="passed",
                    action=(
                        "Create the Environment custom field, set its type to Select, "
                        "add three option values, and save the hosted field catalog."
                    ),
                    observed=environment_row.aria_label,
                )

                settings_page.open_field_editor(CUSTOM_FIELD_NAME)
                environment_editor = settings_page.read_editor_observation()
                result["environment_editor"] = _editor_payload(environment_editor)
                _assert_environment_field_editor(
                    environment_editor,
                    step=7,
                    action_description=(
                        "re-opening the saved Environment field editor after the hosted "
                        "save completed"
                    ),
                )
                _record_step(
                    result,
                    step=7,
                    status="passed",
                    action=(
                        "Verify the saved Environment field keeps its option metadata and "
                        "applies only to Bug."
                    ),
                    observed=environment_editor.body_text,
                )

                settings_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                settings_page.screenshot(str(SCREENSHOT_PATH))
                result["screenshot"] = str(SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    else:
        result["status"] = "passed"
        result["summary"] = (
            "Verified the hosted Settings > Fields screen keeps the reserved Summary "
            "field immutable and can create a Bug-only Environment select field with "
            "three option values."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_summary_row(summary_row: SettingsFieldRowObservation) -> None:
    missing_fragments = [
        fragment
        for fragment in (
            "Summary",
            f"ID: {EXPECTED_RESERVED_FIELD_ID}",
            f"Type: {EXPECTED_RESERVED_FIELD_TYPE}",
            "Required",
            "Reserved",
            "Edit field Summary",
        )
        if fragment not in summary_row.aria_label
    ]
    if missing_fragments:
        raise AssertionError(
            "Step 3 failed: the Summary field row did not expose the expected live "
            "reserved-field metadata.\n"
            f"Missing fragments: {missing_fragments}\n"
            f"Observed Summary row: {summary_row.aria_label}",
        )


def _assert_reserved_field_editor(editor: FieldEditorObservation) -> None:
    failures: list[str] = []
    id_input = editor.id_input
    if id_input is None:
        failures.append("the editor did not expose any ID input")
    else:
        if id_input.value != EXPECTED_RESERVED_FIELD_ID:
            failures.append(
                "the ID input was not prefilled with the reserved Summary field ID "
                f'("{EXPECTED_RESERVED_FIELD_ID}")',
            )
        if not (id_input.disabled or id_input.read_only):
            failures.append("the ID input remained editable")

    type_control = editor.type_control
    if type_control is None:
        failures.append("the editor did not expose any Type control")
    else:
        if type_control.text != f"Type {EXPECTED_RESERVED_FIELD_TYPE}":
            failures.append(
                "the Type control did not show the reserved Summary type "
                f'("{EXPECTED_RESERVED_FIELD_TYPE}")',
            )
        if type_control.role == "button" and type_control.disabled is None:
            failures.append(
                "the Type value was rendered as an enabled interactive button instead of "
                "an immutable read-only value",
            )

    if not failures:
        return

    raise AssertionError(
        "Step 5 failed: the reserved Summary field editor did not keep ID and Type "
        "immutable.\n"
        f"Observed ID input: {_describe_input(id_input)}\n"
        f"Observed Type control: {_describe_type_control(type_control)}\n"
        f"Observed issue-type chips: {_describe_issue_type_chips(editor)}\n"
        f"Observed editor text:\n{editor.body_text}\n"
        f"Detailed failures: {failures}",
    )


def _assert_custom_field_row(environment_row: SettingsFieldRowObservation) -> None:
    failures: list[str] = []
    expected_edit_label = f"Edit field {CUSTOM_FIELD_NAME}"
    if expected_edit_label not in environment_row.aria_label:
        failures.append(
            f'the field list did not expose the "{expected_edit_label}" action label',
        )
    if not environment_row.delete_action_visible:
        failures.append(
            f'the field list did not expose a delete action for "{CUSTOM_FIELD_NAME}"',
        )
    if not failures:
        return
    raise AssertionError(
        "Step 6 failed: the Environment field row did not expose the expected "
        "custom-field CRUD actions after creation.\n"
        f"Observed Environment row: {environment_row.aria_label}\n"
        f"Detailed failures: {failures}",
    )


def _assert_environment_field_editor(
    editor: FieldEditorObservation,
    *,
    step: int,
    action_description: str,
) -> None:
    failures: list[str] = []
    id_input = editor.id_input
    if id_input is None:
        failures.append("the editor did not expose any ID input")
    elif id_input.value != CUSTOM_FIELD_ID:
        failures.append(
            f'the ID input did not retain "{CUSTOM_FIELD_ID}"',
        )

    name_input = editor.name_input
    if name_input is None:
        failures.append("the editor did not expose any Name input")
    elif name_input.value != CUSTOM_FIELD_NAME:
        failures.append(
            f'the Name input did not retain "{CUSTOM_FIELD_NAME}"',
        )

    options_input = editor.options_input
    if options_input is None:
        failures.append("the editor did not expose any Options input")
    elif _normalize_option_values(options_input.value) != _normalize_option_values(
        CUSTOM_FIELD_OPTIONS_TEXT,
    ):
        failures.append(
            f"the Options input did not retain the expected values {CUSTOM_FIELD_OPTIONS}",
        )

    type_control = editor.type_control
    if type_control is None:
        failures.append("the editor did not expose any Type control")
    elif type_control.text != f"Type {CUSTOM_FIELD_TYPE}":
        failures.append(
            f'the Type control did not retain "{CUSTOM_FIELD_TYPE}"',
        )

    selected_issue_types = {
        chip.text for chip in editor.issue_type_chips if chip.selected == "true"
    }
    if selected_issue_types != CUSTOM_FIELD_ISSUE_TYPES:
        failures.append(
            "the Applicable issue types selection was not limited to Bug only",
        )

    if not failures:
        return

    raise AssertionError(
        f"Step {step} failed: the hosted Environment field editor did not retain the "
        f"expected metadata after {action_description}.\n"
        f"Observed ID input: {_describe_input(id_input)}\n"
        f"Observed Name input: {_describe_input(name_input)}\n"
        f"Observed Options input: {_describe_input(options_input)}\n"
        f"Observed Type control: {_describe_type_control(type_control)}\n"
        f"Observed issue-type chips: {_describe_issue_type_chips(editor)}\n"
        f"Observed editor text:\n{editor.body_text}\n"
        f"Detailed failures: {failures}",
    )


def _describe_input(observation: TextInputObservation | None) -> str:
    if observation is None:
        return "<missing>"
    return (
        f'label="{observation.aria_label}", '
        f'value="{observation.value}", '
        f"disabled={observation.disabled}, "
        f"readOnly={observation.read_only}"
    )


def _describe_type_control(observation: TypeControlObservation | None) -> str:
    if observation is None:
        return "<missing>"
    return (
        f'text="{observation.text}", '
        f"role={observation.role}, "
        f"aria-disabled={observation.disabled}"
    )


def _describe_issue_type_chips(editor: FieldEditorObservation) -> str:
    if not editor.issue_type_chips:
        return "<none>"
    return " | ".join(
        f'{chip.text} (selected={chip.selected})' for chip in editor.issue_type_chips
    )


def _normalize_option_values(value: str) -> tuple[str, ...]:
    return tuple(
        item.strip()
        for item in value.split(",")
        if item.strip()
    )


def _row_payload(row: SettingsFieldRowObservation) -> dict[str, object]:
    return {
        "field_name": row.field_name,
        "aria_label": row.aria_label,
        "action_button_count": row.action_button_count,
        "delete_action_visible": row.delete_action_visible,
    }


def _editor_payload(editor: FieldEditorObservation) -> dict[str, object]:
    return {
        "body_text": editor.body_text,
        "id_input": _input_payload(editor.id_input),
        "name_input": _input_payload(editor.name_input),
        "default_value_input": _input_payload(editor.default_value_input),
        "options_input": _input_payload(editor.options_input),
        "type_control": _type_payload(editor.type_control),
        "issue_type_chips": [
            {"text": chip.text, "selected": chip.selected}
            for chip in editor.issue_type_chips
        ],
    }


def _input_payload(observation: TextInputObservation | None) -> dict[str, object] | None:
    if observation is None:
        return None
    return {
        "aria_label": observation.aria_label,
        "value": observation.value,
        "disabled": observation.disabled,
        "read_only": observation.read_only,
    }


def _type_payload(
    observation: TypeControlObservation | None,
) -> dict[str, object] | None:
    if observation is None:
        return None
    return {
        "text": observation.text,
        "role": observation.role,
        "disabled": observation.disabled,
    }


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    assert isinstance(steps, list)
    steps.append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        },
    )


def _reopen_fields_tab(
    *,
    tracker_page,
    settings_page: LiveSettingsFieldsPage,
    collaboration_page: LiveIssueDetailCollaborationPage,
    token: str,
    repository: str,
    user_login: str,
) -> str:
    runtime = tracker_page.open()
    if runtime.kind != "ready":
        raise AssertionError(
            "The hosted app did not return to a ready state after saving field "
            "settings.\n"
            f"Observed body text:\n{runtime.body_text}",
        )
    collaboration_page.ensure_connected(
        token=token,
        repository=repository,
        user_login=user_login,
    )
    collaboration_page.dismiss_connection_banner()
    settings_page.open_settings_admin()
    return settings_page.open_fields_tab()


def _write_result_if_requested(payload: dict[str, object]) -> None:
    configured_path = os.environ.get("TS408_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts408_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
