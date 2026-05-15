from __future__ import annotations

from dataclasses import asdict
import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.core.interfaces.apple_release_toolchain_validation_probe import (  # noqa: E402
    AppleReleaseToolchainValidationJobObservation,
    AppleReleaseToolchainValidationObservation,
    AppleReleaseToolchainValidationProbe,
    AppleReleaseToolchainValidationStepObservation,
)
from testing.tests.support.apple_release_toolchain_validation_probe_factory import (  # noqa: E402
    create_apple_release_toolchain_validation_probe,
)

TICKET_KEY = "TS-707"
TEST_CASE_TITLE = (
    "Validate macOS toolchain contract — validation fails on incorrect environment versions"
)
RUN_COMMAND = "PYTHONPATH=. python3 testing/tests/TS-707/test_ts_707.py"
TEST_FILE_PATH = "testing/tests/TS-707/test_ts_707.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


class TS707PreconditionError(AssertionError):
    pass


REQUEST_STEPS = [
    "Trigger the Apple release workflow by pushing a `v*` tag.",
    "Wait for the workflow to reach the self-hosted runner execution phase.",
    "Inspect the 'macOS environment validation' step logs.",
]
EXPECTED_RESULT = (
    "The validation step fails with an explicit error message stating that Flutter "
    "`3.35.3` is required. The build jobs for the desktop app and CLI do not proceed, "
    "preventing potential version drift or late-stage build errors."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    probe: AppleReleaseToolchainValidationProbe = (
        create_apple_release_toolchain_validation_probe(
            REPO_ROOT,
            screenshot_directory=OUTPUTS_DIR,
        )
    )
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "run_command": RUN_COMMAND,
        "test_file_path": TEST_FILE_PATH,
        "expected_result": EXPECTED_RESULT,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "steps": [],
        "human_verification": [],
    }
    observation: AppleReleaseToolchainValidationObservation | None = None

    try:
        observation = probe.validate()
        result.update(observation.to_dict())
        result["verify_runner_job"] = _job_as_dict(observation.verify_runner_job)
        result["build_job"] = _job_as_dict(observation.build_job)
        result["setup_flutter_step"] = _step_as_dict(observation.setup_flutter_step)
        result["validation_step"] = _step_as_dict(observation.validation_step)
        result["desktop_build_step"] = _step_as_dict(observation.desktop_build_step)
        result["cli_build_step"] = _step_as_dict(observation.cli_build_step)
        _record_human_observations(result, observation)

        _record_step(
            result,
            step=1,
            status="passed",
            action=REQUEST_STEPS[0],
            observed=(
                f"Pushed disposable semantic tag `{observation.test_tag}` that points to "
                f"probe commit `{observation.test_commit_sha}` and observed live Apple "
                f"release run `{observation.run_id}` at `{observation.run_url}`."
            ),
        )

        _assert_self_hosted_phase_reached(observation)
        _record_step(
            result,
            step=2,
            status="passed",
            action=REQUEST_STEPS[1],
            observed=(
                f"The run reached build job `{observation.build_job.name}` with step list "
                f"{_step_name_list(observation.build_job)}. The setup step conclusion was "
                f"`{_step_conclusion(observation.setup_flutter_step)}`."
            ),
        )

        _assert_validation_failure_contract(observation)
        _record_step(
            result,
            step=3,
            status="passed",
            action=REQUEST_STEPS[2],
            observed=(
                f"Step `{observation.validation_step.name}` concluded "
                f"`{_step_conclusion(observation.validation_step)}` and logged "
                f"`{observation.version_error_line}`. Subsequent steps "
                f"`{_step_name(observation.desktop_build_step)}` and "
                f"`{_step_name(observation.cli_build_step)}` did not proceed."
            ),
        )

        _assert_human_verification(observation)
    except Exception as error:
        if _is_precondition_error(error) or _is_harness_failure(observation):
            result["failure_kind"] = "precondition"
        result.setdefault("error", f"{type(error).__name__}: {error}")
        result.setdefault("traceback", traceback.format_exc())
        if observation is not None and not result.get("human_verification"):
            _record_human_observations(result, observation)
        if observation is None:
            _record_partial_progress_from_error(result, str(error))
        _record_failed_step_from_error(result, str(error))
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-707 passed")


