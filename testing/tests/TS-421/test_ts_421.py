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
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import WebAppSession  # noqa: E402
from testing.tests.support.deferred_tab_hydration_observer_runtime import (  # noqa: E402
    DeferredTabHydrationObserverRuntime,
)
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app,
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-421"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
QUIET_WINDOW_MS = 2_000

OUTPUTS_DIR = REPO_ROOT / "outputs"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts421_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-421 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)

    first_comment_path = issue_fixture.comment_paths[0]
    first_comment_body = _first_visible_line(issue_fixture.comment_bodies[0])
    first_comment_id = Path(first_comment_path).stem
    expected_history_fragment = f"Added comment {first_comment_id}"

    runtime = DeferredTabHydrationObserverRuntime(
        repository=service.repository,
        token=token,
        issue_path=issue_fixture.path,
        comment_paths=list(issue_fixture.comment_paths),
    )

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_path": issue_fixture.path,
        "comment_paths": list(issue_fixture.comment_paths),
        "expected_history_fragment": expected_history_fragment,
        "quiet_window_ms": QUIET_WINDOW_MS,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveIssueDetailCollaborationPage(tracker_page)
            session = tracker_page.session

            runtime_state = tracker_page.open()
            result["runtime_state"] = runtime_state.kind
            result["runtime_body_text"] = runtime_state.body_text
            if runtime_state.kind != "ready":
                raise AssertionError(
                    "Step 1 failed: the deployed app did not reach the hosted tracker "
                    "shell before the deferred tab hydration scenario began.\n"
                    f"Observed body text:\n{runtime_state.body_text}",
                )

            page.ensure_connected(
                token=token,
                repository=service.repository,
                user_login=user.login,
            )
            page.dismiss_connection_banner()
            page.open_issue(
                issue_key=issue_fixture.key,
                issue_summary=issue_fixture.summary,
            )
            issue_body_text = page.current_body_text()
            result["issue_body_text"] = issue_body_text
            if page.issue_detail_count(issue_fixture.key) == 0:
                raise AssertionError(
                    "Step 1 failed: opening the seeded issue did not render the requested "
                    "issue detail view.\n"
                    f"Observed body text:\n{issue_body_text}",
                )
            _record_step(
                result,
                step=1,
                status="passed",
                action=(
                    "Open the Issue Detail view for a hosted issue that contains seeded "
                    "comments and history."
                ),
                observed=issue_body_text,
            )

            comments_tabs = page.tab_button_count("Comments")
            history_tabs = page.tab_button_count("History")
            if comments_tabs == 0 or history_tabs == 0:
                raise AssertionError(
                    "Step 2 failed: the Issue Detail view did not keep both the "
                    '"Comments" and "History" tabs visible before deferred hydration '
                    "checks began.\n"
                    f'Visible "Comments" tab count: {comments_tabs}\n'
                    f'Visible "History" tab count: {history_tabs}\n'
                    f"Observed body text:\n{issue_body_text}",
                )

            _wait_for_quiet_window_without_tracked_requests(
                session=session,
                quiet_window_ms=QUIET_WINDOW_MS,
                runtime=runtime,
            )
            pre_activation_state = runtime.observation.as_dict()
            result["pre_activation_hydration_state"] = pre_activation_state
            if _comment_request_count(pre_activation_state) != 0:
                raise AssertionError(
                    "Step 2 failed: comment artifact requests started before the "
                    '"Comments" tab was activated.\n'
                    f"Observed hydration state:\n{json.dumps(pre_activation_state, indent=2)}",
                )
            if _history_request_count(pre_activation_state) != 0:
                raise AssertionError(
                    "Step 2 failed: history requests started before the "
                    '"History" tab was activated.\n'
                    f"Observed hydration state:\n{json.dumps(pre_activation_state, indent=2)}",
                )
            _record_step(
                result,
                step=2,
                status="passed",
                action=(
                    'Verify the visible "Comments" and "History" tabs are present while '
                    "the tracked network log stays quiet for both deferred sections."
                ),
                observed=json.dumps(pre_activation_state, indent=2),
            )
            _record_human_verification(
                result,
                check=(
                    'Confirmed the issue detail showed visible "Comments" and "History" '
                    "tabs before either panel was opened."
                ),
                observed=issue_body_text,
            )

            page.open_collaboration_tab("Comments")
            page.wait_for_text(first_comment_body, timeout_ms=60_000)
            comments_body_text = page.current_body_text()
            comments_state = runtime.observation.as_dict()
            result["comments_tab_body_text"] = comments_body_text
            result["comments_hydration_state"] = comments_state
            if page.selected_tab_count("Comments") == 0:
                raise AssertionError(
                    'Step 3 failed: the visible "Comments" tab did not become the active '
                    "tab after it was opened.\n"
                    f"Observed body text:\n{comments_body_text}",
                )
            _record_step(
                result,
                step=3,
                status="passed",
                action='Click the "Comments" tab.',
                observed=comments_body_text,
            )

            if _history_request_count(comments_state) != 0:
                raise AssertionError(
                    "Step 4 failed: opening the Comments tab also triggered history "
                    "requests before the History tab was activated.\n"
                    f"Observed hydration state:\n{json.dumps(comments_state, indent=2)}",
                )
            requested_comment_paths = _requested_comment_paths(comments_state)
            missing_comment_paths = [
                path
                for path in issue_fixture.comment_paths
                if path not in requested_comment_paths
            ]
            if missing_comment_paths:
                raise AssertionError(
                    "Step 4 failed: opening the Comments tab did not trigger requests for "
                    "all seeded `comments/*.md` files.\n"
                    f"Missing comment paths: {missing_comment_paths}\n"
                    f"Observed hydration state:\n{json.dumps(comments_state, indent=2)}",
                )
            if first_comment_body not in comments_body_text:
                raise AssertionError(
                    "Step 4 failed: the Comments tab request was observed, but the seeded "
                    "comment body was not visible to the user.\n"
                    f"Expected comment body: {first_comment_body}\n"
                    f"Observed body text:\n{comments_body_text}",
                )
            _record_step(
                result,
                step=4,
                status="passed",
                action=(
                    "Verify the Comments tab triggers requests for the seeded "
                    "`comments/*.md` files."
                ),
                observed=json.dumps(comments_state, indent=2),
            )
            _record_human_verification(
                result,
                check=(
                    'Opened the visible "Comments" tab and verified the seeded markdown '
                    "comment body rendered in the active panel."
                ),
                observed=comments_body_text,
            )

            history_count_before_open = _history_request_count(comments_state)
            page.open_collaboration_tab("History")
            page.wait_for_text(expected_history_fragment, timeout_ms=60_000)
            history_body_text = page.current_body_text()
            history_state = runtime.observation.as_dict()
            result["history_tab_body_text"] = history_body_text
            result["history_hydration_state"] = history_state
            if page.selected_tab_count("History") == 0:
                raise AssertionError(
                    'Step 5 failed: the visible "History" tab did not become the active '
                    "tab after it was opened.\n"
                    f"Observed body text:\n{history_body_text}",
                )
            if expected_history_fragment not in history_body_text:
                raise AssertionError(
                    "Step 5 failed: the History tab request was observed, but the expected "
                    "user-visible history entry did not render.\n"
                    f"Expected history text: {expected_history_fragment}\n"
                    f"Observed body text:\n{history_body_text}",
                )
            if _history_request_count(history_state) <= history_count_before_open:
                raise AssertionError(
                    "Step 5 failed: the expected history request count did not increase "
                    "after the History tab was activated.\n"
                    f"Observed hydration state:\n{json.dumps(history_state, indent=2)}",
                )
            _record_step(
                result,
                step=5,
                status="passed",
                action=(
                    'Click the "History" tab and verify history hydration starts only '
                    "after that activation."
                ),
                observed=json.dumps(history_state, indent=2),
            )
            _record_human_verification(
                result,
                check=(
                    'Opened the visible "History" tab and verified the user-facing '
                    f'history entry "{expected_history_fragment}" rendered in the active panel.'
                ),
                observed=history_body_text,
            )
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
        _capture_failure_screenshot(
            config,
            token=token,
            result_path=FAILURE_SCREENSHOT_PATH,
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
        _capture_failure_screenshot(
            config,
            token=token,
            result_path=FAILURE_SCREENSHOT_PATH,
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    else:
        result["status"] = "passed"
        result["summary"] = (
            "Verified the hosted issue detail keeps comments and history hydration "
            "deferred until the user opens each tab."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_preconditions(issue_fixture: LiveHostedIssueFixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-421 expected the seeded DEMO-2 issue fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.comment_paths:
        raise AssertionError(
            "Precondition failed: TS-421 requires seeded comment markdown files.\n"
            f"Observed issue path: {issue_fixture.path}",
        )
    if not issue_fixture.comment_bodies:
        raise AssertionError(
            "Precondition failed: TS-421 requires seeded visible comment bodies.\n"
            f"Observed comment paths: {issue_fixture.comment_paths}",
        )


def _wait_for_quiet_window_without_tracked_requests(
    *,
    session: WebAppSession,
    quiet_window_ms: int,
    runtime: DeferredTabHydrationObserverRuntime,
) -> None:
    session.evaluate(
        """
        ({ quietWindowMs }) =>
          new Promise((resolve) => window.setTimeout(resolve, quietWindowMs))
        """,
        arg={"quietWindowMs": quiet_window_ms},
    )
    state = runtime.observation.as_dict()
    if _comment_request_count(state) != 0 or _history_request_count(state) != 0:
        raise AssertionError(
            "Step 2 failed: tracked comments or history requests appeared during the "
            "quiet observation window before either tab was activated.\n"
            f"Observed hydration state:\n{json.dumps(state, indent=2)}",
        )


def _comment_request_count(state: dict[str, object]) -> int:
    comments = state.get("comments", {})
    if not isinstance(comments, dict):
        return 0
    value = comments.get("requestCount", 0)
    return int(value) if isinstance(value, (int, float)) else 0


def _history_request_count(state: dict[str, object]) -> int:
    history = state.get("history", {})
    if not isinstance(history, dict):
        return 0
    value = history.get("requestCount", 0)
    return int(value) if isinstance(value, (int, float)) else 0


def _requested_comment_paths(state: dict[str, object]) -> tuple[str, ...]:
    comments = state.get("comments", {})
    if not isinstance(comments, dict):
        return ()
    requested = comments.get("requestedPaths", [])
    if not isinstance(requested, list):
        return ()
    return tuple(str(path) for path in requested)


def _capture_failure_screenshot(config, *, token: str, result_path: Path) -> None:
    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            tracker_page.open()
            tracker_page.screenshot(str(result_path))
    except Exception:
        return


def _first_visible_line(markdown_body: str) -> str:
    for line in markdown_body.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return markdown_body.strip()


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
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


def _write_result_if_requested(payload: dict[str, object]) -> None:
    result_path = os.environ.get("TS421_RESULT_PATH")
    if not result_path:
        return
    destination = Path(result_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
