from __future__ import annotations

import json
import os
import sys
import traceback
from dataclasses import dataclass
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

TICKET_KEY = "TS-327"
QUERY = "discovery"
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts327_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts327_success.png"
FIELD_NAMES = ("summary", "description", "acceptance criteria")


@dataclass(frozen=True)
class DiscoveryExpectation:
    matching_issue_labels: tuple[str, ...]
    fields_to_issue_labels: dict[str, tuple[str, ...]]
    inventory: tuple[dict[str, object], ...]

    @property
    def expected_count(self) -> int:
        return len(self.matching_issue_labels)

    @property
    def expected_count_summary(self) -> str:
        if self.expected_count == 0:
            return "No issues"
        suffix = "issue" if self.expected_count == 1 else "issues"
        return f"{self.expected_count} {suffix}"

    @property
    def precondition_failures(self) -> tuple[str, ...]:
        failures: list[str] = []
        distinct_labels = set(self.matching_issue_labels)
        if len(distinct_labels) != 3:
            failures.append(
                "Ticket precondition failed: the live hosted repository does not expose "
                "exactly three Discovery-matching issues across summary, description, "
                f"and acceptance criteria.\nExpected distinct matching issues: 3\n"
                f"Observed distinct matching issues: {len(distinct_labels)}\n"
                f"Observed matching labels: {list(self.matching_issue_labels)}"
            )
        for field_name in FIELD_NAMES:
            labels = self.fields_to_issue_labels[field_name]
            if len(labels) != 1:
                failures.append(
                    "Ticket precondition failed: the live hosted repository does not "
                    f"expose exactly one Discovery match in {field_name}.\n"
                    f"Observed {field_name} matches: {list(labels)}"
                )
        return tuple(failures)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-327 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    issue_paths = service.list_issue_paths("DEMO")
    issue_fixtures = [service.fetch_issue_fixture(path) for path in issue_paths]
    expectation = _build_discovery_expectation(issue_fixtures)

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "query": QUERY,
        "expected_count_summary": expectation.expected_count_summary,
        "expected_issue_labels": list(expectation.matching_issue_labels),
        "matched_issue_labels_by_field": {
            field_name: list(labels)
            for field_name, labels in expectation.fields_to_issue_labels.items()
        },
        "inventory": list(expectation.inventory),
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
                    action="Navigate to the hosted tracker and open the JQL Search page.",
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
                    query=QUERY,
                    expected_count_summaries=_candidate_count_summaries(
                        expectation.expected_count_summary,
                    ),
                )
                result["observation"] = _observation_to_dict(observation)
                search_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)

                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Search for the term 'discovery'.",
                    observed=observation.body_text,
                )

                _assert_ticket_preconditions(expectation=expectation, observation=observation)
                _assert_visible_search_result(
                    expectation=expectation,
                    observation=observation,
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
            "Verified that the hosted JQL Search page preserved the Discovery query, "
            "returned the live cross-field Discovery matches, and showed the matching "
            "user-facing issue count."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _build_discovery_expectation(
    issue_fixtures: list[LiveHostedIssueFixture],
) -> DiscoveryExpectation:
    fields_to_issue_labels: dict[str, list[str]] = {
        field_name: [] for field_name in FIELD_NAMES
    }
    matching_issue_labels: list[str] = []
    inventory: list[dict[str, object]] = []

    for fixture in issue_fixtures:
        matched_fields: list[str] = []
        if QUERY in fixture.summary.lower():
            matched_fields.append("summary")
        if QUERY in fixture.description.lower():
            matched_fields.append("description")
        if any(QUERY in criterion.lower() for criterion in fixture.acceptance_criteria):
            matched_fields.append("acceptance criteria")

        issue_label = _issue_label(fixture)
        inventory.append(
            {
                "key": fixture.key,
                "summary": fixture.summary,
                "path": fixture.path,
                "matched_fields": matched_fields,
            },
        )
        if not matched_fields:
            continue
        matching_issue_labels.append(issue_label)
        for field_name in matched_fields:
            fields_to_issue_labels[field_name].append(issue_label)

    return DiscoveryExpectation(
        matching_issue_labels=tuple(matching_issue_labels),
        fields_to_issue_labels={
            field_name: tuple(labels)
            for field_name, labels in fields_to_issue_labels.items()
        },
        inventory=tuple(inventory),
    )


def _candidate_count_summaries(expected_count_summary: str) -> tuple[str, ...]:
    ordered_candidates = (
        expected_count_summary,
        "No issues",
        "1 issue",
        "2 issues",
        "3 issues",
        "4 issues",
        "5 issues",
        "6 issues",
    )
    unique_candidates: list[str] = []
    for candidate in ordered_candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)
    return tuple(unique_candidates)


def _assert_ticket_preconditions(
    *,
    expectation: DiscoveryExpectation,
    observation,
) -> None:
    if not expectation.precondition_failures:
        return
    raise AssertionError(
        "\n\n".join(
            [
                *expectation.precondition_failures,
                "Observed JQL Search state while reproducing the ticket:",
                f"Visible query: {observation.visible_query}",
                f"Expected count summary from live repository audit: {expectation.expected_count_summary}",
                f"Observed count summary: {observation.count_summary}",
                f"Expected visible issue labels from live repository audit: {list(expectation.matching_issue_labels)}",
                f"Observed visible issue labels: {list(observation.issue_labels)}",
                f"Observed body text:\n{observation.body_text}",
                f"Live repository issue inventory: {list(expectation.inventory)}",
            ],
        ),
    )


def _assert_visible_search_result(
    *,
    expectation: DiscoveryExpectation,
    observation,
) -> None:
    if observation.visible_query != QUERY:
        raise AssertionError(
            "Step 3 failed: the visible JQL Search field did not preserve the "
            "Discovery query exactly as typed.\n"
            f"Expected query: {QUERY}\n"
            f"Observed query: {observation.visible_query}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if observation.count_summary != expectation.expected_count_summary:
        raise AssertionError(
            "Step 3 failed: the hosted JQL Search count summary did not match the "
            "live Discovery-matching issue count.\n"
            f"Expected count summary: {expectation.expected_count_summary}\n"
            f"Observed count summary: {observation.count_summary}\n"
            f"Observed visible issue labels: {list(observation.issue_labels)}\n"
            f"Observed body text:\n{observation.body_text}",
        )

    observed_issue_labels = tuple(observation.issue_labels)
    if observed_issue_labels != expectation.matching_issue_labels:
        raise AssertionError(
            "Human-style verification failed: the visible JQL Search result list did "
            "not show exactly the Discovery-matching issues.\n"
            f"Expected visible issue labels: {list(expectation.matching_issue_labels)}\n"
            f"Observed visible issue labels: {list(observed_issue_labels)}\n"
            f"Observed body text:\n{observation.body_text}",
        )

    if expectation.expected_count_summary not in observation.body_text:
        raise AssertionError(
            "Human-style verification failed: the user-facing issue-count text was not "
            "visible on the JQL Search page after searching for Discovery.\n"
            f"Expected visible text: {expectation.expected_count_summary}\n"
            f"Observed body text:\n{observation.body_text}",
        )


def _issue_label(fixture: LiveHostedIssueFixture) -> str:
    return f"Open {fixture.key} {fixture.summary}"


def _observation_to_dict(observation) -> dict[str, object]:
    return {
        "query": observation.query,
        "visible_query": observation.visible_query,
        "count_summary": observation.count_summary,
        "issue_result_count": observation.issue_result_count,
        "issue_labels": list(observation.issue_labels),
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
    configured_path = os.environ.get("TS327_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts327_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
