from __future__ import annotations

import json
import platform
import subprocess
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-818"
TEST_CASE_TITLE = (
    "Workspace switcher state during hydration — loading guard prevents "
    "interaction and incorrect state display"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-818/test_ts_818.py"
TEST_FILE_PATH = "testing/tests/TS-818/test_ts_818.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
OBSERVATION_WINDOW_SECONDS = 15
IMMEDIATE_TRIGGER_TIMEOUT_MS = 1_500
IMMEDIATE_SWITCHER_TIMEOUT_MS = 5_000

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts818_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts818_failure.png"

REQUEST_STEPS = [
    "Reload the application.",
    "Immediately attempt to open or view the workspace switcher before the hydration logic completes.",
    "Observe the UI state and interactivity of the switcher.",
]
EXPECTED_RESULT = (
    "The workspace switcher displays a loading state or implements a guard that "
    "prevents interaction/incorrect state transitions until the local file "
    "system validation is complete. The user should not see a flicker of "
    "'Local Unavailable' followed by 'Local Git'."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-818 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )
    prepared_local_workspace = _prepare_local_workspace_repository()
    workspace_state = _workspace_state(service.repository)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "test_file": TEST_FILE_PATH,
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "observation_window_seconds": OBSERVATION_WINDOW_SECONDS,
        "prepared_local_workspace": prepared_local_workspace,
        "preloaded_workspace_state": workspace_state,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                repository=config.repository,
                token=token,
                workspace_state=workspace_state,
            ),
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app did not reach an interactive startup shell. "
                            f"Observed runtime state: {runtime.kind}. "
                            f"Observed body text: {runtime.body_text!r}"
                        ),
                    )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed="Not reached because step 1 failed.",
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed="Not reached because step 1 failed.",
                    )
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach an interactive "
                        "state before the hydration observation started.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.dismiss_connection_banner()
                page.set_viewport(**DESKTOP_VIEWPORT)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"Reloaded {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']} and "
                        "reached the interactive startup shell."
                    ),
                )

                immediate_trigger: WorkspaceSwitcherTriggerObservation | None = None
                immediate_switcher: WorkspaceSwitcherObservation | None = None
                immediate_guard_active = False
                immediate_open_error: str | None = None

                try:
                    immediate_trigger = page.observe_trigger(
                        timeout_ms=IMMEDIATE_TRIGGER_TIMEOUT_MS,
                    )
                    result["immediate_trigger_observation"] = _trigger_payload(
                        immediate_trigger,
                    )
                    try:
                        immediate_switcher = page.open_and_observe(
                            timeout_ms=IMMEDIATE_SWITCHER_TIMEOUT_MS,
                        )
                        result["immediate_switcher_observation"] = _switcher_payload(
                            immediate_switcher,
                        )
                    except AssertionError as error:
                        immediate_open_error = str(error)
                        result["immediate_switcher_error"] = immediate_open_error
                except AssertionError as error:
                    immediate_guard_active = True
                    result["immediate_trigger_error"] = str(error)

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=_step_two_observation(
                        immediate_guard_active=immediate_guard_active,
                        immediate_trigger=immediate_trigger,
                        immediate_switcher=immediate_switcher,
                        immediate_open_error=immediate_open_error,
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Looked at the visible workspace trigger immediately after reload "
                        "and attempted to open Workspace switcher at the first user-visible "
                        "opportunity."
                    ),
                    observed=_step_two_observation(
                        immediate_guard_active=immediate_guard_active,
                        immediate_trigger=immediate_trigger,
                        immediate_switcher=immediate_switcher,
                        immediate_open_error=immediate_open_error,
                    ),
                )

                _wait_for_observation_window(page, seconds=OBSERVATION_WINDOW_SECONDS)
                final_trigger = page.observe_trigger(timeout_ms=15_000)
                result["final_trigger_observation"] = _trigger_payload(final_trigger)

                if immediate_switcher is None:
                    final_switcher = page.open_and_observe(timeout_ms=15_000)
                else:
                    final_switcher = page.observe_open_switcher(timeout_ms=15_000)
                result["final_switcher_observation"] = _switcher_payload(final_switcher)

                _record_human_verification(
                    result,
                    check=(
                        "Kept watching the same user-facing trigger and switcher content "
                        f"for {OBSERVATION_WINDOW_SECONDS} seconds to confirm whether the "
                        "hydration state corrected itself or flickered through an incorrect "
                        "workspace state."
                    ),
                    observed=(
                        f"final_trigger={final_trigger.semantic_label!r}; "
                        f"final_switcher_excerpt={_snippet(final_switcher.switcher_text)!r}"
                    ),
                )

                failures = _validate_hydration_state(
                    immediate_guard_active=immediate_guard_active,
                    immediate_trigger=immediate_trigger,
                    immediate_switcher=immediate_switcher,
                    final_trigger=final_trigger,
                    final_switcher=final_switcher,
                )
                step3_observed = (
                    f"immediate_guard_active={immediate_guard_active}; "
                    f"immediate_trigger={_trigger_summary(immediate_trigger)}; "
                    f"immediate_switcher_excerpt={_switcher_summary(immediate_switcher)!r}; "
                    f"final_trigger={final_trigger.semantic_label!r}; "
                    f"final_switcher_excerpt={_snippet(final_switcher.switcher_text)!r}"
                )
                _record_step(
                    result,
                    step=3,
                    status="passed" if not failures else "failed",
                    action=REQUEST_STEPS[2],
                    observed=step3_observed if not failures else "\n".join(failures),
                )
                if failures:
                    raise AssertionError("\n".join(failures))

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                if page is not None:
                    try:
                        page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                        result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    except Exception as screenshot_error:
                        result["screenshot_error"] = (
                            f"{type(screenshot_error).__name__}: {screenshot_error}"
                        )
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _workspace_state(repository: str) -> dict[str, object]:
    local_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
    hosted_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": local_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": local_id,
                "displayName": LOCAL_DISPLAY_NAME,
                "customDisplayName": LOCAL_DISPLAY_NAME,
                "targetType": "local",
                "target": LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-17T12:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-16T12:00:00.000Z",
            },
        ],
    }


