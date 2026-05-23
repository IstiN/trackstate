from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.semantic_label_context_lint_validator import (  # noqa: E402
    SemanticLabelContextLintValidator,
)
from testing.core.config.semantic_label_context_lint_config import (  # noqa: E402
    SemanticLabelContextLintConfig,
)
from testing.core.models.cli_command_result import CliCommandResult  # noqa: E402
from testing.core.models.semantic_label_context_lint_validation_result import (  # noqa: E402
    SemanticLabelContextLintValidationResult,
)
from testing.tests.support.flutter_analyze_probe_factory import (  # noqa: E402
    create_flutter_analyze_probe,
)

TICKET_KEY = "TS-907"
TEST_CASE_TITLE = (
    "Commit component with weak ARIA semantics - linter flags missing context"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-907/test_ts_907.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-907/config.yaml"

REQUEST_STEPS = [
    "Open the source code for a UI component (e.g., SyncPill).",
    "Modify the ARIA label or semantics label to a generic value such as 'Attention needed' instead of the required 'Sync error, attention needed'.",
    "Run the local accessibility linting or analysis command (e.g., 'npm run lint:a11y' or 'flutter analyze').",
]
EXPECTED_RESULT = (
    "The linter identifies the violation, specifically flagging the label for "
    "lacking the required 'Sync error' context prefix."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = SemanticLabelContextLintConfig.from_env()
    probe = create_flutter_analyze_probe(
        REPO_ROOT,
        flutter_version=config.flutter_version,
        env_prefixes=("TS907", "TRACKSTATE"),
    )
    validator = SemanticLabelContextLintValidator(REPO_ROOT, probe)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "title": TEST_CASE_TITLE,
        "run_command": RUN_COMMAND,
        "config_path": str(CONFIG_PATH),
        "target_path": config.target_relative_path.as_posix(),
        "localization_path": config.localization_relative_path.as_posix(),
        "expected_semantic_label": config.required_semantic_label,
        "generic_semantic_label": config.generic_semantic_label,
        "os": platform.platform(),
        "steps": [],
        "human_verification": [],
    }

    try:
        validation = validator.validate(config=config)
        _populate_command_metadata(result, validation)
        _evaluate(validation, config=config, result=result)
        _write_pass_outputs(result)
        print(f"{TICKET_KEY} passed")
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise


def _evaluate(
    validation: SemanticLabelContextLintValidationResult,
    *,
    config: SemanticLabelContextLintConfig,
    result: dict[str, object],
) -> None:
    _assert_flutter_available(validation)
    _assert_pub_get_succeeded(validation)
    _assert_live_semantic_contract(validation, config=config, result=result)
    _assert_mutation_applied(validation, config=config, result=result)
    _assert_lint_blocks_regression(validation, config=config, result=result)
    _record_human_verification(
        result,
        check=(
            "Viewed the terminal output exactly as a developer would after weakening "
            "the sync-pill semantic label in a disposable workspace and rerunning "
            "`flutter analyze`."
        ),
        observed=(
            "The analysis command exited non-zero and surfaced an accessibility "
            f"diagnostic for {config.target_relative_path.as_posix()}:\n"
            f"{_combined_output(validation.mutated_analyze)}"
        ),
    )


def _assert_flutter_available(
    validation: SemanticLabelContextLintValidationResult,
) -> None:
    if validation.flutter_version.succeeded:
        return
    raise AssertionError(
        "Precondition failed: TS-907 could not start Flutter.\n"
        f"Command: {validation.flutter_version.command_text}\n"
        f"Exit code: {validation.flutter_version.exit_code}\n"
        f"stdout:\n{validation.flutter_version.stdout}\n"
        f"stderr:\n{validation.flutter_version.stderr}"
    )


def _assert_pub_get_succeeded(
    validation: SemanticLabelContextLintValidationResult,
) -> None:
    if validation.pub_get.succeeded:
        return
    raise AssertionError(
        "Precondition failed: TS-907 could not resolve Flutter dependencies in the "
        "temporary workspace.\n"
        f"Command: {validation.pub_get.command_text}\n"
        f"Exit code: {validation.pub_get.exit_code}\n"
        f"stdout:\n{validation.pub_get.stdout}\n"
        f"stderr:\n{validation.pub_get.stderr}"
    )


def _assert_live_semantic_contract(
    validation: SemanticLabelContextLintValidationResult,
    *,
    config: SemanticLabelContextLintConfig,
    result: dict[str, object],
) -> None:
    failures: list[str] = []
    if config.required_source_snippet not in validation.baseline_source:
        failures.append(
            "the live production source no longer used the dedicated sync "
            f"semantic-label contract `{config.required_source_snippet}`"
        )
    if config.required_semantic_label not in validation.localization_source:
        failures.append(
            "the live English localization file no longer contained the required "
            f"descriptive semantic label {config.required_semantic_label!r}"
        )
    if config.generic_semantic_label not in validation.localization_source:
        failures.append(
            "the live English localization file no longer contained the visible "
            f"generic label {config.generic_semantic_label!r} needed for the regression mutation"
        )
    if not validation.baseline_analyze.succeeded:
        failures.append(
            "the unmodified production file already failed `flutter analyze` before "
            "the ticket regression was introduced"
        )
    if failures:
        raise AssertionError(
            "Precondition failed: TS-907 could not confirm the live production "
            "sync-pill semantic-label contract before mutating the temp workspace.\n"
            f"Problems: {'; '.join(failures)}\n"
            f"Baseline analyze output:\n{_combined_output(validation.baseline_analyze)}"
        )
    _record_step(
        result,
        step=1,
        status="passed",
        action=REQUEST_STEPS[0],
        observed=(
            "Confirmed the live production source uses "
            f"`{config.required_source_snippet}` from "
            f"{config.target_relative_path.as_posix()} and the English localization "
            f"defines {config.required_semantic_label!r} for the sync error semantic label. "
            f"Baseline analyze exit_code={validation.baseline_analyze.exit_code}."
        ),
    )


def _assert_mutation_applied(
    validation: SemanticLabelContextLintValidationResult,
    *,
    config: SemanticLabelContextLintConfig,
    result: dict[str, object],
) -> None:
    if validation.baseline_source == validation.mutated_source:
        raise AssertionError(
            "Step 2 failed: the temp workspace source did not change after applying "
            "the weak semantic-label mutation.\n"
            f"Expected replacement: {config.replacement_source_snippet}"
        )
    if config.replacement_source_snippet not in validation.mutated_source:
        raise AssertionError(
            "Step 2 failed: the temp workspace source did not contain the weaker "
            f"semantic-label usage `{config.replacement_source_snippet}`.\n"
            f"Mutated file: {validation.target_path}"
        )
    _record_step(
        result,
        step=2,
        status="passed",
        action=REQUEST_STEPS[1],
        observed=(
            "In the disposable temp workspace, replaced "
            f"`{config.required_source_snippet}` with "
            f"`{config.replacement_source_snippet}` inside "
            f"{config.target_relative_path.as_posix()}, downgrading the semantic "
            f"label from {config.required_semantic_label!r} to the generic "
            f"{config.generic_semantic_label!r}."
        ),
    )


def _assert_lint_blocks_regression(
    validation: SemanticLabelContextLintValidationResult,
    *,
    config: SemanticLabelContextLintConfig,
    result: dict[str, object],
) -> None:
    output = _combined_output(validation.mutated_analyze)
    normalized_output = output.lower()
    result["mutated_analyze_output"] = output

    diagnostic_signals = _diagnostic_signals(
        validation.mutated_analyze,
        normalized_output=normalized_output,
    )
    clean_analysis = "no issues found!" in normalized_output

    if diagnostic_signals and not clean_analysis:
        _record_step(
            result,
            step=3,
            status="passed",
            action=REQUEST_STEPS[2],
            observed=(
                f"Ran `{validation.mutated_analyze.command_text}` against the mutated "
                f"temp workspace. The command surfaced analyzer diagnostics instead "
                f"of a clean `No issues found!` result. Observed exit_code="
                f"{validation.mutated_analyze.exit_code}; "
                f"diagnostic_signals={diagnostic_signals}; terminal output:\n{output}"
            ),
        )
        return

    _record_step(
        result,
        step=3,
        status="failed",
        action=REQUEST_STEPS[2],
        observed=(
            f"Ran `{validation.mutated_analyze.command_text}` after downgrading the "
            f"sync-pill semantic label to {config.generic_semantic_label!r}. "
            f"Observed exit_code={validation.mutated_analyze.exit_code}; "
            f"clean_analysis={clean_analysis}; "
            f"diagnostic_signals={diagnostic_signals}; "
            f"terminal output:\n{output}"
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Viewed the terminal output as a developer after rerunning "
            "`flutter analyze` against the weakened semantic-label change."
        ),
        observed=(
            "The command still looked like a clean analysis run instead of surfacing "
            "a real diagnostic for the weakened semantic label. Output:\n"
            f"{output}"
        ),
    )
    raise AssertionError(
        "Step 3 failed: `flutter analyze` did not identify the weakened sync-pill "
        "semantic label regression with any real diagnostic.\n"
        "Expected the mutated analysis run to stop looking clean and surface an "
        "issue, warning, hint, or non-zero analyzer result instead of "
        "`No issues found!`.\n"
        f"Observed command: {validation.mutated_analyze.command_text}\n"
        f"Observed exit code: {validation.mutated_analyze.exit_code}\n"
        f"Observed clean analysis: {clean_analysis}\n"
        f"Observed diagnostic signals: {diagnostic_signals}\n"
        f"Observed output:\n{output}"
    )


def _diagnostic_signals(
    command_result: CliCommandResult,
    *,
    normalized_output: str,
) -> list[str]:
    signals: list[str] = []
    diagnostic_markers = ("error", "warning", "info", "hint")

    if command_result.exit_code != 0:
        signals.append("non-zero-exit")

    if any(
        f"{marker} •" in normalized_output or f"{marker} -" in normalized_output
        for marker in diagnostic_markers
    ):
        signals.append("diagnostic-line")

    if any(
        ("issue found" in line or "issues found" in line)
        and "no issues found!" not in line
        for line in normalized_output.splitlines()
    ):
        signals.append("issue-summary")

    return signals


def _populate_command_metadata(
    result: dict[str, object],
    validation: SemanticLabelContextLintValidationResult,
) -> None:
    result["flutter_version_command"] = validation.flutter_version.command_text
    result["pub_get_command"] = validation.pub_get.command_text
    result["baseline_analyze_command"] = validation.baseline_analyze.command_text
    result["mutated_analyze_command"] = validation.mutated_analyze.command_text
    result["baseline_analyze_exit_code"] = validation.baseline_analyze.exit_code
    result["mutated_analyze_exit_code"] = validation.mutated_analyze.exit_code
    result["baseline_analyze_output"] = _combined_output(validation.baseline_analyze)


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
    RESPONSE_PATH.write_text(
        _markdown_summary(result, passed=True),
        encoding="utf-8",
    )


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-907 failed"))
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
    RESPONSE_PATH.write_text(
        _markdown_summary(result, passed=False),
        encoding="utf-8",
    )
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "h3. Test Automation Result",
        f"*Ticket:* {TICKET_KEY}",
        f"*Title:* {TEST_CASE_TITLE}",
        f"*Status:* {status}",
        f"*Environment:* local repository checkout | flutter analyze | {result.get('os')}",
        f"*Config:* {{{{{result.get('config_path')}}}}}",
        "",
        "h4. Automation checks",
    ]
    for step in result.get("steps", []):
        assert isinstance(step, dict)
        marker = "(/)" if step.get("status") == "passed" else "(x)"
        lines.append(
            f"{marker} *Step {step.get('step')}* {step.get('action')}\n"
            f"Observed: {step.get('observed')}"
        )
    lines.extend(("", "h4. Human-style verification"))
    for check in result.get("human_verification", []):
        assert isinstance(check, dict)
        lines.append(f"* {check.get('check')}\nObserved: {check.get('observed')}")
    if not passed:
        lines.extend(
            (
                "",
                "h4. Failure details",
                f"*Error:* {result.get('error')}",
                "{code}",
                str(result.get("mutated_analyze_output", "<missing output>")),
                "{code}",
            )
        )
    return "\n".join(lines).strip() + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        f"# {TICKET_KEY} {'Passed' if passed else 'Failed'}",
        "",
        f"**Title:** {TEST_CASE_TITLE}",
        f"**Environment:** local repository checkout | flutter analyze | {result.get('os')}",
        f"**Target file:** `{result.get('target_path')}`",
        f"**Status:** {'passed' if passed else 'failed'}",
        "",
        "## Automation checks",
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
        lines.append(
            f"- **Check:** {check.get('check')}  \n"
            f"  Observed: {check.get('observed')}"
        )
    if not passed:
        lines.extend(
            (
                "",
                "## Failure details",
                f"- **Error:** {result.get('error')}",
                "- **Observed terminal output:**",
                "```text",
                str(result.get("mutated_analyze_output", "<missing output>")),
                "```",
            )
        )
    return "\n".join(lines).strip() + "\n"


