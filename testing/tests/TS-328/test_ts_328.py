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
from testing.components.services.live_setup_repository_service import (
    LiveHostedIssueFixture,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-328"
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts328_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts328_success.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-328 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    issue_paths = service.list_issue_paths("DEMO")
    issue_fixtures = [service.fetch_issue_fixture(path) for path in issue_paths]
    _assert_fixture_preconditions(issue_fixtures)

    expected_issue_count = len(issue_fixtures)
    expected_count_summary = f"{expected_issue_count} issues"
    if expected_issue_count == 1:
        expected_count_summary = "1 issue"

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "expected_issue_count": expected_issue_count,
        "expected_count_summary": expected_count_summary,
        "expected_issue_keys": [fixture.key for fixture in issue_fixtures],
        "expected_issue_summaries": [fixture.summary for fixture in issue_fixtures],
        "steps": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            search_page = LiveJqlSearchPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before JQL Search was exercised.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the live app and reach the tracker shell.",
                    observed=runtime.body_text,
                )

                search_page.open()
                panel_body_text = search_page.current_body_text()
                result["panel_body_text"] = panel_body_text
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Open the JQL Search page.",
                    observed=panel_body_text,
                )

                observation = search_page.search_with_expected_counts(
                    query="",
                    expected_count_summaries=(expected_count_summary,),
                )
                search_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["observation"] = _observation_to_dict(observation)
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)

                _assert_empty_query_results(
                    expected_issue_count=expected_issue_count,
                    expected_count_summary=expected_count_summary,
                    expected_issues=issue_fixtures,
                    observation=observation,
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Leave the JQL query empty, execute search, and verify all issues remain listed.",
                    observed=observation.body_text,
                )
            except Exception:
                search_page.screenshot(str(SCREENSHOT_PATH))
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
            "Verified that submitting an empty hosted JQL query keeps the full live "
            "issue list visible and shows the total issue count."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_fixture_preconditions(issue_fixtures: list[LiveHostedIssueFixture]) -> None:
    if len(issue_fixtures) < 2:
        raise AssertionError(
            "Precondition failed: TS-328 expected at least two live issues in the "
            "hosted repository.\n"
            f"Observed issue paths: {[fixture.path for fixture in issue_fixtures]}",
        )
    for fixture in issue_fixtures:
        if not fixture.key.strip():
            raise AssertionError(
                "Precondition failed: one of the live hosted issue fixtures did not "
                "resolve an issue key.\n"
                f"Observed fixture path: {fixture.path}",
            )
        if not fixture.summary.strip():
            raise AssertionError(
                "Precondition failed: one of the live hosted issue fixtures did not "
                "resolve a visible summary.\n"
                f"Observed fixture path: {fixture.path}",
            )


def _assert_empty_query_results(
    *,
    expected_issue_count: int,
    expected_count_summary: str,
    expected_issues: list[LiveHostedIssueFixture],
    observation,
) -> None:
    if observation.visible_query != "":
        raise AssertionError(
            "Step 3 failed: the visible JQL Search field was not empty after submitting "
            "an empty query.\n"
            f"Observed query value: {observation.visible_query!r}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if observation.count_summary != expected_count_summary:
        raise AssertionError(
            "Step 3 failed: the empty JQL query did not show the full live issue count.\n"
            f"Expected count summary: {expected_count_summary}\n"
            f"Observed count summary: {observation.count_summary}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if observation.issue_result_count != expected_issue_count:
        raise AssertionError(
            "Step 3 failed: the visible issue result count did not match the total live "
            "issue inventory after submitting an empty query.\n"
            f"Expected visible issue count: {expected_issue_count}\n"
            f"Observed visible issue count: {observation.issue_result_count}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if "No issues" in observation.body_text:
        raise AssertionError(
            "Step 3 failed: the empty-query JQL Search surface rendered the empty state "
            "instead of listing all issues.\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if expected_count_summary not in observation.body_text:
        raise AssertionError(
            "Human-style verification failed: the visible JQL Search surface did not "
            "show the expected user-facing total issue count summary.\n"
            f"Expected visible text: {expected_count_summary}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    for fixture in expected_issues:
        if fixture.key not in observation.body_text:
            raise AssertionError(
                "Human-style verification failed: a live issue key was missing from the "
                "visible empty-query result list.\n"
                f"Missing issue key: {fixture.key}\n"
                f"Observed body text:\n{observation.body_text}",
            )
        if fixture.summary not in observation.body_text:
            raise AssertionError(
                "Human-style verification failed: a live issue summary was missing from "
                "the visible empty-query result list.\n"
                f"Missing issue summary: {fixture.summary}\n"
                f"Issue key: {fixture.key}\n"
                f"Observed body text:\n{observation.body_text}",
            )


def _observation_to_dict(observation) -> dict[str, object]:
    return {
        "query": observation.query,
        "visible_query": observation.visible_query,
        "count_summary": observation.count_summary,
        "issue_result_count": observation.issue_result_count,
        "body_text": observation.body_text,
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


def _write_result_if_requested(payload: dict[str, object]) -> None:
    configured_path = os.environ.get("TS328_RESULT_PATH")
    result_path = Path(configured_path) if configured_path else REPO_ROOT / "outputs" / "ts328_result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
