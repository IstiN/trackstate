from __future__ import annotations

import json
import os
import re
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (
    LiveIssueDetailCollaborationPage,
    ScreenRect,
)
from testing.components.services.live_comment_metadata_contrast_probe import (
    CommentMetadataContrastObservation,
    LiveCommentMetadataContrastProbe,
)
from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)


TICKET_KEY = "TS-333"
OUTPUTS_DIR = REPO_ROOT / "outputs"
RAW_RESULT_PATH = OUTPUTS_DIR / "ts333_result.json"
TEST_AUTOMATION_RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
LIGHT_SCREENSHOT_PATH = OUTPUTS_DIR / "ts333_comments_light.png"
DARK_SCREENSHOT_PATH = OUTPUTS_DIR / "ts333_comments_dark.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts333_failure.png"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"
RUN_COMMAND = "python3 testing/tests/TS-333/test_ts_333.py"

ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
COMMENT_AUTHOR = "demo-admin"
COMMENT_BODY = "This comment demonstrates markdown-backed collaboration history."
COMMENT_TIMESTAMP = "2026-05-05T00:10:00Z"
REQUEST_STEPS = (
    "Open the issue detail view and navigate to the 'Comments' or 'History' tab.",
    "Inspect the contrast ratio of the metadata text (e.g., 'ana · 2026-05-05...') against the specific background surface (#F1E4D5).",
    "Switch the application theme (e.g., from Light to Dark) to change the background surface tokens.",
    "Re-verify the contrast ratio for metadata in the new theme context.",
)
EXPECTED_RESULT = (
    "The metadata text consistently maintains a contrast ratio of at least 4.5:1 "
    "(WCAG AA) across all background surfaces and validated design system theme tokens."
)
ENVIRONMENT_NAME = "Linux, Playwright Chromium, hosted TrackState setup app"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    repository_service = LiveSetupRepositoryService(config=config)
    token = repository_service.token
    if not token:
        raise RuntimeError(
            "TS-333 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    issue_fixture = repository_service.fetch_issue_fixture(ISSUE_PATH)
    probe = LiveCommentMetadataContrastProbe()

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": repository_service.repository,
        "repository_ref": repository_service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "steps": [],
        "observations": [],
    }
    failures: list[str] = []

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            live_issue_page = LiveIssueDetailCollaborationPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before collaboration metadata contrast was exercised.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=0,
                    status="passed",
                    action="Open the live app and reach the tracker shell.",
                    observed=runtime.body_text,
                )
                result["auth_state"] = _detect_auth_state(runtime.body_text)
                live_issue_page.open_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                live_issue_page.open_collaboration_tab("Comments")
                live_issue_page.wait_for_text(COMMENT_BODY, timeout_ms=60_000)
                comments_text = live_issue_page.current_body_text()
                result["issue_body_text"] = comments_text
                result["comments_body_text_initial"] = comments_text
                if live_issue_page.issue_detail_count(issue_fixture.key) == 0:
                    raise AssertionError(
                        "Step 1 failed: the live app did not open the requested issue "
                        f"detail for {issue_fixture.key}.\n"
                        f"Observed body text:\n{comments_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=(
                        "Open the seeded issue detail and navigate to the Comments "
                        "collaboration tab."
                    ),
                    observed=comments_text,
                )
                for visible_text in (
                    "Comments",
                    COMMENT_AUTHOR,
                    COMMENT_BODY,
                    COMMENT_TIMESTAMP,
                ):
                    if visible_text not in comments_text:
                        failures.append(
                            "Step 1 failed: the Comments tab did not keep the expected "
                            f"user-visible text {visible_text!r} on screen.\n"
                            f"Observed body text:\n{comments_text}",
                        )

                initial_toggle_label = live_issue_page.theme_toggle_label()
                result["initial_theme_toggle_label"] = initial_toggle_label
                initial_theme_name = _theme_name_for_toggle_label(initial_toggle_label)
                result["initial_theme_name"] = initial_theme_name

                initial_observation = _observe_comment_metadata(
                    live_issue_page=live_issue_page,
                    probe=probe,
                    screenshot_path=_screenshot_path_for_theme(initial_theme_name),
                    theme_name=initial_theme_name,
                )
                result["observations"] = [
                    _observation_to_dict(initial_observation),
                ]
                result[f"comments_body_text_{initial_theme_name}"] = comments_text
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=(
                        "Inspect the visible Comments metadata row in the current "
                        f"{initial_theme_name} theme."
                    ),
                    observed=comments_text,
                )
                if initial_observation.contrast_ratio < 4.5:
                    failures.append(
                        f"Step 2 failed: the visible Comments metadata in the current {initial_theme_name} "
                        "theme did not meet the required WCAG AA 4.5:1 contrast ratio.\n"
                        f"Observed {initial_observation.describe()}\n"
                        f"Visible body text:\n{comments_text}",
                    )

                toggled_label = live_issue_page.toggle_theme()
                result["toggled_theme_toggle_label"] = toggled_label
                toggled_theme_name = _theme_name_for_toggle_label(toggled_label)
                result["toggled_theme_name"] = toggled_theme_name
                if toggled_theme_name == initial_theme_name:
                    failures.append(
                        "Step 3 failed: toggling the theme did not switch the UI to the opposite theme.\n"
                        f"Initial toggle label: {initial_toggle_label}\n"
                        f"Toggle label after click: {toggled_label}\n"
                        f"Observed body text:\n{live_issue_page.current_body_text()}",
                    )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Switch the application theme to the opposite validated theme.",
                    observed=(
                        f"initial_toggle_label={initial_toggle_label}; "
                        f"toggled_toggle_label={toggled_label}; "
                        f"theme={toggled_theme_name}"
                    ),
                )
                live_issue_page.wait_for_text(COMMENT_BODY, timeout_ms=60_000)
                comments_text_toggled = live_issue_page.current_body_text()
                result[f"comments_body_text_{toggled_theme_name}"] = comments_text_toggled
                for visible_text in (
                    "Comments",
                    COMMENT_AUTHOR,
                    COMMENT_BODY,
                    COMMENT_TIMESTAMP,
                ):
                    if visible_text not in comments_text_toggled:
                        failures.append(
                            f"Step 4 failed: after switching to the {toggled_theme_name} theme, the Comments tab did "
                            f"not keep the expected user-visible text {visible_text!r} "
                            "on screen.\n"
                            f"Observed body text:\n{comments_text_toggled}",
                        )

                toggled_observation = _observe_comment_metadata(
                    live_issue_page=live_issue_page,
                    probe=probe,
                    screenshot_path=_screenshot_path_for_theme(toggled_theme_name),
                    theme_name=toggled_theme_name,
                )
                observations = result.setdefault("observations", [])
                assert isinstance(observations, list)
                observations.append(_observation_to_dict(toggled_observation))
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Switch themes and re-check the same visible Comments metadata row "
                        f"in the {toggled_theme_name} theme."
                    ),
                    observed=comments_text_toggled,
                )
                if toggled_observation.contrast_ratio < 4.5:
                    failures.append(
                        f"Step 4 failed: the visible Comments metadata in the {toggled_theme_name} theme "
                        "did not meet the required WCAG AA 4.5:1 contrast ratio.\n"
                        f"Observed {toggled_observation.describe()}\n"
                        f"Visible body text:\n{comments_text_toggled}",
                    )
            except Exception:
                live_issue_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["failure_screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        result["product_failure"] = _looks_like_product_failure(result)
        _write_result(result)
        _write_artifacts(
            result,
            status="failed",
            error_message=str(error),
            product_failure=bool(result["product_failure"]),
        )
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["product_failure"] = False
        _write_result(result)
        _write_artifacts(
            result,
            status="failed",
            error_message=str(result["error"]),
            product_failure=False,
        )
        print(json.dumps(result, indent=2))
        raise
    else:
        if failures:
            error_message = "\n\n".join(failures)
            result["error"] = error_message
            result["summary"] = (
                "Observed visible comment metadata in both themes, but at least one "
                "theme missed the required WCAG AA contrast threshold."
            )
            result["product_failure"] = True
            _write_result(result)
            _write_artifacts(
                result,
                status="failed",
                error_message=error_message,
                product_failure=True,
            )
            print(json.dumps(result, indent=2))
            raise AssertionError(error_message)

        result["status"] = "passed"
        result["summary"] = (
            "Verified in the live hosted tracker that the visible Comments metadata "
            "row stayed readable and met WCAG AA contrast in both light and dark themes."
        )
        result["product_failure"] = False
        _write_result(result)
        _write_artifacts(result, status="passed")
        print(json.dumps(result, indent=2))


def _observe_comment_metadata(
    *,
    live_issue_page: LiveIssueDetailCollaborationPage,
    probe: LiveCommentMetadataContrastProbe,
    screenshot_path: Path,
    theme_name: str,
) -> CommentMetadataContrastObservation:
    comment_card = live_issue_page.wait_for_comment_card(
        COMMENT_BODY,
        required_fragments=(COMMENT_AUTHOR, COMMENT_TIMESTAMP),
    )
    row_rect = ScreenRect(
        left=comment_card.left,
        top=comment_card.top,
        width=comment_card.width,
        height=comment_card.height,
    )
    live_issue_page.screenshot(str(screenshot_path))
    return probe.observe(
        screenshot_path=screenshot_path,
        row_rect=row_rect,
        theme_name=theme_name,
    )


def _observation_to_dict(
    observation: CommentMetadataContrastObservation,
) -> dict[str, object]:
    return {
        "theme_name": observation.theme_name,
        "row_background_hex": observation.row_background_hex,
        "expected_background_hex": observation.expected_background_hex,
        "actual_foreground_hex": observation.actual_foreground_hex,
        "inferred_token_name": observation.inferred_token_name,
        "inferred_token_hex": observation.inferred_token_hex,
        "contrast_ratio": round(observation.contrast_ratio, 4),
        "screenshot_path": observation.screenshot_path,
        "timestamp_crop_box": list(observation.timestamp_crop_box),
    }


def _theme_name_for_toggle_label(toggle_label: str) -> str:
    return "light" if toggle_label == "Dark theme" else "dark"


def _screenshot_path_for_theme(theme_name: str) -> Path:
    if theme_name == "light":
        return LIGHT_SCREENSHOT_PATH
    return DARK_SCREENSHOT_PATH


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


def _write_result(payload: dict[str, object]) -> None:
    configured_path = os.environ.get("TS333_RESULT_PATH")
    result_path = Path(configured_path) if configured_path else RAW_RESULT_PATH
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_artifacts(
    payload: dict[str, object],
    *,
    status: str,
    error_message: str | None = None,
    product_failure: bool = False,
) -> None:
    _write_test_automation_result(status=status, error_message=error_message)
    PR_BODY_PATH.write_text(_build_pr_body(payload, status=status), encoding="utf-8")
    JIRA_COMMENT_PATH.write_text(
        _build_jira_comment(payload, status=status),
        encoding="utf-8",
    )
    RESPONSE_PATH.write_text(_build_response(payload, status=status), encoding="utf-8")
    REVIEW_REPLIES_PATH.write_text(
        _build_review_replies(payload, status=status),
        encoding="utf-8",
    )
    if product_failure and status == "failed":
        BUG_DESCRIPTION_PATH.write_text(
            _build_bug_description(payload),
            encoding="utf-8",
        )
    elif BUG_DESCRIPTION_PATH.exists():
        BUG_DESCRIPTION_PATH.unlink()


def _write_test_automation_result(
    *,
    status: str,
    error_message: str | None = None,
) -> None:
    if status == "passed":
        payload = {
            "status": "passed",
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "summary": "1 passed, 0 failed",
        }
    else:
        payload = {
            "status": "failed",
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "summary": "0 passed, 1 failed",
            "error": error_message or "AssertionError",
        }
    TEST_AUTOMATION_RESULT_PATH.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _build_pr_body(payload: dict[str, object], *, status: str) -> str:
    status_label = "PASSED" if status == "passed" else "FAILED"
    lines = [
        f"# {TICKET_KEY} automation result: {status_label}",
        "",
        f"**Environment**: {ENVIRONMENT_NAME}",
        f"**URL**: {payload.get('app_url', 'n/a')}",
        f"**Repository**: {payload.get('repository', 'n/a')}@{payload.get('repository_ref', 'n/a')}",
        f"**Issue**: {payload.get('issue_key', 'n/a')} - {payload.get('issue_summary', 'n/a')}",
        "",
        "## What automation checked",
        *_markdown_list(_automation_checks(payload)),
        "",
        "## Human-style verification",
        *_markdown_list(_human_verification_lines(payload, status=status)),
        "",
        "## Outcome",
        *_markdown_list(_outcome_lines(payload, status=status)),
    ]
    if status == "failed":
        lines.extend(
            [
                "",
                "## Exact error",
                "```text",
                str(payload.get("traceback", payload.get("error", ""))).rstrip(),
                "```",
            ],
        )
    return "\n".join(lines).rstrip() + "\n"


def _build_jira_comment(payload: dict[str, object], *, status: str) -> str:
    status_label = "PASSED" if status == "passed" else "FAILED"
    lines = [
        f"h3. {TICKET_KEY} automation result: {status_label}",
        "",
        f"*Environment*: {ENVIRONMENT_NAME}",
        f"*URL*: {{{{ {payload.get('app_url', 'n/a')} }}}}",
        f"*Repository*: {{{{ {payload.get('repository', 'n/a')}@{payload.get('repository_ref', 'n/a')} }}}}",
        f"*Issue*: {{{{ {payload.get('issue_key', 'n/a')} - {payload.get('issue_summary', 'n/a')} }}}}",
        "",
        "h4. What automation checked",
        *_jira_list(_automation_checks(payload)),
        "",
        "h4. Human-style verification",
        *_jira_list(_human_verification_lines(payload, status=status)),
        "",
        "h4. Outcome",
        *_jira_list(_outcome_lines(payload, status=status)),
    ]
    if status == "failed":
        lines.extend(
            [
                "",
                "h4. Exact error",
                "{code}",
                str(payload.get("traceback", payload.get("error", ""))).rstrip(),
                "{code}",
            ],
        )
    return "\n".join(lines).rstrip() + "\n"


def _build_response(payload: dict[str, object], *, status: str) -> str:
    status_label = "passed" if status == "passed" else "failed"
    lines = [
        f"# {TICKET_KEY} {status_label}",
        "",
        payload.get("summary", EXPECTED_RESULT if status == "passed" else str(payload.get("error", ""))),
        "",
        "## Observed themes",
        *_markdown_list(_theme_lines(payload)),
    ]
    if status == "failed":
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                str(payload.get("error", "")).rstrip(),
                "```",
            ],
        )
    return "\n".join(lines).rstrip() + "\n"


