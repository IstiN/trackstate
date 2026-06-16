from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.ts683_bootstrap_schema_guard_runtime import (  # noqa: E402
    BootstrapSchemaGuardConsoleEvent,
    Ts683BootstrapSchemaGuardRuntime,
)

TICKET_KEY = "TS-683"
TEST_CASE_TITLE = (
    "Schema validation guard during bootstrap - inconsistencies are logged "
    "instead of throwing exceptions"
)
RUN_COMMAND = "PYTHONPATH=. python3 testing/tests/TS-683/test_ts_683.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts683_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts683_failure.png"
REQUEST_STEPS = [
    "Launch the application with an invalid data structure injected into the browser's preloaded state.",
    "Monitor the application logs/console during the startup sequence.",
    "Check if the interactive shell is reached.",
]
REQUIRED_NAVIGATION_LABELS = (
    "Dashboard",
    "Board",
    "JQL Search",
    "Hierarchy",
    "Settings",
)
EXPECTED_DIAGNOSTIC_FRAGMENTS = (
    "workspace",
    "storage",
    "schema",
    "shared_preferences",
    "preloaded",
    "malformed",
    "invalid",
    "repair",
    "normalize",
)
IGNORED_LOG_SNIPPETS = (
    "Installing/Activating first service worker.",
    "Activated new service worker.",
    "Injecting <script> tag. Using callback.",
    "GPU stall due to ReadPixels",
)
EXPECTED_WORKSPACE_ID = "hosted:istin/trackstate-setup@main"


@dataclass(frozen=True)
class ShellObservation:
    body_text: str
    visible_navigation_labels: tuple[str, ...]
    fatal_banner_visible: bool
    trackstate_title_visible: bool
    dashboard_metrics_visible: bool


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-683 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    runtime = Ts683BootstrapSchemaGuardRuntime(
        repository=config.repository,
        token=token,
        malformed_workspace_state=_malformed_workspace_state(),
    )
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "steps": [],
        "human_verification": [],
        "preloaded_invalid_state": {
            runtime.prefixed_workspace_key: runtime.malformed_workspace_value,
            runtime.prefixed_token_key: "<redacted>",
        },
    }

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            try:
                runtime_state = tracker_page.open()
                result["runtime_state"] = runtime_state.kind
                result["runtime_body_text"] = runtime_state.body_text
                if runtime_state.kind != "ready":
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app did not reach an interactive state after "
                            "the malformed browser preload was injected.\n"
                            f"Observed runtime state: {runtime_state.kind}\n"
                            f"Observed body text:\n{runtime_state.body_text}"
                        ),
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Observed the deployed app startup as a user after corrupt "
                            "workspace/auth browser state was preloaded."
                        ),
                        observed=(
                            "The visible experience stopped before the interactive shell "
                            "loaded.\n"
                            f"Visible body text: {_snippet(runtime_state.body_text)}"
                        ),
                    )
                    tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the interactive "
                        "shell after malformed preloaded browser state was injected.\n"
                        f"Observed runtime state: {runtime_state.kind}\n"
                        f"Observed body text:\n{runtime_state.body_text}",
                    )

                failures: list[str] = []
                storage_snapshot = runtime.storage_snapshot()
                result["storage_snapshot"] = storage_snapshot
                storage_summary = _storage_summary(storage_snapshot)
                if _storage_repaired(storage_snapshot, runtime):
                    _record_step(
                        result,
                        step=1,
                        status="passed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "Injected malformed raw Flutter web SharedPreferences values "
                            "for the saved workspace state and hosted token, then observed "
                            "startup rewrite them into the encoded format Flutter web "
                            "expects.\n"
                            f"{storage_summary}"
                        ),
                    )
                else:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=storage_summary,
                    )
                    failures.append(
                        "Step 1 failed: the malformed preloaded browser state was not "
                        "rewritten into the encoded Flutter web SharedPreferences format "
                        "during startup.\n"
                        f"{storage_summary}",
                    )

                interesting_logs = _interesting_console_events(runtime.console_events)
                result["console_events"] = [
                    asdict(event) for event in runtime.console_events
                ]
                result["interesting_console_events"] = [
                    asdict(event) for event in interesting_logs
                ]
                result["page_errors"] = list(runtime.page_errors)
                guard_logs = _diagnostic_console_events(interesting_logs)
                result["diagnostic_console_events"] = [
                    asdict(event) for event in guard_logs
                ]
                console_summary = _console_summary(
                    interesting_logs=interesting_logs,
                    page_errors=runtime.page_errors,
                )
                if guard_logs:
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=console_summary,
                    )
                else:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=console_summary,
                    )
                    failures.append(
                        "Step 2 failed: startup repaired the malformed preloaded browser "
                        "state, but the live app did not emit any descriptive diagnostic "
                        "log about the inconsistency.\n"
                        "Expected: at least one browser console or page-error entry that "
                        "mentions the invalid workspace/auth preload (for example workspace, "
                        "storage, schema, shared_preferences, malformed, invalid, repair, "
                        "or normalize) while allowing startup to continue.\n"
                        f"Observed console summary:\n{console_summary}",
                    )

                shell_observation = _observe_shell(tracker_page)
                result["shell_observation"] = _shell_payload(shell_observation)
                shell_summary = _shell_summary(shell_observation)
                if _shell_visible(shell_observation):
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=REQUEST_STEPS[2],
                        observed=shell_summary,
                    )
                else:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=shell_summary,
                    )
                    failures.append(
                        "Step 3 failed: the expected interactive shell signals were not "
                        "all visible after startup recovered from the malformed preload.\n"
                        f"{shell_summary}",
                    )

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the deployed app as a user after the malformed saved "
                        "workspace/token preload was injected."
                    ),
                    observed=(
                        f"{shell_summary}\n"
                        f"Fatal banner visible: {shell_observation.fatal_banner_visible}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Reviewed the browser console/page diagnostics that a human would "
                        "inspect while the recovered startup sequence ran."
                    ),
                    observed=console_summary,
                )

                if failures:
                    tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    raise AssertionError("\n\n".join(failures))

                tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            except Exception as error:
                result.setdefault("error", _format_error(error))
                result.setdefault("traceback", traceback.format_exc())
                if not FAILURE_SCREENSHOT_PATH.exists():
                    tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                raise
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-683 passed")


