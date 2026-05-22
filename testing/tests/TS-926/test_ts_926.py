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

from testing.core.config.github_accessibility_boundary_pull_request_probe_config import (  # noqa: E402
    GitHubAccessibilityBoundaryPullRequestProbeConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (  # noqa: E402
    GitHubAccessibilityPullRequestGateObservation,
)
from testing.tests.support.github_accessibility_boundary_pull_request_probe_factory import (  # noqa: E402
    create_github_accessibility_boundary_pull_request_probe,
)

TICKET_KEY = "TS-926"
TEST_CASE_TITLE = (
    "UI element with exactly 4.5:1 contrast — axe-core audit identifies as compliant"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-926/test_ts_926.py"
TEST_FILE_PATH = "testing/tests/TS-926/test_ts_926.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-926/config.yaml"
OUTPUTS_DIR = REPO_ROOT / "outputs"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"
THEME_FILE_PATH = REPO_ROOT / "lib" / "ui" / "core" / "trackstate_theme.dart"

REQUEST_STEPS = [
    (
        "Create a Pull Request with a UI component where the text color and "
        "background color provide a contrast ratio of exactly 4.5:1."
    ),
    "Push the changes to trigger the CI pipeline.",
    "Review the logs of the Playwright accessibility audit.",
]
EXPECTED_RESULT = (
    "The axe-core scanner identifies the 4.5:1 ratio as compliant, the test "
    "returns a success exit code, and the CI gate passes."
)
SUCCESS_CONCLUSIONS = {"success"}


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    config = GitHubAccessibilityBoundaryPullRequestProbeConfig.from_file(CONFIG_PATH)
    probe = create_github_accessibility_boundary_pull_request_probe(
        REPO_ROOT,
        config_path=CONFIG_PATH,
    )

    contrast_ratio = _contrast_ratio(
        _parse_rgb(config.text_color),
        _parse_rgb(config.background_color),
    )
    theme_boundary = _load_light_theme_boundary_pair(THEME_FILE_PATH)
    resolved_ratio = _contrast_ratio(
        _parse_rgb(theme_boundary["text_color"]),
        _parse_rgb(theme_boundary["background_color"]),
    )
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
        "browser": "GitHub CLI",
        "os": platform.platform(),
        "exact_contrast_ratio": config.exact_contrast_ratio,
        "contrast_tolerance": config.contrast_tolerance,
        "configured_contrast_ratio": round(contrast_ratio, 4),
        "resolved_probe_text_color": theme_boundary["text_color"],
        "resolved_probe_background_color": theme_boundary["background_color"],
        "resolved_probe_contrast_ratio": round(resolved_ratio, 4),
        "text_color": config.text_color,
        "background_color": config.background_color,
        "visible_text": config.visible_text,
        "accessible_button_label": config.accessible_button_label,
        "probe_path": config.probe_path,
        "probe_render_host_path": config.probe_render_host_path,
        "steps": [],
        "human_verification": [],
    }

    try:
        observation = probe.validate()
        result.update(observation.to_dict())

        failures: list[str] = []
        _evaluate_probe_pull_request(result, config=config, observation=observation, failures=failures)
        _evaluate_live_ci_trigger(result, observation=observation, failures=failures)
        _evaluate_accessibility_audit_logs(result, observation=observation, failures=failures)

        if failures:
            raise AssertionError("\n".join(failures))
    except Exception as error:
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-926 passed")


def _evaluate_probe_pull_request(
    result: dict[str, object],
    *,
    config: GitHubAccessibilityBoundaryPullRequestProbeConfig,
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    configured_ratio = float(result["configured_contrast_ratio"])
    resolved_text_color = str(result["resolved_probe_text_color"])
    resolved_background_color = str(result["resolved_probe_background_color"])
    resolved_ratio = float(result["resolved_probe_contrast_ratio"])
    if observation.pull_request_probe_path not in observation.pull_request_file_paths:
        message = (
            "Step 1 failed: the disposable Pull Request was created, but GitHub did not "
            "report the expected boundary probe file on that PR.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Expected file: {observation.pull_request_probe_path}\n"
            f"Observed PR files: {observation.pull_request_file_paths}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    if observation.probe_render_host_path not in observation.pull_request_file_paths:
        message = (
            "Step 1 failed: the disposable Pull Request did not patch the app entrypoint to "
            "render the boundary probe through the production-visible app surface.\n"
            f"Expected render host: {observation.probe_render_host_path}\n"
            f"Observed PR files: {observation.pull_request_file_paths}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    if resolved_text_color != config.text_color or resolved_background_color != config.background_color:
        message = (
            "Step 1 failed: the live probe still renders from theme tokens, but the current "
            "production token values no longer match the TS-926 boundary pair.\n"
            f"Resolved probe foreground/background: {resolved_text_color} on {resolved_background_color}\n"
            f"Configured boundary pair: {config.text_color} on {config.background_color}\n"
            f"Theme file: {THEME_FILE_PATH}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    if abs(resolved_ratio - config.exact_contrast_ratio) > config.contrast_tolerance:
        message = (
            "Step 1 failed: the live probe theme-token pair does not stay on the required "
            "exact 4.5:1 contrast boundary.\n"
            f"Expected ratio: {config.exact_contrast_ratio}:1 (+/- {config.contrast_tolerance})\n"
            f"Resolved probe ratio: {resolved_ratio}:1\n"
            f"Resolved foreground/background: {resolved_text_color} on {resolved_background_color}\n"
            f"Theme file: {THEME_FILE_PATH}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    if config.accessible_button_label.strip().lower() in {"button", "click", "open", "go"}:
        message = (
            "Step 1 failed: the boundary probe control label is too generic to prove the "
            "ticket keeps the interactive control descriptive.\n"
            f"Configured label: {config.accessible_button_label!r}"
        )
        failures.append(message)
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=message)
        return

    observed = (
        "Created a disposable PR that patches the live app entrypoint to render the exact "
        "boundary probe through `context.ts.primary` on `context.ts.surfaceAlt`, then "
        "resolved those same production theme tokens from the repository before checking "
        "the boundary.\n"
        f"Pull Request URL: {observation.pull_request_url}\n"
        f"Probe file: {observation.pull_request_probe_path}\n"
        f"Render host: {observation.probe_render_host_path}\n"
        f"Configured visible text: {config.visible_text!r}\n"
        f"Configured button label: {config.accessible_button_label!r}\n"
        f"Resolved probe foreground/background: {resolved_text_color} on {resolved_background_color}\n"
        f"Resolved probe contrast ratio: {resolved_ratio}:1\n"
        f"Configured foreground/background: {config.text_color} on {config.background_color}\n"
        f"Configured contrast ratio: {configured_ratio}:1\n"
        "Probe contrast technique: "
        f"{observation.probe_contrast_technique}"
    )
    _record_step(result, step=1, status="passed", action=REQUEST_STEPS[0], observed=observed)


def _evaluate_live_ci_trigger(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    if observation.latest_pull_request_run_id is None:
        message = (
            "Step 2 failed: GitHub Actions did not expose a contributor-visible "
            "`pull_request` workflow run for the disposable PR branch.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Branch: {observation.pull_request_head_branch}\n"
            f"Observed branch runs: {observation.observed_branch_run_names}\n"
            f"Observed run URLs: {observation.observed_branch_run_urls}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    if observation.latest_pull_request_run_event != "pull_request":
        message = (
            "Step 2 failed: the observed workflow run was not triggered by the disposable "
            "Pull Request.\n"
            f"Run URL: {observation.latest_pull_request_run_url}\n"
            f"Observed event: {observation.latest_pull_request_run_event}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    if observation.latest_pull_request_run_conclusion not in SUCCESS_CONCLUSIONS:
        message = (
            "Step 2 failed: the live PR workflow did not pass for the exact-boundary probe.\n"
            f"Run URL: {observation.latest_pull_request_run_url}\n"
            f"Status: {observation.latest_pull_request_run_status}\n"
            f"Conclusion: {observation.latest_pull_request_run_conclusion}\n"
            f"Failed status checks: {observation.failed_status_check_names}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    if observation.accessibility_status_check_conclusion not in SUCCESS_CONCLUSIONS:
        message = (
            "Step 2 failed: the hosted accessibility check did not complete successfully for "
            "the disposable PR.\n"
            f"Run URL: {observation.latest_pull_request_run_url}\n"
            f"Accessibility check: {observation.accessibility_status_check_name or '<none>'}\n"
            f"Accessibility check status: {observation.accessibility_status_check_status or '<none>'}\n"
            "Accessibility check conclusion: "
            f"{observation.accessibility_status_check_conclusion or '<none>'}\n"
            f"Observed status checks: {observation.observed_status_check_names or ['<none>']}"
        )
        failures.append(message)
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=message)
        return

    observed = (
        "GitHub Actions executed the real PR workflow for the disposable boundary probe and "
        "the accessibility check completed successfully.\n"
        f"Run URL: {observation.latest_pull_request_run_url}\n"
        f"Status: {observation.latest_pull_request_run_status}\n"
        f"Conclusion: {observation.latest_pull_request_run_conclusion}\n"
        "Accessibility check conclusion: "
        f"{observation.accessibility_status_check_conclusion or '<none>'}\n"
        f"Observed status checks: {observation.observed_status_check_names or ['<none>']}"
    )
    _record_step(result, step=2, status="passed", action=REQUEST_STEPS[1], observed=observed)


def _evaluate_accessibility_audit_logs(
    result: dict[str, object],
    *,
    observation: GitHubAccessibilityPullRequestGateObservation,
    failures: list[str],
) -> None:
    _record_human_verification(
        result,
        check=(
            "Inspected the disposable PR checks surface and live workflow output through "
            "GitHub CLI (`gh pr view`, `gh run view --log`)."
        ),
        observed=(
            f"PR checks URL: `{observation.pull_request_checks_url}`; run URL: "
            f"`{observation.latest_pull_request_run_url}`; observed jobs: "
            f"{observation.observed_job_names or ['<none>']}; observed steps: "
            f"{observation.observed_step_names or ['<none>']}; status checks: "
            f"{observation.observed_status_check_names or ['<none>']}; accessibility "
            f"check conclusion: `{observation.accessibility_status_check_conclusion or '<none>'}`; "
            f"runtime accessibility evidence: "
            f"`{observation.runtime_accessibility_surface_summary or '<none>'}`; log excerpt: "
            f"`{observation.run_log_excerpt or '<none>'}`."
        ),
    )

    if observation.run_log_error:
        message = (
            "Step 3 failed: the automation could not read the hosted workflow logs for the "
            "real PR run.\n"
            f"Run URL: {observation.latest_pull_request_run_url}\n"
            f"Log error: {observation.run_log_error}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    if observation.accessibility_status_check_conclusion not in SUCCESS_CONCLUSIONS:
        message = (
            "Step 3 failed: the hosted accessibility audit did not report a successful "
            "accessibility check conclusion.\n"
            f"Run URL: {observation.latest_pull_request_run_url}\n"
            f"Accessibility check: {observation.accessibility_status_check_name or '<none>'}\n"
            f"Accessibility check conclusion: "
            f"{observation.accessibility_status_check_conclusion or '<none>'}\n"
            f"Log excerpt: {observation.run_log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    if not observation.matched_accessibility_markers:
        message = (
            "Step 3 failed: the hosted PR workflow surface did not expose accessibility-audit "
            "evidence in the jobs, steps, checks, or logs.\n"
            f"Observed jobs: {observation.observed_job_names}\n"
            f"Observed steps: {observation.observed_step_names}\n"
            f"Observed checks: {observation.observed_status_check_names}\n"
            f"Log excerpt: {observation.run_log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    if not observation.run_log_matched_accessibility_markers:
        message = (
            "Step 3 failed: the hosted accessibility audit never produced log-level axe-core "
            "evidence, so the PR surface alone cannot prove that the audit executed.\n"
            f"Run URL: {observation.latest_pull_request_run_url}\n"
            f"Observed steps: {observation.observed_step_names or ['<none>']}\n"
            f"Log excerpt: {observation.run_log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    if not observation.runtime_accessibility_surface_present:
        message = (
            "Step 3 failed: the hosted accessibility audit never exposed rendered "
            "accessibility output for the exact-boundary probe.\n"
            f"Run URL: {observation.latest_pull_request_run_url}\n"
            "Runtime accessibility evidence: "
            f"{observation.runtime_accessibility_surface_summary or '<none>'}\n"
            f"Log excerpt: {observation.run_log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    forbidden_markers = [
        *observation.run_log_matched_contrast_markers,
        *observation.run_log_matched_semantic_markers,
    ]
    if forbidden_markers:
        message = (
            "Step 3 failed: the hosted accessibility audit logs still reported violation "
            "markers for the exact-boundary probe.\n"
            f"Run URL: {observation.latest_pull_request_run_url}\n"
            f"Forbidden markers: {forbidden_markers}\n"
            f"Log excerpt: {observation.run_log_excerpt or '<none>'}"
        )
        failures.append(message)
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=message)
        return

    observed = (
        "Reviewed the hosted Playwright accessibility audit logs on the real PR workflow and "
        "confirmed the run stayed clean.\n"
        f"Matched accessibility markers: {observation.matched_accessibility_markers}\n"
        "Run-log accessibility markers: "
        f"{observation.run_log_matched_accessibility_markers}\n"
        "Runtime accessibility evidence: "
        f"{observation.runtime_accessibility_surface_summary}\n"
        f"Observed jobs: {observation.observed_job_names or ['<none>']}\n"
        f"Observed steps: {observation.observed_step_names or ['<none>']}\n"
        f"Run log excerpt: {observation.run_log_excerpt or '<none>'}"
    )
    _record_step(result, step=3, status="passed", action=REQUEST_STEPS[2], observed=observed)


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
    _write_review_replies(result, passed=True)
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-926 failed"))
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
    _write_review_replies(result, passed=False)
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Reworked TS-926 to create a disposable pull request and validate the live GitHub Actions PR workflow instead of replaying a local surrogate.",
        "- Moved the boundary probe generation into a reusable testing service so the ticket script depends on abstractions rather than Playwright internals.",
        "- Kept the disposable probe on production theme tokens and tied Step 1 to the actual rendered artifact by resolving `TrackStateColors.light.primary` and `surfaceAlt` before asserting the 4.5:1 boundary.",
        "- Inspected the hosted PR checks surface, workflow jobs/steps, and Playwright accessibility logs for the real CI outcome.",
        "",
        "## Human-style verification",
        *_human_lines(result),
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"- Environment: repository `{result['repository']}` @ "
            f"`{result['default_branch']}`, client `GitHub CLI`, OS `{result['os']}`."
        ),
        "",
        "## Step results",
        *_step_lines(result),
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
        "- Reworked TS-926 to validate the real PR-triggered GitHub Actions accessibility workflow instead of a local Playwright-only surrogate.",
        "- Moved the boundary probe behind a reusable testing service and removed the ticket-local raw Playwright spec layer.",
        "- Coupled Step 1 to the real disposable PR artifact by resolving the same production theme tokens that the probe renders, rather than proving the boundary from config alone.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['repository']}` @ `{result['default_branch']}` "
            f"using GitHub CLI on `{result['os']}`."
        ),
        (
            "- Outcome: the live PR pipeline treated the exact 4.5:1 boundary probe as compliant and the hosted accessibility audit stayed clean."
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


def _review_reply_text(*, result: dict[str, object], passed: bool) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{result.get('error', 'unknown error')}`."
    )
    return (
        "Fixed: Step 1 now stays coupled to the real disposable PR artifact by keeping the "
        "probe on `context.ts.primary` / `context.ts.surfaceAlt` and resolving those same "
        "production theme-token values from `trackstate_theme.dart` before asserting the "
        "exact 4.5:1 boundary. The rerun still requires a hosted accessibility check "
        "conclusion of `success` plus runtime accessibility evidence. "
        f"{rerun_summary}"
    )


def _bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# {TICKET_KEY} - Live PR accessibility workflow does not validate the exact 4.5:1 compliant boundary as expected",
            "",
            "## Steps to reproduce",
            "1. Create a Pull Request with a UI component where the text color and background color provide a contrast ratio of exactly 4.5:1.",
            "2. Push the changes to trigger the CI pipeline.",
            "3. Review the logs of the Playwright accessibility audit.",
            "",
            "## Exact test reproduction",
            (
                "1. The automation created a disposable PR, added "
                f"`{result.get('pull_request_probe_path', '')}`, and patched "
                f"`{result.get('probe_render_host_path', '')}` so the exact-boundary probe is "
                "rendered on app startup."
            ),
            (
                "2. GitHub Actions executed the contributor-visible PR workflow run "
                f"`{result.get('latest_pull_request_run_url', '')}` for that disposable PR."
            ),
            (
                "3. The PR checks surface "
                f"`{result.get('pull_request_checks_url', '')}` exposed status checks "
                f"{result.get('observed_status_check_names', [])} and workflow names "
                f"{result.get('observed_status_check_workflow_names', [])}."
            ),
            (
                "4. The hosted workflow did not demonstrate the expected clean accessibility "
                "result for the exact-boundary compliant probe."
            ),
            "",
            "## Expected result",
            f"- {EXPECTED_RESULT}",
            "",
            "## Actual result",
            (
                "- The live PR workflow or hosted accessibility audit logs did not show the "
                "expected passing CI outcome for the exact 4.5:1 compliant boundary probe."
            ),
            "",
            "## Missing or broken production capability",
            (
                "- The production CI pipeline or hosted accessibility reporting surface does "
                "not reliably expose the expected clean pass result for this compliant "
                "boundary case. From testing/ alone, the automation can create the disposable "
                "PR and inspect real runs/logs, but it cannot repair the missing or incorrect "
                "product behavior outside the testing layer."
            ),
            "",
            "## Environment",
            f"- Repository: `{result.get('repository', '')}`",
            f"- Branch: `{result.get('default_branch', '')}`",
            f"- Pull Request: `{result.get('pull_request_url', '')}`",
            f"- Pull Request checks: `{result.get('pull_request_checks_url', '')}`",
            f"- Workflow run: `{result.get('latest_pull_request_run_url', '')}`",
            f"- OS: `{result.get('os', '')}`",
            "",
            "## Failing command",
            "```bash",
            RUN_COMMAND,
            "```",
            "",
            "## Failing output",
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


def _step_lines(result: dict[str, object]) -> list[str]:
    lines: list[str] = []
    steps = result.get("steps")
    if not isinstance(steps, list):
        return lines
    for entry in steps:
        if not isinstance(entry, dict):
            continue
        lines.append(
            f"- Step {entry.get('step')} — {str(entry.get('status', '')).upper()}: "
            f"{entry.get('action', '')}"
        )
        lines.append(f"  - {entry.get('observed', '')}")
    return lines


def _human_lines(result: dict[str, object]) -> list[str]:
    lines: list[str] = []
    checks = result.get("human_verification")
    if not isinstance(checks, list):
        return lines
    for entry in checks:
        if not isinstance(entry, dict):
            continue
        lines.append(f"- {entry.get('check', '')}")
        lines.append(f"  - {entry.get('observed', '')}")
    return lines


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return str(result.get("error", "The automation failed."))
    failed = [
        entry
        for entry in steps
        if isinstance(entry, dict) and str(entry.get("status")) == "failed"
    ]
    if not failed:
        return str(result.get("error", "The automation failed."))
    first = failed[0]
    return f"Step {first.get('step')} failed. {first.get('observed', '')}"


def _parse_rgb(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(
        r"rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)",
        value.strip(),
        flags=re.IGNORECASE,
    )
    if match is None:
        raise ValueError(f"Unsupported RGB value: {value!r}")
    return tuple(int(channel) for channel in match.groups())


def _load_light_theme_boundary_pair(path: Path) -> dict[str, str]:
    theme_source = path.read_text(encoding="utf-8")
    light_match = re.search(
        r"static const light = TrackStateColors\((?P<body>.*?)\n\s*\);",
        theme_source,
        flags=re.DOTALL,
    )
    if light_match is None:
        raise ValueError(f"Could not locate TrackStateColors.light in {path}.")
    light_body = light_match.group("body")
    return {
        "text_color": _extract_theme_rgb(light_body, token_name="primary", path=path),
        "background_color": _extract_theme_rgb(light_body, token_name="surfaceAlt", path=path),
    }


def _extract_theme_rgb(body: str, *, token_name: str, path: Path) -> str:
    match = re.search(
        rf"{token_name}:\s*Color\(0x(?P<hex>[0-9A-Fa-f]{{8}})\)",
        body,
    )
    if match is None:
        raise ValueError(f"Could not locate TrackStateColors.light.{token_name} in {path}.")
    color_hex = match.group("hex")[-6:]
    return "rgb({red}, {green}, {blue})".format(
        red=int(color_hex[0:2], 16),
        green=int(color_hex[2:4], 16),
        blue=int(color_hex[4:6], 16),
    )


def _contrast_ratio(
    foreground: tuple[int, int, int],
    background: tuple[int, int, int],
) -> float:
    foreground_luminance = _relative_luminance(foreground)
    background_luminance = _relative_luminance(background)
    lighter = max(foreground_luminance, background_luminance)
    darker = min(foreground_luminance, background_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(color: tuple[int, int, int]) -> float:
    red, green, blue = color
    return (
        0.2126 * _normalize_srgb(red)
        + 0.7152 * _normalize_srgb(green)
        + 0.0722 * _normalize_srgb(blue)
    )


def _normalize_srgb(channel: int) -> float:
    normalized = channel / 255
    if normalized <= 0.04045:
        return normalized / 12.92
    return ((normalized + 0.055) / 1.055) ** 2.4


if __name__ == "__main__":
    main()