def _build_bug_description(payload: dict[str, object]) -> str:
    lines = [
        f"# Bug: {TICKET_KEY} collaboration metadata contrast regression",
        "",
        "## Steps to reproduce",
        *_reproduction_lines(payload),
        "",
        "## Exact error message or assertion failure",
        "```text",
        str(payload.get("traceback", payload.get("error", ""))).rstrip(),
        "```",
        "",
        "## Actual vs Expected",
        f"- **Expected:** {EXPECTED_RESULT}",
        f"- **Actual:** {_actual_result_summary(payload)}",
        "",
        "## Environment details",
        f"- URL: {payload.get('app_url', 'n/a')}",
        f"- Repository: {payload.get('repository', 'n/a')}@{payload.get('repository_ref', 'n/a')}",
        f"- Issue: {payload.get('issue_key', 'n/a')} - {payload.get('issue_summary', 'n/a')}",
        f"- Browser/OS: {ENVIRONMENT_NAME}",
        "",
        "## Screenshots or logs",
        *_markdown_list(_evidence_lines(payload)),
    ]
    return "\n".join(lines).rstrip() + "\n"


def _automation_checks(payload: dict[str, object]) -> list[str]:
    return [
        "Opened the deployed tracker shell and confirmed the live hosted workspace was interactive.",
        f"Opened issue {payload.get('issue_key', 'DEMO-2')} and switched to the visible Comments collaboration tab.",
        (
            "Verified the user-facing metadata text "
            f'"{COMMENT_AUTHOR}", "{COMMENT_BODY}", and "{COMMENT_TIMESTAMP}" remained visible.'
        ),
        "Measured the rendered metadata contrast in the current theme, toggled the app theme, and measured the rendered metadata again in the second theme.",
    ]