def _malformed_workspace_state() -> dict[str, object]:
    return {
        "activeWorkspaceId": EXPECTED_WORKSPACE_ID,
        "migrationComplete": True,
        "profiles": [
            {
                "id": EXPECTED_WORKSPACE_ID,
                "displayName": "",
                "targetType": "hosted",
                "target": "IstiN/trackstate-setup",
                "defaultBranch": "main",
                "writeBranch": "main",
            },
        ],
    }


def _storage_repaired(
    storage_snapshot: dict[str, str | None],
    runtime: Ts683BootstrapSchemaGuardRuntime,
) -> bool:
    prefixed_workspace_value = storage_snapshot.get(runtime.prefixed_workspace_key)
    prefixed_token_value = storage_snapshot.get(runtime.prefixed_token_key)
    if (
        prefixed_workspace_value is None
        or prefixed_token_value is None
        or prefixed_workspace_value == runtime.malformed_workspace_value
        or prefixed_token_value == runtime.malformed_token_value
    ):
        return False
    try:
        decoded_workspace_string = json.loads(prefixed_workspace_value)
        decoded_workspace = json.loads(decoded_workspace_string)
        decoded_token = json.loads(prefixed_token_value)
    except (TypeError, json.JSONDecodeError):
        return False
    if not isinstance(decoded_workspace_string, str) or not isinstance(
        decoded_workspace,
        dict,
    ):
        return False
    profiles = decoded_workspace.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        return False
    active_workspace_id = decoded_workspace.get("activeWorkspaceId")
    return (
        active_workspace_id == EXPECTED_WORKSPACE_ID
        and decoded_token == runtime.malformed_token_value
    )


def _storage_summary(storage_snapshot: dict[str, str | None]) -> str:
    lines = []
    for key in sorted(storage_snapshot):
        value = storage_snapshot.get(key)
        if "githubToken" in key and value is not None:
            rendered_value = "<redacted>"
        else:
            rendered_value = _snippet(value)
        lines.append(f"{key}={rendered_value}")
    return "\n".join(lines)


def _interesting_console_events(
    console_events: list[BootstrapSchemaGuardConsoleEvent],
) -> list[BootstrapSchemaGuardConsoleEvent]:
    return [
        event
        for event in console_events
        if not any(snippet in event.text for snippet in IGNORED_LOG_SNIPPETS)
    ]


def _diagnostic_console_events(
    console_events: list[BootstrapSchemaGuardConsoleEvent],
) -> list[BootstrapSchemaGuardConsoleEvent]:
    matches: list[BootstrapSchemaGuardConsoleEvent] = []
    for event in console_events:
        lowered = event.text.lower()
        if any(fragment in lowered for fragment in EXPECTED_DIAGNOSTIC_FRAGMENTS):
            matches.append(event)
    return matches