def _assert_self_hosted_phase_reached(
    observation: AppleReleaseToolchainValidationObservation,
) -> None:
    runner_precondition_message = _runner_precondition_message(observation)
    if runner_precondition_message is not None:
        raise TS707PreconditionError(runner_precondition_message)
    if observation.build_job is None:
        raise AssertionError(
            "Step 2 failed: the Apple release run never exposed the self-hosted build job.\n"
            f"Run URL: {observation.run_url}\n"
            f"Jobs observed: {_job_summary_block(observation.jobs)}\n"
            f"Log excerpt:\n{observation.run_log_excerpt}"
        )
    if not observation.build_job.steps:
        raise AssertionError(
            "Step 2 failed: the Apple release run did not reach the self-hosted runner "
            "execution phase. The build job was present but had no recorded steps.\n"
            f"Build job conclusion: {observation.build_job.conclusion}\n"
            f"Verify-runner job: {_single_job_summary(observation.verify_runner_job)}\n"
            f"Run URL: {observation.run_url}\n"
            f"Log excerpt:\n{observation.run_log_excerpt}"
        )
    if observation.setup_flutter_step is None:
        raise AssertionError(
            "Step 2 failed: the self-hosted build job started, but it never reached the "
            f"`{observation.build_job.name}` step `{_required_setup_step_name()}`.\n"
            f"Observed build steps: {_step_name_list(observation.build_job)}\n"
            f"Run URL: {observation.run_url}\n"
            f"Log excerpt:\n{observation.run_log_excerpt}"
        )


def _assert_validation_failure_contract(
    observation: AppleReleaseToolchainValidationObservation,
) -> None:
    incomplete_validation_message = _incomplete_validation_message(observation)
    if incomplete_validation_message is not None:
        raise TS707PreconditionError(incomplete_validation_message)
    if observation.validation_step is None:
        raise AssertionError(
            "Step 3 failed: the build job never exposed the `Verify runner toolchain` "
            "step, so the macOS environment validation logs could not be inspected.\n"
            f"Build job summary: {_single_job_summary(observation.build_job)}\n"
            f"Observed steps: {_step_name_list(observation.build_job)}\n"
            f"Run URL: {observation.run_url}\n"
            f"Log excerpt:\n{observation.run_log_excerpt}"
        )
    if observation.validation_step.conclusion != "failure":
        raise AssertionError(
            "Step 3 failed: the macOS environment validation step did not fail.\n"
            f"Validation step summary: {_single_step_summary(observation.validation_step)}\n"
            f"Setup Flutter step summary: {_single_step_summary(observation.setup_flutter_step)}\n"
            f"Run URL: {observation.run_url}\n"
            f"Log excerpt:\n{observation.run_log_excerpt}"
        )
    if observation.version_error_line is None:
        raise AssertionError(
            "Step 3 failed: the validation logs did not contain the explicit Flutter "
            f"`3.35.3` required error.\nValidation step summary: "
            f"{_single_step_summary(observation.validation_step)}\n"
            f"Run URL: {observation.run_url}\n"
            f"Log excerpt:\n{observation.run_log_excerpt}"
        )
    if _step_proceeded(observation.desktop_build_step):
        raise AssertionError(
            "Step 3 failed: `Build macOS desktop app` still proceeded after the toolchain "
            "validation failure.\n"
            f"Desktop build step: {_single_step_summary(observation.desktop_build_step)}\n"
            f"Run URL: {observation.run_url}\n"
            f"Log excerpt:\n{observation.run_log_excerpt}"
        )
    if _step_proceeded(observation.cli_build_step):
        raise AssertionError(
            "Step 3 failed: `Build macOS CLI` still proceeded after the toolchain "
            "validation failure.\n"
            f"CLI build step: {_single_step_summary(observation.cli_build_step)}\n"
            f"Run URL: {observation.run_url}\n"
            f"Log excerpt:\n{observation.run_log_excerpt}"
        )


