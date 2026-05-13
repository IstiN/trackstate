from __future__ import annotations

import json
import platform
import sys
import traceback
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_project_settings_page import (  # noqa: E402
    LiveProjectSettingsPage,
    RepositoryAccessActivationObservation,
    RepositoryAccessControlsObservation,
    RepositoryAccessFocusObservation,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-617"
RUN_COMMAND = "PYTHONPATH=. python3 testing/tests/TS-617/test_ts_617.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts617_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts617_failure.png"
CONNECTION_ERROR_PREFIX = "GitHub connection failed:"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-617 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    connected_banner = TrackStateTrackerPage.CONNECTED_BANNER_TEMPLATE.format(
        user_login=user.login,
        repository=service.repository,
    )
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
        "activation_results": [],
        "precondition_token_available": True,
    }

    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            settings_page = LiveProjectSettingsPage(tracker_page)
            try:
                initial_runtime = tracker_page.open()
                result["runtime_state"] = initial_runtime.kind
                result["runtime_body_text"] = initial_runtime.body_text
                if initial_runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the Repository access keyboard activation scenario "
                        "started.\n"
                        f"Observed body text:\n{initial_runtime.body_text}",
                    )

                connected_text = settings_page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                result["initial_connected_text"] = connected_text
                settings_page.dismiss_connection_banner()

                enter_observation = _exercise_keyboard_activation(
                    result=result,
                    settings_page=settings_page,
                    token=token,
                    connected_banner=connected_banner,
                    key="Enter",
                    navigation_step=1,
                    focus_step=2,
                    press_step=3,
                    observe_step=4,
                    combine_navigation_and_focus=False,
                )
                _append_activation_result(result, enter_observation)
                _record_human_verification(
                    result,
                    check=(
                        "Verified as a keyboard user that the visible Repository access "
                        "section kept the Fine-grained token field, Remember on this "
                        "browser checkbox, and Connect token button together before the "
                        "Enter activation."
                    ),
                    observed=(
                        f"visible_controls={_visible_controls_from_activation(enter_observation)}; "
                        f"focus_path={_focus_path_from_activation(enter_observation)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the user-visible response after pressing Enter on the "
                        "focused Connect token button."
                    ),
                    observed=str(enter_observation["feedback_text"]),
                )

                tracker_page.session.goto(
                    config.app_url,
                    wait_until="domcontentloaded",
                    timeout_ms=120_000,
                )
                tracker_page.session.activate_accessibility()
                refreshed_runtime = tracker_page.open()
                result["refreshed_runtime_state"] = refreshed_runtime.kind
                result["refreshed_runtime_body_text"] = refreshed_runtime.body_text
                if refreshed_runtime.kind != "ready":
                    raise AssertionError(
                        "Step 5 failed: refreshing the deployed app did not return to an "
                        "interactive hosted shell before retrying keyboard activation.\n"
                        f"Observed body text:\n{refreshed_runtime.body_text}",
                    )

                refreshed_settings_page = LiveProjectSettingsPage(tracker_page)
                space_observation = _exercise_keyboard_activation(
                    result=result,
                    settings_page=refreshed_settings_page,
                    token=token,
                    connected_banner=connected_banner,
                    key="Space",
                    navigation_step=5,
                    focus_step=5,
                    press_step=6,
                    observe_step=7,
                    combine_navigation_and_focus=True,
                )
                _append_activation_result(result, space_observation)
                _record_human_verification(
                    result,
                    check=(
                        "Verified the page refresh still left the same visible Repository "
                        "access labels in place before retrying keyboard activation."
                    ),
                    observed=(
                        f"visible_controls={_visible_controls_from_activation(space_observation)}; "
                        f"focus_path={_focus_path_from_activation(space_observation)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the user-visible response after pressing Space on the "
                        "focused Connect token button."
                    ),
                    observed=str(space_observation["feedback_text"]),
                )

                refreshed_settings_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                settings_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
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
    print("TS-617 passed")