def _observe_shell(tracker_page: TrackStateTrackerPage) -> ShellObservation:
    body_text = tracker_page.body_text()
    return ShellObservation(
        body_text=body_text,
        visible_navigation_labels=tuple(
            label for label in REQUIRED_NAVIGATION_LABELS if label in body_text
        ),
        fatal_banner_visible="TrackState data was not found" in body_text,
        trackstate_title_visible="TrackState.AI" in body_text,
        dashboard_metrics_visible="Open Issues" in body_text
        and "Issues in Progress" in body_text,
    )


def _shell_visible(shell_observation: ShellObservation) -> bool:
    return (
        not shell_observation.fatal_banner_visible
        and shell_observation.trackstate_title_visible
        and shell_observation.dashboard_metrics_visible
        and len(shell_observation.visible_navigation_labels)
        == len(REQUIRED_NAVIGATION_LABELS)
    )


def _shell_summary(shell_observation: ShellObservation) -> str:
    return (
        f"visible_navigation_labels={shell_observation.visible_navigation_labels}\n"
        f"trackstate_title_visible={shell_observation.trackstate_title_visible}\n"
        f"dashboard_metrics_visible={shell_observation.dashboard_metrics_visible}\n"
        f"fatal_banner_visible={shell_observation.fatal_banner_visible}\n"
        f"body_excerpt={_snippet(shell_observation.body_text)}"
    )


def _shell_payload(shell_observation: ShellObservation) -> dict[str, object]:
    return {
        "visible_navigation_labels": list(shell_observation.visible_navigation_labels),
        "fatal_banner_visible": shell_observation.fatal_banner_visible,
        "trackstate_title_visible": shell_observation.trackstate_title_visible,
        "dashboard_metrics_visible": shell_observation.dashboard_metrics_visible,
        "body_excerpt": _snippet(shell_observation.body_text),
    }


