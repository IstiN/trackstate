from __future__ import annotations

import json
import platform
import re
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_multi_view_refresh_page import (  # noqa: E402
    LabeledTextFieldObservation,
    LiveMultiViewRefreshPage,
    SummaryRequiredValidationObservation,
)
from testing.components.pages.live_project_settings_page import (  # noqa: E402
    LiveProjectSettingsPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.color_contrast import RgbColor, rgb_to_hex  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402

TICKET_KEY = "TS-887"
RUN_COMMAND = "PYTHONPATH=. python3 testing/tests/TS-887/test_ts_887.py"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts887_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts887_success.png"

REQUEST_STEPS = (
    "Clear the content of the Summary field.",
    "Click the Save button to trigger validation.",
    "Inspect the resulting error message (Summary is required).",
    "Verify the error message meets WCAG AA contrast (4.5:1).",
    "Use a screen reader to verify that the error is announced (for example, via a live region or focus shift).",
)
SUMMARY_REQUIRED_FRAGMENT = "Summary is required"
MIN_TEXT_CONTRAST = 4.5
EXPECTED_ERROR_THEME_HEXES = {"#c25742", "#e8a085"}


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-887 requires GH_TOKEN or GITHUB_TOKEN to open the hosted edit flow.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_path": issue_fixture.path,
        "issue_summary": issue_fixture.summary,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "expected_error_theme_hexes": sorted(EXPECTED_ERROR_THEME_HEXES),
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(config) as tracker_page:
            settings_page = LiveProjectSettingsPage(tracker_page)
            edit_page = LiveMultiViewRefreshPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Precondition failed: the deployed app did not reach the hosted "
                        "tracker shell before the edit-validation scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                connected_text = settings_page.ensure_write_capable_connection(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                result["connected_body_text"] = connected_text
                settings_page.dismiss_connection_banner()

                edit_dialog_text = edit_page.open_edit_dialog_for_issue_key(
                    issue_key=issue_fixture.key,
                )
                result["edit_dialog_text"] = edit_dialog_text
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live hosted Edit issue surface as a user and checked "
                        "that the dialog heading and target issue identity were visible."
                    ),
                    observed=(
                        f"Dialog contained `Edit issue`: {'Edit issue' in edit_dialog_text}; "
                        f"dialog contained `{issue_fixture.key}`: {issue_fixture.key in edit_dialog_text}."
                    ),
                )

                summary_field = edit_page.observe_labeled_text_field("Summary")
                result["summary_field"] = _field_payload(summary_field)

                if not summary_field.enabled:
                    observation = _summary_field_failure_observation(summary_field)
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=observation,
                    )
                    _mark_unreached_steps(result, first_unreached=2)
                    _record_human_verification(
                        result,
                        check=(
                            "Tried to start the scenario the same way a user would: by "
                            "placing focus in Summary and clearing the field before saving."
                        ),
                        observed=observation,
                    )
                    raise AssertionError(
                        "Step 1 failed: the live Edit issue surface rendered the required "
                        "Summary field as disabled, so the user could not clear it to trigger "
                        "validation.\n"
                        f"Summary field payload: {_field_payload(summary_field)}\n"
                        f"Observed dialog text:\n{edit_dialog_text}",
                    )

                cleared_field = edit_page.clear_labeled_text_field("Summary")
                result["summary_field_after_clear"] = _field_payload(cleared_field)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"Summary field became editable and cleared successfully. "
                        f"Field payload: {_field_payload(cleared_field)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Cleared the visible Summary field and kept the live Edit issue "
                        "dialog open to trigger validation the same way a user would."
                    ),
                    observed=(
                        f"Summary field after clearing: {_field_payload(cleared_field)}"
                    ),
                )

                try:
                    validation = edit_page.trigger_required_summary_validation(
                        message_fragment=SUMMARY_REQUIRED_FRAGMENT,
                    )
                except Exception as error:
                    result["post_step_2_body_text"] = edit_page.current_body_text()
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=str(error),
                    )
                    _mark_unreached_steps(result, first_unreached=3)
                    raise

                result["summary_validation"] = _validation_payload(validation)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=_step_two_observation(validation),
                )

                if not _validation_message_matches(validation):
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=_missing_validation_message_observation(validation),
                    )
                    _mark_unreached_steps(result, first_unreached=4)
                    raise AssertionError(
                        "Step 3 failed: clicking Save did not expose the expected visible "
                        f"Summary-required message containing {SUMMARY_REQUIRED_FRAGMENT!r}.\n"
                        f"Validation payload: {_validation_payload(validation)}",
                    )

                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=_step_three_observation(validation),
                )

                if not _uses_error_theme_token(validation):
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=_error_theme_failure_observation(validation),
                    )
                    _mark_unreached_steps(result, first_unreached=5)
                    raise AssertionError(
                        "Step 4 failed: the visible Summary-required validation message did "
                        "not use the expected TrackState error theme token.\n"
                        f"Validation payload: {_validation_payload(validation)}",
                    )

                if not _meets_text_contrast_requirement(validation):
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=_contrast_failure_observation(validation),
                    )
                    _mark_unreached_steps(result, first_unreached=5)
                    raise AssertionError(
                        "Step 4 failed: the visible Summary-required validation message did "
                        f"not meet the required {MIN_TEXT_CONTRAST}:1 text contrast ratio.\n"
                        f"Validation payload: {_validation_payload(validation)}",
                    )

                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=_step_four_observation(validation),
                )

                if not _has_accessible_announcement_path(validation):
                    _record_step(
                        result,
                        step=5,
                        status="failed",
                        action=REQUEST_STEPS[4],
                        observed=_accessibility_failure_observation(validation),
                    )
                    raise AssertionError(
                        "Step 5 failed: the Summary-required validation feedback did not "
                        "expose a detectable assistive-technology announcement path such as "
                        "a linked error description, a live region containing the error, or "
                        "focus moving to the error content.\n"
                        f"Validation payload: {_validation_payload(validation)}",
                    )

                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=REQUEST_STEPS[4],
                    observed=_step_five_observation(validation),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Clicked Save with an empty Summary and inspected both the visible "
                        "validation message and the accessibility feedback exposed to the "
                        "focused control."
                    ),
                    observed=(
                        f"Visible validation text: {_validation_texts(validation)}; "
                        f"focus: {_focused_element_summary(validation)}; "
                        f"live regions: {list(validation.live_region_texts)!r}"
                    ),
                )

                tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)