def _human_verification_lines(
    payload: dict[str, object],
    *,
    status: str,
) -> list[str]:
    lines = [
        (
            "Viewed the same Comments surface a user sees and confirmed the tab label, "
            "author name, comment body, and timestamp stayed on screen in the active issue detail."
        ),
    ]
    theme_lines = _theme_lines(payload)
    if theme_lines:
        lines.extend(theme_lines)
    if status == "passed":
        lines.append(
            "The observed light and dark theme metadata both met the WCAG AA 4.5:1 minimum and matched the expected result."
        )
    else:
        lines.append(
            "The observed behavior did not fully match the expected WCAG AA contrast requirement across the validated themes."
        )
    return lines


def _outcome_lines(payload: dict[str, object], *, status: str) -> list[str]:
    if status == "passed":
        return [
            "Result matched the expected outcome.",
            str(payload.get("summary", EXPECTED_RESULT)),
        ]
    return [
        "Result did not match the expected outcome.",
        f"Failed step: {_failed_step_summary(payload)}",
        f"Actual vs expected: {_actual_result_summary(payload)}",
    ]


def _theme_lines(payload: dict[str, object]) -> list[str]:
    observations = payload.get("observations", [])
    if not isinstance(observations, list):
        return []
    lines: list[str] = []
    for entry in observations:
        if not isinstance(entry, dict):
            continue
        theme_name = str(entry.get("theme_name", "unknown"))
        foreground = str(entry.get("actual_foreground_hex", "n/a"))
        background = str(entry.get("row_background_hex", "n/a"))
        contrast = entry.get("contrast_ratio", "n/a")
        screenshot = str(entry.get("screenshot_path", "n/a"))
        lines.append(
            f"{theme_name.title()} theme metadata rendered as {foreground} on {background} with {contrast}:1 contrast (screenshot: {screenshot})."
        )
    return lines