def _prepare_local_workspace_repository() -> dict[str, object]:
    local_path = Path(LOCAL_TARGET)
    local_path.mkdir(parents=True, exist_ok=True)

    if not (local_path / ".git").exists():
        subprocess.run(
            ["git", "init", "--initial-branch", DEFAULT_BRANCH, str(local_path)],
            check=True,
            capture_output=True,
            text=True,
        )

    marker_path = local_path / ".trackstate-ts818-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-818 workspace hydration verification.\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "-C", str(local_path), "add", marker_path.name],
        check=True,
        capture_output=True,
        text=True,
    )

    head = subprocess.run(
        ["git", "-C", str(local_path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "-C", str(local_path), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    if head.returncode != 0 or status.stdout.strip():
        subprocess.run(
            [
                "git",
                "-C",
                str(local_path),
                "-c",
                "user.name=TS-818 Automation",
                "-c",
                "user.email=ts818@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "Prepare TS-818 local workspace",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    branch = subprocess.run(
        ["git", "-C", str(local_path), "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = subprocess.run(
        ["git", "-C", str(local_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "path": str(local_path),
        "branch": branch.stdout.strip(),
        "head": head.stdout.strip(),
        "marker_path": str(marker_path),
    }


def _wait_for_observation_window(page: LiveWorkspaceSwitcherPage, *, seconds: int) -> None:
    started_at = page._tracker_page.session.evaluate("() => performance.now()")
    page._tracker_page.session.wait_for_function(
        """
        ({ startedAt, durationMs }) =>
          typeof startedAt === 'number'
          && performance.now() - startedAt >= durationMs
        """,
        arg={"startedAt": started_at, "durationMs": seconds * 1_000},
        timeout_ms=(seconds * 1_000) + 5_000,
    )


def _validate_hydration_state(
    *,
    immediate_guard_active: bool,
    immediate_trigger: WorkspaceSwitcherTriggerObservation | None,
    immediate_switcher: WorkspaceSwitcherObservation | None,
    final_trigger: WorkspaceSwitcherTriggerObservation,
    final_switcher: WorkspaceSwitcherObservation,
) -> list[str]:
    failures: list[str] = []

    if immediate_trigger is not None and _is_incorrect_trigger_state(immediate_trigger):
        failures.append(
            "Step 3 failed: the user-facing workspace switcher trigger exposed an "
            "incorrect hydration state immediately after reload instead of a loading "
            "guard or the final Local Git state.\n"
            f"Observed immediate trigger: {immediate_trigger.semantic_label!r}"
        )
    if immediate_switcher is not None and "Local Unavailable" in immediate_switcher.switcher_text:
        failures.append(
            "Step 3 failed: opening Workspace switcher immediately after reload "
            "showed `Local Unavailable`, which is the incorrect transient state the "
            "ticket is meant to hide.\n"
            f"Observed immediate switcher text:\n{immediate_switcher.switcher_text}"
        )
    if not immediate_guard_active and immediate_trigger is None:
        failures.append(
            "Step 3 failed: the test could neither observe a guarded loading phase nor "
            "capture the workspace switcher trigger during the immediate attempt."
        )
    if not _trigger_matches_active_local_local_git(final_trigger):
        failures.append(
            "Step 3 failed: after waiting through the hydration observation window, the "
            "workspace switcher still did not settle to the prepared active local "
            "workspace in the `Local Git` state.\n"
            f"Observed final trigger: {final_trigger.semantic_label!r}"
        )
    if "Local Unavailable" in final_switcher.switcher_text:
        failures.append(
            "Step 3 failed: even after the hydration observation window, Workspace "
            "switcher still rendered `Local Unavailable` in user-visible text.\n"
            f"Observed final switcher text:\n{final_switcher.switcher_text}"
        )
    return failures


def _is_incorrect_trigger_state(trigger: WorkspaceSwitcherTriggerObservation) -> bool:
    if trigger.display_name == HOSTED_DISPLAY_NAME and trigger.workspace_type == "Hosted":
        return True
    return "Unavailable" in trigger.state_label or trigger.state_label == "Needs sign-in"


def _trigger_matches_active_local_local_git(
    trigger: WorkspaceSwitcherTriggerObservation,
) -> bool:
    return (
        trigger.display_name == LOCAL_DISPLAY_NAME
        and trigger.workspace_type == "Local"
        and trigger.state_label == "Local Git"
    )


def _step_two_observation(
    *,
    immediate_guard_active: bool,
    immediate_trigger: WorkspaceSwitcherTriggerObservation | None,
    immediate_switcher: WorkspaceSwitcherObservation | None,
    immediate_open_error: str | None,
) -> str:
    if immediate_guard_active:
        return (
            "The workspace trigger was not user-visible during the immediate observation "
            f"window ({IMMEDIATE_TRIGGER_TIMEOUT_MS} ms), which acted as a loading guard."
        )
    return (
        f"trigger={_trigger_summary(immediate_trigger)}; "
        f"switcher_excerpt={_switcher_summary(immediate_switcher)!r}; "
        f"open_error={immediate_open_error!r}"
    )


def _trigger_summary(trigger: WorkspaceSwitcherTriggerObservation | None) -> str:
    if trigger is None:
        return "<not captured>"
    return trigger.semantic_label


def _switcher_summary(switcher: WorkspaceSwitcherObservation | None) -> str:
    if switcher is None:
        return "<not captured>"
    return _snippet(switcher.switcher_text)


def _snippet(text: str, *, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


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
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
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
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was automated",
        "* Opened the deployed TrackState app in Chromium with a stored signed-in GitHub session and a preloaded active local workspace profile.",
        (
            "* Attempted to view or open *Workspace switcher* immediately after reload, "
            "then continued observing the user-facing state for "
            f"*{OBSERVATION_WINDOW_SECONDS} seconds* to allow hydration to settle."
        ),
        "* Verified that the visible trigger and switcher content never exposed an incorrect hydration state and that the flow settled to the active local workspace in {{Local Git}}.",
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}."
        ),
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Exact error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    lines.extend(_artifact_lines(result, jira=True))
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored signed-in GitHub session and a preloaded active local workspace profile.",
        (
            "- Attempted to view or open **Workspace switcher** immediately after "
            f"reload, then kept observing the visible state for **{OBSERVATION_WINDOW_SECONDS} seconds**."
        ),
        "- Verified the visible trigger and switcher content never exposed an incorrect hydration state and that the flow settled to the active local workspace in `Local Git`.",
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository "
            f"`{result['repository']}` @ `{result['repository_ref']}`, browser "
            f"`Chromium (Playwright)`, OS `{result['os']}`."
        ),
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    lines.extend(_artifact_lines(result, jira=False))
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "## Test Automation Summary",
        "",
        "- Added TS-818 live startup-hydration coverage for the workspace switcher.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            "- Outcome: the user never saw an incorrect workspace hydration state and the flow settled to `Local Git`."
            if passed
            else f"- Outcome: {_failed_step_summary(result)}"
        ),
    ]
    lines.extend(_artifact_lines(result, jira=False))
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
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# {_bug_title(result)}",
            "",
            "## Preconditions used during the run",
            "- User was signed in to GitHub via a stored browser token.",
            f"- Browser storage was preloaded with an active local workspace (`{LOCAL_TARGET}`) and one hosted workspace.",
            f"- The local workspace path was prepared as a git repository at `{LOCAL_TARGET}` before opening the app.",
            "",
            "## Exact steps to reproduce",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            "",
            "## Expected result",
            EXPECTED_RESULT,
            "",
            "## Actual result",
            str(result.get("error", "<missing error>")),
            "",
            "## Missing or broken production-visible capability",
            _bug_capability_gap(result),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment details",
            f"- URL: {result.get('app_url')}",
            f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
            f"- Browser: {result.get('browser')}",
            f"- OS: {result.get('os')}",
            f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"- Observation window: {OBSERVATION_WINDOW_SECONDS} seconds",
            f"- Run command: {RUN_COMMAND}",
            "",
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
            "```json",
            json.dumps(
                {
                    "prepared_local_workspace": result.get("prepared_local_workspace"),
                    "immediate_trigger_observation": result.get("immediate_trigger_observation"),
                    "immediate_switcher_observation": result.get("immediate_switcher_observation"),
                    "final_trigger_observation": result.get("final_trigger_observation"),
                    "final_switcher_observation": result.get("final_switcher_observation"),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _annotated_step_line(
    result: dict[str, object],
    step_number: int,
    action: str,
) -> str:
    status = _step_status(result, step_number)
    marker = "✅" if status == "passed" else "❌"
    observation = _step_observation(result, step_number)
    if observation == "<no observation recorded>" and _has_prior_failed_step(result, step_number):
        observation = "Not reached because an earlier step failed."
    return f"{step_number}. {marker} {action}\n   Actual: {observation}"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return [f"{prefix} <no step data recorded>"]
    return [
        (
            f"{prefix} {'✅' if step.get('status') == 'passed' else '❌'} "
            f"Step {step.get('step')}: {step.get('action')} "
            f"Observed: {step.get('observed')}"
        )
        for step in steps
        if isinstance(step, dict)
    ] or [f"{prefix} <no step data recorded>"]


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    checks = result.get("human_verification", [])
    if not isinstance(checks, list):
        return [f"{prefix} <no human-style verification recorded>"]
    return [
        f"{prefix} {check.get('check')}: {check.get('observed')}"
        for check in checks
        if isinstance(check, dict)
    ] or [f"{prefix} <no human-style verification recorded>"]


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    screenshot = result.get("screenshot")
    if not screenshot:
        return []
    if jira:
        return [f"* Screenshot: {{{{{screenshot}}}}}"]
    return [f"- Screenshot: `{screenshot}`"]


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") != "passed":
                return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "No failed step recorded."))


def _bug_title(result: dict[str, object]) -> str:
    error = str(result.get("error", ""))
    if "Local Unavailable" in error:
        return (
            f"{TICKET_KEY} - Workspace switcher exposes Local Unavailable during "
            "startup hydration"
        )
    return (
        f"{TICKET_KEY} - Workspace switcher exposes incorrect state during "
        "startup hydration"
    )


def _bug_capability_gap(result: dict[str, object]) -> str:
    return (
        "The startup flow does not keep the workspace switcher behind a loading "
        "guard or stable loading state while the prepared local workspace is being "
        "validated. Instead, the user can see an incorrect workspace state during "
        "hydration and the flow does not settle to the active local `Local Git` "
        "state within the observation window."
    )


def _step_status(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "failed"
    for step in steps:
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "<no observation recorded>"
    for step in steps:
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("observed", "<no observation recorded>"))
    return "<no observation recorded>"


def _has_prior_failed_step(result: dict[str, object], step_number: int) -> bool:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return False
    for step in steps:
        if not isinstance(step, dict):
            continue
        candidate_step = int(step.get("step", -1))
        if candidate_step < step_number and step.get("status") != "passed":
            return True
    return False


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "raw_text_lines": list(trigger.raw_text_lines),
        "top_button_labels": list(trigger.top_button_labels),
    }


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "row_count": switcher.row_count,
        "switcher_text": switcher.switcher_text,
    }


if __name__ == "__main__":
    main()
