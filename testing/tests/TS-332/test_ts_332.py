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
from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-332"
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts332_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts332_success.png"
MAX_TAB_STEPS = 8


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-332 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture("DEMO/DEMO-1/DEMO-2")
    attachment_name = Path(issue_fixture.attachment_paths[0]).name
    expected_download_label = f"Download {attachment_name}"

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "attachment_name": attachment_name,
        "expected_download_label": expected_download_label,
        "max_tab_steps": MAX_TAB_STEPS,
        "steps": [],
    }

    _assert_preconditions(issue_fixture)

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            live_issue_page = LiveIssueDetailCollaborationPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the attachment download accessibility scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the live app and reach the tracker shell.",
                    observed=runtime.body_text,
                )

                live_issue_page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                live_issue_page.open_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                issue_detail_text = live_issue_page.current_body_text()
                if live_issue_page.issue_detail_count(issue_fixture.key) <= 0:
                    raise AssertionError(
                        "Step 1 failed: the hosted app did not open the requested issue "
                        f"detail for {issue_fixture.key}.\n"
                        f"Observed body text:\n{issue_detail_text}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Open the seeded issue detail that contains an attachment.",
                    observed=issue_detail_text,
                )

                live_issue_page.open_collaboration_tab("Attachments")
                live_issue_page.wait_for_text(attachment_name, timeout_ms=30_000)
                attachments_text = live_issue_page.current_body_text()
                result["attachments_body_text"] = attachments_text

                if attachment_name not in attachments_text:
                    raise AssertionError(
                        "Step 3 failed: the Attachments tab did not render the seeded "
                        f"attachment {attachment_name}.\n"
                        f"Observed body text:\n{attachments_text}",
                    )
                download_button_count = live_issue_page.attachment_download_button_count(
                    attachment_name,
                )
                if download_button_count <= 0:
                    raise AssertionError(
                        "Step 3 failed: the Attachments tab did not expose a visible "
                        "download control for the seeded attachment.\n"
                        f"Expected visible control text: {expected_download_label}\n"
                        f"Observed body text:\n{attachments_text}",
                    )
                visible_download_label = live_issue_page.attachment_download_button_label(
                    attachment_name,
                )
                result["visible_download_label"] = visible_download_label
                if visible_download_label != expected_download_label:
                    raise AssertionError(
                        "Step 3 failed: the attachment download control did not expose the "
                        "expected localized user-facing label.\n"
                        f"Expected label: {expected_download_label}\n"
                        f"Observed label: {visible_download_label}",
                    )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Open the Attachments tab and verify the visible download label.",
                    observed=attachments_text,
                )

                live_issue_page.focus_collaboration_tab("Attachments")
                traversal = [_focused_element_dict(live_issue_page.active_element())]
                for _ in range(MAX_TAB_STEPS):
                    live_issue_page.press_key("Tab")
                    traversal.append(_focused_element_dict(live_issue_page.active_element()))
                result["tab_traversal"] = traversal

                focused_download = _find_download_focus(traversal, expected_download_label)
                if focused_download is None:
                    raise AssertionError(
                        "Step 4 failed: keyboard Tab navigation did not move focus from the "
                        "Attachments tab to the attachment download control.\n"
                        f"Expected focused label: {expected_download_label}\n"
                        f"Observed focus traversal: {_format_focus_traversal(traversal)}\n"
                        f"Observed Attachments text:\n{attachments_text}",
                    )

                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Use keyboard Tab navigation to move focus from the Attachments tab to the download control.",
                    observed=_format_focus_traversal(traversal),
                )

                downloaded_filename = live_issue_page.trigger_focused_download()
                result["downloaded_filename"] = downloaded_filename
                if downloaded_filename != attachment_name:
                    raise AssertionError(
                        "Step 5 failed: pressing Enter on the focused download control did "
                        "not start the expected attachment download.\n"
                        f"Expected downloaded file: {attachment_name}\n"
                        f"Observed downloaded file: {downloaded_filename}\n"
                        f"Observed focus traversal: {_format_focus_traversal(traversal)}",
                    )

                live_issue_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Press Enter on the focused download control.",
                    observed=downloaded_filename,
                )
            except Exception:
                live_issue_page.screenshot(str(SCREENSHOT_PATH))
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
            "Verified that the hosted attachment download control is visibly labeled, "
            "reachable with keyboard Tab navigation, and triggers the expected file "
            "download when activated with Enter."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_preconditions(issue_fixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-332 expected the seeded DEMO-2 fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.attachment_paths:
        raise AssertionError(
            "Precondition failed: DEMO-2 does not contain any seeded attachments in "
            f"{issue_fixture.path}.",
        )


def _focused_element_dict(observation) -> dict[str, str | None]:
    return {
        "tag_name": observation.tag_name,
        "role": observation.role,
        "accessible_name": observation.accessible_name,
        "text": observation.text,
        "tabindex": observation.tabindex,
        "outer_html": observation.outer_html,
    }


def _find_download_focus(
    traversal: list[dict[str, str | None]],
    expected_download_label: str,
) -> dict[str, str | None] | None:
    for observation in traversal:
        if observation.get("role") != "button":
            continue
        accessible_name = (observation.get("accessible_name") or "").strip()
        text = (observation.get("text") or "").strip()
        if accessible_name == expected_download_label or text == expected_download_label:
            return observation
    return None


def _format_focus_traversal(traversal: list[dict[str, str | None]]) -> str:
    parts: list[str] = []
    for index, observation in enumerate(traversal):
        label = observation.get("accessible_name") or observation.get("text") or "<empty>"
        tag = observation.get("tag_name") or "UNKNOWN"
        role = observation.get("role") or "none"
        parts.append(f"{index}: {label} [{tag}, role={role}]")
    return " -> ".join(parts)


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
    configured_path = os.environ.get("TS332_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts332_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
