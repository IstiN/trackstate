from __future__ import annotations

from collections import Counter
from dataclasses import asdict, replace
import json
import math
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.components.services.live_workspace_switcher_delete_contrast_probe import (  # noqa: E402
    LiveWorkspaceSwitcherDeleteContrastProbe,
    WorkspaceSwitcherDeleteContrastObservation,
)
from testing.core.utils.color_contrast import (  # noqa: E402
    RgbColor,
    color_distance,
    contrast_ratio,
    rgb_to_hex,
)
from testing.core.utils.png_image import RgbImage  # noqa: E402
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-928"
TEST_CASE_TITLE = (
    "Workspace switcher Delete action keeps WCAG AA 4.5:1 text contrast"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-928/test_ts_928.py"
REQUEST_STEPS = [
    "Identify the visible Delete action control for a workspace (for example, `Delete: istin/trackstate-setup`).",
    "Measure the rendered Delete text contrast against the workspace switcher surface background.",
]
EXPECTED_RESULT = (
    "The workspace switcher Delete action measures at least 4.5:1 text contrast "
    "against the rendered surface background."
)
LINKED_BUGS = ["TS-902"]
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
MIN_TEXT_CONTRAST = 4.5
HOSTED_TARGET = "IstiN/trackstate-setup"
SECONDARY_HOSTED_TARGET = "IstiN/trackstate"
DEFAULT_BRANCH = "main"
SECONDARY_BRANCH = "gh-pages"
PREFERRED_DELETE_WORKSPACE = "istin/trackstate-setup"

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
PROBE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts928_probe.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts928_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts928_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    PROBE_SCREENSHOT_PATH.unlink(missing_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    repository_service = LiveSetupRepositoryService(config=config)
    token = repository_service.token
    if not token:
        raise RuntimeError(
            "TS-928 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state()
    hosted_workspace_id = f"hosted:{HOSTED_TARGET.lower()}@{DEFAULT_BRANCH}"
    probe = LiveWorkspaceSwitcherDeleteContrastProbe()
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": repository_service.repository,
        "repository_ref": repository_service.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "linked_bugs": LINKED_BUGS,
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
                workspace_token_profile_ids=(hosted_workspace_id,),
            ),
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
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
                        "The deployed app did not reach the interactive tracker shell "
                        "before the workspace switcher Delete contrast scenario began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}"
                    ),
                )
                _mark_unreached_steps(result, first_unreached=2)
                raise AssertionError(
                    "Step 1 failed: the deployed app did not reach the interactive "
                    "tracker shell before the workspace switcher Delete contrast "
                    "scenario began.\n"
                    f"Observed runtime state: {runtime.kind}\n"
                    f"Observed body text:\n{runtime.body_text}"
                )

            page.dismiss_connection_banner()
            page.set_viewport(**DESKTOP_VIEWPORT)
            trigger = page.observe_trigger(timeout_ms=20_000)
            result["trigger_observation"] = _trigger_payload(trigger)
            page.open_switcher(timeout_ms=20_000)
            surface = page.observe_surface(timeout_ms=20_000)
            _capture_screenshot(page, PROBE_SCREENSHOT_PATH, result)
            surface = _enrich_surface_interactive_text_contrast(
                surface=surface,
                screenshot_path=PROBE_SCREENSHOT_PATH,
            )
            result["surface_heading"] = surface.heading_text
            result["surface_body_text"] = surface.body_text
            result["surface_interactive_elements"] = [
                _interactive_element_payload(item) for item in surface.interactive_elements
            ]
            result["surface_interactive_texts"] = [
                _interactive_text_payload(item) for item in surface.interactive_texts
            ]
            result["surface_interactive_icons"] = [
                _interactive_icon_payload(item) for item in surface.interactive_icons
            ]
            result["surface_semantics"] = [
                _semantics_payload(item) for item in surface.semantics_nodes
            ]

            try:
                delete_observation = probe.observe(
                    surface=surface,
                    preferred_workspace=PREFERRED_DELETE_WORKSPACE,
                )
            except AssertionError as error:
                _record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"{error}\n"
                        f"surface_heading={surface.heading_text!r}\n"
                        f"interactive_elements={result['surface_interactive_elements']!r}\n"
                        f"interactive_texts={result['surface_interactive_texts']!r}\n"
                        f"interactive_icons={result['surface_interactive_icons']!r}"
                    ),
                )
                _mark_unreached_steps(result, first_unreached=2)
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live Workspace switcher from the deployed top bar and "
                        "checked whether any Delete control was actually visible to the user."
                    ),
                    observed=(
                        f"heading={surface.heading_text!r}; "
                        f"body_text={surface.body_text!r}; "
                        f"interactive_elements={result['surface_interactive_elements']!r}; "
                        f"interactive_texts={result['surface_interactive_texts']!r}; "
                        f"interactive_icons={result['surface_interactive_icons']!r}"
                    ),
                )
                raise
            result["delete_contrast_observation"] = delete_observation.to_dict()
            _record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Opened the live Workspace switcher and located the visible Delete "
                    "action inside the saved workspace list. "
                    f"Trigger={json.dumps(_trigger_payload(trigger), ensure_ascii=True)}; "
                    f"surface_heading={surface.heading_text!r}; "
                    f"delete_observation={delete_observation.describe()}"
                ),
            )

            _record_human_verification(
                result,
                check=(
                    "Viewed the live Workspace switcher from the deployed top bar and "
                    "confirmed the Delete action text was visible in the saved workspace list."
                ),
                observed=(
                    f"heading={surface.heading_text!r}; "
                    f"visible_delete_text={delete_observation.visible_text!r}; "
                    f"available_delete_controls={list(delete_observation.available_delete_controls)!r}"
                ),
            )

            if delete_observation.text_contrast_ratio is None:
                _record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "The Delete action was visible, but the live probe could not resolve "
                        "a rendered text contrast ratio from the computed foreground and "
                        "background colors. "
                        f"delete_observation={delete_observation.describe()}"
                    ),
                )
                raise AssertionError(
                    "Step 2 failed: the live workspace switcher Delete action did not "
                    "resolve a measurable text contrast ratio.\n"
                    f"Observed control: {delete_observation.describe()}"
                )

            if delete_observation.text_contrast_ratio < MIN_TEXT_CONTRAST:
                _record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "The Delete action remained below the required WCAG AA text "
                        "contrast threshold. "
                        f"delete_observation={delete_observation.describe()}"
                    ),
                )
                raise AssertionError(
                    "Step 2 failed: the live workspace switcher Delete action did not "
                    f"meet the required {MIN_TEXT_CONTRAST}:1 text contrast ratio.\n"
                    f"Observed control: {delete_observation.describe()}"
                )

            _record_step(
                result,
                step=2,
                status="passed",
                action=REQUEST_STEPS[1],
                observed=(
                    "Measured the rendered Delete text against the live switcher surface "
                    f"background and it met WCAG AA. delete_observation={delete_observation.describe()}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Checked the same visible Delete control the user sees on screen and "
                    "compared its rendered foreground and background colors."
                ),
                observed=delete_observation.describe(),
            )

            _capture_screenshot(page, SUCCESS_SCREENSHOT_PATH, result)
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        if page is not None and "screenshot" not in result:
            _capture_screenshot(page, FAILURE_SCREENSHOT_PATH, result)
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _workspace_state() -> dict[str, object]:
    hosted_id = f"hosted:{HOSTED_TARGET.lower()}@{DEFAULT_BRANCH}"
    secondary_hosted_id = f"hosted:{SECONDARY_HOSTED_TARGET.lower()}@{SECONDARY_BRANCH}"
    return {
        "activeWorkspaceId": hosted_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": hosted_id,
                "displayName": "",
                "targetType": "hosted",
                "target": HOSTED_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-22T08:30:00.000Z",
            },
            {
                "id": secondary_hosted_id,
                "displayName": "",
                "targetType": "hosted",
                "target": SECONDARY_HOSTED_TARGET,
                "defaultBranch": SECONDARY_BRANCH,
                "writeBranch": SECONDARY_BRANCH,
                "lastOpenedAt": "2026-05-21T08:30:00.000Z",
            },
        ],
    }


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "raw_text_lines": list(trigger.raw_text_lines),
    }