def _assert_human_verification(
    observation: AppleReleaseToolchainValidationObservation,
) -> None:
    if observation.main_ui_error is not None:
        raise AssertionError(
            "Human-style verification failed: the GitHub workflow file page did not load.\n"
            f"Error: {observation.main_ui_error}"
        )
    body_text = observation.main_ui_body_text
    required_tokens = (
        observation.workflow_name,
        _required_flutter_line(observation),
        "Verify runner toolchain",
        "./tool/check_macos_release_runner.sh",
    )
    missing = [token for token in required_tokens if token not in body_text]
    if missing:
        raise AssertionError(
            "Human-style verification failed: the visible GitHub workflow page did not "
            "show the expected release toolchain contract text.\n"
            f"Missing text: {missing}\n"
            f"URL: {observation.main_ui_url}\n"
            f"Visible body text excerpt:\n{_snippet(body_text, limit=1200)}"
        )


def _record_human_observations(
    result: dict[str, object],
    observation: AppleReleaseToolchainValidationObservation,
) -> None:
    _record_human_verification(
        result,
        check=(
            "Opened the live GitHub workflow file on the default branch and checked "
            "the visible toolchain contract text."
        ),
        observed=(
            f"GitHub page `{observation.main_ui_url}` visibly showed "
            f"`{observation.workflow_name}`, `{_required_flutter_line(observation)}`, "
            f"`{observation.validation_step.name if observation.validation_step else 'Verify runner toolchain'}`, "
            f"and `./tool/check_macos_release_runner.sh`. Screenshot: "
            f"`{observation.main_ui_screenshot_path}`."
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Reviewed the live Actions run as a maintainer would through the GitHub "
            "run summary and logs."
        ),
        observed=(
            f"Run `{observation.run_url}` ended with conclusion "
            f"`{observation.run_conclusion}`. Job summary was "
            f"{_job_summary_inline(observation.jobs)}. Log excerpt included: "
            f"`{observation.version_error_line or _first_non_empty_line(observation.run_log_excerpt)}`."
        ),
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
            }
        )
        + "\n",
        encoding="utf-8",
    )
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": str(result.get("error", "AssertionError: TS-707 failed")),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(result, passed=False), encoding="utf-8")
    if _is_precondition_failure(result) or not _validation_step_executed(result):
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    else:
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {'✅ PASSED' if passed else '❌ FAILED'}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        (
            "* Triggered the live {{Apple Release Builds}} workflow using a disposable "
            "semantic tag whose disposable workflow branch leaves {{Set up Flutter}} on "
            "{{3.35.3}} but injects an incompatible Flutter {{3.30.0}} version shim "
            "immediately before {{Verify runner toolchain}}."
        ),
        (
            "* Checked whether the run reached the self-hosted macOS build job and whether "
            "the {{Verify runner toolchain}} step produced the explicit Flutter-version "
            "error before any desktop or CLI build step proceeded."
        ),
        (
            "* Opened the live GitHub workflow file page on {{main}} and verified the "
            "visible workflow text still advertises Flutter {{3.35.3}} and the "
            "{{./tool/check_macos_release_runner.sh}} contract."
        ),
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else _failure_result_line(result, jira=True)
        ),
        (
            f"* Environment: repository {{{{{result.get('repository', '')}}}}}, branch "
            f"{{{{{result.get('default_branch', '')}}}}}, disposable tag "
            f"{{{{{result.get('test_tag', '')}}}}}, browser {{Chromium (Playwright)}}, "
            f"OS {{{{{result.get('os', '')}}}}}."
        ),
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
            ]
        )
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        (
            "- Triggered the live `Apple Release Builds` workflow using a disposable "
            "semantic tag whose disposable workflow branch leaves `Set up Flutter` on "
            "`3.35.3` but injects an incompatible Flutter `3.30.0` version shim "
            "immediately before `Verify runner toolchain`."
        ),
        (
            "- Checked whether the run reached the self-hosted macOS build job and whether "
            "the `Verify runner toolchain` step produced the explicit Flutter-version "
            "error before any desktop or CLI build step proceeded."
        ),
        (
            "- Opened the live GitHub workflow file page on `main` and verified the "
            "visible workflow text still advertises Flutter `3.35.3` and the "
            "`./tool/check_macos_release_runner.sh` contract."
        ),
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else _failure_result_line(result, jira=False)
        ),
        (
            f"- Environment: repository `{result.get('repository', '')}`, branch "
            f"`{result.get('default_branch', '')}`, disposable tag "
            f"`{result.get('test_tag', '')}`, browser `Chromium (Playwright)`, "
            f"OS `{result.get('os', '')}`."
        ),
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


