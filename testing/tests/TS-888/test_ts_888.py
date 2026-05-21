from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_project_settings_page import (  # noqa: E402
    LiveProjectSettingsPage,
)
from testing.components.pages.live_startup_recovery_page import (  # noqa: E402
    LiveStartupRecoveryPage,
    StartupRecoveryShellObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-888"
TEST_CASE_TITLE = "Discoverable navigation - App shell to Settings/Admin entry path"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-888/test_ts_888.py"
INPUT_DIR = REPO_ROOT / "input" / TICKET_KEY
OUTPUTS_DIR = REPO_ROOT / "outputs"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
DISCUSSIONS_RAW_PATH = INPUT_DIR / "pr_discussions_raw.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts888_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts888_failure.png"

REQUEST_STEPS = [
    "Launch the application at the default entry point.",
    "Locate the 'Settings' action in the primary navigation sidebar or top-bar.",
    "Click the 'Settings' action.",
    "Verify that the view transitions to the Settings surface.",
    "Verify that the 'Admin' tabs (Statuses, Workflows, etc.) are rendered and interactive.",
]
EXPECTED_RESULT = (
    "The navigation labels and buttons are functional, leading the user correctly "
    "to the administration workspace (AC2)."
)
PRIMARY_NAVIGATION_LABELS = (
    "Dashboard",
    "Board",
    "JQL Search",
    "Hierarchy",
    "Settings",
)
TAB_EXPECTATIONS = (
    (
        "Statuses",
        None,
        "Add status",
    ),
    (
        "Workflows",
        "Delivery Workflow ID: delivery-workflow • Statuses: todo, in-progress, in-review, done • Transitions: 4",
        "Add workflow",
    ),
    (
        "Issue Types",
        "Bug ID: bug • Workflow: delivery-workflow • Hierarchy level: 0",
        None,
    ),
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "steps": [],
        "human_verification": [],
    }

    try:
        if not token:
            raise RuntimeError(
                "TS-888 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            settings_page = LiveProjectSettingsPage(tracker_page)
            shell_page = LiveStartupRecoveryPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the Settings navigation scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                settings_page.dismiss_connection_banner()

                interactive_shell = tracker_page.observe_interactive_shell(
                    PRIMARY_NAVIGATION_LABELS,
                    timeout_ms=120_000,
                )
                result["interactive_shell_before_settings"] = interactive_shell
                if not interactive_shell.get("shell_ready"):
                    raise AssertionError(
                        "Step 1 failed: the hosted tracker shell never exposed all primary "
                        "navigation labels before the Settings navigation attempt.\n"
                        f"Observed shell: {json.dumps(interactive_shell, indent=2)}",
                    )

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed hosted tracker in a fresh Chromium browser "
                        "context and reached the default interactive app shell. "
                        f"Visible navigation labels={interactive_shell.get('visible_navigation_labels')!r}"
                    ),
                )

                visible_navigation_labels = interactive_shell.get(
                    "visible_navigation_labels",
                    [],
                )
                if "Settings" not in visible_navigation_labels:
                    raise AssertionError(
                        "Step 2 failed: the default app shell did not visibly expose the "
                        "Settings action in primary navigation.\n"
                        f"Observed shell: {json.dumps(interactive_shell, indent=2)}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "The primary navigation visibly included the Settings action "
                        f"alongside {visible_navigation_labels!r}."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the default app shell before interacting and checked that "
                        "Settings was visible as a primary navigation option."
                    ),
                    observed=(
                        f"Visible navigation labels={visible_navigation_labels!r}; "
                        f"visible body text={interactive_shell.get('body_text', '')!r}"
                    ),
                )

                settings_page.open_settings()
                settings_shell = shell_page.observe_shell()
                result["settings_shell_after_click"] = _shell_payload(settings_shell)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Activated the visible Settings navigation control. "
                        f"Selected navigation buttons={settings_shell.selected_button_labels!r}."
                    ),
                )

                _assert_settings_surface(settings_shell)
                settings_text = settings_page.body_text()
                result["settings_body_text"] = settings_text
                rendered_tab_labels = settings_page.rendered_tab_labels()
                result["rendered_tab_labels"] = rendered_tab_labels
                missing_tab_labels = [
                    label
                    for label, _, _ in TAB_EXPECTATIONS
                    if label not in rendered_tab_labels
                ]
                if missing_tab_labels:
                    raise AssertionError(
                        "Step 4 failed: the Settings surface opened, but not all expected "
                        "admin tab labels were rendered.\n"
                        f"Missing labels: {missing_tab_labels}\n"
                        f"Observed rendered tab labels: {rendered_tab_labels}\n"
                        f"Observed body text:\n{settings_text}",
                    )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "The app transitioned to Project Settings and selected Settings in "
                        "primary navigation. "
                        f"Selected buttons={settings_shell.selected_button_labels!r}; "
                        f"topbar_title_visible={settings_shell.topbar_title_visible}; "
                        f"settings_heading_visible={settings_shell.settings_heading_visible}; "
                        f"rendered_tab_labels={rendered_tab_labels!r}."
                    ),
                )

                tab_observations = []
                for label, expected_visible_text, signal_label in TAB_EXPECTATIONS:
                    observation = settings_page.observe_admin_tab(
                        label,
                        expected_visible_text=expected_visible_text,
                        signal_label=signal_label,
                    )
                    tab_observations.append(_tab_observation_payload(observation))

                result["tab_observations"] = tab_observations
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=REQUEST_STEPS[4],
                    observed=(
                        "The core admin tabs were rendered and interactive. "
                        f"Observed tab interactions={json.dumps(tab_observations, indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Clicked through the visible Settings admin tabs like a user and "
                        "confirmed each tab visibly switched the page content."
                    ),
                    observed=(
                        "Statuses showed Add status, Workflows showed Delivery Workflow, "
                        "and Issue Types showed the Bug workflow mapping while each tab "
                        "became the selected tab."
                    ),
                )

                settings_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                print("TS-888 passed")
                return
            except Exception as error:
                result.setdefault("error", _format_error(error))
                result.setdefault("traceback", traceback.format_exc())
                if not FAILURE_SCREENSHOT_PATH.exists():
                    settings_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise


def _assert_settings_surface(observation: StartupRecoveryShellObservation) -> None:
    if (
        observation.settings_selected
        and observation.topbar_title_visible
        and observation.settings_heading_visible
    ):
        return
    raise AssertionError(
        "Step 4 failed: clicking Settings did not visibly transition the user into the "
        "Project Settings administration surface.\n"
        f"Observed selected buttons: {observation.selected_button_labels}\n"
        f"Observed visible navigation labels: {observation.visible_navigation_labels}\n"
        f"Observed body text:\n{observation.body_text}",
    )


def _shell_payload(observation: StartupRecoveryShellObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "location_href": observation.location_href,
        "location_hash": observation.location_hash,
        "location_pathname": observation.location_pathname,
        "selected_button_labels": list(observation.selected_button_labels),
        "visible_navigation_labels": list(observation.visible_navigation_labels),
        "visible_button_labels": list(observation.visible_button_labels),
        "retry_visible": observation.retry_visible,
        "connect_github_visible": observation.connect_github_visible,
        "topbar_title_visible": observation.topbar_title_visible,
        "settings_heading_visible": observation.settings_heading_visible,
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
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


def _tab_observation_payload(observation) -> dict[str, object]:
    return {
        "tab": observation.label,
        "selected_tab": observation.selected_tab_label,
        "expected_visible_text": observation.expected_visible_text,
        "signal": observation.signal_text,
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
    RESPONSE_PATH.write_text(_tracker_rework_summary(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_comment_body(result, passed=True), encoding="utf-8")
    _write_review_replies(result, passed=True)


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-888 failed"))
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
    RESPONSE_PATH.write_text(
        _tracker_rework_summary(result, passed=False),
        encoding="utf-8",
    )
    PR_BODY_PATH.write_text(_pr_comment_body(result, passed=False), encoding="utf-8")
    _write_review_replies(result, passed=False)
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _tracker_rework_summary(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "h3. PR Rework Result",
        "",
        "*Fixed:* Added `testing/tests/TS-888/README.md` and moved Settings admin-tab label discovery/activation into `LiveProjectSettingsPage`, so `test_ts_888.py` now stays on page-object APIs.",
        f"*Test Run:* `{RUN_COMMAND}`",
        f"*Result:* {'✅ PASSED' if passed else '❌ FAILED'}",
    ]
    if passed:
        lines.append("*Summary:* 1 passed, 0 failed.")
    else:
        lines.extend(
            [
                "*Summary:* 0 passed, 1 failed.",
                f"*Error:* {result.get('error')}",
            ],
        )
    return "\n".join(lines).strip() + "\n"


def _pr_comment_body(result: dict[str, object], *, passed: bool) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{result.get('error')}`."
    )
    lines = [
        "## Rework completed",
        "",
        "- Added `testing/tests/TS-888/README.md` to satisfy the per-ticket folder requirements.",
        "- Moved Settings admin-tab label discovery and activation/verification into `LiveProjectSettingsPage`, so the test no longer reaches into Playwright session internals or raw DOM selectors.",
        f"- {rerun_summary}",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Failure details",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines).strip() + "\n"


def _write_review_replies(result: dict[str, object], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(result=result, passed=passed),
        }
        for thread in _discussion_threads()
    ]
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": replies}, indent=2) + "\n",
        encoding="utf-8",
    )


def _discussion_threads() -> list[dict[str, object]]:
    if not DISCUSSIONS_RAW_PATH.is_file():
        return []
    raw = json.loads(DISCUSSIONS_RAW_PATH.read_text(encoding="utf-8"))
    threads = raw.get("threads")
    if not isinstance(threads, list):
        return []
    return [
        thread
        for thread in threads
        if isinstance(thread, dict)
        and thread.get("resolved") is False
        and thread.get("rootCommentId") is not None
        and thread.get("threadId") is not None
    ]


def _review_reply_text(result: dict[str, object], *, passed: bool) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{result.get('error', 'unknown error')}`."
    )
    return (
        "Fixed: added `testing/tests/TS-888/README.md` and moved the Settings admin-tab "
        "label discovery plus activation/verification flow into `LiveProjectSettingsPage`, "
        "so `test_ts_888.py` now stays on reusable page-object APIs instead of raw "
        f"Playwright session and DOM selector work. {rerun_summary}"
    )


def _bug_description(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    step_map = {
        int(step["step"]): step
        for step in steps
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    lines = [
        f"h4. Environment",
        f"* URL: {result.get('app_url')}",
        "* Browser: Chromium via Playwright",
        f"* OS: {result.get('os')}",
        f"* Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        "",
        "h4. Steps to Reproduce",
    ]
    for index, action in enumerate(REQUEST_STEPS, start=1):
        observed = step_map.get(index, {}).get("observed", "<step did not complete>")
        status = step_map.get(index, {}).get("status")
        status_text = "PASSED ✅" if status == "passed" else "FAILED ❌"
        lines.extend(
            [
                f"# {action}",
                f"**Result:** {status_text}",
                f"**Observed:** {observed}",
            ],
        )
    lines.extend(
        [
            "",
            "h4. Expected Result",
            EXPECTED_RESULT,
            "",
            "h4. Actual Result",
            (
                "The hosted app did not complete the expected discoverable navigation into "
                "Project Settings and/or did not keep the admin tabs visibly interactive. "
                f"Latest visible shell snapshot: {json.dumps(result.get('settings_shell_after_click', result.get('interactive_shell_before_settings', {})), indent=2)}"
            ),
            "",
            "h4. Logs / Error Output",
            "{code}",
            str(result.get("traceback", result.get("error", "<missing>"))),
            "{code}",
            "",
            "h4. Notes",
            f"* Screenshot: {result.get('screenshot')}",
            (
                "* Human verification: "
                + "; ".join(
                    str(check.get("observed"))
                    for check in result.get("human_verification", [])
                    if isinstance(check, dict)
                )
            ),
        ],
    )
    return "\n".join(lines).strip() + "\n"


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


if __name__ == "__main__":
    main()