def _assert_preconditions(issue_fixture: LiveHostedIssueFixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-887 expected the seeded DEMO-2 issue fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )


def _field_payload(field: LabeledTextFieldObservation) -> dict[str, object]:
    return {
        "label": field.label,
        "value": field.value,
        "enabled": field.enabled,
        "disabled": field.disabled,
        "read_only": field.read_only,
        "aria_label": field.aria_label,
        "aria_invalid": field.aria_invalid,
        "aria_describedby": field.aria_describedby,
        "aria_errormessage": field.aria_errormessage,
        "outer_html": field.outer_html,
    }


def _summary_field_failure_observation(field: LabeledTextFieldObservation) -> str:
    return (
        "The visible Summary input existed inside the Edit issue dialog, but it was not "
        f"editable. enabled={field.enabled}, disabled={field.disabled}, "
        f"read_only={field.read_only}, value={field.value!r}, "
        f"aria_invalid={field.aria_invalid!r}, "
        f"aria_describedby={field.aria_describedby!r}, "
        f"aria_errormessage={field.aria_errormessage!r}."
    )


def _validation_payload(
    validation: SummaryRequiredValidationObservation,
) -> dict[str, object]:
    return {
        "field": _field_payload(validation.field),
        "message": (
            None
            if validation.message is None
            else {
                "text": validation.message.text,
                "tag_name": validation.message.tag_name,
                "role": validation.message.role,
                "aria_live": validation.message.aria_live,
                "element_id": validation.message.element_id,
                "color": validation.message.color,
                "background_color": validation.message.background_color,
                "contrast_ratio": validation.message.contrast_ratio,
            }
        ),
        "describedby_texts": list(validation.describedby_texts),
        "errormessage_texts": list(validation.errormessage_texts),
        "live_region_texts": list(validation.live_region_texts),
        "active_element": {
            "tag_name": validation.active_element.tag_name,
            "role": validation.active_element.role,
            "accessible_name": validation.active_element.accessible_name,
            "text": validation.active_element.text,
            "tabindex": validation.active_element.tabindex,
            "outer_html": validation.active_element.outer_html,
        },
        "field_is_active": validation.field_is_active,
        "dialog_text": validation.dialog_text,
    }


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").split())