def _interactive_element_payload(item: object) -> dict[str, object]:
    return {
        "label": getattr(item, "label", ""),
        "accessible_label": getattr(item, "accessible_label", ""),
        "role": getattr(item, "role", None),
        "tag_name": getattr(item, "tag_name", ""),
    }


def _interactive_text_payload(item: object) -> dict[str, object]:
    return {
        "label": getattr(item, "label", ""),
        "visible_text": getattr(item, "visible_text", ""),
        "role": getattr(item, "role", None),
        "foreground_color": getattr(item, "foreground_color", None),
        "background_color": getattr(item, "background_color", None),
        "contrast_ratio": getattr(item, "contrast_ratio", None),
    }


def _interactive_icon_payload(item: object) -> dict[str, object]:
    return {
        "label": getattr(item, "label", ""),
        "foreground_color": getattr(item, "foreground_color", None),
        "background_color": getattr(item, "background_color", None),
        "contrast_ratio": getattr(item, "contrast_ratio", None),
    }


def _semantics_payload(item: object) -> dict[str, object]:
    return {
        "label": getattr(item, "label", ""),
        "role": getattr(item, "role", None),
        "tag_name": getattr(item, "tag_name", ""),
        "visible_text": getattr(item, "visible_text", ""),
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


def _mark_unreached_steps(result: dict[str, object], *, first_unreached: int) -> None:
    recorded = {
        int(step["step"])
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    for index in range(first_unreached, len(REQUEST_STEPS) + 1):
        if index in recorded:
            continue
        _record_step(
            result,
            step=index,
            status="not_run",
            action=REQUEST_STEPS[index - 1],
            observed="Not reached because the earlier required step did not complete.",
        )


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    entries = result.setdefault("human_verification", [])
    assert isinstance(entries, list)
    entries.append({"check": check, "observed": observed})


def _capture_screenshot(
    page: LiveWorkspaceSwitcherPage,
    path: Path,
    result: dict[str, object],
) -> None:
    path.unlink(missing_ok=True)
    try:
        page.screenshot(str(path))
    except Exception as error:  # pragma: no cover - diagnostic path
        result["screenshot_capture_error"] = _format_error(error)
        return
    if path.exists():
        result["screenshot"] = str(path)


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
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        (
            "* Opened the deployed TrackState web app in Chromium with saved "
            "workspace profiles preloaded into browser storage."
        ),
        (
            "* Opened the live Workspace switcher at the desktop viewport and measured "
            "the visible Delete action text against the rendered panel background."
        ),
        "",
        "h4. Result",
        (
            "* Matched the expected result: the visible Delete action in the live Workspace "
            "switcher met the WCAG AA 4.5:1 text contrast requirement."
            if passed
            else f"* Did not match the expected result. {_failure_summary(result)}"
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}, "
            f"viewport {{{{{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}}}}}."
        ),
        "",
        "h4. Test file",
        "{code}",
        "testing/tests/TS-928/test_ts_928.py",
        "{code}",
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
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
    if result.get("screenshot"):
        lines.extend(["", f"*Screenshot:* {{{{{result['screenshot']}}}}}"])
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Opened the deployed TrackState web app in Chromium with preloaded saved workspace profiles.",
        "- Opened the live Workspace switcher at 1440x900 and measured the visible Delete action text against the rendered switcher surface.",
        "",
        "## Result",
        (
            "- The observed behavior matched the expected result."
            if passed
            else f"- The observed behavior did not match the expected result. {_failure_summary(result)}"
        ),
        "",
        "## Test file",
        "`testing/tests/TS-928/test_ts_928.py`",
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    if result.get("screenshot"):
        lines.extend(["", f"**Screenshot:** `{result['screenshot']}`"])
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    return _pr_body(result, passed=passed)


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return []
    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        raw_status = str(step.get("status", "failed"))
        status = (
            "PASSED"
            if raw_status == "passed"
            else "NOT RUN" if raw_status == "not_run" else "FAILED"
        )
        action = str(step.get("action", ""))
        observed = str(step.get("observed", ""))
        if jira:
            lines.append(
                f"* Step {step.get('step')}: *{status}* — {action} Observed: {observed}"
            )
        else:
            lines.append(
                f"- Step {step.get('step')}: **{status}** — {action} Observed: {observed}"
            )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    checks = result.get("human_verification", [])
    if not isinstance(checks, list):
        return []
    lines: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        if jira:
            lines.append(
                f"* {check.get('check')} Observed: {check.get('observed')}"
            )
        else:
            lines.append(
                f"- {check.get('check')} Observed: {check.get('observed')}"
            )
    return lines


def _failure_summary(result: dict[str, object]) -> str:
    failed_steps = [
        step
        for step in result.get("steps", [])
        if isinstance(step, dict) and step.get("status") == "failed"
    ]
    if not failed_steps:
        return str(result.get("error", "Unknown failure"))
    first = failed_steps[0]
    return f"First failed step: {first.get('step')} — {first.get('observed')}"


def _bug_description(result: dict[str, object]) -> str:
    failed_steps = [
        step
        for step in result.get("steps", [])
        if isinstance(step, dict) and step.get("status") == "failed"
    ]
    first_failed = failed_steps[0] if failed_steps else None
    delete_observation = result.get("delete_contrast_observation")
    return "\n".join(
        [
            f"# {TICKET_KEY}: Workspace switcher Delete action contrast regression",
            "",
            "## Steps to reproduce",
            _reproduction_steps(result),
            "",
            "## Expected result",
            EXPECTED_RESULT,
            "",
            "## Actual result",
            (
                str(first_failed.get("observed"))
                if isinstance(first_failed, dict)
                else str(result.get("error", "Unknown failure"))
            ),
            "",
            "## Actual vs Expected",
            (
                f"- **Expected:** the visible Delete action text in the live Workspace "
                f"switcher measures at least {MIN_TEXT_CONTRAST}:1 contrast."
            ),
            (
                f"- **Actual:** the live observation was "
                f"{json.dumps(delete_observation, ensure_ascii=True, indent=2)}"
                if isinstance(delete_observation, dict)
                else (
                    "- **Actual:** the live Workspace switcher rendered no visible Delete "
                    "text/icon control to inspect. "
                    f"interactive_elements={json.dumps(result.get('surface_interactive_elements', []), ensure_ascii=True)} "
                    f"interactive_texts={json.dumps(result.get('surface_interactive_texts', []), ensure_ascii=True)} "
                    f"interactive_icons={json.dumps(result.get('surface_interactive_icons', []), ensure_ascii=True)}"
                )
            ),
            "",
            "## Environment",
            f"- URL: {result.get('app_url')}",
            f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
            f"- Browser: {result.get('browser')}",
            f"- OS: {result.get('os')}",
            f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            "",
            "## Exact error message / stack trace",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Screenshot / logs",
            f"- Screenshot: {result.get('screenshot', '<not captured>')}",
            "- Step log:",
            "```json",
            json.dumps(result.get("steps", []), indent=2),
            "```",
        ],
    ) + "\n"


def _reproduction_steps(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "1. Open the live app and launch the Workspace switcher.\n2. Inspect the visible Delete action."
    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        icon = (
            "✅"
            if step.get("status") == "passed"
            else "❌" if step.get("status") == "failed" else "⚪"
        )
        lines.append(
            f"{step.get('step')}. {icon} {step.get('action')} "
            f"Observed: {step.get('observed')}"
        )
    return "\n".join(lines)


def _enrich_surface_interactive_text_contrast(
    *,
    surface,
    screenshot_path: Path,
):
    if not screenshot_path.exists() or not surface.interactive_texts:
        return surface
    image = RgbImage.open(screenshot_path)
    interactive_texts = tuple(
        _observe_interactive_text(image=image, text_control=text_control)
        for text_control in surface.interactive_texts
    )
    interactive_icons = tuple(
        _observe_interactive_icon(image=image, icon=icon)
        for icon in surface.interactive_icons
    )
    return replace(
        surface,
        interactive_texts=interactive_texts,
        interactive_icons=interactive_icons,
    )


def _observe_interactive_text(*, image: RgbImage, text_control):
    box = _box(
        image=image,
        left=text_control.x,
        top=text_control.y,
        width=text_control.width,
        height=text_control.height,
    )
    if box is None:
        return text_control
    crop = image.crop(box)
    background = _dominant_color(crop)
    foreground = _sample_foreground(crop, background=background)
    return replace(
        text_control,
        foreground_color=(rgb_to_hex(foreground).lower() if foreground is not None else None),
        background_color=rgb_to_hex(background).lower(),
        contrast_ratio=(
            round(contrast_ratio(foreground, background), 2)
            if foreground is not None
            else None
        ),
    )


def _observe_interactive_icon(*, image: RgbImage, icon):
    box = _box(
        image=image,
        left=icon.x,
        top=icon.y,
        width=icon.width,
        height=icon.height,
    )
    if box is None:
        return icon
    crop = image.crop(box)
    background = _dominant_color(crop)
    foreground = _sample_foreground(crop, background=background)
    return replace(
        icon,
        foreground_color=(rgb_to_hex(foreground).lower() if foreground is not None else None),
        background_color=rgb_to_hex(background).lower(),
        contrast_ratio=(
            round(contrast_ratio(foreground, background), 2)
            if foreground is not None
            else None
        ),
    )


def _box(
    *,
    image: RgbImage,
    left: float,
    top: float,
    width: float,
    height: float,
) -> tuple[int, int, int, int] | None:
    if width <= 0 or height <= 0:
        return None
    box = (
        max(int(math.floor(left)), 0),
        max(int(math.floor(top)), 0),
        min(int(math.ceil(left + width)), image.width),
        min(int(math.ceil(top + height)), image.height),
    )
    if box[0] >= box[2] or box[1] >= box[3]:
        return None
    return box


def _dominant_color(image: RgbImage) -> RgbColor:
    counts = Counter(image.getdata())
    color, _ = counts.most_common(1)[0]
    return color


def _sample_foreground(
    image: RgbImage,
    *,
    background: RgbColor,
) -> RgbColor | None:
    counts = Counter(image.getdata())
    samples = [
        (color, count)
        for color, count in counts.items()
        if color_distance(color, background) > 20
    ]
    if not samples:
        return None
    strongest_distance = max(
        color_distance(color, background)
        for color, _ in samples
    )
    strongest_samples = [
        (color, count)
        for color, count in samples
        if strongest_distance - color_distance(color, background) <= 8
    ]
    total = sum(count for _, count in strongest_samples)
    return (
        round(sum(color[0] * count for color, count in strongest_samples) / total),
        round(sum(color[1] * count for color, count in strongest_samples) / total),
        round(sum(color[2] * count for color, count in strongest_samples) / total),
    )


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


if __name__ == "__main__":
    main()
