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
from testing.components.pages.live_jql_search_page import LiveJqlSearchPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.deferred_comments_delay_runtime import (  # noqa: E402
    DeferredCommentsDelayRuntime,
)
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402

TICKET_KEY = "TS-452"
PRIMARY_ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
SECONDARY_ISSUE_PATH = "DEMO/DEMO-1/DEMO-2/DEMO-3"
DELAY_MS = 8_000
NON_EMPTY_COUNT_SUMMARIES = tuple([f"{count} issues" for count in range(2, 21)] + ["1 issue"])

OUTPUTS_DIR = REPO_ROOT / "outputs"
RESULT_PATH = OUTPUTS_DIR / "ts452_result.json"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts452_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts452_success.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-452 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    primary_issue = service.fetch_issue_fixture(PRIMARY_ISSUE_PATH)
    secondary_issue = service.fetch_issue_fixture(SECONDARY_ISSUE_PATH)
    _assert_preconditions(primary_issue=primary_issue, secondary_issue=secondary_issue)

    runtime = DeferredCommentsDelayRuntime(
        repository=service.repository,
        token=token,
        delayed_comment_paths=primary_issue.comment_paths,
        delay_ms=DELAY_MS,
    )

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "primary_issue_key": primary_issue.key,
        "primary_issue_summary": primary_issue.summary,
        "secondary_issue_key": secondary_issue.key,
        "secondary_issue_summary": secondary_issue.summary,
        "delayed_comment_paths": list(primary_issue.comment_paths),
        "delay_ms": DELAY_MS,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveIssueDetailCollaborationPage(tracker_page)
            search_page = LiveJqlSearchPage(tracker_page)
            session = tracker_page.session
            try:
                runtime_state = tracker_page.open()
                result["runtime_state"] = runtime_state.kind
                result["runtime_body_text"] = runtime_state.body_text
                if runtime_state.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the deferred detail hydration scenario began.\n"
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
                    action=(
                        "Finish the hosted GitHub session handshake and dismiss any transient "
                        "connection banner."
                    ),
                    observed=page.current_body_text(),
                )

                search_observation = search_page.search_with_expected_counts(
                    query="",
                    expected_count_summaries=NON_EMPTY_COUNT_SUMMARIES,
                )
                result["search_observation"] = _search_observation_payload(search_observation)
                _assert_visible_issue_row(
                    page=page,
                    issue=primary_issue,
                    step=3,
                )
                _assert_visible_issue_row(
                    page=page,
                    issue=secondary_issue,
                    step=3,
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "Open JQL Search with the default issue list and verify both target "
                        "issues are visibly available in the live list context."
                    ),
                    observed=(
                        f"{search_observation.count_summary}\n"
                        + "\n".join(page.visible_issue_result_labels())
                    ),
                )

                page.select_issue_from_visible_list(
                    issue_key=primary_issue.key,
                    issue_summary=primary_issue.summary,
                )
                primary_detail_label = page.issue_detail_accessible_label(
                    primary_issue.key,
                    expected_fragment=primary_issue.summary,
                    timeout_ms=30_000,
                )
                result["primary_detail_before_comments"] = primary_detail_label
                for expected_fragment in (
                    primary_issue.summary,
                    "Status",
                    "Priority",
                ):
                    if expected_fragment not in primary_detail_label:
                        raise AssertionError(
                            "Step 4 failed: selecting the not-yet-hydrated live issue did not "
                            "leave the selected issue header and detail summary visible before "
                            "Comments hydration began.\n"
                            f"Missing fragment: {expected_fragment}\n"
                            f"Observed detail label:\n{primary_detail_label}",
                        )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Select the seeded issue that still needs deferred Comments hydration.",
                    observed=primary_detail_label,
                )

                page.open_collaboration_tab("Comments")
                comments_loading_label = page.wait_for_deferred_loading(
                    "Comments",
                    timeout_ms=30_000,
                )
                loading_delay_state = _delay_state_payload(session)
                result["comments_loading_label"] = comments_loading_label
                result["delay_state_while_loading"] = loading_delay_state
                result["visible_issue_result_labels_while_loading"] = list(
                    page.visible_issue_result_labels(),
                )
                primary_detail_during_loading = page.issue_detail_accessible_label(
                    primary_issue.key,
                    expected_fragment=primary_issue.summary,
                    timeout_ms=30_000,
                )
                result["primary_detail_during_loading"] = primary_detail_during_loading

                if "Comments loading" not in comments_loading_label:
                    raise AssertionError(
                        "Step 5 failed: opening the unresolved Comments tab did not expose the "
                        "expected Comments-only loading skeleton label.\n"
                        f"Observed loading label:\n{comments_loading_label}",
                    )
                if loading_delay_state["activeCount"] < 1:
                    raise AssertionError(
                        "Step 5 failed: the synthetic comments delay never left a live deferred "
                        "Comments request in flight, so the loading state was not exercised.\n"
                        f"Observed delay state: {loading_delay_state}",
                    )
                if page.text_fragment_count("Detail loading") != 0:
                    raise AssertionError(
                        "Step 5 failed: the Detail section showed a loading skeleton even "
                        "though only Comments hydration should be pending.\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                if page.text_fragment_count("Attachments loading") != 0:
                    raise AssertionError(
                        "Step 5 failed: the Attachments section showed a loading skeleton "
                        "while only the Comments tab should have been hydrating.\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                if page.text_fragment_count("History loading") != 0:
                    raise AssertionError(
                        "Step 5 failed: the History section showed a loading skeleton while "
                        "only the Comments tab should have been hydrating.\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                for expected_fragment in (
                    primary_issue.key,
                    primary_issue.summary,
                    "In Progress",
                    "High",
                ):
                    if expected_fragment not in primary_detail_during_loading:
                        raise AssertionError(
                            "Step 5 failed: the selected issue header stopped exposing the "
                            "current issue context while Comments was still hydrating.\n"
                            f"Missing fragment: {expected_fragment}\n"
                            f"Observed detail label:\n{primary_detail_during_loading}",
                        )
                _assert_visible_issue_row(
                    page=page,
                    issue=secondary_issue,
                    step=5,
                )
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=(
                        "Open Comments and verify only the Comments content area shows a "
                        "loading skeleton while the list context and selected issue header "
                        "remain visible."
                    ),
                    observed=(
                        f"loading_label={comments_loading_label}\n"
                        f"detail_label={primary_detail_during_loading}\n"
                        f"visible_results={page.visible_issue_result_labels()}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        'Verified the user could still read the selected issue heading, status, '
                        'priority, and the adjacent issue list while only the "Comments loading" '
                        "card occupied the content area."
                    ),
                    observed=(
                        f"detail_label={primary_detail_during_loading}\n"
                        f"loading_label={comments_loading_label}"
                    ),
                )

                page.select_issue_from_visible_list(
                    issue_key=secondary_issue.key,
                    issue_summary=secondary_issue.summary,
                )
                secondary_detail_label = page.issue_detail_accessible_label(
                    secondary_issue.key,
                    expected_fragment=secondary_issue.summary,
                    timeout_ms=30_000,
                )
                delay_state_after_switch = _delay_state_payload(session)
                result["secondary_detail_after_switch"] = secondary_detail_label
                result["delay_state_after_switch"] = delay_state_after_switch
                result["visible_issue_result_labels_after_switch"] = list(
                    page.visible_issue_result_labels(),
                )
                if secondary_issue.summary not in secondary_detail_label:
                    raise AssertionError(
                        "Step 6 failed: selecting a different issue from the live list did not "
                        "switch the selected issue detail while the original Comments tab was "
                        "still hydrating.\n"
                        f"Observed detail label:\n{secondary_detail_label}",
                    )
                if delay_state_after_switch["activeCount"] < 1:
                    raise AssertionError(
                        "Step 6 failed: the issue switch finished only after the delayed "
                        "Comments request had already completed, so the list was not proven "
                        "interactive during hydration.\n"
                        f"Observed delay state after switching: {delay_state_after_switch}",
                    )
                _assert_visible_issue_row(
                    page=page,
                    issue=primary_issue,
                    step=6,
                )
                _record_step(
                    result,
                    step=6,
                    status="passed",
                    action=(
                        "Select a different issue from the visible list while the Comments "
                        "skeleton is still shown for the previous issue."
                    ),
                    observed=secondary_detail_label,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the user could click another issue immediately from the list "
                        "without waiting for the original Comments skeleton to finish."
                    ),
                    observed=(
                        f"secondary_detail={secondary_detail_label}\n"
                        f"delay_state={delay_state_after_switch}"
                    ),
                )

                session.wait_for_function(
                    """
                    () => {
                      const state = window.__ts452DelayState;
                      return !!state && state.activeCount === 0 && state.completedUrls.length > 0;
                    }
                    """,
                    timeout_ms=DELAY_MS + 15_000,
                )
                result["delay_state_after_completion"] = _delay_state_payload(session)

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
            "Verified the hosted Search/Detail experience keeps the issue list and selected "
            "issue header interactive during deferred Comments hydration, shows a "
            "Comments-only skeleton, and allows switching issues before hydration finishes."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_preconditions(
    *,
    primary_issue: LiveHostedIssueFixture,
    secondary_issue: LiveHostedIssueFixture,
) -> None:
    if primary_issue.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-452 expected DEMO-2 as the deferred-hydration issue.\n"
            f"Observed issue key: {primary_issue.key}",
        )
    if secondary_issue.key != "DEMO-3":
        raise AssertionError(
            "Precondition failed: TS-452 expected DEMO-3 as the alternative selectable issue.\n"
            f"Observed issue key: {secondary_issue.key}",
        )
    if not primary_issue.comment_paths:
        raise AssertionError(
            "Precondition failed: DEMO-2 no longer exposes comment artifacts needed for the "
            "deferred Comments hydration scenario.\n"
            f"Observed comment paths: {primary_issue.comment_paths}",
        )
    if not primary_issue.summary.strip() or not secondary_issue.summary.strip():
        raise AssertionError(
            "Precondition failed: the live issue fixtures did not expose the visible "
            "summaries required for the user-facing assertions.\n"
            f"DEMO-2 summary: {primary_issue.summary!r}\n"
            f"DEMO-3 summary: {secondary_issue.summary!r}",
        )


