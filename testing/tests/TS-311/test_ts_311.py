from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (  # noqa: E402
    LiveIssueDetailCollaborationPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import WebAppTimeoutError  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-311"
OUTPUTS_DIR = REPO_ROOT / "outputs"
RESULT_PATH = OUTPUTS_DIR / "ts311_result.json"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts311_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts311_success.png"

ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
DOWNLOAD_ONLY_MESSAGE = "This repository session is download-only for Git LFS attachments."
UPLOAD_CONTROL_FRAGMENTS = ("Upload", "Choose file", "Select file", "Add attachment")


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    repository_service = LiveSetupRepositoryService(config=config)
    token = repository_service.token
    if not token:
        raise RuntimeError(
            "TS-311 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = repository_service.fetch_authenticated_user()
    issue_fixture = repository_service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)

    comment_body = issue_fixture.comment_bodies[0].strip()
    attachment_name = Path(issue_fixture.attachment_paths[0]).name
    expected_download_label = f"Download {attachment_name}"

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": repository_service.repository,
        "repository_ref": repository_service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "comment_body": comment_body,
        "attachment_name": attachment_name,
        "expected_download_label": expected_download_label,
        "upload_control_fragments": list(UPLOAD_CONTROL_FRAGMENTS),
        "steps": [],
        "tab_counts": {},
        "tab_observations": {},
    }
    failures: list[str] = []

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
                        "shell before the collaboration-tab scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the live app and reach the hosted tracker shell.",
                    observed=runtime.body_text,
                )

                live_issue_page.ensure_connected(
                    token=token,
                    repository=repository_service.repository,
                    user_login=user.login,
                )
                live_issue_page.open_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                issue_detail_text = live_issue_page.current_body_text()
                result["initial_issue_detail_text"] = issue_detail_text
                if live_issue_page.issue_detail_count(issue_fixture.key) <= 0:
                    raise AssertionError(
                        "Step 1 failed: the hosted app did not open the requested issue "
                        f"detail for {issue_fixture.key}.\n"
                        f"Observed body text:\n{issue_detail_text}",
                    )

                tab_counts = {
                    "Detail": live_issue_page.tab_button_count("Detail"),
                    "Comments": live_issue_page.tab_button_count("Comments"),
                    "Attachments": live_issue_page.tab_button_count("Attachments"),
                    "History": live_issue_page.tab_button_count("History"),
                }
                result["tab_counts"] = tab_counts

                if live_issue_page.selected_tab_count("Detail") <= 0:
                    failures.append(
                        "Step 2 failed: the issue detail did not open on the dedicated "
                        '"Detail" tab before collaboration navigation began.\n'
                        f"Observed body text:\n{issue_detail_text}",
                    )
                for label, count in tab_counts.items():
                    if count <= 0:
                        failures.append(
                            f'Step 2 failed: the issue detail did not expose a dedicated "{label}" '
                            "tab button in the hosted session.\n"
                            f"Observed body text:\n{issue_detail_text}",
                        )
                if comment_body in issue_detail_text:
                    failures.append(
                        "Step 2 failed: the seeded comment body was already visible on the "
                        'initial issue-detail surface instead of being gated by the "Comments" tab.\n'
                        f"Unexpected text: {comment_body}\n"
                        f"Observed body text:\n{issue_detail_text}",
                    )
                if attachment_name in issue_detail_text:
                    failures.append(
                        "Step 2 failed: the seeded attachment name was already visible on the "
                        'initial issue-detail surface instead of being gated by the "Attachments" tab.\n'
                        f"Unexpected text: {attachment_name}\n"
                        f"Observed body text:\n{issue_detail_text}",
                    )
                if DOWNLOAD_ONLY_MESSAGE in issue_detail_text:
                    failures.append(
                        "Step 2 failed: the attachment read-only guidance was already visible "
                        'before the "Attachments" tab was opened.\n'
                        f"Unexpected text: {DOWNLOAD_ONLY_MESSAGE}\n"
                        f"Observed body text:\n{issue_detail_text}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed" if not failures else "failed",
                    action=(
                        "Open the seeded issue detail and verify collaboration data stays "
                        "behind dedicated tabs before navigation."
                    ),
                    observed=issue_detail_text,
                )

                if tab_counts["Comments"] > 0:
                    _exercise_comments_tab(
                        live_issue_page=live_issue_page,
                        comment_body=comment_body,
                        result=result,
                        failures=failures,
                    )
                if tab_counts["History"] > 0:
                    _exercise_history_tab(
                        live_issue_page=live_issue_page,
                        result=result,
                        failures=failures,
                    )
                if tab_counts["Attachments"] > 0:
                    _exercise_attachments_tab(
                        live_issue_page=live_issue_page,
                        attachment_name=attachment_name,
                        expected_download_label=expected_download_label,
                        result=result,
                        failures=failures,
                    )

                screenshot_path = SUCCESS_SCREENSHOT_PATH if not failures else FAILURE_SCREENSHOT_PATH
                live_issue_page.screenshot(str(screenshot_path))
                result["screenshot"] = str(screenshot_path)
            except Exception:
                live_issue_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_result(result)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_result(result)
        print(json.dumps(result, indent=2))
        raise
    else:
        if failures:
            error_message = "\n\n".join(failures)
            result["error"] = error_message
            result["summary"] = (
                "Observed the live hosted collaboration-tab flow, but at least one "
                "tab-gating or attachment-capability expectation did not match TS-311."
            )
            _write_result(result)
            print(json.dumps(result, indent=2))
            raise AssertionError(error_message)

        result["status"] = "passed"
        result["summary"] = (
            "Verified in the live hosted tracker that issue-detail collaboration data "
            "is tab-gated and the Attachments tab is download-only for the seeded "
            "Git LFS attachment."
        )
        _write_result(result)
        print(json.dumps(result, indent=2))


