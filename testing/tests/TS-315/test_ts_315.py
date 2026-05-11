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


TICKET_KEY = "TS-315"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
EXPECTED_ISSUE_KEY = "DEMO-2"
EXPECTED_ISSUE_SUMMARY = "Explore the issue board"
SUMMARY_TERM = "explore"
DESCRIPTION_TERM = "assignees"
ACCEPTANCE_TERM = "accessibility"
COMMENT_TERM = "markdown-backed"
SUMMARY_QUERY = "eXpLoRe"
DESCRIPTION_QUERY = "ASSIGNEES"
ACCEPTANCE_QUERY = "AcCeSsIbIlItY"
COMMENT_QUERY = "MARKDOWN-BACKED"
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts315_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-315 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_fixture_preconditions(issue_fixture)

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_description": issue_fixture.description,
        "issue_acceptance_criteria": issue_fixture.acceptance_criteria,
        "issue_comment_bodies": issue_fixture.comment_bodies,
        "queries": {
            "summary": SUMMARY_QUERY,
            "description": DESCRIPTION_QUERY,
            "acceptanceCriteria": ACCEPTANCE_QUERY,
            "commentExcluded": COMMENT_QUERY,
        },
        "steps": [],
    }

    try:
        summary_run = _run_live_search_query(
            config=config,
            token=token,
            query=SUMMARY_QUERY,
            screenshot_path=SCREENSHOT_PATH,
        )
        result["runtime_state"] = summary_run["runtime_state"]
        result["runtime_body_text"] = summary_run["runtime_body_text"]
        if summary_run["runtime_state"] != "ready":
            raise AssertionError(
                "Step 1 failed: the deployed app did not reach the hosted tracker "
                "shell before JQL Search was exercised.\n"
                f"Observed body text:\n{summary_run['runtime_body_text']}",
            )
        _record_step(
            result,
            step=1,
            status="passed",
            action="Open the live app and reach the tracker shell.",
            observed=str(summary_run["runtime_body_text"]),
        )
        _record_step(
            result,
            step=2,
            status="passed",
            action="Open the JQL Search panel.",
            observed=str(summary_run["panel_body_text"]),
        )

        summary_observation = summary_run["observation"]
        _assert_positive_search(
            label="summary",
            query=SUMMARY_QUERY,
            observation=summary_observation,
        )
        result["summary_search"] = _observation_to_dict(summary_observation)
        _record_step(
            result,
            step=3,
            status="passed",
            action=(
                f"Search for the mixed-case summary term '{SUMMARY_QUERY}' and "
                "verify the DEMO-2 result stays visible."
            ),
            observed=summary_observation.body_text,
        )

        description_run = _run_live_search_query(
            config=config,
            token=token,
            query=DESCRIPTION_QUERY,
            screenshot_path=SCREENSHOT_PATH,
        )
        description_observation = description_run["observation"]
        _assert_positive_search(
            label="description",
            query=DESCRIPTION_QUERY,
            observation=description_observation,
        )
        result["description_search"] = _observation_to_dict(description_observation)
        _record_step(
            result,
            step=4,
            status="passed",
            action=(
                f"Search for the uppercase description term '{DESCRIPTION_QUERY}' "
                "and verify the DEMO-2 result stays visible."
            ),
            observed=description_observation.body_text,
        )

        acceptance_run = _run_live_search_query(
            config=config,
            token=token,
            query=ACCEPTANCE_QUERY,
            screenshot_path=SCREENSHOT_PATH,
        )
        acceptance_observation = acceptance_run["observation"]
        _assert_positive_search(
            label="acceptance criteria",
            query=ACCEPTANCE_QUERY,
            observation=acceptance_observation,
        )
        result["acceptance_search"] = _observation_to_dict(acceptance_observation)
        _record_step(
            result,
            step=5,
            status="passed",
            action=(
                f"Search for the mixed-case acceptance-criteria term "
                f"'{ACCEPTANCE_QUERY}' and verify the DEMO-2 result stays visible."
            ),
            observed=acceptance_observation.body_text,
        )

        comment_run = _run_live_search_query(
            config=config,
            token=token,
            query=COMMENT_QUERY,
            screenshot_path=SCREENSHOT_PATH,
        )
        comment_observation = comment_run["observation"]
        _assert_negative_search(
            query=COMMENT_QUERY,
            observation=comment_observation,
        )
        result["comment_search"] = _observation_to_dict(comment_observation)
        _record_step(
            result,
            step=6,
            status="passed",
            action=(
                f"Search for the uppercase comment-only term '{COMMENT_QUERY}' "
                'and verify the panel shows "No results".'
            ),
            observed=comment_observation.body_text,
        )
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        result["screenshot"] = str(SCREENSHOT_PATH)
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["screenshot"] = str(SCREENSHOT_PATH)
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    else:
        result["status"] = "passed"
        result["summary"] = (
            "Verified case-insensitive free-text JQL matches the DEMO-2 summary, "
            "description, and acceptance criteria, while comment-only text remains "
            "excluded from live hosted search."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_fixture_preconditions(issue_fixture) -> None:
    if issue_fixture.key != EXPECTED_ISSUE_KEY:
        raise AssertionError(
            "Precondition failed: TS-315 expected to validate the seeded DEMO-2 issue.\n"
            f"Observed key: {issue_fixture.key}",
        )
    if issue_fixture.summary != EXPECTED_ISSUE_SUMMARY:
        raise AssertionError(
            "Precondition failed: TS-315 expected the seeded DEMO-2 summary to remain "
            "stable.\n"
            f"Expected summary: {EXPECTED_ISSUE_SUMMARY}\n"
            f"Observed summary: {issue_fixture.summary}",
        )
    if SUMMARY_TERM not in issue_fixture.summary.lower():
        raise AssertionError(
            "Precondition failed: the seeded DEMO-2 summary no longer contains the "
            f"expected summary term {SUMMARY_TERM!r}.\n"
            f"Observed summary: {issue_fixture.summary}",
        )
    if DESCRIPTION_TERM not in issue_fixture.description.lower():
        raise AssertionError(
            "Precondition failed: the seeded DEMO-2 description no longer contains the "
            f"expected description term {DESCRIPTION_TERM!r}.\n"
            f"Observed description: {issue_fixture.description}",
        )
    if not any(
        ACCEPTANCE_TERM in criterion.lower()
        for criterion in issue_fixture.acceptance_criteria
    ):
        raise AssertionError(
            "Precondition failed: the seeded DEMO-2 acceptance criteria no longer "
            f"contain the expected term {ACCEPTANCE_TERM!r}.\n"
            f"Observed acceptance criteria: {issue_fixture.acceptance_criteria}",
        )
    if not any(COMMENT_TERM in body.lower() for body in issue_fixture.comment_bodies):
        raise AssertionError(
            "Precondition failed: the seeded DEMO-2 comments no longer contain the "
            f"expected comment term {COMMENT_TERM!r}.\n"
            f"Observed comment bodies: {issue_fixture.comment_bodies}",
        )


def _run_live_search_query(
    *,
    config,
    token: str,
    query: str,
    screenshot_path: Path,
) -> dict[str, object]:
    with create_live_tracker_app_with_stored_token(
        config,
        token=token,
    ) as tracker_page:
        search_page = LiveJqlSearchPage(tracker_page)
        runtime = tracker_page.open()
        if runtime.kind != "ready":
            return {
                "runtime_state": runtime.kind,
                "runtime_body_text": runtime.body_text,
                "panel_body_text": runtime.body_text,
                "observation": None,
            }
        try:
            search_page.open()
            panel_body_text = search_page.current_body_text()
            observation = search_page.search(query=query)
        except Exception:
            search_page.screenshot(str(screenshot_path))
            raise
        search_page.screenshot(str(screenshot_path))
        return {
            "runtime_state": runtime.kind,
            "runtime_body_text": runtime.body_text,
            "panel_body_text": panel_body_text,
            "observation": observation,
        }


def _assert_positive_search(
    *,
    label: str,
    query: str,
    observation,
) -> None:
    if observation.visible_query != query:
        raise AssertionError(
            f"Step failed: the visible JQL Search field did not preserve the {label} "
            "query exactly as typed.\n"
            f"Expected query: {query}\n"
            f"Observed query: {observation.visible_query}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if observation.count_summary != "1 issue":
        raise AssertionError(
            f"Step failed: searching for the {label} term {query!r} did not narrow the "
            'live JQL Search result list down to the visible "1 issue" state.\n'
            f"Observed count summary: {observation.count_summary}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if "No issues" in observation.body_text:
        raise AssertionError(
            f"Step failed: searching for the {label} term {query!r} rendered the empty "
            'state instead of the matching issue result.\n'
            f"Observed body text:\n{observation.body_text}",
        )
    if "1 issue" not in observation.body_text:
        raise AssertionError(
            f"Human-style verification failed: the visible JQL Search surface did not "
            f"show the user-facing \"1 issue\" summary after searching for {query!r}.\n"
            f"Observed body text:\n{observation.body_text}",
        )


def _assert_negative_search(
    *,
    query: str,
    observation,
) -> None:
    if observation.visible_query != query:
        raise AssertionError(
            "Step 7 failed: the visible JQL Search field did not preserve the negative "
            "comment query exactly as typed.\n"
            f"Expected query: {query}\n"
            f"Observed query: {observation.visible_query}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if observation.count_summary != "No issues":
        raise AssertionError(
            'Human-style verification failed: the visible JQL Search surface did not '
            'show the "No issues" empty state for the comment-only query.\n'
            f"Observed count summary: {observation.count_summary}\n"
            f"Observed body text:\n{observation.body_text}",
        )


def _observation_to_dict(observation) -> dict[str, object]:
    return {
        "query": observation.query,
        "visible_query": observation.visible_query,
        "count_summary": observation.count_summary,
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
    result_path = os.environ.get("TS315_RESULT_PATH")
    if not result_path:
        return
    destination = Path(result_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