def _contains_summary_required(value: str | None) -> bool:
    return SUMMARY_REQUIRED_FRAGMENT.lower() in _normalize_text(value).lower()


def _validation_texts(
    validation: SummaryRequiredValidationObservation,
) -> tuple[str, ...]:
    texts: list[str] = []
    if validation.message is not None and validation.message.text:
        texts.append(validation.message.text)
    texts.extend(validation.describedby_texts)
    texts.extend(validation.errormessage_texts)
    texts.extend(validation.live_region_texts)
    deduped: list[str] = []
    for value in texts:
        normalized = _normalize_text(value)
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    return tuple(deduped)


def _validation_message_matches(
    validation: SummaryRequiredValidationObservation,
) -> bool:
    return any(_contains_summary_required(value) for value in _validation_texts(validation))


def _step_two_observation(validation: SummaryRequiredValidationObservation) -> str:
    return (
        "Clicking Save kept the Edit issue dialog open and surfaced an observable "
        f"validation state. Summary field payload: {_field_payload(validation.field)}; "
        f"focused element: {_focused_element_summary(validation)}"
    )


def _step_three_observation(validation: SummaryRequiredValidationObservation) -> str:
    return (
        "The hosted Edit issue dialog exposed the expected Summary-required feedback. "
        f"Observed validation texts: {_validation_texts(validation)!r}"
    )


def _missing_validation_message_observation(
    validation: SummaryRequiredValidationObservation,
) -> str:
    return (
        "Clicking Save exposed a validation state, but the visible/associated feedback did "
        f"not contain {SUMMARY_REQUIRED_FRAGMENT!r}. "
        f"Observed validation texts: {_validation_texts(validation)!r}; "
        f"focused element: {_focused_element_summary(validation)}"
    )


def _meets_text_contrast_requirement(
    validation: SummaryRequiredValidationObservation,
) -> bool:
    return (
        validation.message is not None
        and validation.message.contrast_ratio is not None
        and validation.message.contrast_ratio >= MIN_TEXT_CONTRAST
    )


def _uses_error_theme_token(validation: SummaryRequiredValidationObservation) -> bool:
    if validation.message is None:
        return False
    normalized_color = _normalized_css_color_hex(validation.message.color)
    return normalized_color in EXPECTED_ERROR_THEME_HEXES


def _parse_css_color(value: str | None) -> RgbColor | None:
    normalized = _normalize_text(value).lower()
    if not normalized:
        return None
    if normalized.startswith("#"):
        hex_value = normalized.removeprefix("#")
        if len(hex_value) == 3:
            hex_value = "".join(character * 2 for character in hex_value)
        if len(hex_value) != 6:
            return None
        try:
            return (
                int(hex_value[0:2], 16),
                int(hex_value[2:4], 16),
                int(hex_value[4:6], 16),
            )
        except ValueError:
            return None
    match = re.fullmatch(
        r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*(?:0|1|0?\.\d+))?\s*\)",
        normalized,
    )
    if match is None:
        return None
    red, green, blue = (int(group) for group in match.groups())
    if any(channel > 255 for channel in (red, green, blue)):
        return None
    return red, green, blue


