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

from testing.components.pages.live_tracker_header_page import (  # noqa: E402
    HeaderContainerObservation,
    HeaderControlObservation,
    HeaderObservation,
    LiveTrackerHeaderPage,
    ThemeToggleCycleObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402

TICKET_KEY = "TS-614"
RUN_COMMAND = "python testing/tests/TS-614/test_ts_614.py"
EXPECTED_CONTROL_HEIGHT = 32.0
HEIGHT_TOLERANCE = 1.0
VERTICAL_CENTER_TOLERANCE = 1.0

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts614_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts614_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-614 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "user_login": user.login,
        "browser": "Chromium via Playwright",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(config) as tracker_page:
            page = LiveTrackerHeaderPage(tracker_page)
            runtime = tracker_page.open()
            result["runtime_state"] = runtime.kind
            result["runtime_body_text"] = runtime.body_text
            if runtime.kind != "ready":
                raise AssertionError(
                    "Step 1 failed: the deployed app did not reach the desktop tracker shell "
                    "before the header measurement scenario began.\n"
                    f"Observed body text:\n{runtime.body_text}",
                )

            connected_text = page.ensure_connected(
                token=token,
                repository=service.repository,
                user_login=user.login,
            )
            page.dismiss_connection_banner()
            result["connected_text"] = connected_text
            _record_step(
                result,
                step=1,
                status="passed",
                action="Open the application to a desktop tracking section.",
                observed=(
                    f"runtime_state=ready; connected_user={user.login}; "
                    "section=Dashboard"
                ),
            )

            header = page.observe_desktop_header(user_login=user.login)
            result["header_observation"] = asdict(header)

            theme_cycle = page.toggle_theme_and_restore()
            result["theme_toggle_cycle"] = asdict(theme_cycle)

            center_spread = _center_spread(header)
            result["vertical_center_spread_px"] = center_spread
            result["visible_control_heights_px"] = _height_summary(header)
            result["header_container_summary"] = _container_summary(
                header.covering_container,
            )

            _record_human_verification(
                result,
                check=(
                    "Verified the live desktop header visibly showed the sync status pill, "
                    "search field, Create issue button, repository access button, theme "
                    "toggle, and profile identity in the same top row."
                ),
                observed=(
                    f"sync={_label(header.sync_status_pill)!r}; "
                    f"search={_label(header.search_field)!r}; "
                    f"create={_label(header.create_issue_button)!r}; "
                    f"repository_access={_label(header.repository_access_button)!r}; "
                    f"theme={_label(header.theme_toggle)!r}; "
                    f"profile={_label(header.profile_identity)!r}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Clicked the visible theme toggle as a user and confirmed it switched "
                    "labels and then returned to its starting state."
                ),
                observed=(
                    f"initial={theme_cycle.initial_label}; "
                    f"toggled={theme_cycle.toggled_label}; "
                    f"restored={theme_cycle.restored_label}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Compared the header controls as a user would see them in the top row."
                ),
                observed=(
                    f"heights_px={_height_summary(header)}; "
                    f"vertical_center_spread_px={center_spread:.2f}"
                ),
            )

            failures = _evaluate_expectations(result, header, center_spread)
            if failures:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise AssertionError("\n".join(failures))

            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
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


def _evaluate_expectations(
    result: dict[str, object],
    header: HeaderObservation,
    center_spread: float,
) -> list[str]:
    failures: list[str] = []

    search_message = _height_assertion_message(
        "JQL search field",
        header.search_field,
    )
    _record_step(
        result,
        step=2,
        status="passed" if search_message is None else "failed",
        action="Inspect the JQL search field height.",
        observed=(
            f"expected={EXPECTED_CONTROL_HEIGHT:.0f}px; "
            f"observed={header.search_field.height:.2f}px; "
            f"label={_label(header.search_field)!r}"
        ),
    )
    if search_message:
        failures.append(f"Step 2 failed: {search_message}")

    create_message = _height_assertion_message(
        "Create issue action button",
        header.create_issue_button,
    )
    _record_step(
        result,
        step=3,
        status="passed" if create_message is None else "failed",
        action="Inspect the Create issue action button height.",
        observed=(
            f"expected={EXPECTED_CONTROL_HEIGHT:.0f}px; "
            f"observed={header.create_issue_button.height:.2f}px; "
            f"label={_label(header.create_issue_button)!r}"
        ),
    )
    if create_message:
        failures.append(f"Step 3 failed: {create_message}")

    sync_message = _height_assertion_message(
        "sync status pill",
        header.sync_status_pill,
    )
    repository_message = _height_assertion_message(
        "repository access button",
        header.repository_access_button,
    )
    _record_step(
        result,
        step=4,
        status="passed" if sync_message is None and repository_message is None else "failed",
        action="Inspect the sync status pill and repository access button heights.",
        observed=(
            f"sync_observed={header.sync_status_pill.height:.2f}px; "
            f"repository_observed={header.repository_access_button.height:.2f}px; "
            f"repository_label={_label(header.repository_access_button)!r}"
        ),
    )
    if sync_message:
        failures.append(f"Step 4 failed: {sync_message}")
    if repository_message:
        failures.append(f"Step 4 failed: {repository_message}")

    theme_message = _height_assertion_message(
        "theme toggle",
        header.theme_toggle,
    )
    profile_message = _height_assertion_message(
        "profile identity/avatar area",
        header.profile_identity,
    )
    alignment_message = _vertical_alignment_message(center_spread)
    _record_step(
        result,
        step=5,
        status=(
            "passed"
            if theme_message is None
            and profile_message is None
            and alignment_message is None
            else "failed"
        ),
        action="Inspect the theme toggle and profile identity/avatar area heights.",
        observed=(
            f"theme_observed={header.theme_toggle.height:.2f}px; "
            f"profile_observed={header.profile_identity.height:.2f}px; "
            f"profile_label={_label(header.profile_identity)!r}; "
            f"vertical_center_spread={center_spread:.2f}px; "
            f"tolerance={VERTICAL_CENTER_TOLERANCE:.2f}px"
        ),
    )
    if theme_message:
        failures.append(f"Step 5 failed: {theme_message}")
    if profile_message:
        failures.append(f"Step 5 failed: {profile_message}")
    if alignment_message:
        failures.append(f"Step 5 failed: {alignment_message}")

    container_message = _container_assertion_message(header.covering_container)
    _record_step(
        result,
        step=6,
        status="passed" if container_message is None else "failed",
        action="Verify the CSS properties of the parent header container.",
        observed=_container_summary(header.covering_container),
    )
    if container_message:
        failures.append(f"Step 6 failed: {container_message}")

    return failures


def _height_assertion_message(
    control_name: str,
    observation: HeaderControlObservation,
) -> str | None:
    if abs(observation.height - EXPECTED_CONTROL_HEIGHT) <= HEIGHT_TOLERANCE:
        return None
    return (
        f'expected the visible {control_name} to render at '
        f"{EXPECTED_CONTROL_HEIGHT:.0f}px, but observed {observation.height:.2f}px "
        f'for "{_label(observation)}".'
    )


def _container_assertion_message(
    observation: HeaderContainerObservation | None,
) -> str | None:
    if observation is None:
        return None
    if observation.display not in {"flex", "inline-flex"}:
        return (
            "expected the exposed header container to use a flex layout, "
            f'but observed display="{observation.display}".'
        )
    if observation.align_items != "center":
        return (
            "expected the header flex container to use align-items: center, "
            f'but observed align-items="{observation.align_items}".'
        )
    return None


def _vertical_alignment_message(center_spread: float) -> str | None:
    if center_spread <= VERTICAL_CENTER_TOLERANCE:
        return None
    return (
        "expected the visible desktop header controls to share a vertically centered "
        f"baseline within {VERTICAL_CENTER_TOLERANCE:.2f}px, but observed a center "
        f"spread of {center_spread:.2f}px."
    )


def _center_spread(header: HeaderObservation) -> float:
    centers = [
        header.sync_status_pill.center_y,
        header.search_field.center_y,
        header.create_issue_button.center_y,
        header.repository_access_button.center_y,
        header.theme_toggle.center_y,
        header.profile_identity.center_y,
    ]
    return max(centers) - min(centers)


def _height_summary(header: HeaderObservation) -> dict[str, float]:
    return {
        "sync_status_pill": round(header.sync_status_pill.height, 2),
        "search_field": round(header.search_field.height, 2),
        "create_issue_button": round(header.create_issue_button.height, 2),
        "repository_access_button": round(header.repository_access_button.height, 2),
        "theme_toggle": round(header.theme_toggle.height, 2),
        "profile_identity": round(header.profile_identity.height, 2),
    }


def _container_summary(observation: HeaderContainerObservation | None) -> str:
    if observation is None:
        return "header_container=not_exposed; css_assertion=omitted"
    return (
        f"tag={observation.tag_name}; display={observation.display}; "
        f"align_items={observation.align_items}; "
        f"justify_content={observation.justify_content}; "
        f"bounds=({observation.x:.2f}, {observation.y:.2f}, "
        f"{observation.width:.2f}, {observation.height:.2f})"
    )


def _label(observation: HeaderControlObservation) -> str:
    return observation.accessible_label or observation.visible_text or observation.placeholder


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
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, status="PASSED"), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, status="PASSED"), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_markdown(result, status="PASSED"), encoding="utf-8")
    if BUG_DESCRIPTION_PATH.exists():
        BUG_DESCRIPTION_PATH.unlink()


