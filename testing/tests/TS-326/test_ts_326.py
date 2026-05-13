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
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-326"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
EXPECTED_ISSUE_KEY = "DEMO-2"
SUMMARY_TERM = "explore"
SUMMARY_QUERY = "eXpLoRe"
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts326_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts326_success.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-326 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_fixture_preconditions(issue_fixture)
    expected_result_label = f"Open {issue_fixture.key} {issue_fixture.summary}"

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "query": SUMMARY_QUERY,
        "expected_result_label": expected_result_label,
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
                        "shell before the mixed-case summary search was exercised.\n"
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

                observation = search_page.search_for_unique_issue(query=SUMMARY_QUERY)
                search_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["observation"] = _observation_to_dict(observation)
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)

                _assert_summary_search(
                    query=SUMMARY_QUERY,
                    expected_issue_key=issue_fixture.key,
                    expected_issue_summary=issue_fixture.summary,
                    expected_result_label=expected_result_label,
                    observation=observation,
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        f"Enter the mixed-case summary term '{SUMMARY_QUERY}' and "
                        "execute the search."
                    ),
                    observed=(
                        f"{observation.count_summary}\n"
                        + "\n".join(observation.issue_result_labels)
                    ),
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
            "Verified that the hosted JQL Search page returns DEMO-2 when the "
            "mixed-case summary term eXpLoRe is submitted."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_fixture_preconditions(issue_fixture) -> None:
    if issue_fixture.key != EXPECTED_ISSUE_KEY:
        raise AssertionError(
            "Precondition failed: TS-326 expected to validate the seeded DEMO-2 issue.\n"
            f"Observed key: {issue_fixture.key}",
        )
    if SUMMARY_TERM not in issue_fixture.summary.lower():
        raise AssertionError(
            "Precondition failed: the seeded DEMO-2 summary no longer contains the "
            f"expected summary term {SUMMARY_TERM!r}.\n"
            f"Observed summary: {issue_fixture.summary}",
        )


def _assert_summary_search(
    *,
    query: str,
    expected_issue_key: str,
    expected_issue_summary: str,
    expected_result_label: str,
    observation,
) -> None:
    if observation.visible_query != query:
        raise AssertionError(
            "Step 3 failed: the visible JQL Search field did not preserve the mixed-case "
            "summary query exactly as typed.\n"
            f"Expected query: {query}\n"
            f"Observed query: {observation.visible_query}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if observation.count_summary != "1 issue":
        raise AssertionError(
            "Step 3 failed: the mixed-case summary query did not narrow the live JQL "
            'Search result list to the visible "1 issue" state.\n'
            f"Observed count summary: {observation.count_summary}\n"
            f"Observed body text:\n{observation.body_text}\n"
            f"Observed result labels: {list(observation.issue_result_labels)}",
        )
    if observation.issue_result_count != 1:
        raise AssertionError(
            "Step 3 failed: the mixed-case summary query did not leave exactly one live "
            "issue result visible.\n"
            f"Observed visible result count: {observation.issue_result_count}\n"
            f"Observed result labels: {list(observation.issue_result_labels)}",
        )
    if expected_result_label not in observation.issue_result_labels:
        raise AssertionError(
            "Step 3 failed: the expected DEMO-2 search result was not visible after the "
            "mixed-case summary query was submitted.\n"
            f"Expected result label: {expected_result_label}\n"
            f"Observed result labels: {list(observation.issue_result_labels)}",
        )
    if "No issues" in observation.body_text:
        raise AssertionError(
            "Step 3 failed: the mixed-case summary query rendered the empty state instead "
            "of the matching DEMO-2 result.\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if "1 issue" not in observation.body_text:
        raise AssertionError(
            "Human-style verification failed: the visible JQL Search surface did not "
            'show the user-facing "1 issue" summary after the mixed-case summary '
            "query was submitted.\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if expected_issue_key not in expected_result_label or expected_issue_summary not in expected_result_label:
        raise AssertionError(
            "Precondition failed: the expected JQL result label did not retain the issue "
            "key and summary needed for human-style verification.\n"
            f"Expected result label: {expected_result_label}",
        )


def _observation_to_dict(observation) -> dict[str, object]:
    return {
        "query": observation.query,
        "visible_query": observation.visible_query,
        "count_summary": observation.count_summary,
        "issue_result_count": observation.issue_result_count,
        "issue_result_labels": list(observation.issue_result_labels),
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
    configured_path = os.environ.get("TS326_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts326_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
