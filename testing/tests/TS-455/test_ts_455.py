from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (  # noqa: E402
    LiveIssueDetailCollaborationPage,
    TabChipObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.comments_artifact_outage_runtime import (  # noqa: E402
    CommentsArtifactOutageObservation,
    CommentsArtifactOutageRuntime,
)
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402

TICKET_KEY = "TS-455"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
EXPECTED_ISSUE_KEY = "DEMO-2"
EXPECTED_COMMENT_BODY = "This comment demonstrates markdown-backed collaboration history."
FAILURE_MESSAGE = "TS-455 synthetic comments outage"
MIN_FAILURE_WIDTH_DELTA = 8.0

OUTPUTS_DIR = REPO_ROOT / "outputs"
RESULT_PATH = OUTPUTS_DIR / "ts455_result.json"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts455_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts455_success.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-455 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)

    outage_observation = CommentsArtifactOutageObservation.from_comment_paths(
        issue_fixture.comment_paths,
        failure_message=FAILURE_MESSAGE,
    )
    runtime = CommentsArtifactOutageRuntime(
        repository=service.repository,
        token=token,
        observation=outage_observation,
    )

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_description": issue_fixture.description,
        "comment_paths": list(issue_fixture.comment_paths),
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveIssueDetailCollaborationPage(tracker_page)
            try:
                runtime_state = tracker_page.open()
                result["runtime_state"] = runtime_state.kind
                result["runtime_body_text"] = runtime_state.body_text
                if runtime_state.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the deferred comments outage scenario began.\n"
                        f"Observed body text:\n{runtime_state.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the live app and reach the hosted tracker shell.",
                    observed=runtime_state.body_text,
                )

                page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                page.dismiss_connection_banner()
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Connect the hosted GitHub session for the deployed repository.",
                    observed=page.current_body_text(),
                )

                page.open_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                issue_detail_text = page.current_body_text()
                result["issue_detail_text_before_failure"] = issue_detail_text
                if page.issue_detail_count(issue_fixture.key) == 0:
                    raise AssertionError(
                        "Step 3 failed: selecting the seeded issue did not open the hosted "
                        "issue detail before the Comments artifact failure was exercised.\n"
                        f"Observed body text:\n{issue_detail_text}",
                    )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Open the seeded issue detail page.",
                    observed=issue_detail_text,
                )

                initial_comments_tab = page.observe_tab_chip("Comments")
                result["comments_tab_before_failure"] = _tab_payload(initial_comments_tab)

                page.open_collaboration_tab("Comments")
                comments_error_label = page.wait_for_deferred_error(
                    "Comments",
                    expected_fragment=FAILURE_MESSAGE,
                    timeout_ms=60_000,
                )
                failed_comments_tab = page.observe_tab_chip("Comments")
                result["comments_error_label"] = comments_error_label
                result["comments_tab_after_failure"] = _tab_payload(failed_comments_tab)
                result["blocked_comment_urls"] = list(outage_observation.blocked_urls)

                if not outage_observation.blocked_was_exercised:
                    raise AssertionError(
                        "Step 4 failed: the synthetic comments outage UI appeared without "
                        "intercepting any live Comments artifact request.\n"
                        f"Tracked comment paths: {list(issue_fixture.comment_paths)}",
                    )
                for expected_fragment in ("Comments error", "Comments", FAILURE_MESSAGE, "Retry"):
                    if expected_fragment not in comments_error_label:
                        raise AssertionError(
                            "Step 4 failed: the Comments error state did not expose the "
                            "expected accessible inline error content.\n"
                            f"Missing fragment: {expected_fragment}\n"
                            f"Observed accessible label:\n{comments_error_label}",
                        )
                width_delta = failed_comments_tab.width - initial_comments_tab.width
                result["comments_failure_width_delta"] = width_delta
                if width_delta <= MIN_FAILURE_WIDTH_DELTA:
                    raise AssertionError(
                        "Step 4 failed: the Comments tab chip did not grow to show the "
                        "warning/error indicator after the artifact failure.\n"
                        f"Width before failure: {initial_comments_tab.width}\n"
                        f"Width after failure: {failed_comments_tab.width}\n"
                        f"Observed accessible label:\n{comments_error_label}",
                    )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Block the Comments artifact request, open Comments, and verify the "
                        "tab-strip warning indicator plus the inline Retry error UI."
                    ),
                    observed=comments_error_label,
                )
                _record_human_verification(
                    result,
                    check=(
                        'Verified the visible "Comments" chip widened to include the '
                        "failure indicator and the Comments panel exposed a Retry action."
                    ),
                    observed=(
                        f"width_before={initial_comments_tab.width}, "
                        f"width_after={failed_comments_tab.width}, "
                        f"error_label={comments_error_label}"
                    ),
                )

                page.open_collaboration_tab("Detail")
                page.wait_for_selected_tab("Detail", timeout_ms=30_000)
                detail_tab = page.observe_tab_chip("Detail")
                detail_text = page.issue_detail_accessible_label(
                    issue_fixture.key,
                    expected_fragment="Priority",
                    timeout_ms=30_000,
                )
                result["detail_tab_after_comments_failure"] = _tab_payload(detail_tab)
                result["detail_text_after_comments_failure"] = detail_text
                if not detail_tab.is_selected:
                    raise AssertionError(
                        "Step 5 failed: switching away from the failed Comments tab did not "
                        "leave the Detail tab selected.\n"
                        f"Observed detail tab: {_tab_payload(detail_tab)}",
                    )
                for expected_fragment in (issue_fixture.summary, "Priority", "Status"):
                    if expected_fragment not in detail_text:
                        raise AssertionError(
                            "Step 5 failed: the Detail tab was blocked by the Comments "
                            "artifact failure and did not expose the expected issue detail "
                            "content.\n"
                            f"Missing fragment: {expected_fragment}\n"
                            f"Observed body text:\n{detail_text}",
                        )
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Open Detail and verify its issue content stays usable.",
                    observed=detail_text,
                )
                _record_human_verification(
                    result,
                    check=(
                        'Verified the visible "Detail" tab still showed the issue summary, '
                        "Status, and Priority while Comments remained in an error state."
                    ),
                    observed=detail_text,
                )

                page.open_collaboration_tab("Comments")
                page.wait_for_deferred_error(
                    "Comments",
                    expected_fragment=FAILURE_MESSAGE,
                    timeout_ms=30_000,
                )
                runtime.restore_connectivity()
                page.click_deferred_retry("Comments", timeout_ms=30_000)
                remaining_error_cards = page.wait_for_deferred_error_to_clear(
                    "Comments",
                    timeout_ms=60_000,
                )
                recovered_comments_text = page.wait_for_text(
                    EXPECTED_COMMENT_BODY,
                    timeout_ms=60_000,
                )
                recovered_comments_tab = page.observe_tab_chip("Comments")
                result["comments_tab_after_retry"] = _tab_payload(recovered_comments_tab)
                result["comments_text_after_retry"] = recovered_comments_text
                result["allowed_comment_urls"] = list(outage_observation.allowed_urls)
                result["remaining_comments_error_cards"] = remaining_error_cards

                if remaining_error_cards != 0:
                    raise AssertionError(
                        "Step 6 failed: the Comments inline error UI remained visible after "
                        "the retry action completed.\n"
                        f"Remaining error card count: {remaining_error_cards}\n"
                        f"Observed body text:\n{recovered_comments_text}",
                    )
                if EXPECTED_COMMENT_BODY not in recovered_comments_text:
                    raise AssertionError(
                        "Step 6 failed: retrying the Comments artifact did not restore the "
                        "seeded visible comment body.\n"
                        f"Expected visible comment: {EXPECTED_COMMENT_BODY}\n"
                        f"Observed body text:\n{recovered_comments_text}",
                    )
                if recovered_comments_tab.width >= failed_comments_tab.width - MIN_FAILURE_WIDTH_DELTA:
                    raise AssertionError(
                        "Step 6 failed: the Comments tab strip warning indicator did not "
                        "clear after Retry restored the artifact.\n"
                        f"Width while failed: {failed_comments_tab.width}\n"
                        f"Width after retry: {recovered_comments_tab.width}\n"
                        f"Allowed retry URLs: {outage_observation.allowed_urls}",
                    )
                _record_step(
                    result,
                    step=6,
                    status="passed",
                    action=(
                        "Restore connectivity and click Retry in the Comments body to "
                        "refetch the failed artifact."
                    ),
                    observed=recovered_comments_text,
                )
                _record_human_verification(
                    result,
                    check=(
                        'Verified the visible "Retry" action cleared the Comments error, '
                        "restored the seeded comment text, and removed the tab warning indicator."
                    ),
                    observed=(
                        f"width_after_retry={recovered_comments_tab.width}, "
                        f"comments_text={recovered_comments_text}"
                    ),
                )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
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
            "Verified the hosted issue detail isolates a failed Comments artifact with a "
            "tab-strip warning indicator and inline Retry UI, keeps Detail usable, and "
            "successfully restores Comments after connectivity returns."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_preconditions(issue_fixture: LiveHostedIssueFixture) -> None:
    if issue_fixture.key != EXPECTED_ISSUE_KEY:
        raise AssertionError(
            "Precondition failed: TS-455 expected the seeded DEMO-2 fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.comment_paths:
        raise AssertionError(
            "Precondition failed: DEMO-2 does not contain any seeded comments in "
            f"{issue_fixture.path}.",
        )
    if EXPECTED_COMMENT_BODY not in issue_fixture.comment_bodies:
        raise AssertionError(
            "Precondition failed: DEMO-2 no longer exposes the expected seeded comment "
            "content needed for the Retry recovery check.\n"
            f"Observed comment bodies: {issue_fixture.comment_bodies}",
        )


def _tab_payload(observation: TabChipObservation) -> dict[str, object]:
    return {
        "label": observation.label,
        "is_selected": observation.is_selected,
        "left": observation.left,
        "top": observation.top,
        "width": observation.width,
        "height": observation.height,
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


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    verifications = result.setdefault("human_verification", [])
    assert isinstance(verifications, list)
    verifications.append({"check": check, "observed": observed})


def _write_result_if_requested(payload: dict[str, object]) -> None:
    configured_path = os.environ.get("TS455_RESULT_PATH")
    result_path = Path(configured_path) if configured_path else RESULT_PATH
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
