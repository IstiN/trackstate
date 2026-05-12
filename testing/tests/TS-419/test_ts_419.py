from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_dashboard_page import (  # noqa: E402
    LiveDashboardObservation,
    LiveDashboardPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.ts419_bootstrap_request_runtime import (  # noqa: E402
    HostedBootstrapReadObservation,
    Ts419BootstrapRequestRuntime,
)

TICKET_KEY = "TS-419"
PROJECT_PATH = "DEMO"
PROJECT_JSON_PATH = f"{PROJECT_PATH}/project.json"
ISSUES_INDEX_PATH = f"{PROJECT_PATH}/.trackstate/index/issues.json"
OBSERVATION_WINDOW_SECONDS = 5
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts419_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts419_failure.png"
EXPECTED_CONFIG_FILENAMES = (
    "issue-types.json",
    "statuses.json",
    "fields.json",
    "workflows.json",
    "priorities.json",
    "versions.json",
    "components.json",
    "resolutions.json",
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-419 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    default_locale = service.fetch_project_locale_configuration(PROJECT_PATH).default_locale
    expected_config_paths = [
        f"{PROJECT_PATH}/config/i18n/{default_locale}.json",
        *[
            f"{PROJECT_PATH}/config/{filename}"
            for filename in EXPECTED_CONFIG_FILENAMES
        ],
    ]
    summary_index_entries = _summary_index_entries(service)
    expected_dashboard_labels = {
        f"{entry['key']} · {entry['summary']}" for entry in summary_index_entries
    }
    request_observation = HostedBootstrapReadObservation(
        repository=config.repository,
        ref=config.ref,
        project_path=PROJECT_PATH,
    )
    runtime = Ts419BootstrapRequestRuntime(
        repository=config.repository,
        token=token,
        observation=request_observation,
    )

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": config.repository,
        "repository_ref": config.ref,
        "project": PROJECT_PATH,
        "issues_index_path": ISSUES_INDEX_PATH,
        "expected_project_path": PROJECT_JSON_PATH,
        "expected_config_paths": expected_config_paths,
        "expected_dashboard_labels_sample": sorted(expected_dashboard_labels)[:5],
        "observation_window_seconds": OBSERVATION_WINDOW_SECONDS,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveDashboardPage(tracker_page)
            try:
                runtime_state = tracker_page.open()
                result["runtime_state"] = runtime_state.kind
                result["runtime_body_text"] = runtime_state.body_text
                if runtime_state.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the bootstrap envelope scenario began.\n"
                        f"Observed body text:\n{runtime_state.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Start the hosted web app while monitoring repository network requests.",
                    observed=runtime_state.body_text,
                )

                startup_recorded, _ = poll_until(
                    probe=lambda: (
                        len(request_observation.issues_index_urls),
                        len(request_observation.project_json_urls),
                        len(request_observation.config_json_urls),
                    ),
                    is_satisfied=lambda snapshot: snapshot[0] >= 1 and snapshot[1] >= 1,
                    timeout_seconds=120,
                    interval_seconds=1,
                )
                if not startup_recorded:
                    raise AssertionError(
                        "Step 2 failed: startup never recorded the hosted summary-index and "
                        "project-metadata requests needed for TS-419.\n"
                        f"Observed request payload: {_request_observation_payload(request_observation)}\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )

                tracker_page.session.wait_for_function(
                    """
                    ({ startedAt, durationMs }) =>
                      typeof startedAt === 'number'
                      && performance.now() - startedAt >= durationMs
                    """,
                    arg={
                        "startedAt": tracker_page.session.evaluate("() => performance.now()"),
                        "durationMs": OBSERVATION_WINDOW_SECONDS * 1000,
                    },
                    timeout_ms=(OBSERVATION_WINDOW_SECONDS + 5) * 1000,
                )

                request_payload = _request_observation_payload(request_observation)
                result["request_observation"] = request_payload

                if not request_observation.issues_index_urls:
                    raise AssertionError(
                        "Step 2 failed: startup never fetched `.trackstate/index/issues.json`.\n"
                        f"Observed request payload: {request_payload}\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Verify that `.trackstate/index/issues.json` is fetched.",
                    observed="\n".join(request_observation.issues_index_urls),
                )

                observed_project_paths = _normalized_paths(request_observation.project_json_urls)
                observed_config_paths = _normalized_paths(request_observation.config_json_urls)
                missing_project_paths = [
                    PROJECT_JSON_PATH for path in [PROJECT_JSON_PATH] if path not in observed_project_paths
                ]
                missing_config_paths = [
                    path for path in expected_config_paths if path not in observed_config_paths
                ]
                if missing_project_paths or missing_config_paths:
                    raise AssertionError(
                        "Step 3 failed: startup did not fetch the full expected project/config "
                        "metadata envelope.\n"
                        f"Missing project paths: {missing_project_paths}\n"
                        f"Missing config paths: {missing_config_paths}\n"
                        f"Observed project paths: {observed_project_paths}\n"
                        f"Observed config paths: {observed_config_paths}\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Verify that project and config JSON files are fetched.",
                    observed=(
                        f"project_paths={observed_project_paths}\n"
                        f"config_paths={observed_config_paths}"
                    ),
                )

                if (
                    request_observation.main_markdown_urls
                    or request_observation.comments_urls
                    or request_observation.attachments_urls
                ):
                    raise AssertionError(
                        "Step 4 failed: startup eagerly requested issue detail artifacts.\n"
                        f"Observed main.md URLs: {request_observation.main_markdown_urls}\n"
                        f"Observed comments URLs: {request_observation.comments_urls}\n"
                        f"Observed attachments URLs: {request_observation.attachments_urls}\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Verify that no requests are made for issue `main.md` files or "
                        "`comments/` directories during the initial load."
                    ),
                    observed=(
                        f"tree_requests={len(request_observation.tree_urls)}; "
                        f"main_md_reads={len(request_observation.main_markdown_urls)}; "
                        f"comments_reads={len(request_observation.comments_urls)}; "
                        f"attachments_reads={len(request_observation.attachments_urls)}; "
                        f"tombstone_metadata_reads={len(request_observation.tombstone_metadata_urls)}"
                    ),
                )

                dashboard_observation = page.open()
                result["dashboard_observation"] = _dashboard_payload(dashboard_observation)
                _assert_dashboard_matches_index(
                    observation=dashboard_observation,
                    expected_dashboard_labels=expected_dashboard_labels,
                )
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Navigate to the Dashboard and verify issue summaries are displayed from the index data.",
                    observed="\n".join(dashboard_observation.visible_issue_labels),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible Dashboard surface shows user-facing KPI cards "
                        "and issue labels rather than a generic loading shell."
                    ),
                    observed=(
                        f"open_issues_visible={dashboard_observation.open_issues_visible}; "
                        f"team_velocity_visible={dashboard_observation.team_velocity_visible}; "
                        f"active_epics_visible={dashboard_observation.active_epics_visible}; "
                        f"recent_activity_visible={dashboard_observation.recent_activity_visible}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible Dashboard issue labels matched entries from the "
                        "hosted summary index without any eager issue detail fetches."
                    ),
                    observed=(
                        f"visible_issue_labels={list(dashboard_observation.visible_issue_labels)}; "
                        f"issues_index_reads={len(request_observation.issues_index_urls)}; "
                        f"main_md_reads={len(request_observation.main_markdown_urls)}"
                    ),
                )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                return
            except Exception:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["request_observation"] = _request_observation_payload(request_observation)
        _write_failure_outputs(result)
        raise