def _exercise_keyboard_activation(
    *,
    result: dict[str, object],
    settings_page: LiveProjectSettingsPage,
    token: str,
    connected_banner: str,
    key: str,
    navigation_step: int,
    focus_step: int,
    press_step: int,
    observe_step: int,
    combine_navigation_and_focus: bool,
) -> dict[str, object]:
    settings_body = settings_page.open_settings()
    controls = settings_page.observe_repository_access_controls()
    _assert_visible_controls(controls, step=navigation_step)
    return _exercise_keyboard_activation_with_result(
        result=result,
        settings_page=settings_page,
        token=token,
        connected_banner=connected_banner,
        key=key,
        navigation_step=navigation_step,
        focus_step=focus_step,
        press_step=press_step,
        observe_step=observe_step,
        settings_body=settings_body,
        controls=controls,
        combine_navigation_and_focus=combine_navigation_and_focus,
    )


def _exercise_keyboard_activation_with_result(
    *,
    result: dict[str, object],
    settings_page: LiveProjectSettingsPage,
    token: str,
    connected_banner: str,
    key: str,
    navigation_step: int,
    focus_step: int,
    press_step: int,
    observe_step: int,
    settings_body: str,
    controls: RepositoryAccessControlsObservation,
    combine_navigation_and_focus: bool,
) -> dict[str, object]:
    focus_sequence = _focus_connect_token(
        settings_page=settings_page,
        token=token,
        step=focus_step,
    )
    final_focus = focus_sequence[-1]
    navigation_observed = (
        f"project_settings_visible={controls.project_settings_visible}; "
        f"repository_access_visible={controls.repository_access_visible}; "
        f"visible_controls={_visible_controls_summary(controls)}"
    )
    focus_observed = _focus_path_summary(focus_sequence)
    if combine_navigation_and_focus:
        _record_step(
            result,
            step=navigation_step,
            status="passed",
            action="Refresh the page and repeat steps 1-2.",
            observed=f"{navigation_observed}; focus_path={focus_observed}",
        )
    else:
        _record_step(
            result,
            step=navigation_step,
            status="passed",
            action="Navigate to Project Settings → Repository access.",
            observed=navigation_observed,
        )
        _record_step(
            result,
            step=focus_step,
            status="passed",
            action="Press the Tab key until the focus indicator is on the Connect token button.",
            observed=focus_observed,
        )

    settings_page.wait_for_repository_access_feedback_absence(
        [connected_banner, CONNECTION_ERROR_PREFIX],
        timeout_ms=5_000,
    )
    activation_observation = settings_page.activate_focused_repository_access_connect_token(
        key=key,
        feedback_texts=[connected_banner, CONNECTION_ERROR_PREFIX],
        connected_banner_text=connected_banner,
        timeout_ms=120_000,
    )
    _record_step(
        result,
        step=press_step,
        status="passed",
        action="Press the Enter key." if key == "Enter" else "Press the Space bar.",
        observed=f"{_focus_summary(final_focus)}; pre_press_feedback_absent=True",
    )
    _record_step(
        result,
        step=observe_step,
        status="passed",
        action="Observe the application behavior.",
        observed=_activation_feedback_summary(activation_observation),
    )

    if settings_page.body_text().count(connected_banner):
        settings_page.dismiss_connection_banner()

    return {
        "key": key,
        "settings_body": settings_body,
        "controls": asdict(controls),
        "focus_sequence": [asdict_focus(item) for item in focus_sequence],
        "section_text": controls.section_text or controls.body_text,
        "feedback_kind": activation_observation.response_kind,
        "feedback_text": activation_observation.response_text,
        "matched_feedback": activation_observation.matched_text,
        "body_text_before_activation": activation_observation.body_text_before,
        "body_text_after_activation": activation_observation.body_text_after,
    }