def _reproduction_lines(payload: dict[str, object]) -> list[str]:
    step_statuses = _step_status_map(payload)
    lines: list[str] = []
    for index, step in enumerate(REQUEST_STEPS, start=1):
        status = step_statuses.get(index, "not reached")
        marker = "✅" if status == "passed" else "❌"
        annotation = _step_annotation(index, payload)
        lines.append(f"{index}. {marker} {step}")
        if annotation:
            lines.append(f"   - {annotation}")
    return lines


def _step_status_map(payload: dict[str, object]) -> dict[int, str]:
    statuses: dict[int, str] = {}
    steps = payload.get("steps", [])
    if not isinstance(steps, list):
        return _apply_failed_step_overrides(statuses, payload)
    for entry in steps:
        if not isinstance(entry, dict):
            continue
        step_number = entry.get("step")
        status = entry.get("status")
        if isinstance(step_number, int) and isinstance(status, str):
            statuses[step_number] = status
    return _apply_failed_step_overrides(statuses, payload)


def _apply_failed_step_overrides(
    statuses: dict[int, str],
    payload: dict[str, object],
) -> dict[int, str]:
    error_text = str(payload.get("error", ""))
    for match in re.finditer(r"Step ([1-4]) failed", error_text):
        statuses[int(match.group(1))] = "failed"
    return statuses


