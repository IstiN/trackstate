from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.semantic_label_context_compliance_validator import (  # noqa: E402
    SemanticLabelContextComplianceValidator,
)
from testing.core.config.semantic_label_context_lint_config import (  # noqa: E402
    SemanticLabelContextLintConfig,
)
from testing.core.models.semantic_label_context_compliance_result import (  # noqa: E402
    SemanticLabelContextComplianceResult,
)
from testing.tests.support.flutter_analyze_probe_factory import (  # noqa: E402
    create_flutter_analyze_probe,
)

TICKET_KEY = "TS-923"
TEST_CASE_TITLE = "Run analyzer on compliant sync component - no violations reported"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-923/test_ts_923.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-923/config.yaml"

REQUEST_STEPS = [
    "Open a UI component that uses a correctly contextualized label (e.g., l10n.workspaceSyncAttentionNeededSemanticLabel).",
    "Verify that the underlying localization value contains the mandatory 'Sync error' prefix.",
    "Run the local analysis command: flutter analyze lib/ui/features/tracker/views/trackstate_app.dart.",
]
EXPECTED_RESULT = (
    "The analyzer reports 'No issues found!' and exits with code 0, confirming "
    "valid labels are permitted."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = SemanticLabelContextLintConfig.from_env(
        env_prefixes=("TS923", "TRACKSTATE"),
    )
    probe = create_flutter_analyze_probe(
        REPO_ROOT,
        flutter_version=config.flutter_version,
        env_prefixes=("TS923", "TRACKSTATE"),
    )
    validator = SemanticLabelContextComplianceValidator(REPO_ROOT, probe)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "title": TEST_CASE_TITLE,
        "run_command": RUN_COMMAND,
        "config_path": str(CONFIG_PATH),
        "target_path": config.target_relative_path.as_posix(),
        "localization_path": config.localization_relative_path.as_posix(),
        "semantic_label_localization_key": config.semantic_label_localization_key,
        "expected_semantic_label": config.required_semantic_label,
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
    validation: SemanticLabelContextComplianceResult,
    *,
    config: SemanticLabelContextLintConfig,
    result: dict[str, object],
) -> None:
    _assert_flutter_available(validation)
    _assert_pub_get_succeeded(validation)
    _assert_source_uses_contextual_label(validation, config=config, result=result)
    _assert_localized_prefix_is_preserved(validation, config=config, result=result)
    _assert_analyzer_allows_valid_label(validation, result=result)
    _record_human_verification(
        result,
        check=(
            "Viewed the terminal output exactly as a developer would after running "
            "`flutter analyze` on the unmodified sync component."
        ),
        observed=(
            "The analyzer finished cleanly with exit code 0 and showed "
            f"`No issues found!`, matching a user-visible successful terminal run.\n"
            f"{_combined_output(validation.analyze)}"
        ),
    )


def _assert_flutter_available(
    validation: SemanticLabelContextComplianceResult,
) -> None:
    if validation.flutter_version.succeeded:
        return
    raise AssertionError(
        "Precondition failed: TS-923 could not start Flutter.\n"
        f"Command: {validation.flutter_version.command_text}\n"
        f"Exit code: {validation.flutter_version.exit_code}\n"
        f"stdout:\n{validation.flutter_version.stdout}\n"
        f"stderr:\n{validation.flutter_version.stderr}"
    )


def _assert_pub_get_succeeded(
    validation: SemanticLabelContextComplianceResult,
) -> None:
    if validation.pub_get.succeeded:
        return
    raise AssertionError(
        "Precondition failed: TS-923 could not resolve Flutter dependencies in the "
        "temporary workspace.\n"
        f"Command: {validation.pub_get.command_text}\n"
        f"Exit code: {validation.pub_get.exit_code}\n"
        f"stdout:\n{validation.pub_get.stdout}\n"
        f"stderr:\n{validation.pub_get.stderr}"
    )


def _assert_source_uses_contextual_label(
    validation: SemanticLabelContextComplianceResult,
    *,
    config: SemanticLabelContextLintConfig,
    result: dict[str, object],
) -> None:
    if config.required_source_snippet not in validation.source:
        _record_step(
            result,
            step=1,
            status="failed",
            action=REQUEST_STEPS[0],
            observed=(
                "The live production source no longer returned the expected semantic "
                f"label getter `{config.required_source_snippet}` from "
                f"{config.target_relative_path.as_posix()}."
            ),
        )
        raise AssertionError(
            "Step 1 failed: the compliant sync component no longer uses the expected "
            "contextual semantic-label getter.\n"
            f"Expected source snippet: {config.required_source_snippet}\n"
            f"Target file: {config.target_relative_path.as_posix()}"
        )
    _record_step(
        result,
        step=1,
        status="passed",
        action=REQUEST_STEPS[0],
        observed=(
            "Confirmed the live production source still returns "
            f"`{config.required_source_snippet}` from "
            f"{config.target_relative_path.as_posix()}."
        ),
    )