def _console_summary(
    *,
    interesting_logs: list[BootstrapSchemaGuardConsoleEvent],
    page_errors: list[str],
) -> str:
    if not interesting_logs and not page_errors:
        return (
            "No application-specific console diagnostics were captured. The browser "
            "emitted only generic service-worker / GPU messages, and no page errors "
            "were raised."
        )
    lines = ["Console diagnostics:"]
    for event in interesting_logs:
        lines.append(f"- [{event.level}] {event.text}")
    if page_errors:
        lines.append("Page errors:")
        for error in page_errors:
            lines.append(f"- {error}")
    return "\n".join(lines)


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
    checks.append(
        {
            "check": check,
            "observed": observed,
        },
    )


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

    shell_payload = result.get("shell_observation", {})
    if not isinstance(shell_payload, dict):
        shell_payload = {}
    console_summary = _console_summary(
        interesting_logs=[
            BootstrapSchemaGuardConsoleEvent(**event)
            for event in result.get("diagnostic_console_events", [])
            if isinstance(event, dict)
        ],
        page_errors=[
            str(item) for item in result.get("page_errors", []) if isinstance(item, str)
        ],
    )
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was automated",
        f"* Step 1: Injected malformed raw values into {jira_inline('flutter.trackstate.workspaceProfiles.state')} and the hosted token key before loading the deployed app.",
        "* Step 2: Monitored browser console/page diagnostics during startup and looked for a descriptive guard log about the malformed preload.",
        "* Step 3: Verified the interactive shell stayed visible with the main navigation and dashboard content instead of failing startup.",
        "",
        "h4. Human-style verification",
        (
            "* Observed the visible shell as a user would: navigation "
            f"{jira_inline(', '.join(shell_payload.get('visible_navigation_labels', [])))} "
            "remained visible, the TrackState title stayed on screen, and the fatal "
            "{quote}TrackState data was not found{quote} banner was absent."
        ),
        f"* Reviewed the console/page diagnostics a human would inspect and observed the expected descriptive guard log. {jira_inline(console_summary)}",
        "",
        "h4. Result",
        "* The malformed preloaded browser state was normalized into Flutter web's encoded SharedPreferences format.",
        "* A descriptive diagnostic log was emitted instead of an unhandled startup exception.",
        "* The interactive shell remained visible and matched the expected result.",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
        "",
        "h4. Screenshot",
        f"* {SUCCESS_SCREENSHOT_PATH}",
    ]

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Injected malformed raw values into `flutter.trackstate.workspaceProfiles.state` and the hosted token key before loading the deployed app.",
        "- Monitored browser console/page diagnostics during startup and looked for a descriptive guard log about the malformed preload.",
        "- Verified the interactive shell stayed visible with the main navigation and dashboard content instead of failing startup.",
        "",
        "## Human-style verification",
        (
            "- Observed the visible shell as a user would: navigation "
            f"`{', '.join(shell_payload.get('visible_navigation_labels', []))}` remained "
            "visible, the TrackState title stayed on screen, and the fatal "
            "`TrackState data was not found` banner was absent."
        ),
        f"- Reviewed the console/page diagnostics a human would inspect and observed the expected descriptive guard log. `{console_summary}`",
        "",
        "## Result",
        "- The malformed preloaded browser state was normalized into Flutter web's encoded SharedPreferences format.",
        "- A descriptive diagnostic log was emitted instead of an unhandled startup exception.",
        "- The interactive shell remained visible and matched the expected result.",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
        "",
        "## Screenshot",
        f"- `{SUCCESS_SCREENSHOT_PATH}`",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error_message = str(result.get("error", "AssertionError: TS-683 failed"))
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_message,
            },
        )
        + "\n",
        encoding="utf-8",
    )

    steps = result.get("steps", [])
    if not isinstance(steps, list):
        steps = []
    human_checks = result.get("human_verification", [])
    if not isinstance(human_checks, list):
        human_checks = []
    shell_payload = result.get("shell_observation", {})
    if not isinstance(shell_payload, dict):
        shell_payload = {}
    screenshot_path = (
        str(FAILURE_SCREENSHOT_PATH)
        if FAILURE_SCREENSHOT_PATH.exists()
        else "<screenshot was not captured>"
    )
    console_summary = _console_summary(
        interesting_logs=[
            BootstrapSchemaGuardConsoleEvent(**event)
            for event in result.get("interesting_console_events", [])
            if isinstance(event, dict)
        ],
        page_errors=[
            str(item) for item in result.get("page_errors", []) if isinstance(item, str)
        ],
    )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. Failed step",
    ]
    for step in steps:
        if not isinstance(step, dict):
            continue
        status_marker = "✅" if step.get("status") == "passed" else "❌"
        jira_lines.append(
            f"* {status_marker} Step {step.get('step')}: {step.get('action')} "
            f"Observed: {jira_inline(str(step.get('observed', '')))}",
        )
    jira_lines.extend(
        [
            "",
            "h4. Human-style verification",
        ],
    )
    for check in human_checks:
        if not isinstance(check, dict):
            continue
        jira_lines.append(
            f"* {jira_inline(str(check.get('check', '')))} Observed: {jira_inline(str(check.get('observed', '')))}",
        )
    jira_lines.extend(
        [
            "",
            "h4. Actual vs Expected",
            "* Expected: the schema validation guard catches the malformed preloaded browser state, emits a descriptive diagnostic log, and the interactive shell remains visible.",
            (
                "* Actual: the app recovered and the shell remained visible, but the "
                "console/page diagnostics did not expose any descriptive log about the "
                "invalid preloaded workspace/auth state."
            ),
            "",
            "h4. Environment",
            f"* URL: {jira_inline(str(result.get('app_url', '')))}",
            f"* Repository: {jira_inline(str(result.get('repository', '')))} @ {jira_inline(str(result.get('repository_ref', '')))}",
            f"* Browser: {jira_inline(str(result.get('browser', 'Chromium (Playwright)')))}",
            f"* OS: {jira_inline(str(result.get('os', '')))}",
            "",
            "h4. Console and page diagnostics",
            "{code}",
            console_summary,
            "{code}",
            "",
            "h4. Assertion / traceback",
            "{code}",
            str(result.get("traceback", result.get("error", "<missing traceback>"))),
            "{code}",
            "",
            "h4. Screenshot",
            f"* {screenshot_path}",
        ],
    )

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## Failed step",
    ]
    for step in steps:
        if not isinstance(step, dict):
            continue
        status_marker = "✅" if step.get("status") == "passed" else "❌"
        markdown_lines.append(
            f"- {status_marker} Step {step.get('step')}: {step.get('action')} Observed: `{step.get('observed')}`",
        )
    markdown_lines.extend(
        [
            "",
            "## Human-style verification",
        ],
    )
    for check in human_checks:
        if not isinstance(check, dict):
            continue
        markdown_lines.append(
            f"- `{check.get('check')}` Observed: `{check.get('observed')}`",
        )
    markdown_lines.extend(
        [
            "",
            "## Actual vs Expected",
            "- Expected: the schema validation guard catches the malformed preloaded browser state, emits a descriptive diagnostic log, and the interactive shell remains visible.",
            "- Actual: the app recovered and the shell remained visible, but the console/page diagnostics did not expose any descriptive log about the invalid preloaded workspace/auth state.",
            "",
            "## Environment",
            f"- URL: `{result.get('app_url', '')}`",
            f"- Repository: `{result.get('repository', '')}` @ `{result.get('repository_ref', '')}`",
            f"- Browser: `{result.get('browser', 'Chromium (Playwright)')}`",
            f"- OS: `{result.get('os', '')}`",
            "",
            "## Console and page diagnostics",
            "```text",
            console_summary,
            "```",
            "",
            "## Assertion / traceback",
            "```text",
            str(result.get("traceback", result.get("error", "<missing traceback>"))),
            "```",
            "",
            "## Screenshot",
            f"- `{screenshot_path}`",
        ],
    )

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(
        _bug_description_markdown(
            result=result,
            console_summary=console_summary,
            screenshot_path=screenshot_path,
            shell_payload=shell_payload,
        ),
        encoding="utf-8",
    )