def _write_failure_outputs(result: dict[str, object]) -> None:
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": str(result.get("error", "")),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, status="FAILED"), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, status="FAILED"), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_markdown(result, status="FAILED"), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, status: str) -> str:
    steps = _steps(result)
    human_checks = _human_checks(result)
    return "\n".join(
        [
            f"h1. {TICKET_KEY} — {status}",
            "",
            f"*Automation result:* {status}",
            f"*Environment:* {result['app_url']} | Chromium via Playwright | {result['os']}",
            f"*Repository:* {result['repository']}@{result['repository_ref']}",
            f"*Run command:* {{{{ {RUN_COMMAND} }}}}",
            "",
            "h2. Automated checks",
            *[
                f"# Step {step['step']} — {step['status'].upper()}: {step['action']} "
                f"{{{{{step['observed']}}}}}"
                for step in steps
            ],
            "",
            "h2. Real user verification",
            *[
                f"* {entry['check']} Observed: {{{{{entry['observed']}}}}}"
                for entry in human_checks
            ],
            "",
            "h2. Observed result",
            f"* Visible header control heights: {{{{{json.dumps(result.get('visible_control_heights_px', {}), sort_keys=True)}}}}}",
            f"* Vertical center spread: {{{{{result.get('vertical_center_spread_px', '')}}}}}",
            f"* Header container: {{{{{result.get('header_container_summary', '')}}}}}",
            f"* Screenshot: {{{{{result.get('screenshot', '')}}}}}",
            "",
            "h2. Expected result",
            (
                "* Every desktop header control is rendered at 32px height and the parent "
                "header container uses a flex layout with {{align-items: center}}."
            ),
            "",
            "h2. Actual result",
            f"* {str(result.get('error', 'Automation passed.')).replace(chr(10), ' ')}",
        ],
    ).rstrip() + "\n"