def _response(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## Outcome",
        (
            "- The Apple release workflow reached the macOS validation step and rejected "
            "the incompatible Flutter version before any desktop or CLI build work ran."
            if passed
            else _failure_outcome_line(result)
        ),
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
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
    repository = _as_text(result.get("repository"))
    branch = _as_text(result.get("default_branch"))
    tag = _as_text(result.get("test_tag"))
    run_url = _as_text(result.get("run_url"))
    browser = _as_text(result.get("browser"))
    os_name = _as_text(result.get("os"))
    screenshot_path = _as_text(result.get("main_ui_screenshot_path"))
    log_excerpt = _as_text(result.get("run_log_excerpt"))
    traceback_text = _as_text(result.get("traceback")) or _as_text(result.get("error"))

    lines = [
        f"# {TICKET_KEY} - Apple release workflow violated the macOS toolchain validation contract",
        "",
        "## Expected",
        EXPECTED_RESULT,
        "",
        "## Actual",
        _actual_result_summary(result),
        "",
        "## Steps to reproduce",
        (
            "1. Trigger the Apple release workflow by pushing a `v*` tag. "
            f"{_step_status_icon(result, 1)} {_step_observation_text(result, 1)}"
        ),
        (
            "2. Wait for the workflow to reach the self-hosted runner execution phase. "
            f"{_step_status_icon(result, 2)} {_step_observation_text(result, 2)}"
        ),
        (
            "3. Inspect the 'macOS environment validation' step logs. "
            f"{_step_status_icon(result, 3)} {_step_observation_text(result, 3)}"
        ),
        "",
        "## Actual vs Expected",
        (
            f"- **Expected:** The build job reaches `Verify runner toolchain`, logs "
            f"`Flutter 3.35.3 or newer is required`, and the later `Build macOS desktop app` / "
            "`Build macOS CLI` steps do not proceed."
        ),
        f"- **Actual:** {_actual_result_summary(result)}",
        "",
        "## Missing or broken production capability",
        _product_gap_summary(result),
        "",
        "## Exact error message or assertion failure",
        "```text",
        traceback_text,
        "```",
        "",
        "## Environment details",
        f"- Repository: `{repository}`",
        f"- Branch: `{branch}`",
        f"- Disposable tag: `{tag}`",
        f"- Run URL: `{run_url}`",
        f"- Browser: `{browser}`",
        f"- OS: `{os_name}`",
        "",
        "## Logs / Evidence",
        (
            f"- Workflow file screenshot: `{screenshot_path}`"
            if screenshot_path
            else "- Workflow file screenshot: not captured"
        ),
        "```text",
        log_excerpt,
        "```",
    ]
    return "\n".join(lines) + "\n"


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    if isinstance(steps, list):
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
    verifications = result.setdefault("human_verification", [])
    if isinstance(verifications, list):
        verifications.append({"check": check, "observed": observed})


def _record_partial_progress_from_error(result: dict[str, object], error_message: str) -> None:
    if "did not reach a non-cancelled completed state within the timeout" not in error_message:
        return
    run_id = _error_detail(error_message, "Run ID:")
    run_url = _error_detail(error_message, "URL:")
    status = _error_detail(error_message, "Status:") or "queued"
    if not run_url:
        return
    _record_step(
        result,
        step=1,
        status="passed",
        action=REQUEST_STEPS[0],
        observed=(
            f"Observed disposable Apple release run `{run_id or '<unknown>'}` at "
            f"`{run_url}`, but the workflow remained `{status}` until the automation "
            "timeout expired."
        ),
    )


def _record_failed_step_from_error(result: dict[str, object], error_message: str) -> None:
    steps = result.get("steps")
    if not isinstance(steps, list):
        steps = []
        result["steps"] = steps

    completed_steps = {
        int(step.get("step"))
        for step in steps
        if isinstance(step, dict)
        and isinstance(step.get("step"), int)
        and step.get("status") == "passed"
    }
    for index, action in enumerate(REQUEST_STEPS, start=1):
        if index in completed_steps:
            continue
        steps.append(
            {
                "step": index,
                "status": "failed",
                "action": action,
                "observed": error_message,
            }
        )
        break


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for entry in result.get("steps", []):
        if not isinstance(entry, dict):
            continue
        prefix = "✅" if entry.get("status") == "passed" else "❌"
        action = _as_text(entry.get("action"))
        observed = _as_text(entry.get("observed"))
        if jira:
            lines.append(f"* {prefix} Step {entry.get('step')}: {action}")
            lines.append(f"** Observed: {observed}")
        else:
            lines.append(f"- {prefix} Step {entry.get('step')}: {action}")
            lines.append(f"  - Observed: {observed}")
    return lines or ["- No step results were recorded."]


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for entry in result.get("human_verification", []):
        if not isinstance(entry, dict):
            continue
        check = _as_text(entry.get("check"))
        observed = _as_text(entry.get("observed"))
        if jira:
            lines.append(f"* {check}")
            lines.append(f"** Observed: {observed}")
        else:
            lines.append(f"- {check}")
            lines.append(f"  - Observed: {observed}")
    return lines or ["- Human-style verification did not run."]


def _failed_step_summary(result: dict[str, object]) -> str:
    for entry in result.get("steps", []):
        if isinstance(entry, dict) and entry.get("status") == "failed":
            return (
                f"Step {entry.get('step')} failed while checking "
                f"`{_as_text(entry.get('action'))}`. {_as_text(entry.get('observed'))}"
            )
    return _as_text(result.get("error")) or "The run failed before a step result was recorded."


def _failure_result_line(result: dict[str, object], *, jira: bool) -> str:
    prefix = "* " if jira else "- "
    if _is_precondition_failure(result):
        return (
            f"{prefix}Could not validate the expected result because a non-product "
            f"precondition or test-harness condition failed. {_failed_step_summary(result)}"
        )
    return f"{prefix}Did not match the expected result. {_failed_step_summary(result)}"


def _failure_outcome_line(result: dict[str, object]) -> str:
    if _is_precondition_failure(result):
        return (
            "- The Apple release workflow did not reach a product-valid TS-707 outcome "
            f"because a non-product precondition or test-harness condition failed. "
            f"{_failed_step_summary(result)}"
        )
    return (
        "- The Apple release workflow did not satisfy the requested toolchain "
        f"contract. {_failed_step_summary(result)}"
    )


def _actual_result_summary(result: dict[str, object]) -> str:
    failed_summary = _failed_step_summary(result)
    run_url = _as_text(result.get("run_url"))
    verify_runner = _as_text((result.get("verify_runner_job") or {}).get("conclusion"))
    build_job = _as_text((result.get("build_job") or {}).get("conclusion"))
    if _is_precondition_failure(result):
        if _setup_failed_before_validation(result):
            setup_name = _as_text((result.get("setup_flutter_step") or {}).get("name")) or "Set up Flutter"
            return (
                f"The disposable Apple release run at `{run_url}` failed in `{setup_name}` "
                "before `Verify runner toolchain` executed. Build job conclusion was "
                f"`{build_job}`, so the automation did not reach the product validation "
                f"surface and should be treated as a non-product harness failure: "
                f"{failed_summary}"
            )
        return (
            f"The disposable Apple release run at `{run_url}` stopped in the runner-"
            f"availability guard before the macOS validation step executed. Verify-runner "
            f"job conclusion was `{verify_runner}`, build job conclusion was `{build_job}`, "
            f"and the run was blocked by an unmet infrastructure precondition: "
            f"{failed_summary}"
        )
    return (
        f"The disposable Apple release run at `{run_url}` did not reach the expected "
        f"validation outcome. Verify-runner job conclusion was `{verify_runner}`, build "
        f"job conclusion was `{build_job}`, and the ticket check failed because {failed_summary}"
    )


def _step_status_icon(result: dict[str, object], step_number: int) -> str:
    for entry in result.get("steps", []):
        if isinstance(entry, dict) and entry.get("step") == step_number:
            return "✅" if entry.get("status") == "passed" else "❌"
    return "❌"


def _is_precondition_failure(result: dict[str, object]) -> bool:
    return result.get("failure_kind") == "precondition"


def _validation_step_executed(result: dict[str, object]) -> bool:
    validation_step = result.get("validation_step")
    if not isinstance(validation_step, dict) or not _as_text(validation_step.get("name")):
        return False
    conclusion = _as_text(validation_step.get("conclusion"))
    status = _as_text(validation_step.get("status"))
    return bool(conclusion) or status == "completed"


def _is_precondition_error(error: Exception) -> bool:
    if isinstance(error, TS707PreconditionError):
        return True
    error_message = str(error)
    return (
        "did not reach a non-cancelled completed state within the timeout" in error_message
        and "Status: queued" in error_message
    )


def _is_harness_failure(
    observation: AppleReleaseToolchainValidationObservation | None,
) -> bool:
    if observation is None:
        return False
    return (
        _incomplete_validation_message(observation) is not None
        or (
            observation.validation_step is None
            and observation.setup_flutter_step is not None
            and observation.setup_flutter_step.conclusion == "failure"
        )
    )


def _setup_failed_before_validation(result: dict[str, object]) -> bool:
    setup_step = result.get("setup_flutter_step")
    return (
        isinstance(setup_step, dict)
        and (_as_text(setup_step.get("conclusion")) == "failure" or _as_text(setup_step.get("status")) == "in_progress")
        and not _validation_step_executed(result)
    )


def _incomplete_validation_message(
    observation: AppleReleaseToolchainValidationObservation,
) -> str | None:
    if observation.build_job is None or observation.run_conclusion != "failure":
        return None

    setup_incomplete = observation.setup_flutter_step is not None and (
        observation.setup_flutter_step.status in {"pending", "in_progress"}
        or observation.setup_flutter_step.conclusion is None
    )
    validation_incomplete = observation.validation_step is not None and (
        observation.validation_step.status in {"pending", "in_progress"}
        or observation.validation_step.conclusion is None
    )
    if not (setup_incomplete or validation_incomplete):
        return None

    return (
        "Step 3 blocked: the build job ended in a non-final tool-state before "
        "`Verify runner toolchain` actually executed, so TS-707 did not reach the "
        "product validation surface.\n"
        f"Build job summary: {_single_job_summary(observation.build_job)}\n"
        f"Setup Flutter step summary: {_single_step_summary(observation.setup_flutter_step)}\n"
        f"Validation step summary: {_single_step_summary(observation.validation_step)}\n"
        f"Run URL: {observation.run_url}\n"
        f"Log excerpt:\n{observation.run_log_excerpt}"
    )


def _step_observation_text(result: dict[str, object], step_number: int) -> str:
    for entry in result.get("steps", []):
        if isinstance(entry, dict) and entry.get("step") == step_number:
            return _as_text(entry.get("observed"))
    for entry in result.get("steps", []):
        if (
            isinstance(entry, dict)
            and isinstance(entry.get("step"), int)
            and entry.get("status") == "failed"
            and int(entry.get("step")) < step_number
        ):
            return (
                f"Not reached because Step {entry.get('step')} failed first. "
                f"{_as_text(entry.get('observed'))}"
            )
    return "No observation recorded."


def _job_as_dict(
    job: AppleReleaseToolchainValidationJobObservation | None,
) -> dict[str, object] | None:
    return asdict(job) if job is not None else None


def _step_as_dict(
    step: AppleReleaseToolchainValidationStepObservation | None,
) -> dict[str, object] | None:
    return asdict(step) if step is not None else None


def _runner_precondition_message(
    observation: AppleReleaseToolchainValidationObservation,
) -> str | None:
    verify_runner_failed = (
        observation.verify_runner_job is not None
        and observation.verify_runner_job.conclusion == "failure"
    )
    build_job_not_started = observation.build_job is None or not observation.build_job.steps
    if not (verify_runner_failed and build_job_not_started):
        return None

    reason = _runner_guard_reason(observation.run_log_excerpt)
    reason_line = f"Runner-guard reason: {reason}\n" if reason else ""
    return (
        "Step 2 blocked: TS-707 requires an online self-hosted macOS release runner, "
        "but the workflow stopped in `Verify macOS runner availability` before the "
        "build job reached the macOS validation path.\n"
        f"{reason_line}"
        f"Verify-runner job: {_single_job_summary(observation.verify_runner_job)}\n"
        f"Build job: {_single_job_summary(observation.build_job)}\n"
        f"Run URL: {observation.run_url}\n"
        f"Log excerpt:\n{observation.run_log_excerpt}"
    )


def _runner_guard_reason(log_excerpt: str) -> str:
    for token in (
        "No runner registered",
        "none are online",
        "Bring the TrackState release runner online",
        "Provision the TrackState maintainer-owned macOS release runner",
    ):
        for line in log_excerpt.splitlines():
            if token in line:
                return line.strip()
    return ""


def _product_gap_summary(result: dict[str, object]) -> str:
    failed_summary = _failed_step_summary(result)
    if "Verify runner toolchain" in failed_summary:
        return (
            "The release workflow did not expose or execute the `Verify runner toolchain` "
            "step as required by the macOS release contract."
        )
    if "Flutter `3.35.3` required error" in failed_summary:
        return (
            "The `Verify runner toolchain` step executed, but it did not emit the explicit "
            "Flutter `3.35.3` requirement error required by the release contract."
        )
    if "Build macOS desktop app" in failed_summary or "Build macOS CLI" in failed_summary:
        return (
            "The release workflow allowed downstream desktop or CLI build steps to proceed "
            "after the macOS toolchain validation should have stopped the job."
        )
    return (
        "The Apple release workflow did not preserve the macOS toolchain validation "
        "contract required by TS-707."
    )


def _error_detail(error_message: str, label: str) -> str:
    prefix = f"{label} "
    for line in error_message.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    return ""


def _required_flutter_line(observation: AppleReleaseToolchainValidationObservation) -> str:
    prefix = "flutter-version: '"
    for line in observation.workflow_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped
    return "flutter-version: '3.35.3'"


def _required_setup_step_name() -> str:
    return "Set up Flutter"


def _job_summary_inline(
    jobs: list[AppleReleaseToolchainValidationJobObservation],
) -> str:
    return ", ".join(
        f"`{job.name}`={job.conclusion or job.status or 'unknown'}" for job in jobs
    )


def _job_summary_block(
    jobs: list[AppleReleaseToolchainValidationJobObservation],
) -> str:
    if not jobs:
        return "<no jobs>"
    return "\n".join(f"- {job.name}: {job.conclusion or job.status or 'unknown'}" for job in jobs)


def _single_job_summary(job: AppleReleaseToolchainValidationJobObservation | None) -> str:
    if job is None:
        return "<missing>"
    return f"{job.name} ({job.conclusion or job.status or 'unknown'})"


def _single_step_summary(step: AppleReleaseToolchainValidationStepObservation | None) -> str:
    if step is None:
        return "<missing>"
    return f"{step.name} ({step.conclusion or step.status or 'unknown'})"


def _step_name_list(job: AppleReleaseToolchainValidationJobObservation | None) -> str:
    if job is None or not job.steps:
        return "<none>"
    return ", ".join(f"`{step.name}`" for step in job.steps)


def _step_name(step: AppleReleaseToolchainValidationStepObservation | None) -> str:
    return step.name if step is not None else "<missing>"


def _step_conclusion(step: AppleReleaseToolchainValidationStepObservation | None) -> str:
    if step is None:
        return "missing"
    return step.conclusion or step.status or "unknown"


def _step_proceeded(step: AppleReleaseToolchainValidationStepObservation | None) -> bool:
    if step is None:
        return False
    return step.conclusion == "success"


def _snippet(text: str, *, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n…"


def _as_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


if __name__ == "__main__":
    main()