def _assert_visible_issue_row(
    *,
    page: LiveIssueDetailCollaborationPage,
    issue: LiveHostedIssueFixture,
    step: int,
) -> None:
    if page.issue_result_button_count(issue_key=issue.key, issue_summary=issue.summary) > 0:
        return
    raise AssertionError(
        f"Step {step} failed: the live Search/Detail list did not keep the visible issue row "
        f"for {issue.key} {issue.summary} accessible.\n"
        f"Visible issue rows: {list(page.visible_issue_result_labels())}\n"
        f"Observed body text:\n{page.current_body_text()}",
    )


def _search_observation_payload(observation) -> dict[str, object]:
    return {
        "query": observation.query,
        "visible_query": observation.visible_query,
        "count_summary": observation.count_summary,
        "issue_result_count": observation.issue_result_count,
        "issue_result_labels": list(observation.issue_result_labels),
        "body_text": observation.body_text,
    }


def _delay_state_payload(session) -> dict[str, object]:
    payload = session.evaluate(
        """
        () => {
          const state = window.__ts452DelayState;
          if (!state) {
            return null;
          }
          return {
            trackedPaths: Array.isArray(state.trackedPaths) ? [...state.trackedPaths] : [],
            delayMs: state.delayMs ?? null,
            activeCount: state.activeCount ?? 0,
            startedUrls: Array.isArray(state.startedUrls) ? [...state.startedUrls] : [],
            completedUrls: Array.isArray(state.completedUrls) ? [...state.completedUrls] : [],
            lastDelayStartedAt: state.lastDelayStartedAt ?? null,
            lastDelayCompletedAt: state.lastDelayCompletedAt ?? null,
          };
        }
        """,
    )
    if not isinstance(payload, dict):
        raise AssertionError(
            "TS-452 could not read the injected deferred-comments delay state from the live "
            "browser session.",
        )
    return payload


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
    configured_path = os.environ.get("TS452_RESULT_PATH")
    result_path = Path(configured_path) if configured_path else RESULT_PATH
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