def _normalized_css_color_hex(value: str | None) -> str | None:
    parsed = _parse_css_color(value)
    if parsed is None:
        return None
    return rgb_to_hex(parsed).lower()


def _error_theme_failure_observation(
    validation: SummaryRequiredValidationObservation,
) -> str:
    if validation.message is None:
        return (
            "No visible validation message element was available to confirm the expected "
            "TrackState error theme token after Save was clicked."
        )
    normalized_color = _normalized_css_color_hex(validation.message.color)
    return (
        "The visible Summary-required validation text did not use the expected "
        "TrackState error theme token. "
        f"text={validation.message.text!r}, rendered_color={validation.message.color!r}, "
        f"normalized_color={normalized_color!r}, "
        f"expected_error_colors={sorted(EXPECTED_ERROR_THEME_HEXES)!r}, "
        f"background={validation.message.background_color!r}."
    )


def _contrast_failure_observation(
    validation: SummaryRequiredValidationObservation,
) -> str:
    if validation.message is None:
        return (
            "No visible validation message element was available to measure contrast after "
            "Save was clicked."
        )
    return (
        "The visible Summary-required validation text did not meet WCAG AA text contrast. "
        f"text={validation.message.text!r}, contrast_ratio={validation.message.contrast_ratio}, "
        f"foreground={validation.message.color!r}, "
        f"background={validation.message.background_color!r}."
    )


def _step_four_observation(validation: SummaryRequiredValidationObservation) -> str:
    assert validation.message is not None
    normalized_color = _normalized_css_color_hex(validation.message.color)
    return (
        "The visible Summary-required validation text used the expected TrackState error "
        "theme token and met WCAG AA contrast. "
        f"text={validation.message.text!r}, contrast_ratio={validation.message.contrast_ratio:.2f}:1, "
        f"foreground={validation.message.color!r}, normalized_foreground={normalized_color!r}, "
        f"background={validation.message.background_color!r}."
    )


def _has_accessible_announcement_path(
    validation: SummaryRequiredValidationObservation,
) -> bool:
    return bool(_announcement_paths(validation))


def _announcement_paths(
    validation: SummaryRequiredValidationObservation,
) -> tuple[str, ...]:
    paths: list[str] = []
    if any(_contains_summary_required(text) for text in validation.live_region_texts):
        paths.append("live region")
    if any(_contains_summary_required(text) for text in validation.describedby_texts):
        paths.append("aria-describedby")
    if any(_contains_summary_required(text) for text in validation.errormessage_texts):
        paths.append("aria-errormessage")
    focused_text_candidates = (
        validation.active_element.accessible_name,
        validation.active_element.text,
    )
    if any(_contains_summary_required(text) for text in focused_text_candidates):
        paths.append("focus on error content")
    return tuple(paths)


def _accessibility_failure_observation(
    validation: SummaryRequiredValidationObservation,
) -> str:
    return (
        "The Summary-required validation feedback did not expose a reliable assistive-"
        "technology announcement path. "
        f"aria_invalid={validation.field.aria_invalid!r}, "
        f"aria_describedby={validation.field.aria_describedby!r}, "
        f"aria_errormessage={validation.field.aria_errormessage!r}, "
        f"describedby_texts={list(validation.describedby_texts)!r}, "
        f"errormessage_texts={list(validation.errormessage_texts)!r}, "
        f"live_region_texts={list(validation.live_region_texts)!r}, "
        f"focused element: {_focused_element_summary(validation)}"
    )


def _step_five_observation(validation: SummaryRequiredValidationObservation) -> str:
    return (
        "The Summary-required validation feedback exposed the error text to assistive "
        f"technology via {', '.join(_announcement_paths(validation))}. "
        f"aria_invalid={validation.field.aria_invalid!r}, "
        f"describedby_texts={list(validation.describedby_texts)!r}, "
        f"errormessage_texts={list(validation.errormessage_texts)!r}, "
        f"live_region_texts={list(validation.live_region_texts)!r}, "
        f"focused element: {_focused_element_summary(validation)}"
    )


