from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_create_issue_form_page import (
    CreateIssueDialogObservation,
    CreateIssueSurfaceObservation,
    LiveCreateIssueFormPage,
)
from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app

TICKET_KEY = "TS-335"
VIEWPORT_WIDTH = 390
VIEWPORT_HEIGHT = 844
OUTPUTS_DIR = REPO_ROOT / "outputs"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts335_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts335_success.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    user = service.fetch_authenticated_user()
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-335 requires GH_TOKEN or GITHUB_TOKEN to open the live hosted Create issue flow.",
        )

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "viewport": {
            "width": VIEWPORT_WIDTH,
            "height": VIEWPORT_HEIGHT,
        },
        "steps": [],
    }

    try:
        with create_live_tracker_app(
            config,
            viewport_width=VIEWPORT_WIDTH,
            viewport_height=VIEWPORT_HEIGHT,
        ) as tracker_page:
            create_issue_page = LiveCreateIssueFormPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the live hosted app did not reach an interactive "
                        f"state at {VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT}.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=0,
                    status="passed",
                    action=f"Open the live hosted app at {VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT}.",
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
                    step=1,
                    status="passed",
                    action="Connect GitHub so the hosted Create issue action becomes writable.",
                    observed=connection.body_text,
                )

                dialog = create_issue_page.open_create_issue_dialog_from_current_view()
                result["dialog_observation"] = _dialog_to_dict(dialog)
                _assert_dialog(dialog)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Open the Create issue form and verify the user-visible controls.",
                    observed=dialog.dialog_text,
                )

                layout = create_issue_page.observe_surface_layout()
                result["layout"] = _layout_to_dict(layout)
                _assert_layout(layout)
                create_issue_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Inspect the Create issue surface dimensions and origin coordinates.",
                    observed=f"{layout.describe()}\n\nVisible dialog text:\n{layout.dialog_text}",
                )
            except Exception:
                create_issue_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
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
            "Verified on the live hosted app that Create issue opens as a full-screen "
            f"{VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT} surface at (0,0) with no side or bottom inset."
        )
        print(json.dumps(result, indent=2))


def _assert_dialog(dialog: CreateIssueDialogObservation) -> None:
    failures: list[str] = []
    for required_text in (
        "Create issue",
        "Issue Type",
        "Priority",
        "Initial status",
        "Save",
        "Cancel",
    ):
        if required_text not in dialog.dialog_text:
            failures.append(
                f'Step 2 failed: the live Create issue dialog did not show "{required_text}".',
            )

    if dialog.summary_field_count != 1:
        failures.append(
            "Step 2 failed: the live Create issue dialog did not expose exactly one "
            f'Summary field. Observed Summary field count: {dialog.summary_field_count}.',
        )
    if dialog.description_field_count != 1:
        failures.append(
            "Step 2 failed: the live Create issue dialog did not expose exactly one "
            "Description field. Observed Description field count: "
            f"{dialog.description_field_count}.",
        )

    if failures:
        raise AssertionError(
            "\n".join(
                [
                    *failures,
                    "",
                    "Observed Create issue dialog text:",
                    dialog.dialog_text,
                ],
            ),
        )


def _assert_layout(layout: CreateIssueSurfaceObservation) -> None:
    failures: list[str] = []
    epsilon = 0.5
    if abs(layout.viewport_width - VIEWPORT_WIDTH) > epsilon or abs(layout.viewport_height - VIEWPORT_HEIGHT) > epsilon:
        failures.append(
            "Step 1 failed: the hosted viewport did not remain at the requested "
            f"{VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT} size.\nObserved layout: {layout.describe()}",
        )

    if (
        abs(layout.surface_left) > epsilon
        or abs(layout.surface_top) > epsilon
        or abs(layout.surface_width - VIEWPORT_WIDTH) > epsilon
        or abs(layout.surface_height - VIEWPORT_HEIGHT) > epsilon
    ):
        failures.append(
            "Step 3 failed: the live Create issue surface did not render as a full-screen "
            f"{VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT} surface at coordinates (0,0).\n"
            f"Observed layout: {layout.describe()}",
        )

    if (
        abs(layout.left_inset) > epsilon
        or abs(layout.right_inset) > epsilon
        or abs(layout.top_inset) > epsilon
        or abs(layout.bottom_inset) > epsilon
    ):
        failures.append(
            "Expected Result failed: the live Create issue surface still left at least one "
            f"inset on the mobile viewport.\nObserved layout: {layout.describe()}",
        )

    if failures:
        raise AssertionError(
            "\n".join(
                [
                    *failures,
                    "",
                    "Observed Create issue dialog text:",
                    layout.dialog_text,
                ],
            ),
        )


def _dialog_to_dict(dialog: CreateIssueDialogObservation) -> dict[str, object]:
    return {
        "board_text": dialog.board_text,
        "dialog_text": dialog.dialog_text,
        "summary_field_count": dialog.summary_field_count,
        "description_field_count": dialog.description_field_count,
        "assignee_field_count": dialog.assignee_field_count,
        "labels_field_count": dialog.labels_field_count,
        "labels_helper_visible": dialog.labels_helper_visible,
    }


def _layout_to_dict(layout: CreateIssueSurfaceObservation) -> dict[str, object]:
    return {
        "viewport_width": layout.viewport_width,
        "viewport_height": layout.viewport_height,
        "surface_left": layout.surface_left,
        "surface_top": layout.surface_top,
        "surface_width": layout.surface_width,
        "surface_height": layout.surface_height,
        "left_inset": layout.left_inset,
        "right_inset": layout.right_inset,
        "top_inset": layout.top_inset,
        "bottom_inset": layout.bottom_inset,
        "description": layout.describe(),
        "dialog_text": layout.dialog_text,
        "body_text": layout.body_text,
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


if __name__ == "__main__":
    main()