def _exercise_comments_tab(
    *,
    live_issue_page: LiveIssueDetailCollaborationPage,
    comment_body: str,
    result: dict[str, object],
    failures: list[str],
) -> None:
    try:
        live_issue_page.open_collaboration_tab("Comments")
        live_issue_page.wait_for_selected_tab("Comments", timeout_ms=30_000)
        live_issue_page.wait_for_text(comment_body, timeout_ms=30_000)
    except WebAppTimeoutError as error:
        failures.append(
            "Step 3 failed: the visible Comments tab did not become the active "
            "collaboration view with the seeded comment content.\n"
            f"Observed body text:\n{live_issue_page.current_body_text()}",
        )
        result["tab_observations"] = {
            **_tab_observations(result),
            "Comments": {
                "selected": live_issue_page.selected_tab_count("Comments"),
                "body_text": live_issue_page.current_body_text(),
            },
        }
        return

    comments_text = live_issue_page.current_body_text()
    _tab_observations(result)["Comments"] = {
        "selected": live_issue_page.selected_tab_count("Comments"),
        "body_text": comments_text,
    }
    if live_issue_page.selected_tab_count("Comments") <= 0:
        failures.append(
            "Step 3 failed: the Comments tab was visible but did not stay selected "
            "after it was opened.\n"
            f"Observed body text:\n{comments_text}",
        )
    if comment_body not in comments_text:
        failures.append(
            "Step 3 failed: opening the Comments tab did not render the seeded "
            "comment body for the user.\n"
            f"Expected comment text: {comment_body}\n"
            f"Observed body text:\n{comments_text}",
        )
    _record_step(
        result,
        step=3,
        status="passed",
        action="Open the Comments tab and verify the seeded comment becomes visible.",
        observed=comments_text,
    )


def _exercise_history_tab(
    *,
    live_issue_page: LiveIssueDetailCollaborationPage,
    result: dict[str, object],
    failures: list[str],
) -> None:
    try:
        live_issue_page.open_collaboration_tab("History")
        live_issue_page.wait_for_selected_tab("History", timeout_ms=30_000)
    except WebAppTimeoutError:
        failures.append(
            "Step 4 failed: the visible History tab did not become the active "
            "collaboration view after it was opened.\n"
            f"Observed body text:\n{live_issue_page.current_body_text()}",
        )
        _tab_observations(result)["History"] = {
            "selected": live_issue_page.selected_tab_count("History"),
            "body_text": live_issue_page.current_body_text(),
        }
        return

    history_text = live_issue_page.current_body_text()
    _tab_observations(result)["History"] = {
        "selected": live_issue_page.selected_tab_count("History"),
        "body_text": history_text,
    }
    if live_issue_page.selected_tab_count("History") <= 0:
        failures.append(
            "Step 4 failed: the History tab was visible but did not stay selected "
            "after it was opened.\n"
            f"Observed body text:\n{history_text}",
        )
    _record_step(
        result,
        step=4,
        status="passed",
        action="Open the History tab and verify the issue detail switches to that tab.",
        observed=history_text,
    )