def _focused_element_summary(validation: SummaryRequiredValidationObservation) -> str:
    active = validation.active_element
    return (
        f"tag={active.tag_name!r}, role={active.role!r}, "
        f"accessible_name={active.accessible_name!r}, text={active.text!r}, "
        f"field_is_active={validation.field_is_active}"
    )


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
            observed="Not reached because the production UI failed the earlier required step.",
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
    _write_review_replies()


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
    _write_review_replies()


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        "* Opened the deployed hosted TrackState app.",
        "* Connected the live session with the configured GitHub token until the write-capable connected banner appeared.",
        "* Opened the live Edit issue surface for DEMO-2.",
        "* Attempted the required user flow: clear Summary, click Save, inspect the Summary-required feedback, check contrast, and verify the accessibility announcement path.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the hosted Edit issue flow exposed visible Summary-required validation feedback, the visible message met WCAG AA contrast, and the error text was reachable to assistive technology."
            if passed
            else f"* Did not match the expected result. {_failure_summary(result)}"
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
        "### Rework updates",
        "- Matched Summary-validation message discovery to the ticket fragment `Summary is required`, so compliant shorter copy is still detected for contrast measurement.",
        "- Tightened the accessibility assertion so Step 5 now requires the error text itself to be reachable through `aria-describedby`, `aria-errormessage`, a live region, or focused error content.",
        "- Added an error-token assertion so the visible validation text must render with the TrackState error theme color (`#c25742` light / `#e8a085` dark), not just any readable color.",
        "- Added the standard pass-path artifact writer, stale bug cleanup, and review-reply output so the workflow can record a real pass once the product bug is fixed.",
        "",
        "### Automation",
        "- Opened the deployed hosted TrackState app.",
        "- Connected the live session with the configured GitHub token until the connected banner appeared.",
        "- Opened the live `Edit issue` surface for `DEMO-2`.",
        "- Exercised the ticket flow: cleared `Summary`, clicked `Save`, inspected the `Summary is required` feedback, checked contrast, and checked the accessibility announcement path.",
        "",
        "### Observed result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failure_summary(result)}"
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
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {TICKET_KEY} rework {status}",
        "",
        "*Fixes applied*",
        "* Relaxed visible-message discovery to the ticket fragment {{Summary is required}} so compliant shorter copy is still measured.",
        "* Tightened Step 5 so the error text itself must be reachable via ARIA linkage, a live region, or focused error content.",
        "* Added an assertion that the visible validation text uses the TrackState error theme token colors (`#c25742` / `#e8a085`) rather than any arbitrary high-contrast color.",
        "* Added pass-path artifact writing plus stale bug cleanup and review replies.",
        "",
        "*New test result*",
        (
            "* PASSED — the hosted Edit issue validation flow now meets the ticket requirements end to end."
            if passed
            else f"* FAILED — {_failure_summary(result)}"
        ),
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