def _bug_description_markdown(
    *,
    result: dict[str, object],
    console_summary: str,
    screenshot_path: str,
    shell_payload: dict[str, object],
) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        steps = []
    annotated_steps = []
    for requested_step in REQUEST_STEPS:
        matching_step = next(
            (
                step
                for step in steps
                if isinstance(step, dict) and step.get("action") == requested_step
            ),
            None,
        )
        if matching_step is None:
            annotated_steps.append(f"- {requested_step} - not reached.")
            continue
        status_marker = "✅" if matching_step.get("status") == "passed" else "❌"
        annotated_steps.append(
            f"- {status_marker} {requested_step}\n"
            f"  Actual: {matching_step.get('observed')}",
        )

    shell_summary = (
        f"visible_navigation_labels={shell_payload.get('visible_navigation_labels')}; "
        f"trackstate_title_visible={shell_payload.get('trackstate_title_visible')}; "
        f"dashboard_metrics_visible={shell_payload.get('dashboard_metrics_visible')}; "
        f"fatal_banner_visible={shell_payload.get('fatal_banner_visible')}"
    )

    lines = [
        f"# {TICKET_KEY} - bootstrap schema guard does not log malformed preloaded browser state",
        "",
        "## Steps to reproduce",
        "1. Open the deployed TrackState app with malformed preloaded Flutter web preference values for the saved workspace state and hosted token.",
        "2. Monitor browser console/page diagnostics during startup.",
        "3. Observe whether the interactive shell is reached.",
        "",
        "## Exact steps from the test case with observations",
        *annotated_steps,
        "",
        "## Actual vs Expected",
        "- Expected: the schema validation guard catches the malformed preloaded browser state, emits a descriptive diagnostic log about the inconsistency, and the app continues to the interactive shell.",
        "- Actual: the app recovered and the interactive shell remained visible, but the browser console/page diagnostics only showed generic service-worker or GPU messages and no descriptive log about the malformed workspace/auth preload.",
        "",
        "## Environment",
        f"- URL: `{result.get('app_url', '')}`",
        f"- Repository: `{result.get('repository', '')}` @ `{result.get('repository_ref', '')}`",
        f"- Browser: `{result.get('browser', 'Chromium (Playwright)')}`",
        f"- OS: `{result.get('os', '')}`",
        f"- Screenshot: `{screenshot_path}`",
        "",
        "## Visible user-facing state at failure",
        f"- Shell observation: `{shell_summary}`",
        f"- Runtime state: `{result.get('runtime_state', '<missing>')}`",
        f"- Body excerpt: `{_snippet(str(result.get('runtime_body_text', '')) or '')}`",
        "",
        "## Console and page diagnostics",
        "```text",
        console_summary,
        "```",
        "",
        "## Exact error message / traceback",
        "```text",
        str(result.get("traceback", result.get("error", "<missing traceback>"))),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def _snippet(value: str | None, limit: int = 600) -> str:
    if value is None:
        return "<missing>"
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def jira_inline(value: str) -> str:
    return "{{" + value + "}}"


if __name__ == "__main__":
    main()