def _step_annotation(step: int, payload: dict[str, object]) -> str:
    if step == 0:
        auth_state = payload.get("auth_state")
        if auth_state:
            return (
                "Reached the hosted tracker shell before exercising the collaboration "
                f"surface (auth_state={auth_state})."
            )
        return "Reached the hosted tracker shell before exercising the collaboration surface."
    if step == 1:
        return (
            f"Opened {payload.get('issue_key', 'DEMO-2')} and rendered the Comments surface "
            f'with visible metadata text "{COMMENT_AUTHOR}" and "{COMMENT_TIMESTAMP}".'
        )
    if step == 2:
        failing_observation = _first_failing_observation(payload)
        if failing_observation is None:
            return "Measured the rendered metadata against the collaboration background surface."
        return (
            "Measured the rendered metadata contrast on the collaboration row and observed "
            f"{failing_observation.get('actual_foreground_hex', 'n/a')} on "
            f"{failing_observation.get('row_background_hex', 'n/a')} at "
            f"{failing_observation.get('contrast_ratio', 'n/a')}:1."
        )
    if step == 3:
        toggled_theme = payload.get("toggled_theme_name")
        if toggled_theme:
            return f"Theme toggle switched the app into the {toggled_theme} theme."
        return "The failure happened before the theme toggle could be completed."
    if step == 4:
        second_observation = _second_observation(payload)
        if second_observation is None:
            return "The failure happened before the second theme measurement completed."
        return (
            f"Re-checked the metadata in {second_observation.get('theme_name', 'the toggled')} theme at "
            f"{second_observation.get('contrast_ratio', 'n/a')}:1 contrast."
        )
    return ""


