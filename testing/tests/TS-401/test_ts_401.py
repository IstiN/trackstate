from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_multi_view_refresh_page import (
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
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Open the Edit issue surface for DEMO-3 from JQL Search.",
                    observed=dialog_text,
                )

                status_control = page.status_control()
                priority_control = page.priority_control()
                result["status_control"] = {
                    "label": status_control.label,
                    "text": status_control.text,
                }
                result["priority_control"] = {
                    "label": priority_control.label,
                    "text": priority_control.text,
                }

                if status_control.label and "No workflow transitions available." in status_control.label:
                    raise AssertionError(
                        "Step 1 failed: the Edit issue surface for DEMO-3 did not expose "
                        "any workflow transitions, so the scenario could not change the "
                        "Status to Done before saving.\n"
                        f"Expected visible status option: {TARGET_STATUS_LABEL}\n"
                        f"Observed status control label: {status_control.label}\n"
                        f"Observed priority control text: {priority_control.text}\n"
                        f"Observed dialog text:\n{dialog_text}",
                    )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Verify the edit surface exposes both the current priority and a workflow transition control.",
                    observed=dialog_text,
                )
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
            "Verified that the hosted edit surface opened for DEMO-3 and exposed "
            "the visible controls needed to change status and priority for the "
            "multi-view refresh scenario."
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