def _write_review_replies() -> None:
    REVIEW_REPLIES_PATH.write_text(
        json.dumps(
            {
                "replies": [
                    {
                        "inReplyToId": 3282755133,
                        "threadId": "PRRT_kwDOSU6Gf86D3eir",
                        "reply": (
                            "Fixed: Step 4 now asserts the visible Summary validation text uses "
                            "the TrackState error theme token, normalizing the computed CSS "
                            "foreground color and requiring the expected error values "
                            "(`#c25742` in light mode or `#e8a085` in dark mode`) before the "
                            "contrast check can pass."
                        ),
                    },
                    {
                        "inReplyToId": 3282703459,
                        "threadId": "PRRT_kwDOSU6Gf86D3VGB",
                        "reply": (
                            "Fixed: the Summary validation probe now discovers the visible message using the ticket fragment `Summary is required` instead of the stricter full sentence, so compliant shorter copy is still captured for the contrast and accessibility checks."
                        ),
                    },
                    {
                        "inReplyToId": 3282703608,
                        "threadId": "PRRT_kwDOSU6Gf86D3VH4",
                        "reply": (
                            "Fixed: Step 5 no longer treats `aria-invalid` plus focus on the Summary field as sufficient. It now requires the error text itself to be reachable through `aria-describedby`, `aria-errormessage`, a live region, or focused error content."
                        ),
                    },
                    {
                        "inReplyToId": 3282703774,
                        "threadId": "PRRT_kwDOSU6Gf86D3VJz",
                        "reply": (
                            "Fixed: TS-887 now writes the standard pass artifacts on success (`test_automation_result.json`, `response.md`, `pr_body.md`, review replies), and it removes any stale `bug_description.md` when the scenario passes."
                        ),
                    },
                ]
            },
        )
        + "\n",
        encoding="utf-8",
    )


def _failure_summary(result: dict[str, object]) -> str:
    step = _first_failed_step(result)
    if step is not None:
        return str(step.get("observed", result.get("error", "The scenario failed.")))
    return str(result.get("error", "The scenario failed."))


def _first_failed_step(result: dict[str, object]) -> dict[str, object] | None:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("status") == "failed":
            return step
    return None


def _bug_description(result: dict[str, object]) -> str:
    failing_step = _first_failed_step(result)
    missing_capability = (
        "The hosted Edit issue surface does not expose a production-usable path to trigger and verify Summary validation feedback."
        if failing_step is None
        else f"The hosted Edit issue surface failed at Step {failing_step.get('step')}: {failing_step.get('action')}"
    )
    lines = [
        f"# {TICKET_KEY} - Hosted Edit issue Summary validation does not meet the ticket requirements",
        "",
        "## Steps to reproduce",
        "1. Clear the content of the `Summary` field.",
        f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
        "2. Click the `Save` button to trigger validation.",
        f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
        "3. Inspect the resulting error message (`Summary is required`).",
        f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
        "4. Verify the error message meets WCAG AA contrast (4.5:1).",
        f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
        "5. Use a screen reader to verify that the error is announced.",
        f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
        "",
        "## Actual vs Expected",
        "- Expected: the live Edit issue surface lets the user clear Summary, click Save, see the visible `Summary is required` validation message, and verify its contrast/accessibility behavior.",
        f"- Actual: {_failure_summary(result)}",
        f"- Missing/broken production capability: {missing_capability}",
        "",
        "## Failing command",
        "```bash",
        RUN_COMMAND,
        "```",
        "",
        "## Exact error message",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Environment",
        f"- URL: `{result['app_url']}`",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
        f"- Issue: `{result.get('issue_key', '')}` (`{result.get('issue_path', '')}`)",
        "- Browser: `Chromium (Playwright)`",
        f"- OS: `{platform.platform()}`",
        "",
        "## Evidence",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
        "",
        "## Observed body text at failure",
        "```text",
        str(
            result.get(
                "post_step_2_body_text",
                result.get("edit_dialog_text", result.get("runtime_body_text", "")),
            )
        ),
        "```",
        "",
        "## Observed Summary field payload",
        "```json",
        json.dumps(result.get("summary_field", {}), indent=2, sort_keys=True),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — {step['status']}: {step['observed']}"
        )
    if not lines:
        lines.append("# No step details were recorded." if jira else "1. No step details were recorded.")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for entry in result.get("human_verification", []):
        if not isinstance(entry, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(f"{prefix} {entry['check']} Observed: {entry['observed']}")
    if not lines:
        lines.append(
            "* No human-style verification was recorded."
            if jira
            else "- No human-style verification was recorded."
        )
    return lines


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", "No observation recorded."))
    return str(result.get("error", "No observation recorded."))


if __name__ == "__main__":
    main()