def _assert_visible_controls(
    controls: RepositoryAccessControlsObservation,
    *,
    step: int,
) -> None:
    if (
        controls.project_settings_visible
        and controls.repository_access_visible
        and controls.fine_grained_token_visible
        and controls.remember_on_this_browser_visible
        and controls.connect_token_visible
    ):
        return
    raise AssertionError(
        f"Step {step} failed: the hosted Project Settings screen did not expose the "
        "visible Repository access controls required by the test case.\n"
        f"Observed controls: {asdict(controls)}\n"
        f"Observed body text:\n{controls.body_text}",
    )


def _focus_connect_token(
    *,
    settings_page: LiveProjectSettingsPage,
    token: str,
    step: int,
) -> list[RepositoryAccessFocusObservation]:
    try:
        return settings_page.focus_repository_access_connect_token_via_keyboard(
            token=token,
            timeout_ms=30_000,
        )
    except AssertionError as error:
        raise AssertionError(
            f"Step {step} failed: tabbing through the visible Repository access controls "
            "did not leave focus on the Connect token button.\n"
            f"{error}",
        ) from None


def _append_activation_result(
    result: dict[str, object],
    activation: dict[str, object],
) -> None:
    activations = result.setdefault("activation_results", [])
    assert isinstance(activations, list)
    activations.append(activation)


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
        }
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


def asdict_focus(observation: RepositoryAccessFocusObservation) -> dict[str, object]:
    return {
        "label": observation.label,
        "tag_name": observation.tag_name,
        "role": observation.role,
        "accessible_name": observation.accessible_name,
        "text": observation.text,
        "outer_html": observation.outer_html,
    }


def _visible_controls_summary(observation: RepositoryAccessControlsObservation) -> str:
    visible = []
    if observation.fine_grained_token_visible:
        visible.append("Fine-grained token")
    if observation.remember_on_this_browser_visible:
        visible.append("Remember on this browser")
    if observation.connect_token_visible:
        visible.append("Connect token")
    return ", ".join(visible) if visible else "<none>"


def _focus_summary(observation: RepositoryAccessFocusObservation) -> str:
    return (
        f"focused_label={observation.label}; "
        f"tag={observation.tag_name}; "
        f"role={observation.role}; "
        f"accessible_name={observation.accessible_name!r}"
    )


def _focus_path_summary(sequence: list[RepositoryAccessFocusObservation]) -> str:
    labels = [item.label or "<unknown>" for item in sequence]
    return " -> ".join(labels)


def _activation_feedback_summary(
    observation: RepositoryAccessActivationObservation,
) -> str:
    return (
        f"feedback_kind={observation.response_kind}; "
        f"feedback_text={observation.response_text}"
    )


def _visible_controls_from_activation(activation: dict[str, object]) -> str:
    controls = activation.get("controls", {})
    if not isinstance(controls, dict):
        return "<unknown>"
    visible = []
    if controls.get("fine_grained_token_visible"):
        visible.append("Fine-grained token")
    if controls.get("remember_on_this_browser_visible"):
        visible.append("Remember on this browser")
    if controls.get("connect_token_visible"):
        visible.append("Connect token")
    return ", ".join(visible) if visible else "<none>"


def _focus_path_from_activation(activation: dict[str, object]) -> str:
    sequence = activation.get("focus_sequence", [])
    if not isinstance(sequence, list):
        return "<unknown>"
    labels = []
    for item in sequence:
        if isinstance(item, dict):
            labels.append(str(item.get("label", "<unknown>")))
    return " -> ".join(labels) if labels else "<unknown>"


def _activation_by_key(result: dict[str, object], key: str) -> dict[str, object]:
    for activation in result.get("activation_results", []):
        if isinstance(activation, dict) and str(activation.get("key")) == key:
            return activation
    return {}