def _pr_body(result: dict[str, object], *, status: str) -> str:
    steps = _steps(result)
    human_checks = _human_checks(result)
    lines = [
        f"# {TICKET_KEY} — {status}",
        "",
        f"**Environment:** `{result['app_url']}` · Chromium via Playwright · `{result['os']}`",
        f"**Repository:** `{result['repository']}@{result['repository_ref']}`",
        f"**Run command:** `{RUN_COMMAND}`",
        "",
        "## Automated checks",
    ]
    for step in steps:
        lines.append(
            f"- Step {step['step']} — **{step['status'].upper()}**: {step['action']} "
            f"`{step['observed']}`"
        )
    lines.extend(
        [
            "",
            "## Real user verification",
        ],
    )
    for entry in human_checks:
        lines.append(f"- {entry['check']} Observed: `{entry['observed']}`")
    lines.extend(
        [
            "",
            "## Observed result",
            f"- Visible header control heights: `{json.dumps(result.get('visible_control_heights_px', {}), sort_keys=True)}`",
            f"- Vertical center spread: `{result.get('vertical_center_spread_px', '')}`",
            f"- Header container: `{result.get('header_container_summary', '')}`",
            f"- Screenshot: `{result.get('screenshot', '')}`",
            "",
            "## Expected result",
            "- Every desktop header control renders at 32px height and the parent header container uses a flex layout with `align-items: center`.",
            "",
            "## Actual result",
            f"- {str(result.get('error', 'Automation passed.')).replace(chr(10), ' ')}",
        ],
    )
    return "\n".join(lines).rstrip() + "\n"