def _failed_step_summary(payload: dict[str, object]) -> str:
    error_text = str(payload.get("error", ""))
    for prefix in ("Step 1", "Step 2", "Step 3", "Step 4"):
        if prefix in error_text:
            return prefix
    return "scenario execution"


def _actual_result_summary(payload: dict[str, object]) -> str:
    failing_observation = _first_failing_observation(payload)
    if failing_observation is not None:
        return (
            "The visible Comments metadata did not consistently meet the 4.5:1 threshold: "
            f"{failing_observation.get('theme_name', 'one')} theme rendered "
            f"{failing_observation.get('actual_foreground_hex', 'n/a')} on "
            f"{failing_observation.get('row_background_hex', 'n/a')} at "
            f"{failing_observation.get('contrast_ratio', 'n/a')}:1."
        )
    return str(payload.get("error", "Scenario failed before the expected contrast verification completed."))


def _evidence_lines(payload: dict[str, object]) -> list[str]:
    lines = _theme_lines(payload)
    failure_screenshot = payload.get("failure_screenshot")
    if failure_screenshot:
        lines.append(f"Failure screenshot: {failure_screenshot}")
    raw_error = str(payload.get("error", "")).strip()
    if raw_error:
        lines.append(f"Runtime error excerpt: {raw_error}")
    return lines


def _first_failing_observation(payload: dict[str, object]) -> dict[str, object] | None:
    observations = payload.get("observations", [])
    if not isinstance(observations, list):
        return None
    for entry in observations:
        if not isinstance(entry, dict):
            continue
        contrast = entry.get("contrast_ratio")
        if isinstance(contrast, (int, float)) and contrast < 4.5:
            return entry
    for entry in observations:
        if isinstance(entry, dict):
            return entry
    return None


def _second_observation(payload: dict[str, object]) -> dict[str, object] | None:
    observations = payload.get("observations", [])
    if isinstance(observations, list) and len(observations) > 1:
        second = observations[1]
        if isinstance(second, dict):
            return second
    return None


def _looks_like_product_failure(payload: dict[str, object]) -> bool:
    error_text = str(payload.get("error", ""))
    if "GH_TOKEN" in error_text or "GITHUB_TOKEN" in error_text:
        return False
    if "ModuleNotFoundError" in error_text or "RuntimeError" in error_text:
        return False
    if "Precondition failed" in error_text:
        return False
    auth_markers = (
        "Needs sign-in",
        "Connect GitHub",
        "authentication precondition",
        "GitHub connection failed",
        "token connect flow",
        "auth gate",
    )
    if any(marker in error_text for marker in auth_markers):
        return False
    return any(prefix in error_text for prefix in ("Step 1", "Step 2", "Step 3", "Step 4"))


def _detect_auth_state(body_text: str) -> str:
    if "Needs sign-in" in body_text or "GitHub write access is not connected" in body_text:
        return "read-only"
    if "Connected as " in body_text:
        return "connected"
    return "unknown"


def _build_review_replies(payload: dict[str, object], *, status: str) -> str:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(payload, status=status),
        }
        for thread in _discussion_threads()
    ]
    return json.dumps({"replies": replies}, indent=2) + "\n"


def _discussion_threads() -> list[dict[str, object]]:
    if not DISCUSSIONS_RAW_PATH.is_file():
        return []
    raw_payload = json.loads(DISCUSSIONS_RAW_PATH.read_text(encoding="utf-8"))
    threads = raw_payload.get("threads")
    if not isinstance(threads, list):
        return []
    normalized_threads: list[dict[str, object]] = []
    for thread in threads:
        if isinstance(thread, dict) and thread.get("resolved") is not True:
            normalized_threads.append(thread)
    return normalized_threads


def _review_reply_text(payload: dict[str, object], *, status: str) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if status == "passed"
        else f"Re-ran `{RUN_COMMAND}`: failed with `{str(payload.get('error', '')).strip()}`."
    )
    return (
        "Fixed: TS-333 now measures the weakest visible metadata color inside the comment "
        "header band instead of the strongest text in an expanded timestamp crop. The probe "
        "uses the specific seeded comment card, limits sampling to the metadata strip, and "
        "evaluates the minimum significant foreground contrast so darker nearby body text "
        f"cannot mask a muted timestamp token. {rerun_summary}"
    )


def _markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def _jira_list(items: list[str]) -> list[str]:
    return [f"* {item}" for item in items]
if __name__ == "__main__":
    main()
