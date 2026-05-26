from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_create_issue_form_page import (  # noqa: E402
    LiveCreateIssueFormPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import (  # noqa: E402
    load_live_setup_test_config,
)
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)


OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts304_failure.png"
TICKET_KEY = "TS-304"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-304 requires GH_TOKEN or GITHUB_TOKEN to open the hosted create flow.",
        )

    user = service.fetch_authenticated_user()
    assignee_query = user.login[: max(3, min(len(user.login), 6))]

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "user_login": user.login,
        "assignee_query": assignee_query,
        "steps": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            create_issue_page = LiveCreateIssueFormPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Precondition failed: the deployed app did not reach the hosted "
                        "tracker shell before TS-304 began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=0,
                    status="passed",
                    action="Open the live app and reach the tracker shell.",
                    observed=runtime.body_text,
                )

                connection = tracker_page.connect_with_token(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                result["connect_dialog_text"] = connection.dialog_text
                result["connected_body_text"] = connection.body_text
                _record_step(
                    result,
                    step=0,
                    status="passed",
                    action="Connect the hosted session with GitHub write access.",
                    observed=connection.body_text,
                )

                dialog = create_issue_page.open_create_issue_dialog()
                result["board_text"] = dialog.board_text
                result["create_issue_dialog_text"] = dialog.dialog_text
                _assert_dialog_surface(dialog)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the Create Issue form.",
                    observed=dialog.dialog_text,
                )

                assignee_observation = create_issue_page.search_assignee(
                    query=assignee_query,
                    expected_suggestion=user.login,
                )
                result["assignee_observation"] = {
                    "query": assignee_observation.query,
                    "typed_value": assignee_observation.typed_value,
                    "selected_value": assignee_observation.selected_value,
                    "option_count": assignee_observation.option_count,
                    "matching_option_count": assignee_observation.matching_option_count,
                    "listbox_count": assignee_observation.listbox_count,
                    "body_text": assignee_observation.body_text,
                }
                _assert_assignee_picker(
                    query=assignee_query,
                    expected_suggestion=user.login,
                    observation=assignee_observation,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=(
                        f"Focus Assignee, type {assignee_query!r}, and verify a "
                        "searchable collaborator picker appears."
                    ),
                    observed=assignee_observation.body_text,
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=f"Select the {user.login!r} collaborator suggestion.",
                    observed=assignee_observation.selected_value,
                )

                labels_observation = create_issue_page.commit_labels()
                result["labels_observation"] = {
                    "labels_value_after_enter": labels_observation.labels_value_after_enter,
                    "labels_value_before_comma": labels_observation.labels_value_before_comma,
                    "labels_value_after_comma": labels_observation.labels_value_after_comma,
                    "frontend_token_count": labels_observation.frontend_token_count,
                    "bug_token_count": labels_observation.bug_token_count,
                    "body_text": labels_observation.body_text,
                }
                _assert_label_tokenization(labels_observation)
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Commit the frontend label with Enter.",
                    observed=labels_observation.body_text,
                )
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Commit the bug label with the comma key.",
                    observed=labels_observation.body_text,
                )
            except Exception:
                create_issue_page.screenshot(str(SCREENSHOT_PATH))
                result["screenshot"] = str(SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        print(json.dumps(result, indent=2))
        raise
    else:
        result["status"] = "passed"
        result["summary"] = (
            "Verified the hosted create issue flow exposes a collaborator "
            "assignee picker and tokenizes labels on Enter and comma."
        )
        print(json.dumps(result, indent=2))


def _assert_dialog_surface(dialog) -> None:
    if dialog.summary_field_count != 1:
        raise AssertionError(
            "Step 1 failed: the create issue dialog did not expose exactly one "
            '"Summary" field.\n'
            f"Observed dialog text:\n{dialog.dialog_text}",
        )
    if dialog.assignee_field_count != 1:
        raise AssertionError(
            "Step 1 failed: the create issue dialog did not expose exactly one "
            '"Assignee" field.\n'
            f"Observed dialog text:\n{dialog.dialog_text}",
        )
    if dialog.labels_field_count != 1:
        raise AssertionError(
            "Step 1 failed: the create issue dialog did not expose exactly one "
            '"Labels" field.\n'
            f"Observed dialog text:\n{dialog.dialog_text}",
        )
    if not dialog.labels_helper_visible:
        raise AssertionError(
            "Human-style verification failed: the create issue form did not show the "
            'user-facing helper text "Press comma or Enter to add a label."\n'
            f"Observed dialog text:\n{dialog.dialog_text}",
        )


def _assert_assignee_picker(
    *,
    query: str,
    expected_suggestion: str,
    observation,
) -> None:
    if observation.typed_value != query:
        raise AssertionError(
            "Step 2 failed: the Assignee field did not preserve the typed query.\n"
            f"Expected query: {query}\n"
            f"Observed value: {observation.typed_value}\n"
            f"Observed page text:\n{observation.body_text}",
        )
    if observation.matching_option_count <= 0 and observation.listbox_count <= 0:
        raise AssertionError(
            "Step 2 failed: typing in Assignee did not show any searchable picker or "
            "collaborator suggestion surface.\n"
            f"Typed query: {query}\n"
            f"Expected collaborator suggestion: {expected_suggestion}\n"
            f"Visible field value: {observation.typed_value}\n"
            f"Suggestion option count: {observation.option_count}\n"
            f"Matching suggestion count: {observation.matching_option_count}\n"
            f"Listbox count: {observation.listbox_count}\n"
            f"Observed page text:\n{observation.body_text}",
        )
    if observation.selected_value != expected_suggestion:
        raise AssertionError(
            "Step 3 failed: selecting an assignee suggestion did not leave the chosen "
            "collaborator in the field.\n"
            f"Expected assignee: {expected_suggestion}\n"
            f"Observed value: {observation.selected_value}\n"
            f"Observed page text:\n{observation.body_text}",
        )


def _assert_label_tokenization(observation) -> None:
    if observation.labels_value_after_enter != "":
        raise AssertionError(
            "Step 5 failed: pressing Enter did not clear the Labels field after "
            'committing "frontend".\n'
            f"Observed value after Enter: {observation.labels_value_after_enter}\n"
            f"Observed page text:\n{observation.body_text}",
        )
    if observation.frontend_token_count <= 0:
        raise AssertionError(
            'Step 5 failed: pressing Enter did not render a visible "frontend" label '
            "token.\n"
            f"Observed page text:\n{observation.body_text}",
        )
    if observation.labels_value_before_comma != "bug":
        raise AssertionError(
            'Step 5 failed: the Labels field did not contain the typed "bug" value '
            "before the comma keypress.\n"
            f"Observed value before comma: {observation.labels_value_before_comma}\n"
            f"Observed page text:\n{observation.body_text}",
        )
    if observation.labels_value_after_comma != "":
        raise AssertionError(
            "Step 5 failed: pressing the comma key did not clear the Labels field "
            'after committing "bug".\n'
            f"Observed value after comma: {observation.labels_value_after_comma}\n"
            f"Observed page text:\n{observation.body_text}",
        )
    if observation.bug_token_count <= 0:
        raise AssertionError(
            'Step 5 failed: pressing the comma key did not render a visible "bug" '
            "label token.\n"
            f"Observed page text:\n{observation.body_text}",
        )


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


if __name__ == "__main__":
    main()