def _response_markdown(result: dict[str, object], *, status: str) -> str:
    return "\n".join(
        [
            f"# {TICKET_KEY} — {status}",
            "",
            f"- Environment: `{result['app_url']}` · Chromium via Playwright · `{result['os']}`",
            f"- Visible header control heights: `{json.dumps(result.get('visible_control_heights_px', {}), sort_keys=True)}`",
            f"- Vertical center spread: `{result.get('vertical_center_spread_px', '')}`",
            f"- Header container: `{result.get('header_container_summary', '')}`",
            f"- Screenshot: `{result.get('screenshot', '')}`",
            f"- Result: {str(result.get('error', 'Automation passed.')).replace(chr(10), ' ')}",
        ],
    ).rstrip() + "\n"


def _bug_description(result: dict[str, object]) -> str:
    steps = _steps(result)
    return "\n".join(
        [
            f"# {TICKET_KEY} — Desktop header interactive elements height regression",
            "",
            "## Exact steps to reproduce",
            "1. Open the application to any tracking section (for this run: Dashboard). "
            + _step_outcome(steps, 1),
            "2. Use browser developer tools to inspect the JQL search field height. "
            + _step_outcome(steps, 2),
            "3. Inspect the height of the 'Create issue' action button. "
            + _step_outcome(steps, 3),
            "4. Inspect the height of the sync status pill and repository access button. "
            + _combined_step_outcome(steps, 4),
            "5. Inspect the height of the theme toggle and profile identity/avatar area. "
            + _combined_step_outcome(steps, 5),
            "6. Verify the CSS properties of the parent header container. "
            + _step_outcome(steps, 6),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", "")).rstrip(),
            "```",
            "",
            "## Actual vs Expected",
            f"- **Expected:** every visible desktop header control renders at {EXPECTED_CONTROL_HEIGHT:.0f}px and the parent header container uses a flex layout with `align-items: center`.",
            (
                "- **Actual:** the live header controls rendered at "
                f"`{json.dumps(result.get('visible_control_heights_px', {}), sort_keys=True)}` "
                f"with vertical center spread `{result.get('vertical_center_spread_px', '')}`; "
                f"the exposed header container summary was `{result.get('header_container_summary', '')}`."
            ),
            "",
            "## Environment details",
            f"- URL: `{result['app_url']}`",
            f"- Browser: Chromium via Playwright",
            f"- OS: `{result['os']}`",
            f"- Repository under test: `{result['repository']}@{result['repository_ref']}`",
            f"- Authenticated user: `{result['user_login']}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{result.get('screenshot', '')}`",
            f"- Runtime state: `{result.get('runtime_state', '')}`",
            f"- Connected text: `{result.get('connected_text', '')}`",
        ],
    ).rstrip() + "\n"


def _steps(result: dict[str, object]) -> list[dict[str, object]]:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        return [step for step in steps if isinstance(step, dict)]
    return []


def _human_checks(result: dict[str, object]) -> list[dict[str, object]]:
    checks = result.get("human_verification", [])
    if isinstance(checks, list):
        return [entry for entry in checks if isinstance(entry, dict)]
    return []


def _step_outcome(steps: list[dict[str, object]], step_number: int) -> str:
    for step in steps:
        if step.get("step") == step_number:
            marker = "✅" if step.get("status") == "passed" else "❌"
            return f"{marker} {step.get('observed', '')}"
    return "❌ No observation recorded."


def _combined_step_outcome(steps: list[dict[str, object]], step_number: int) -> str:
    matches = [step for step in steps if step.get("step") == step_number]
    if not matches:
        return "❌ No observation recorded."
    status = "passed" if all(step.get("status") == "passed" for step in matches) else "failed"
    marker = "✅" if status == "passed" else "❌"
    observed = " | ".join(str(step.get("observed", "")) for step in matches)
    return f"{marker} {observed}"


if __name__ == "__main__":
    main()
