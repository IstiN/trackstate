from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_jql_search_page import LiveJqlSearchPage
from testing.components.pages.live_multi_view_refresh_page import (
    EditControlObservation,
    LiveMultiViewRefreshPage,
)
from testing.components.services.live_setup_repository_service import (
    LiveHostedIssueFixture,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-401"
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts401_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts401_success.png"
TARGET_ISSUE_KEY = "DEMO-3"
TARGET_STATUS_LABEL = "Done"
TARGET_PRIORITY_LABEL = "Highest"
EXPECTED_BOARD_COLUMN = "Done"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-401 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = _find_issue_fixture(service=service, issue_key=TARGET_ISSUE_KEY)

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "expected_status": TARGET_STATUS_LABEL,
        "expected_priority": TARGET_PRIORITY_LABEL,
        "steps": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            page = LiveMultiViewRefreshPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the multi-view edit scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the hosted tracker.",
                    observed=runtime.body_text,
                )

                page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Confirm the hosted session is connected with GitHub write access.",
                    observed=page.current_body_text(),
                )

                dialog_text = page.open_edit_dialog_for_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                result["edit_dialog_text"] = dialog_text
                initial_status_control = page.status_control()
                initial_priority_control = page.priority_control()
                result["status_control_before_edit"] = _control_payload(
                    initial_status_control,
                )
                result["priority_control_before_edit"] = _control_payload(
                    initial_priority_control,
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Open the Edit issue surface for DEMO-3 from JQL Search.",
                    observed=dialog_text,
                )

                updated_priority_control = page.change_priority(TARGET_PRIORITY_LABEL)
                result["priority_control_after_edit"] = _control_payload(
                    updated_priority_control,
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Change Priority to Highest in the live Edit issue dialog.",
                    observed=page.current_body_text(),
                )

                updated_status_control = page.change_status_transition(
                    TARGET_STATUS_LABEL,
                )
                result["status_control_after_edit"] = _control_payload(
                    updated_status_control,
                )
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Change Status to Done in the live Edit issue dialog.",
                    observed=page.current_body_text(),
                )

                post_save_detail_text = page.save_issue_edits(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                result["post_save_detail_text"] = post_save_detail_text
                detail_projection_text = page.wait_for_issue_detail_state(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                    expected_status=TARGET_STATUS_LABEL,
                    expected_priority=TARGET_PRIORITY_LABEL,
                    step_number=6,
                )
                result["detail_projection_text"] = detail_projection_text
                _record_step(
                    result,
                    step=6,
                    status="passed",
                    action="Save the edit and wait for the issue detail to refresh.",
                    observed=detail_projection_text,
                )

                board_projection_text = page.wait_for_board_projection(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                    expected_column=EXPECTED_BOARD_COLUMN,
                    expected_priority=TARGET_PRIORITY_LABEL,
                )
                result["board_projection_text"] = board_projection_text
                _record_step(
                    result,
                    step=7,
                    status="passed",
                    action="Verify Board refreshes DEMO-3 into Done with Highest priority.",
                    observed=board_projection_text,
                )

                page.navigate_to_section("Hierarchy")
                hierarchy_body = page.open_issue_from_current_section(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                hierarchy_detail_text = page.wait_for_issue_detail_state(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                    expected_status=TARGET_STATUS_LABEL,
                    expected_priority=TARGET_PRIORITY_LABEL,
                    step_number=8,
                )
                result["hierarchy_body_text"] = hierarchy_body
                result["hierarchy_detail_text"] = hierarchy_detail_text
                _record_step(
                    result,
                    step=8,
                    status="passed",
                    action="Verify Hierarchy reopens DEMO-3 with the refreshed status and priority.",
                    observed=hierarchy_detail_text,
                )

                search_page = LiveJqlSearchPage(tracker_page)
                search_observation = search_page.search(query=issue_fixture.key)
                result["jql_search_observation"] = {
                    "query": search_observation.query,
                    "visible_query": search_observation.visible_query,
                    "count_summary": search_observation.count_summary,
                    "issue_result_labels": list(search_observation.issue_labels),
                    "body_text": search_observation.body_text,
                }
                if (
                    search_observation.count_summary != "1 issue"
                    or f"Open {issue_fixture.key} {issue_fixture.summary}"
                    not in search_observation.issue_labels
                ):
                    raise AssertionError(
                        "Step 9 failed: JQL Search did not visibly refresh down to the "
                        "edited DEMO-3 issue after saving.\n"
                        f"Observed count summary: {search_observation.count_summary}\n"
                        f"Observed result labels: {list(search_observation.issue_labels)}\n"
                        f"Observed JQL Search text:\n{search_observation.body_text}",
                    )
                page.open_issue_from_current_section(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                jql_detail_text = page.wait_for_issue_detail_state(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                    expected_status=TARGET_STATUS_LABEL,
                    expected_priority=TARGET_PRIORITY_LABEL,
                    step_number=9,
                )
                result["jql_detail_text"] = jql_detail_text
                _record_step(
                    result,
                    step=9,
                    status="passed",
                    action="Verify JQL Search can reopen DEMO-3 with the refreshed status and priority.",
                    observed=jql_detail_text,
                )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                page.screenshot(str(SCREENSHOT_PATH))
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
            "Verified the live hosted edit flow for DEMO-3 end-to-end: Priority "
            "changed to Highest, Status changed to Done, and the refreshed issue "
            "state was observed from issue detail, Board, Hierarchy, and JQL Search."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _find_issue_fixture(
    *,
    service: LiveSetupRepositoryService,
    issue_key: str,
) -> LiveHostedIssueFixture:
    issue_path = next(
        (path for path in service.list_issue_paths("DEMO") if path.split("/")[-1] == issue_key),
        None,
    )
    if issue_path is None:
        raise AssertionError(
            "Precondition failed: the live hosted repository does not contain the issue "
            f"{issue_key} needed for TS-401.",
        )
    return service.fetch_issue_fixture(issue_path)


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


def _control_payload(control: EditControlObservation) -> dict[str, object]:
    return {
        "label": control.label,
        "text": control.text,
        "tabindex": control.tabindex,
        "expanded": control.expanded,
    }


def _write_result_if_requested(payload: dict[str, object]) -> None:
    configured_path = os.environ.get("TS401_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts401_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