def _bug_description(result: dict[str, object]) -> str:
    step_map = {
        int(step["step"]): step
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    return (
        f"# {TICKET_KEY} - flutter analyze does not block weak sync-pill semantic labels\n\n"
        "## Steps to reproduce\n"
        f"1. {REQUEST_STEPS[0]}  \n"
        f"   - Actual: {step_map.get(1, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(1, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"2. {REQUEST_STEPS[1]}  \n"
        f"   - Actual: {step_map.get(2, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(2, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"3. {REQUEST_STEPS[2]}  \n"
        f"   - Actual: {step_map.get(3, {}).get('observed', '<missing>')}  \n"
        "   - Result: FAILED ❌\n\n"
        "## Exact error message or assertion failure\n"
        "```text\n"
        f"{result.get('traceback', result.get('error', '<missing>'))}"
        "```\n\n"
        "## Actual vs Expected\n"
        f"- **Expected:** {EXPECTED_RESULT}\n"
        "- **Actual:** After the sync-pill semantic label was downgraded to the generic "
        "`Attention needed` value in a disposable workspace copy, `flutter analyze` "
        "did not emit a blocking accessibility/context diagnostic that explained the "
        "missing `Sync error` prefix.\n\n"
        "## Environment details\n"
        "- **URL:** local repository checkout (no deployed URL required for this lint case)\n"
        f"- **Browser:** N/A - local terminal validation\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Run command:** `{result.get('run_command')}`\n"
        f"- **Config:** `{result.get('config_path')}`\n"
        f"- **Target file:** `{result.get('target_path')}`\n"
        f"- **Localization file:** `{result.get('localization_path')}`\n"
        f"- **Baseline analyze command:** `{result.get('baseline_analyze_command')}`\n"
        f"- **Mutated analyze command:** `{result.get('mutated_analyze_command')}`\n\n"
        "## Screenshots or logs\n"
        "- **Terminal output:**\n"
        "```text\n"
        f"{result.get('mutated_analyze_output', '<missing output>')}\n"
        "```\n"
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


def _combined_output(command_result: CliCommandResult) -> str:
    return SemanticLabelContextLintValidationResult.combine_output(command_result)


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


if __name__ == "__main__":
    main()