def _activation_feedback_detail(result: dict[str, object], key: str) -> str:
    activation = _activation_by_key(result, key)
    if not activation:
        return f"{key}: <not recorded>"
    feedback_kind = str(activation.get("feedback_kind", "feedback"))
    feedback_text = _snippet(activation.get("feedback_text", "<not recorded>"))
    return f"{key}: {feedback_kind} ({feedback_text})"


def _pass_result_summary(result: dict[str, object], *, jira: bool) -> str:
    enter_feedback = _activation_feedback_detail(result, "Enter")
    space_feedback = _activation_feedback_detail(result, "Space")
    if jira:
        return (
            "* Matched the expected result: both keyboard activations surfaced visible "
            "connection feedback after the focused {{Connect token}} button was triggered "
            f"({{{{{enter_feedback}}}}}; {{{{{space_feedback}}}}}), confirming the button "
            "behaves like a standard interactive element."
        )
    return (
        "- Matched the expected result: both keyboard activations surfaced visible "
        "connection feedback after the focused `Connect token` button was triggered "
        f"(`{enter_feedback}`; `{space_feedback}`), confirming the button behaves like a "
        "standard interactive element."
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
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")
    _write_review_replies()


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
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    _write_review_replies()


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            "* Opened the deployed hosted TrackState app in Chromium using the configured "
            "GitHub token and navigated to *Project Settings → Repository access*."
        ),
        (
            "* Verified the visible repository-access controls included {{Fine-grained "
            "token}}, {{Remember on this browser}}, and {{Connect token}} in the same "
            "section."
        ),
        (
            "* Entered a valid token, used keyboard Tab navigation to move focus onto "
            "the visible {{Connect token}} button, then activated it with {{Enter}}."
        ),
        (
            "* Refreshed the page, repeated the same keyboard navigation, then activated "
            "the focused {{Connect token}} button with {{Space}}."
        ),
        "",
        "*Observed result*",
        (
            _pass_result_summary(result, jira=True)
            if passed
            else "* Did not match the expected result: a focused-button keyboard activation did not surface new visible connection feedback."
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
            ]
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Rework",
        "- Relaxed the assertion so the test passes on any visible connection feedback caused by the focused-button keyboard activation, including success and error feedback.",
        "- Added a pre-press absence check for connection feedback before each Enter/Space activation so the observed response is causally tied to that key press.",
        "- Moved token entry, keyboard focus traversal, and focused-button activation behind `LiveProjectSettingsPage`.",
        "",
        "### Automation",
        (
            "- Opened the deployed hosted TrackState app in Chromium using the configured "
            "GitHub token and navigated to `Project Settings → Repository access`."
        ),
        (
            "- Verified the visible repository-access controls included `Fine-grained "
            "token`, `Remember on this browser`, and `Connect token` in the same section."
        ),
        (
            "- Entered a valid token, used keyboard Tab navigation to move focus onto the "
            "visible `Connect token` button, then activated it with `Enter`."
        ),
        (
            "- Refreshed the page, repeated the same keyboard navigation, then activated "
            "the focused `Connect token` button with `Space`."
        ),
        "",
        "### Observed result",
        (
            _pass_result_summary(result, jira=False)
            if passed
            else "- Did not match the expected result: a focused-button keyboard activation did not surface new visible connection feedback."
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
            ]
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"# {TICKET_KEY} rework {status}",
        "",
        "- Fixed the assertion to accept any visible connection feedback triggered by the focused `Connect token` button instead of only the success banner.",
        "- Added a pre-press absence check so each Enter/Space observation is tied to a new keyboard-triggered response.",
        "- Moved Repository access token entry, keyboard focus traversal, and focused-button activation into `LiveProjectSettingsPage`.",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
    ]
    if passed:
        lines.append(f"- Result: {_activation_feedback_detail(result, 'Enter')}; {_activation_feedback_detail(result, 'Space')}")
    else:
        lines.extend(
            [
                "- Result: failed because a focused-button keyboard activation did not surface new visible connection feedback.",
                "",
                "## Error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _write_review_replies() -> None:
    REVIEW_REPLIES_PATH.write_text(
        json.dumps(
            {
                "replies": [
                    {
                        "inReplyToId": 3235710279,
                        "threadId": "PRRT_kwDOSU6Gf86B0MG1",
                        "reply": (
                            "Fixed: the test now waits for visible connection feedback triggered by the focused `Connect token` keyboard activation and accepts either the success banner or a visible `GitHub connection failed:` error instead of requiring only the connected banner."
                        ),
                    },
                    {
                        "inReplyToId": 3235710462,
                        "threadId": "PRRT_kwDOSU6Gf86B0MJG",
                        "reply": (
                            "Fixed: each Enter/Space run now first proves the success/error feedback is absent before the key press, then waits for new visible feedback after that activation so the pass condition is causally linked to the keyboard event."
                        ),
                    },
                    {
                        "inReplyToId": 3235710722,
                        "threadId": "PRRT_kwDOSU6Gf86B0MMH",
                        "reply": (
                            "Fixed: token entry, Repository access keyboard traversal, pre-press feedback checks, and focused-button activation now live on `LiveProjectSettingsPage`, so the test stays at the business-action layer."
                        ),
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            "# TS-617 - Focused Connect token button does not surface visible keyboard feedback",
            "",
            "## Steps to reproduce",
            "1. Navigate to Project Settings → Repository access.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Press Tab until the focus indicator is on the Connect token button.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Press the Enter key.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "4. Observe the application behavior.",
            f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
            "5. Refresh the page and repeat steps 1-2.",
            f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
            "6. Press the Space bar.",
            f"   - {'✅' if _step_status(result, 6) == 'passed' else '❌'} {_step_observation(result, 6)}",
            "7. Observe the application behavior.",
            f"   - {'✅' if _step_status(result, 7) == 'passed' else '❌'} {_step_observation(result, 7)}",
            "",
            "## Actual vs Expected",
            (
                "- Expected: after keyboard focus reaches the visible `Connect token` "
                "button in Project Settings → Repository access, both `Enter` and `Space` "
                "should initiate the connection flow and surface user-visible connection "
                "feedback such as a success banner or a visible `GitHub connection failed:` error."
            ),
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the focused Connect token button did not surface new visible "
                    "connection feedback after keyboard activation."
                )
            ),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment details",
            f"- Command: `{RUN_COMMAND}`",
            f"- URL: `{result['app_url']}`",
            f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
            f"- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.platform()}`",
            "",
            "## Missing or broken production capability",
            "- The hosted Repository access flow does not expose new visible connection feedback after keyboard activation of the focused `Connect token` button.",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
            "### Activation observations",
            "```json",
            json.dumps(result.get("activation_results", []), indent=2),
            "```",
            "### Runtime body text",
            "```text",
            str(result.get("runtime_body_text", "")),
            "```",
            "### Refreshed runtime body text",
            "```text",
            str(result.get("refreshed_runtime_body_text", "")),
            "```",
        ]
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        status = str(step.get("status", "failed"))
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — "
            f"{status.upper() if jira else status}: {step['observed']}"
        )
    if not lines:
        lines.append(
            "# No step details were recorded."
            if jira
            else "1. No step details were recorded."
        )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(f"{prefix} {check.get('check')}: {check.get('observed')}")
    if not lines:
        lines.append(
            "# No human-style verification data was recorded."
            if jira
            else "1. No human-style verification data was recorded."
        )
    return lines


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("observed", "No observation recorded."))
    previous_step = step_number - 1
    if previous_step >= 1 and _step_status(result, previous_step) != "passed":
        return (
            f"Not reached because Step {previous_step} failed: "
            f"{_step_observation(result, previous_step)}"
        )
    return str(result.get("error", "No observation recorded."))


def _snippet(value: object, *, limit: int = 400) -> str:
    collapsed = " ".join(str(value).split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


if __name__ == "__main__":
    main()