def _exercise_attachments_tab(
    *,
    live_issue_page: LiveIssueDetailCollaborationPage,
    attachment_name: str,
    expected_download_label: str,
    result: dict[str, object],
    failures: list[str],
) -> None:
    try:
        live_issue_page.open_collaboration_tab("Attachments")
        live_issue_page.wait_for_selected_tab("Attachments", timeout_ms=30_000)
        live_issue_page.wait_for_text(attachment_name, timeout_ms=30_000)
    except WebAppTimeoutError:
        failures.append(
            "Step 5 failed: the visible Attachments tab did not become the active "
            "collaboration view with the seeded attachment row.\n"
            f"Observed body text:\n{live_issue_page.current_body_text()}",
        )
        _tab_observations(result)["Attachments"] = {
            "selected": live_issue_page.selected_tab_count("Attachments"),
            "body_text": live_issue_page.current_body_text(),
        }
        return

    attachments_text = live_issue_page.current_body_text()
    upload_button_counts = {
        fragment: live_issue_page.visible_button_label_fragment_count(fragment)
        for fragment in UPLOAD_CONTROL_FRAGMENTS
    }
    attachments_observation = {
        "selected": live_issue_page.selected_tab_count("Attachments"),
        "body_text": attachments_text,
        "download_only_message_count": live_issue_page.text_fragment_count(
            DOWNLOAD_ONLY_MESSAGE,
        ),
        "download_button_count": live_issue_page.attachment_download_button_count(
            attachment_name,
        ),
        "download_button_disabled_count": live_issue_page.button_label_fragment_disabled_count(
            "Download",
        ),
        "upload_button_counts": upload_button_counts,
        "visible_file_input_count": live_issue_page.visible_file_input_count(),
    }
    _tab_observations(result)["Attachments"] = attachments_observation

    if attachments_observation["selected"] <= 0:
        failures.append(
            "Step 5 failed: the Attachments tab was visible but did not stay selected "
            "after it was opened.\n"
            f"Observed body text:\n{attachments_text}",
        )
    if attachment_name not in attachments_text:
        failures.append(
            "Step 5 failed: opening the Attachments tab did not render the seeded "
            "attachment row for the user.\n"
            f"Expected attachment: {attachment_name}\n"
            f"Observed body text:\n{attachments_text}",
        )
    if DOWNLOAD_ONLY_MESSAGE not in attachments_text:
        failures.append(
            "Step 5 failed: the hosted Attachments tab did not show the explicit "
            "download-only guidance for Git LFS attachments.\n"
            f"Expected message: {DOWNLOAD_ONLY_MESSAGE}\n"
            f"Observed body text:\n{attachments_text}",
        )
    if attachments_observation["download_button_count"] <= 0:
        failures.append(
            "Step 5 failed: the hosted Attachments tab did not keep a visible "
            "download action for the seeded attachment.\n"
            f"Expected label: {expected_download_label}\n"
            f"Observed body text:\n{attachments_text}",
        )
    else:
        visible_download_label = live_issue_page.attachment_download_button_label(
            attachment_name,
        )
        attachments_observation["visible_download_label"] = visible_download_label
        if visible_download_label != expected_download_label:
            failures.append(
                "Step 5 failed: the attachment download action did not expose the "
                "expected user-facing label.\n"
                f"Expected label: {expected_download_label}\n"
                f"Observed label: {visible_download_label}",
            )
    if attachments_observation["download_button_disabled_count"] > 0:
        failures.append(
            "Step 5 failed: the download action appeared disabled even though TS-311 "
            "requires download to remain available for LFS-backed attachments.\n"
            f"Observed body text:\n{attachments_text}",
        )
    if attachments_observation["visible_file_input_count"] > 0 or any(
        count > 0 for count in upload_button_counts.values()
    ):
        failures.append(
            "Step 5 failed: the hosted Attachments tab still exposed upload controls "
            "instead of a download-only experience for Git LFS attachments.\n"
            f"Visible upload button counts: {upload_button_counts}\n"
            f"Visible file input count: {attachments_observation['visible_file_input_count']}\n"
            f"Observed body text:\n{attachments_text}",
        )
    _record_step(
        result,
        step=5,
        status="passed",
        action=(
            "Open the Attachments tab and verify download-only guidance, hidden upload "
            "controls, and an available download action for the seeded attachment."
        ),
        observed=attachments_text,
    )


def _assert_preconditions(issue_fixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-311 expected the seeded DEMO-2 fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.attachment_paths:
        raise AssertionError(
            "Precondition failed: DEMO-2 does not contain any seeded attachments in "
            f"{issue_fixture.path}.",
        )
    if not issue_fixture.comment_bodies:
        raise AssertionError(
            "Precondition failed: DEMO-2 does not contain any seeded comments in "
            f"{issue_fixture.path}.",
        )


def _tab_observations(result: dict[str, object]) -> dict[str, object]:
    tab_observations = result.setdefault("tab_observations", {})
    assert isinstance(tab_observations, dict)
    return tab_observations


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


def _write_result(payload: dict[str, object]) -> None:
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
