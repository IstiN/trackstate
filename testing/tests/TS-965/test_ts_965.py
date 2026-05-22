from __future__ import annotations

from dataclasses import asdict
import json
import math
import platform
import re
import sys
import traceback
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.github_actions_page import GitHubActionsPageObservation  # noqa: E402
from testing.components.services.github_accessibility_alpha_blended_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityAlphaBlendedPullRequestGateProbeService,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (  # noqa: E402
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (  # noqa: E402
    GitHubActionsWorkflowJobObservation,
)
from testing.tests.support.github_accessibility_alpha_blended_pull_request_gate_probe_factory import (  # noqa: E402
    create_github_accessibility_alpha_blended_pull_request_gate_probe,
)
from testing.tests.support.github_actions_page_factory import (  # noqa: E402
    create_github_actions_page,
)

TICKET_KEY = "TS-965"
TEST_CASE_TITLE = (
    "Alpha-blended text contrast — accessibility audit identifies violations after layer flattening"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-965/test_ts_965.py"
TEST_FILE_PATH = "testing/tests/TS-965/test_ts_965.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-965/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
RUN_SCREENSHOT_PATH = OUTPUTS_DIR / "ts965_run_page.png"
THEME_FILE_PATH = REPO_ROOT / "lib" / "ui" / "core" / "trackstate_theme.dart"

REQUEST_STEPS = [
    (
        "Create a Pull Request that introduces a UI component using an alpha-blended color "
        "(for example `onSurface.withAlpha(89)`) on a solid background surface."
    ),
    "Ensure the resulting flattened contrast ratio is mathematically below the 4.5:1 WCAG AA threshold.",
    "Push the changes to trigger the CI pipeline.",
    "Review the results and logs of the 'Accessibility checks' job.",
]
EXPECTED_RESULT = (
    "The accessibility audit correctly calculates the luminosity ratio for the alpha-blended "
    "layer, the contrast assertion fails, and the CI job reports a failure status."
)
FAILURE_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required"}
ACCESSIBILITY_JOB_MARKERS = ["Accessibility checks", "accessibility"]
HUMAN_PAGE_TEXT_PATTERNS = (
    re.compile(r"Accessibility checks", re.IGNORECASE),
    re.compile(r"Failed|Failure|failing", re.IGNORECASE),
    re.compile(r"Flutter Required Checks", re.IGNORECASE),
)
STRONG_CONTRAST_FAILURE_PATTERNS = (
    re.compile(r"color-contrast", re.IGNORECASE),
    re.compile(r"contrast ratio", re.IGNORECASE),
    re.compile(r"below\s+4\.5:1", re.IGNORECASE),
    re.compile(r"4\.5:1", re.IGNORECASE),
    re.compile(r"meetsGuideline\(textContrastGuideline\)", re.IGNORECASE),
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_config = _load_yaml(CONFIG_PATH)
    runtime_inputs = raw_config.get("runtime_inputs", {})
    assert isinstance(runtime_inputs, dict)
    config = GitHubAccessibilityPullRequestGateConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_alpha_blended_pull_request_gate_probe(
        REPO_ROOT,
        config_path=CONFIG_PATH,
    )
    ui_timeout_seconds = _positive_int(runtime_inputs, "ui_timeout_seconds", default=60)

    theme_pair = _load_light_theme_surface_pair(THEME_FILE_PATH)
    flattened_foreground = _flatten_rgba(
        foreground=theme_pair["on_surface_rgb"],
        background=theme_pair["surface_rgb"],
        alpha=GitHubAccessibilityAlphaBlendedPullRequestGateProbeService.alpha_value / 255,
    )
    flattened_ratio = _contrast_ratio(flattened_foreground, theme_pair["surface_rgb"])

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "run_command": RUN_COMMAND,
        "test_file_path": TEST_FILE_PATH,
        "expected_result": EXPECTED_RESULT,
        "repository": config.repository,
        "default_branch": config.base_branch,
        "target_workflow_name": config.target_workflow_name,
        "target_workflow_path": config.target_workflow_path,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "theme_surface_hex": theme_pair["surface_hex"],
        "theme_on_surface_hex": theme_pair["on_surface_hex"],
        "alpha_value": GitHubAccessibilityAlphaBlendedPullRequestGateProbeService.alpha_value,
        "expected_semantic_label": (
            GitHubAccessibilityAlphaBlendedPullRequestGateProbeService.expected_semantic_label
        ),
        "flattened_foreground_hex": _rgb_to_hex(flattened_foreground),
        "flattened_contrast_ratio": round(flattened_ratio, 4),
        "steps": [],
        "human_verification": [],
    }

    try:
        observation = probe.validate()
        result.update(observation.to_dict())

        accessibility_job = _find_matching_job(
            list(observation.observed_run_jobs),
            ACCESSIBILITY_JOB_MARKERS,
        )
        run_page, run_page_error = _open_run_page(
            observation=observation,
            accessibility_job=accessibility_job,
            timeout_seconds=ui_timeout_seconds,
        )
        result["accessibility_job"] = (
            None if accessibility_job is None else asdict(accessibility_job)
        )
        result["run_page"] = None if run_page is None else asdict(run_page)
        result["run_page_error"] = run_page_error

        failures: list[str] = []
        _evaluate_probe_pull_request(result, observation=observation, failures=failures)
        _evaluate_flattened_ratio(result, flattened_ratio=flattened_ratio, failures=failures)
        _evaluate_ci_trigger(result, observation=observation, failures=failures)
        _evaluate_accessibility_failure(
            result,
            observation=observation,
            accessibility_job=accessibility_job,
            run_page=run_page,
            run_page_error=run_page_error,
            failures=failures,
        )

        if failures:
            raise AssertionError("\n\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-965 passed")


def _evaluate_probe_pull_request(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    if observation.pull_request_probe_path not in observation.pull_request_file_paths:
        step_failures.append(
            f"GitHub did not record the expected alpha-blended probe file `{observation.pull_request_probe_path}`."
        )
    if not observation.probe_rendered_in_application:
        step_failures.append(
            "the disposable PR did not wire the alpha-blended probe into a rendered application surface."
        )
    if not observation.probe_contains_low_contrast_indicator:
        step_failures.append(
            "the disposable PR probe did not include the requested `withAlpha(89)` contrast signal."
        )
    if (
        observation.probe_semantic_label
        != GitHubAccessibilityAlphaBlendedPullRequestGateProbeService.expected_semantic_label
    ):
        step_failures.append(
            "the disposable PR probe did not preserve the expected descriptive semantics label."
        )

    if step_failures:
        message = (
            "Step 1 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Observed PR files: {observation.pull_request_file_paths}\n"
            + f"Observed probe label: {observation.probe_semantic_label!r}\n"
            + f"Probe technique: {observation.probe_contrast_technique}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Created a disposable PR with a rendered alpha-blended probe using "
        "`colorScheme.onSurface.withAlpha(89)` on `colorScheme.surface` and a descriptive "
        "semantics label.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Observed PR files: {observation.pull_request_file_paths}\n"
        f"Observed probe label: {observation.probe_semantic_label!r}\n"
        f"Probe technique: {observation.probe_contrast_technique}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_flattened_ratio(
    result: dict[str, object],
    *,
    flattened_ratio: float,
    failures: list[str],
) -> None:
    if flattened_ratio >= 4.5:
        message = (
            "Step 2 failed: independently flattening the alpha-blended foreground against the "
            "current production surface did not fall below the WCAG AA 4.5:1 threshold.\n"
            f"Theme onSurface: {result['theme_on_surface_hex']}\n"
            f"Theme surface: {result['theme_surface_hex']}\n"
            f"Flattened foreground: {result['flattened_foreground_hex']}\n"
            f"Flattened ratio: {result['flattened_contrast_ratio']}:1"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "Resolved the current production light-theme colors and independently verified that the "
        "flattened alpha-blended foreground stays below WCAG AA.\n"
        f"Theme onSurface: {result['theme_on_surface_hex']}\n"
        f"Theme surface: {result['theme_surface_hex']}\n"
        f"Flattened foreground: {result['flattened_foreground_hex']}\n"
        f"Flattened ratio: {result['flattened_contrast_ratio']}:1"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_ci_trigger(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    step_failures: list[str] = []
    if observation.latest_pull_request_run_id is None:
        step_failures.append(
            "GitHub Actions did not expose a contributor-visible `pull_request` run for the disposable PR."
        )
    if observation.latest_pull_request_run_event != "pull_request":
        step_failures.append(
            f"the observed workflow event was `{observation.latest_pull_request_run_event or '<none>'}` instead of `pull_request`."
        )

    if step_failures:
        message = (
            "Step 3 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"Observed branch runs: {observation.observed_branch_run_names}\n"
            + f"Observed run URLs: {observation.observed_branch_run_urls}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        "Pushed the disposable PR branch and observed the live pull-request workflow run.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Status: {observation.latest_pull_request_run_status}\n"
        f"Conclusion: {observation.latest_pull_request_run_conclusion or '<pending>'}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


def _evaluate_accessibility_failure(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    accessibility_job: GitHubActionsWorkflowJobObservation | None,
    run_page: GitHubActionsPageObservation | None,
    run_page_error: str | None,
    failures: list[str],
) -> None:
    _record_human_verification(
        result,
        check=(
            "Reviewed the contributor-visible GitHub Actions run page plus the live workflow "
            "jobs, status checks, and log excerpt for the alpha-blended contrast scenario."
        ),
        observed=(
            f"Run page: `{observation.latest_pull_request_run_url or '<none>'}`; accessibility job: "
            f"{_single_job_summary(accessibility_job)}; status checks: "
            f"{observation.observed_status_check_names or ['<none>']}; failed checks: "
            f"{observation.failed_status_check_names or ['<none>']}; run-log contrast markers: "
            f"{observation.run_log_matched_contrast_markers or ['<none>']}; run-log excerpt: "
            f"`{observation.run_log_excerpt or '<none>'}`; screenshot: "
            f"`{run_page.screenshot_path if run_page is not None else '<none>'}`."
        ),
    )

    step_failures: list[str] = []
    if observation.run_log_error:
        step_failures.append(
            f"the hosted workflow logs could not be read (`{observation.run_log_error}`)."
        )

    accessibility_failure_visible = (
        (observation.accessibility_status_check_conclusion or "").lower() in FAILURE_CONCLUSIONS
        or (
            accessibility_job is not None
            and (accessibility_job.conclusion or "").lower() in FAILURE_CONCLUSIONS
        )
    )
    if not accessibility_failure_visible:
        step_failures.append(
            "the contributor-visible CI surface did not report a failing `Accessibility checks` outcome."
        )

    if not _has_strong_contrast_failure_evidence(observation):
        step_failures.append(
            "the live workflow log did not expose contrast-failure evidence for the alpha-blended probe."
        )

    if run_page is None:
        step_failures.append(
            "the GitHub Actions run page could not be opened for human-style verification "
            f"({run_page_error or 'unknown error'})."
        )
    else:
        if not run_page.screenshot_path:
            step_failures.append(
                "the GitHub Actions run page opened, but no screenshot was captured."
            )
        visible_body = run_page.body_text
        if not all(pattern.search(visible_body) for pattern in HUMAN_PAGE_TEXT_PATTERNS):
            step_failures.append(
                "the visible GitHub Actions page text did not clearly show the failing accessibility run."
            )

    if step_failures:
        message = (
            "Step 4 failed: "
            + " ".join(step_failures)
            + "\n"
            + f"Pull Request URL: {observation.pull_request_url}\n"
            + f"PR checks URL: {observation.pull_request_checks_url}\n"
            + f"Run URL: {observation.latest_pull_request_run_url or '<none>'}\n"
            + f"Accessibility job: {_single_job_summary(accessibility_job)}\n"
            + "Accessibility check conclusion: "
            + f"{observation.accessibility_status_check_conclusion or '<none>'}\n"
            + f"Run conclusion: {observation.latest_pull_request_run_conclusion or '<none>'}\n"
            + f"Observed status checks: {observation.observed_status_check_names or ['<none>']}\n"
            + f"Failed status checks: {observation.failed_status_check_names or ['<none>']}\n"
            + f"Run-log contrast markers: {observation.run_log_matched_contrast_markers or ['<none>']}\n"
            + f"Run log error: {observation.run_log_error or '<none>'}\n"
            + f"Run log excerpt: {observation.run_log_excerpt or '<none>'}\n"
            + f"Run page error: {run_page_error or '<none>'}\n"
            + "Run page visible text: "
            + f"{_snippet(run_page.body_text if run_page is not None else '', limit=1200)}\n"
            + "Screenshot: "
            + f"{run_page.screenshot_path if run_page is not None else '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=4, status="failed", action=REQUEST_STEPS[3], observed=message)
        return

    observed = (
        "The live accessibility surface reported the alpha-blended contrast failure and the "
        "GitHub Actions run page visibly showed the failing workflow.\n"
        f"Accessibility job: {_single_job_summary(accessibility_job)}\n"
        "Accessibility check conclusion: "
        f"{observation.accessibility_status_check_conclusion or '<none>'}\n"
        f"Run-log contrast markers: {observation.run_log_matched_contrast_markers}\n"
        f"Run page screenshot: {run_page.screenshot_path or '<none>'}"
    )
    _record_step(result, step=4, status="passed", action=REQUEST_STEPS[3], observed=observed)


def _open_run_page(
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    accessibility_job: GitHubActionsWorkflowJobObservation | None,
    timeout_seconds: int,
) -> tuple[GitHubActionsPageObservation | None, str | None]:
    if observation.latest_pull_request_run_url is None:
        return None, "The workflow run URL is missing."
    expected_texts = [
        observation.target_workflow_name,
        "Accessibility checks",
        "Failed",
    ]
    if accessibility_job is not None and accessibility_job.name:
        expected_texts.append(accessibility_job.name)
    try:
        with create_github_actions_page() as actions_page:
            return (
                actions_page.open_page(
                    url=observation.latest_pull_request_run_url,
                    expected_texts=tuple(dict.fromkeys(expected_texts)),
                    screenshot_path=str(RUN_SCREENSHOT_PATH),
                    timeout_seconds=timeout_seconds,
                ),
                None,
            )
    except Exception as error:  # noqa: BLE001
        return None, f"{type(error).__name__}: {error}"


def _find_matching_job(
    jobs: list[GitHubActionsWorkflowJobObservation],
    markers: list[str],
) -> GitHubActionsWorkflowJobObservation | None:
    normalized_markers = [marker.lower() for marker in markers if marker.strip()]
    for job in jobs:
        haystack = " ".join(
            value
            for value in (job.name, job.status, job.conclusion)
            if isinstance(value, str) and value
        ).lower()
        if any(marker in haystack for marker in normalized_markers):
            return job
    return None


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must deserialize to a mapping.")
    return payload


def _positive_int(payload: dict[str, object], key: str, *, default: int) -> int:
    value = payload.get(key, default)
    return value if isinstance(value, int) and value > 0 else default


def _has_strong_contrast_failure_evidence(
    observation: GitHubAccessibilityPullRequestGateObservation,
) -> bool:
    excerpt = observation.run_log_excerpt or ""
    markers = observation.run_log_matched_contrast_markers or []
    if any(
        marker in {"color-contrast", "contrast ratio", "below 4.5", "4.5:1"}
        for marker in markers
    ):
        return True
    return any(pattern.search(excerpt) for pattern in STRONG_CONTRAST_FAILURE_PATTERNS)


def _load_light_theme_surface_pair(path: Path) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    light_match = re.search(
        r"static const light = TrackStateColors\((?P<body>.*?)\);\n\n  static const dark",
        source,
        re.DOTALL,
    )
    if light_match is None:
        raise AssertionError(f"Could not locate TrackStateColors.light in {path}.")
    body = light_match.group("body")
    surface_hex = _require_theme_color(body, "surface")
    text_hex = _require_theme_color(body, "text")
    return {
        "surface_hex": surface_hex,
        "on_surface_hex": text_hex,
        "surface_rgb": _hex_to_rgb(surface_hex),
        "on_surface_rgb": _hex_to_rgb(text_hex),
    }


def _require_theme_color(body: str, name: str) -> str:
    match = re.search(rf"{name}:\s*Color\(0x([0-9A-Fa-f]{{8}})\)", body)
    if match is None:
        raise AssertionError(f"Could not locate `{name}` in TrackStateColors.light.")
    return f"#{match.group(1)[2:].upper()}"


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.removeprefix("#")
    return tuple(float(int(value[index : index + 2], 16)) for index in (0, 2, 4))


def _flatten_rgba(
    *,
    foreground: tuple[float, float, float],
    background: tuple[float, float, float],
    alpha: float,
) -> tuple[float, float, float]:
    return tuple(
        foreground[index] * alpha + background[index] * (1 - alpha)
        for index in range(3)
    )


def _contrast_ratio(
    foreground: tuple[float, float, float],
    background: tuple[float, float, float],
) -> float:
    foreground_luminance = _relative_luminance(foreground)
    background_luminance = _relative_luminance(background)
    lighter = max(foreground_luminance, background_luminance)
    darker = min(foreground_luminance, background_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    def _channel(value: float) -> float:
        normalized = value / 255
        if normalized <= 0.03928:
            return normalized / 12.92
        return math.pow((normalized + 0.055) / 1.055, 2.4)

    red, green, blue = rgb
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    channels = [max(0, min(255, round(value))) for value in rgb]
    return "#" + "".join(f"{channel:02X}" for channel in channels)


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
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-965 failed"))
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
        "* Created a disposable pull request against the live repository with a rendered alpha-blended contrast probe.",
        "* Resolved the current production light-theme colors and independently calculated the flattened contrast ratio.",
        "* Waited for the live pull-request GitHub Actions workflow run and inspected the status checks, jobs, logs, and run page.",
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
            f"* Environment: repository {{{{{result['repository']}}}}} @ "
            f"{{{{{result['default_branch']}}}}}, browser {{{{{result['browser']}}}}}, "
            f"OS {{{{{result['os']}}}}}."
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
            ]
        )
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
        "- Created a disposable pull request against the live repository with a rendered alpha-blended contrast probe.",
        "- Resolved the current production light-theme colors and independently calculated the flattened contrast ratio.",
        "- Waited for the live pull-request GitHub Actions workflow run and inspected the status checks, jobs, logs, and run page.",
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
            f"- Environment: repository `{result['repository']}` @ "
            f"`{result['default_branch']}`, browser `{result['browser']}`, OS `{result['os']}`."
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
            ]
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "## Test Automation Summary",
        "",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using `{result['browser']}` on `{result['os']}`."
        ),
        (
            "- Outcome: the live accessibility workflow failed on the alpha-blended contrast violation."
            if passed
            else f"- Outcome: {_failed_step_summary(result)}"
        ),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    steps = _steps_by_number(result)
    return "\n".join(
        [
            "# TS-965 - Alpha-blended contrast violation was not surfaced correctly by the live accessibility workflow",
            "",
            "## Steps to reproduce",
            _step_repro_line(1, steps, REQUEST_STEPS[0]),
            _step_repro_line(2, steps, REQUEST_STEPS[1]),
            _step_repro_line(3, steps, REQUEST_STEPS[2]),
            _step_repro_line(4, steps, REQUEST_STEPS[3]),
            "",
            "## Expected result",
            f"- {EXPECTED_RESULT}",
            "",
            "## Actual result",
            (
                "- The live workflow did not expose the expected failing accessibility outcome "
                "for the alpha-blended contrast probe. See the step evidence below for the "
                "exact contributor-visible status, log excerpt, and run page text."
            ),
            "",
            "## Actual vs expected",
            (
                f"- Expected: the flattened alpha-blended probe fails below 4.5:1 and the "
                f"`Accessibility checks` job reports failure."
            ),
            (
                f"- Actual: accessibility conclusion `{result.get('accessibility_status_check_conclusion', '<none>')}`, "
                f"overall run conclusion `{result.get('latest_pull_request_run_conclusion', '<none>')}`, "
                f"run-log contrast markers {result.get('run_log_matched_contrast_markers', [])}."
            ),
            "",
            "## Environment",
            f"- Repository: `{result.get('repository', '')}`",
            f"- Branch: `{result.get('default_branch', '')}`",
            f"- Pull Request: `{result.get('pull_request_url', '')}`",
            f"- Pull Request checks: `{result.get('pull_request_checks_url', '')}`",
            f"- Workflow run: `{result.get('latest_pull_request_run_url', '')}`",
            f"- Browser: `{result.get('browser', '')}`",
            f"- OS: `{result.get('os', '')}`",
            f"- Theme onSurface/surface: `{result.get('theme_on_surface_hex', '')}` on `{result.get('theme_surface_hex', '')}`",
            f"- Flattened foreground: `{result.get('flattened_foreground_hex', '')}`",
            f"- Flattened contrast ratio: `{result.get('flattened_contrast_ratio', '')}:1`",
            f"- Screenshot: `{_screenshot_path(result)}`",
            "",
            "## Relevant logs",
            "```text",
            str(result.get("run_log_excerpt", "<missing run log excerpt>")),
            "```",
            "",
            "## Exact error message / assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", "<missing traceback>"))),
            "```",
        ]
    ) + "\n"


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


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    steps = result.get("steps")
    if not isinstance(steps, list):
        return lines
    for entry in steps:
        if not isinstance(entry, dict):
            continue
        step = entry.get("step")
        status = str(entry.get("status", "")).upper()
        action = str(entry.get("action", ""))
        observed = str(entry.get("observed", ""))
        if jira:
            action = _jira_inline(action)
            observed = _jira_inline(observed)
        prefix = f"* Step {step} — {status}: " if jira else f"- Step {step} — {status}: "
        lines.append(prefix + action)
        detail_prefix = "* " if jira else "  - "
        lines.append(detail_prefix + observed)
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    checks = result.get("human_verification")
    if not isinstance(checks, list):
        return lines
    for entry in checks:
        if not isinstance(entry, dict):
            continue
        check = str(entry.get("check", ""))
        observed = str(entry.get("observed", ""))
        if jira:
            check = _jira_inline(check)
            observed = _jira_inline(observed)
            lines.append(f"* {check}")
            lines.append(f"* {observed}")
        else:
            lines.append(f"- {check}")
            lines.append(f"  - {observed}")
    return lines


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return "The test failed before step details were recorded."
    failed = [
        entry for entry in steps if isinstance(entry, dict) and entry.get("status") == "failed"
    ]
    if not failed:
        return "The test failed before a specific step result was recorded."
    first = failed[0]
    return f"Step {first.get('step')} failed. {first.get('observed', '')}"


def _jira_inline(text: str) -> str:
    return (
        text.replace("{", "\\{")
        .replace("}", "\\}")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def _single_job_summary(job: GitHubActionsWorkflowJobObservation | None) -> str:
    if job is None:
        return "<none>"
    return (
        f"name={job.name or '<none>'}, status={job.status or '<none>'}, "
        f"conclusion={job.conclusion or '<none>'}"
    )


def _snippet(text: str, *, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _steps_by_number(result: dict[str, object]) -> dict[int, dict[str, object]]:
    indexed: dict[int, dict[str, object]] = {}
    raw_steps = result.get("steps")
    if not isinstance(raw_steps, list):
        return indexed
    for entry in raw_steps:
        if not isinstance(entry, dict):
            continue
        step = entry.get("step")
        if isinstance(step, int):
            indexed[step] = entry
    return indexed


def _step_repro_line(
    step_number: int,
    steps: dict[int, dict[str, object]],
    action: str,
) -> str:
    entry = steps.get(step_number)
    if entry is None:
        return f"{step_number}. ❌ {action} — no step result was recorded."
    icon = "✅" if entry.get("status") == "passed" else "❌"
    observed = str(entry.get("observed", "")).strip() or "No observation recorded."
    return f"{step_number}. {icon} {action} — {observed}"


def _screenshot_path(result: dict[str, object]) -> str:
    run_page = result.get("run_page")
    if isinstance(run_page, dict):
        screenshot = run_page.get("screenshot_path")
        if isinstance(screenshot, str) and screenshot:
            return screenshot
    return "<none>"


if __name__ == "__main__":
    main()