def _summary_index_entries(service: LiveSetupRepositoryService) -> list[dict[str, str]]:
    payload = json.loads(service.fetch_repo_text(ISSUES_INDEX_PATH))
    if not isinstance(payload, list):
        raise AssertionError(
            "Precondition failed: the hosted issues summary index was not a JSON list.\n"
            f"Observed payload type: {type(payload).__name__}",
        )
    entries: list[dict[str, str]] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key", "")).strip()
        summary = str(entry.get("summary", "")).strip()
        if key and summary:
            entries.append({"key": key, "summary": summary})
    if len(entries) < 3:
        raise AssertionError(
            "Precondition failed: the hosted issues summary index did not expose at least "
            "three visible issues for Dashboard verification.\n"
            f"Observed entries: {entries}",
        )
    return entries


def _assert_dashboard_matches_index(
    *,
    observation: LiveDashboardObservation,
    expected_dashboard_labels: set[str],
) -> None:
    if not observation.active_dashboard_visible:
        raise AssertionError(
            "Step 5 failed: the visible selected navigation target was not Dashboard.\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if not observation.open_issues_visible or not observation.team_velocity_visible:
        raise AssertionError(
            "Step 5 failed: the Dashboard did not render the expected user-facing KPI cards "
            "`Open Issues` and `Team Velocity`.\n"
            f"Observed body text:\n{observation.body_text}",
        )
    if len(observation.visible_issue_labels) < 2:
        raise AssertionError(
            "Step 5 failed: the Dashboard did not expose enough visible issue summary labels "
            "to prove the summary index was rendered.\n"
            f"Observed labels: {list(observation.visible_issue_labels)}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    missing_labels = [
        label
        for label in observation.visible_issue_labels
        if label not in expected_dashboard_labels
    ]
    if missing_labels:
        raise AssertionError(
            "Step 5 failed: the Dashboard rendered issue labels that did not match the hosted "
            "summary index entries.\n"
            f"Unexpected labels: {missing_labels}\n"
            f"Observed labels: {list(observation.visible_issue_labels)}",
        )


def _normalized_paths(urls: list[str]) -> list[str]:
    normalized: list[str] = []
    for url in urls:
        parsed = url.split("/contents/", maxsplit=1)
        if len(parsed) != 2:
            continue
        normalized.append(parsed[1].split("?", maxsplit=1)[0])
    return normalized


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


def _dashboard_payload(observation: LiveDashboardObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "active_dashboard_visible": observation.active_dashboard_visible,
        "active_epics_visible": observation.active_epics_visible,
        "recent_activity_visible": observation.recent_activity_visible,
        "open_issues_visible": observation.open_issues_visible,
        "team_velocity_visible": observation.team_velocity_visible,
        "visible_issue_labels": list(observation.visible_issue_labels),
    }


def _request_observation_payload(
    observation: HostedBootstrapReadObservation,
) -> dict[str, object]:
    return {
        "tree_urls": list(observation.tree_urls),
        "project_json_urls": list(observation.project_json_urls),
        "config_json_urls": list(observation.config_json_urls),
        "issues_index_urls": list(observation.issues_index_urls),
        "tombstone_metadata_urls": list(observation.tombstone_metadata_urls),
        "main_markdown_urls": list(observation.main_markdown_urls),
        "comments_urls": list(observation.comments_urls),
        "attachments_urls": list(observation.attachments_urls),
        "other_content_urls": list(observation.other_content_urls),
        "all_content_paths": observation.all_content_paths,
    }


def _write_pass_outputs(result: dict[str, object]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: unknown failure"))
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error,
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            f"* Recorded hosted repository reads for {OBSERVATION_WINDOW_SECONDS} seconds "
            "during startup with a stored GitHub token."
        ),
        f"* Verified {{{{{ISSUES_INDEX_PATH}}}}} was fetched.",
        f"* Verified {{{{{PROJECT_JSON_PATH}}}}} and the expected config JSON files were fetched.",
        "* Verified no eager issue detail artifact reads (`main.md`, `comments/`, `attachments/`) occurred during initial load.",
        "* Opened Dashboard and checked the visible issue summary labels against the hosted summary index.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}."
        ),
        f"* Screenshot: {{{{{screenshot_path}}}}}",
        "",
        "*Step results*",
        *_step_lines(result, jira=True),
        "",
        "*Human-style verification*",
        *_human_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact error*",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        f"- Recorded hosted repository reads for {OBSERVATION_WINDOW_SECONDS} seconds during startup with a stored GitHub token.",
        f"- Verified `{ISSUES_INDEX_PATH}` plus `{PROJECT_JSON_PATH}` and the expected config JSON files were fetched.",
        "- Verified startup did not eagerly request issue `main.md`, `comments/`, or `attachments/` artifacts.",
        "- Opened Dashboard and verified the visible issue summary labels matched entries from the hosted summary index.",
        "",
        "### Observed result",
        (
            "- Matched the expected result."
            if passed
            else "- Did not match the expected result."
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{platform.system()}`."
        ),
        f"- Screenshot: `{screenshot_path}`",
        "",
        "### Step results",
        *_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "### Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    request_observation = result.get("request_observation", {})
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            f"Observed hosted startup reads for `{PROJECT_PATH}` and verified the bootstrap "
            "request envelope stayed on project/config metadata plus the summary index."
        ),
        "",
        "## Observed",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        (
            f"- Requested content paths: `{request_observation.get('all_content_paths', [])}`"
            if isinstance(request_observation, dict)
            else ""
        ),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(line for line in lines if line != "") + "\n"


def _bug_description(result: dict[str, object]) -> str:
    request_observation = result.get("request_observation", {})
    lines = [
        f"# {TICKET_KEY} - Hosted bootstrap read envelope regression",
        "",
        "## Steps to reproduce",
        "1. Start the hosted web app while monitoring repository network requests.",
        f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
        "2. Verify that `.trackstate/index/issues.json` is fetched.",
        f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
        "3. Verify that project and config JSON files are fetched.",
        f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
        "4. Verify that no requests are made for issue `main.md` files or `comments/` directories during the initial load.",
        f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
        "5. Navigate to the Dashboard and verify issue summaries are displayed from the index data.",
        f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
        "",
        "## Actual vs Expected",
        (
            "- Expected: hosted startup fetches the project/config metadata envelope and "
            "the summary index, avoids eager issue detail reads, and Dashboard shows issue "
            "summaries that match the index data."
        ),
        (
            "- Actual: "
            + str(
                result.get("error")
                or "the startup request envelope or visible Dashboard summaries did not match the expected behavior."
            )
        ),
        "",
        "## Exact error message",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Environment",
        f"- URL: `{result['app_url']}`",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
        "- Browser: `Chromium (Playwright)`",
        f"- OS: `{platform.platform()}`",
        f"- Observation window: `{OBSERVATION_WINDOW_SECONDS}s`",
        "",
        "## Evidence",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
        (
            f"- Requested content paths: `{request_observation.get('all_content_paths', [])}`"
            if isinstance(request_observation, dict)
            else "- Requested content paths: `[]`"
        ),
        (
            f"- `main.md` reads: `{request_observation.get('main_markdown_urls', [])}`"
            if isinstance(request_observation, dict)
            else "- `main.md` reads: `[]`"
        ),
        (
            f"- `comments/` reads: `{request_observation.get('comments_urls', [])}`"
            if isinstance(request_observation, dict)
            else "- `comments/` reads: `[]`"
        ),
        (
            f"- Dashboard labels: `{result.get('dashboard_observation', {}).get('visible_issue_labels', [])}`"
            if isinstance(result.get("dashboard_observation"), dict)
            else "- Dashboard labels: `[]`"
        ),
    ]
    return "\n".join(lines) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} Step {step.get('step')} ({step.get('status')}): "
            f"{step.get('action')} Observed: {step.get('observed')}",
        )
    return lines or ([("* No steps recorded." if jira else "- No steps recorded.")])


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for index, check in enumerate(result.get("human_verification", []), start=1):
        if not isinstance(check, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} Check {index}: {check.get('check')} Observed: {check.get('observed')}",
        )
    return lines or ([("* No human-style checks recorded." if jira else "- No human-style checks recorded.")])


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", "No observation recorded."))
    return str(result.get("error", "Step was not completed."))


if __name__ == "__main__":
    main()