def _assert_localized_prefix_is_preserved(
    validation: SemanticLabelContextComplianceResult,
    *,
    config: SemanticLabelContextLintConfig,
    result: dict[str, object],
) -> None:
    localization = json.loads(validation.localization_source)
    actual_value = localization.get(config.semantic_label_localization_key)

    if not isinstance(actual_value, str):
        _record_step(
            result,
            step=2,
            status="failed",
            action=REQUEST_STEPS[1],
            observed=(
                "The English localization file did not contain a string value for "
                f"`{config.semantic_label_localization_key}`."
            ),
        )
        raise AssertionError(
            "Step 2 failed: the English localization file is missing the required "
            "semantic-label entry.\n"
            f"Localization key: {config.semantic_label_localization_key}\n"
            f"Localization file: {config.localization_relative_path.as_posix()}"
        )

    required_prefix = _required_semantic_prefix(config)
    normalized_value = actual_value.strip()
    if not normalized_value.startswith(required_prefix):
        _record_step(
            result,
            step=2,
            status="failed",
            action=REQUEST_STEPS[1],
            observed=(
                "The localization entry was present, but it did not preserve the "
                f"required `{required_prefix}` prefix. Observed value: {actual_value!r}"
            ),
        )
        raise AssertionError(
            "Step 2 failed: the underlying localization value no longer preserves the "
            f"mandatory `{required_prefix}` prefix.\n"
            f"Expected prefix: {required_prefix!r}\n"
            f"Observed value: {actual_value!r}\n"
            f"Localization key: {config.semantic_label_localization_key}\n"
            f"Localization file: {config.localization_relative_path.as_posix()}"
        )

    _record_step(
        result,
        step=2,
        status="passed",
        action=REQUEST_STEPS[1],
        observed=(
            "Confirmed the English localization entry "
            f"`{config.semantic_label_localization_key}` contains "
            f"{actual_value!r}, preserving the mandatory `{required_prefix}` prefix."
        ),
    )


def _required_semantic_prefix(config: SemanticLabelContextLintConfig) -> str:
    prefix, separator, _ = config.required_semantic_label.partition(",")
    return prefix.strip() if separator else config.required_semantic_label.strip()


def _assert_analyzer_allows_valid_label(
    validation: SemanticLabelContextComplianceResult,
    *,
    result: dict[str, object],
) -> None:
    output = _combined_output(validation.analyze)
    normalized_output = output.lower()
    result["analyze_output"] = output

    if validation.analyze.exit_code == 0 and "no issues found!" in normalized_output:
        _record_step(
            result,
            step=3,
            status="passed",
            action=REQUEST_STEPS[2],
            observed=(
                f"Ran `{validation.analyze.command_text}` against the live, unmodified "
                f"sync component in the disposable workspace. The analyzer exited with "
                f"code {validation.analyze.exit_code} and reported `No issues found!`.\n"
                f"Terminal output:\n{output}"
            ),
        )
        return

    _record_step(
        result,
        step=3,
        status="failed",
        action=REQUEST_STEPS[2],
        observed=(
            f"Ran `{validation.analyze.command_text}` against the live, unmodified sync "
            f"component, but the analyzer did not stay clean. Observed exit_code="
            f"{validation.analyze.exit_code}; terminal output:\n{output}"
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Viewed the terminal output as a developer after running `flutter analyze` "
            "on the unmodified sync component."
        ),
        observed=(
            "Instead of a clean `No issues found!` terminal result, the analyzer "
            f"reported a failing or unexpected outcome.\n{output}"
        ),
    )
    raise AssertionError(
        "Step 3 failed: `flutter analyze` did not stay clean for the compliant sync "
        "semantic label implementation.\n"
        "Expected exit code 0 and `No issues found!` for the unmodified production "
        "file.\n"
        f"Observed command: {validation.analyze.command_text}\n"
        f"Observed exit code: {validation.analyze.exit_code}\n"
        f"Observed output:\n{output}"
    )


def _populate_command_metadata(
    result: dict[str, object],
    validation: SemanticLabelContextComplianceResult,
) -> None:
    result["flutter_version_command"] = validation.flutter_version.command_text
    result["pub_get_command"] = validation.pub_get.command_text
    result["analyze_command"] = validation.analyze.command_text
    result["analyze_exit_code"] = validation.analyze.exit_code
    result["analyze_output"] = _combined_output(validation.analyze)


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
    RESPONSE_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-923 failed"))
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
    RESPONSE_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
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
                str(result.get("analyze_output", "<missing output>")),
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
                str(result.get("analyze_output", "<missing output>")),
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
        f"# {TICKET_KEY} - compliant sync semantic label is not analyzer-clean\n\n"
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
        "- **Actual:** The live compliant semantic label implementation did not remain "
        "analyzer-clean, or the localized semantic-label text no longer preserved the "
        "required `Sync error` prefix for the sync attention-needed state.\n\n"
        "## Environment details\n"
        "- **URL:** local repository checkout (no deployed URL required for this lint case)\n"
        "- **Browser:** N/A - local terminal validation\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Run command:** `{result.get('run_command')}`\n"
        f"- **Config:** `{result.get('config_path')}`\n"
        f"- **Target file:** `{result.get('target_path')}`\n"
        f"- **Localization file:** `{result.get('localization_path')}`\n"
        f"- **Localization key:** `{result.get('semantic_label_localization_key')}`\n"
        f"- **Analyze command:** `{result.get('analyze_command')}`\n\n"
        "## Screenshots or logs\n"
        "- **Terminal output:**\n"
        "```text\n"
        f"{result.get('analyze_output', '<missing output>')}\n"
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


def _combined_output(command_result) -> str:
    return SemanticLabelContextComplianceResult.combine_output(command_result)


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


if __name__ == "__main__":
    main()
