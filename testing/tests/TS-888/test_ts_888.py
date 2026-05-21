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
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
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
        'flt-semantics[aria-label="Add status"]',
    ),
    (
        "Workflows",
        "Delivery Workflow ID: delivery-workflow • Statuses: todo, in-progress, in-review, done • Transitions: 4",
        'flt-semantics[aria-label="Add workflow"]',
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
                rendered_tab_labels = _settings_tab_labels(tracker_page)
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
                for label, expected_visible_text, visible_signal_selector in TAB_EXPECTATIONS:
                    tab_observations.append(
                        _activate_settings_tab(
                            tracker_page=tracker_page,
                            label=label,
                            required_text=expected_visible_text,
                            visible_signal_selector=visible_signal_selector,
                        ),
                    )

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


def _settings_tab_labels(tracker_page) -> list[str]:
    payload = tracker_page.session.evaluate(
        """
        () => Array.from(document.querySelectorAll('flt-semantics[role="tab"]'))
          .map((tab) => (tab.getAttribute('aria-label') ?? '').trim())
          .filter((label) => label.length > 0)
        """,
    )
    if not isinstance(payload, list):
        raise AssertionError(
            "Step 4 failed: the Settings surface did not expose readable admin tab labels.\n"
            f"Observed body text:\n{tracker_page.body_text()}",
        )
    return [str(item) for item in payload]


def _activate_settings_tab(
    *,
    tracker_page,
    label: str,
    required_text: str | None,
    visible_signal_selector: str | None,
) -> dict[str, object]:
    session = tracker_page.session
    selector = f'flt-semantics[role="tab"][aria-label="{label}"]'
    session.evaluate(
        "(value) => document.querySelector(value)?.scrollIntoView({ block: 'center' })",
        arg=selector,
    )
    rect = session.bounding_box(selector, timeout_ms=30_000)
    session.mouse_click(rect.x + (rect.width / 2), rect.y + (rect.height / 2))
    payload = session.wait_for_function(
        """
        ({ tabSelector, requiredText, visibleSignalSelector }) => {
          const tab = document.querySelector(tabSelector);
          if (!tab || tab.getAttribute('aria-selected') !== 'true') {
            return null;
          }
          const bodyText = document.body?.innerText ?? '';
          if (requiredText && !bodyText.includes(requiredText)) {
            return null;
          }
          let signalText = '';
          if (visibleSignalSelector) {
            const signal = document.querySelector(visibleSignalSelector);
            if (!signal) {
              return null;
            }
            const rect = signal.getBoundingClientRect();
            const style = window.getComputedStyle(signal);
            const isVisible = rect.width > 0
              && rect.height > 0
              && style.visibility !== 'hidden'
              && style.display !== 'none';
            if (!isVisible) {
              return null;
            }
            signalText = signal.getAttribute('aria-label')
              ?? signal.innerText
              ?? signal.textContent
              ?? '';
          }
          return {
            selectedTab: tab.getAttribute('aria-label') ?? '',
            bodyText,
            signalText,
          };
        }
        """,
        arg={
            "tabSelector": selector,
            "requiredText": required_text,
            "visibleSignalSelector": visible_signal_selector,
        },
        timeout_ms=30_000,
    )
    if not isinstance(payload, dict):
        raise AssertionError(
            "Step 5 failed: the Settings admin tab did not become visibly active.\n"
            f"Tab: {label}\n"
            f"Observed body text:\n{tracker_page.body_text()}",
        )
    selected_tab = str(payload.get("selectedTab", "")).strip()
    if selected_tab != label:
        raise AssertionError(
            "Step 5 failed: clicking the Settings admin tab did not change the selected "
            "tab.\n"
            f"Expected selected tab: {label}\n"
            f"Observed selected tab: {selected_tab}\n"
            f"Observed body text:\n{tracker_page.body_text()}",
        )
    return {
        "tab": label,
        "selected_tab": selected_tab,
        "expected_visible_text": required_text,
        "signal": str(payload.get("signalText", "")).strip(),
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
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")


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
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {'✅ PASSED' if passed else '❌ FAILED'}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        "* Discoverable navigation from the default hosted app shell to Project Settings.",
        "* Visibility of the Settings primary navigation action before interaction.",
        "* Visible transition into the administration workspace and interactivity of the Statuses, Workflows, and Issue Types tabs.",
        "",
        "h4. Result",
    ]
    for step in result.get("steps", []):
        assert isinstance(step, dict)
        emoji = "(/)" if step.get("status") == "passed" else "(x)"
        lines.append(
            f"{emoji} *Step {step.get('step')}* {step.get('action')}\n"
            f"Observed: {step.get('observed')}"
        )
    lines.extend(("", "h4. Human-style verification"))
    for check in result.get("human_verification", []):
        assert isinstance(check, dict)
        lines.append(f"* {check.get('check')}\nObserved: {check.get('observed')}")
    lines.extend(
        [
            "",
            "h4. Test file",
            "{code}",
            "testing/tests/TS-888/test_ts_888.py",
            "{code}",
            "",
            "h4. Run command",
            "{code:bash}",
            RUN_COMMAND,
            "{code}",
        ],
    )
    if not passed:
        lines.extend(
            [
                "",
                "h4. Failure details",
                f"* Error: {result.get('error')}",
                f"* Screenshot: {result.get('screenshot')}",
            ],
        )
    return "\n".join(lines).strip() + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium using the live hosted tracker harness.",
        "- Verified the default shell visibly exposed the Settings primary navigation action.",
        "- Clicked Settings and checked the Statuses, Workflows, and Issue Types tabs switch visibly.",
        "",
        "## Result",
    ]
    for step in result.get("steps", []):
        assert isinstance(step, dict)
        status = "passed" if step.get("status") == "passed" else "failed"
        lines.append(
            f"- **Step {step.get('step')} ({status})** {step.get('action')}  \n"
            f"  Observed: {step.get('observed')}"
        )
    lines.extend(("", "## Human-style verification"))
    for check in result.get("human_verification", []):
        assert isinstance(check, dict)
        lines.append(f"- **Check:** {check.get('check')}  \n  Observed: {check.get('observed')}")
    lines.extend(
        [
            "",
            "## How to run",
            "```bash",
            RUN_COMMAND,
            "```",
        ],
    )
    if not passed:
        lines.extend(
            [
                "",
                "## Failure details",
                f"- **Error:** {result.get('error')}",
                f"- **Screenshot:** `{result.get('screenshot')}`",
            ],
        )
    return "\n".join(lines).strip() + "\n"


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
