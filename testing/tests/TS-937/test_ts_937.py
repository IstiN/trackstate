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

from testing.core.models.cli_command_result import CliCommandResult  # noqa: E402
from testing.frameworks.python.flutter_analyze_framework import (  # noqa: E402
    PythonFlutterAnalyzeFramework,
)

TICKET_KEY = "TS-937"
TEST_CASE_TITLE = "Sync widget unit test — signature enforces localization contract"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-937/test_ts_937.py"
FLUTTER_VERSION = "3.35.3"
TEST_TARGET = Path("test/workspace_sync_semantic_label_contract_test.dart")
SOURCE_TARGET = Path("lib/ui/features/tracker/views/trackstate_app.dart")
LOCALIZATION_TARGET = Path("lib/l10n/generated/app_localizations_en.dart")
EXPECTED_TEST_NAME = (
    "flutter analyze rejects a raw string passed to the workspace sync semantic label API"
)
EXPECTED_RESULT = (
    "The unit test passes, confirming that the widget's API is programmatically "
    "constrained to the authorized localization contract, preventing regressions "
    "to primitive String literals."
)
REQUEST_STEPS = [
    "Open the unit test file responsible for validating UI component signatures (e.g., test/ui/features/tracker/sync_widget_test.dart).",
    "Locate the test case that asserts the 'semanticLabel' parameter type.",
    "Run the command: flutter test.",
]

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-937/config.yaml"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    probe = PythonFlutterAnalyzeFramework(
        REPO_ROOT,
        flutter_version=FLUTTER_VERSION,
        env_prefixes=("TS937", "TRACKSTATE"),
    )
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "title": TEST_CASE_TITLE,
        "run_command": RUN_COMMAND,
        "config_path": str(CONFIG_PATH),
        "test_target": TEST_TARGET.as_posix(),
        "source_target": SOURCE_TARGET.as_posix(),
        "localization_target": LOCALIZATION_TARGET.as_posix(),
        "expected_result": EXPECTED_RESULT,
        "expected_test_name": EXPECTED_TEST_NAME,
        "os": platform.platform(),
        "steps": [],
        "human_verification": [],
    }

    try:
        flutter_version = probe.flutter_version()
        pub_get = probe.pub_get(REPO_ROOT)
        _populate_command_metadata(result, flutter_version=flutter_version, pub_get=pub_get)
        _assert_flutter_available(flutter_version)
        _assert_pub_get_succeeded(pub_get)

        test_source = _read_required_file(TEST_TARGET)
        source = _read_required_file(SOURCE_TARGET)
        localization = _read_required_file(LOCALIZATION_TARGET)
        result["test_source_excerpt"] = _test_source_excerpt(test_source)
        result["source_signature_excerpt"] = _source_signature_excerpt(source)

        _assert_dedicated_unit_test_exists(test_source, result=result)
        _assert_live_signature_is_wrapped(
            test_source,
            source=source,
            localization=localization,
            result=result,
        )

        flutter_test = probe.test(REPO_ROOT, TEST_TARGET, reporter="expanded")
        result["flutter_test_command"] = flutter_test.command_text
        result["flutter_test_exit_code"] = flutter_test.exit_code
        result["flutter_test_output"] = _combined_output(flutter_test)

        _assert_flutter_test_passed(flutter_test, result=result)
        _record_human_verification(
            result,
            check=(
                "Read the live sync widget contract and its dedicated regression test "
                "the way a developer would before trusting the terminal result."
            ),
            observed=(
                f"The production `_SyncPill` still declares `final _SyncPillSemanticLabel? semanticLabel;`, "
                "the helper returns `_SyncPillSemanticLabel`, and the dedicated Flutter test "
                f"`{EXPECTED_TEST_NAME}` mutates the live call site to the raw "
                "`'Attention needed'` string before rerunning `flutter analyze`."
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Viewed the expanded `flutter test` terminal output as a developer would "
                "after running the dedicated sync widget regression test."
            ),
            observed=(
                "The terminal output showed the dedicated test name and a passing Flutter "
                f"test run for `{TEST_TARGET.as_posix()}`.\n{_combined_output(flutter_test)}"
            ),
        )

        _write_pass_outputs(result)
        print(f"{TICKET_KEY} passed")
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise


def _assert_flutter_available(command: CliCommandResult) -> None:
    if command.succeeded:
        return
    raise AssertionError(
        "Precondition failed: TS-937 could not start Flutter.\n"
        f"Command: {command.command_text}\n"
        f"Exit code: {command.exit_code}\n"
        f"stdout:\n{command.stdout}\n"
        f"stderr:\n{command.stderr}"
    )


def _assert_pub_get_succeeded(command: CliCommandResult) -> None:
    if command.succeeded:
        return
    raise AssertionError(
        "Precondition failed: TS-937 could not resolve Flutter dependencies in the live repository checkout.\n"
        f"Command: {command.command_text}\n"
        f"Exit code: {command.exit_code}\n"
        f"stdout:\n{command.stdout}\n"
        f"stderr:\n{command.stderr}"
    )


def _assert_dedicated_unit_test_exists(
    test_source: str,
    *,
    result: dict[str, object],
) -> None:
    failures: list[str] = []
    required_snippets = (
        "test(",
        EXPECTED_TEST_NAME,
        "semanticLabel: _workspaceSyncSemanticLabel(l10n, viewModel),",
        "semanticLabel: 'Attention needed',",
        "lib/ui/features/tracker/views/trackstate_app.dart",
        "'analyze'",
    )
    for snippet in required_snippets:
        if snippet not in test_source:
            failures.append(f"missing `{snippet}`")

    if failures:
        observed = (
            f"Opened `{TEST_TARGET.as_posix()}`, but it no longer contains the dedicated "
            f"sync semantic-label regression logic. Problems: {', '.join(failures)}."
        )
        _record_step(
            result,
            step=1,
            status="failed",
            action=REQUEST_STEPS[0],
            observed=observed,
        )
        raise AssertionError(f"Step 1 failed: {observed}")

    _record_step(
        result,
        step=1,
        status="passed",
        action=REQUEST_STEPS[0],
        observed=(
            f"Opened `{TEST_TARGET.as_posix()}` and confirmed it is the dedicated sync "
            "widget contract regression test. The file defines the expected test case "
            f"`{EXPECTED_TEST_NAME}` and targets the live tracker source file."
        ),
    )


def _assert_live_signature_is_wrapped(
    test_source: str,
    *,
    source: str,
    localization: str,
    result: dict[str, object],
) -> None:
    failures: list[str] = []
    source_requirements = (
        "final _SyncPillSemanticLabel? semanticLabel;",
        "_SyncPillSemanticLabel _workspaceSyncSemanticLabel(",
        "return _StaticSyncPillSemanticLabel(",
        "return _PrefixedSyncPillSemanticLabel(",
        "semanticLabel: _workspaceSyncSemanticLabel(l10n, viewModel),",
    )
    for snippet in source_requirements:
        if snippet not in source:
            failures.append(f"live source missing `{snippet}`")

    if "Sync error, attention needed" not in localization:
        failures.append(
            "generated English localization missing `Sync error, attention needed`"
        )

    if "semanticLabel: 'Attention needed'," not in test_source:
        failures.append("test no longer mutates the call site to a primitive String")

    if failures:
        observed = (
            "The dedicated test no longer maps cleanly to the live sync widget "
            f"signature contract. Problems: {', '.join(failures)}."
        )
        _record_step(
            result,
            step=2,
            status="failed",
            action=REQUEST_STEPS[1],
            observed=observed,
        )
        raise AssertionError(f"Step 2 failed: {observed}")

    _record_step(
        result,
        step=2,
        status="passed",
        action=REQUEST_STEPS[1],
        observed=(
            "Located the semanticLabel type contract in the live implementation: "
            "`_SyncPill` still declares `final _SyncPillSemanticLabel? semanticLabel;`, "
            "`_workspaceSyncSemanticLabel(...)` returns wrapper instances, the live call "
            "site still passes `_workspaceSyncSemanticLabel(l10n, viewModel)`, and the "
            "English semantic label remains `Sync error, attention needed`. The dedicated "
            "test asserts this contract by mutating the call site to the raw "
            "`'Attention needed'` string and rerunning `flutter analyze`."
        ),
    )


def _assert_flutter_test_passed(
    command: CliCommandResult,
    *,
    result: dict[str, object],
) -> None:
    output = _combined_output(command)
    normalized_output = output.lower()
    passed = command.exit_code == 0 and EXPECTED_TEST_NAME.lower() in normalized_output
    all_tests_passed = "all tests passed" in normalized_output or "+1:" in normalized_output

    if passed and all_tests_passed:
        _record_step(
            result,
            step=3,
            status="passed",
            action=REQUEST_STEPS[2],
            observed=(
                f"Ran `{command.command_text}`. Flutter exited with code 0, printed the "
                f"dedicated test name `{EXPECTED_TEST_NAME}`, and reported a passing test run.\n"
                f"Terminal output:\n{output}"
            ),
        )
        return

    observed = (
        f"Ran `{command.command_text}`, but the dedicated contract test did not complete "
        f"as a clear pass. Observed exit_code={command.exit_code}; "
        f"test_name_seen={EXPECTED_TEST_NAME.lower() in normalized_output}; "
        f"all_tests_passed={all_tests_passed}.\nTerminal output:\n{output}"
    )
    _record_step(
        result,
        step=3,
        status="failed",
        action=REQUEST_STEPS[2],
        observed=observed,
    )
    raise AssertionError(
        "Step 3 failed: `flutter test` did not report a passing run for the dedicated "
        "workspace sync semantic-label contract test.\n"
        f"Observed command: {command.command_text}\n"
        f"Observed exit code: {command.exit_code}\n"
        f"Observed output:\n{output}"
    )


def _read_required_file(relative_path: Path) -> str:
    path = REPO_ROOT / relative_path
    if not path.is_file():
        raise AssertionError(f"Required file is missing: {relative_path.as_posix()}")
    return path.read_text(encoding="utf-8")


def _test_source_excerpt(source: str) -> str:
    return _snippet_block(
        source,
        "semanticLabel: _workspaceSyncSemanticLabel(l10n, viewModel),",
        after=220,
    )


def _source_signature_excerpt(source: str) -> str:
    return _snippet_block(source, "final _SyncPillSemanticLabel? semanticLabel;", after=220)


def _snippet_block(source: str, needle: str, *, after: int) -> str:
    index = source.find(needle)
    if index == -1:
        return "<snippet not found>"
    start = max(0, index - 80)
    end = min(len(source), index + len(needle) + after)
    return source[start:end].strip()


def _populate_command_metadata(
    result: dict[str, object],
    *,
    flutter_version: CliCommandResult,
    pub_get: CliCommandResult,
) -> None:
    result["flutter_version_command"] = flutter_version.command_text
    result["flutter_version_output"] = _combined_output(flutter_version)
    result["pub_get_command"] = pub_get.command_text
    result["pub_get_output"] = _combined_output(pub_get)


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
    error = str(result.get("error", "AssertionError: TS-937 failed"))
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
        f"*Environment:* local repository checkout | flutter test | {result.get('os')}",
        f"*Config:* {{{{{result.get('config_path')}}}}}",
        "",
        "h4. Automation checks",
    ]
    for step in result.get("steps", []):
        assert isinstance(step, dict)
        marker = "(/)" if step.get("status") == "passed" else "(x)"
        lines.append(
            f"{marker} *Step {step.get('step')}* {step.get('action')}\n"
            f"Observed: {_jira_inline_code(str(step.get('observed')))}"
        )
    lines.extend(("", "h4. Human-style verification"))
    for check in result.get("human_verification", []):
        assert isinstance(check, dict)
        lines.append(
            f"* {_jira_inline_code(str(check.get('check')))}\n"
            f"Observed: {_jira_inline_code(str(check.get('observed')))}"
        )
    if not passed:
        lines.extend(
            (
                "",
                "h4. Failure details",
                f"*Error:* {result.get('error')}",
                "{code}",
                str(result.get("flutter_test_output", "<missing output>")),
                "{code}",
            )
        )
    return "\n".join(lines).strip() + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        f"# {TICKET_KEY} {'Passed' if passed else 'Failed'}",
        "",
        f"**Title:** {TEST_CASE_TITLE}",
        f"**Environment:** local repository checkout | flutter test | {result.get('os')}",
        f"**Test target:** `{result.get('test_target')}`",
        f"**Production target:** `{result.get('source_target')}`",
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
                str(result.get("flutter_test_output", "<missing output>")),
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
        f"# {TICKET_KEY} - sync widget semantic-label contract test failed\n\n"
        "## Steps to reproduce\n"
        f"1. {REQUEST_STEPS[0]}  \n"
        f"   - Actual: {step_map.get(1, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(1, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"2. {REQUEST_STEPS[1]}  \n"
        f"   - Actual: {step_map.get(2, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(2, {}).get('status') == 'passed' else 'FAILED ❌'}\n"
        f"3. {REQUEST_STEPS[2]}  \n"
        f"   - Actual: {step_map.get(3, {}).get('observed', '<missing>')}  \n"
        f"   - Result: {'PASSED ✅' if step_map.get(3, {}).get('status') == 'passed' else 'FAILED ❌'}\n\n"
        "## Exact error message or assertion failure\n"
        "```text\n"
        f"{result.get('traceback', result.get('error', '<missing>'))}"
        "```\n\n"
        "## Actual vs Expected\n"
        f"- **Expected:** {EXPECTED_RESULT}\n"
        "- **Actual:** The dedicated sync semantic-label regression test was missing, no "
        "longer matched the live `_SyncPill` wrapper contract, or `flutter test` did not "
        "complete with a passing result for `test/workspace_sync_semantic_label_contract_test.dart`.\n\n"
        "## Environment details\n"
        "- **URL:** local repository checkout (no deployed URL required for this unit test case)\n"
        "- **Browser:** N/A - local terminal validation\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Run command:** `{result.get('run_command')}`\n"
        f"- **Config:** `{result.get('config_path')}`\n"
        f"- **Test target:** `{result.get('test_target')}`\n"
        f"- **Production target:** `{result.get('source_target')}`\n"
        f"- **Localization target:** `{result.get('localization_target')}`\n"
        f"- **Flutter version command:** `{result.get('flutter_version_command')}`\n"
        f"- **Pub get command:** `{result.get('pub_get_command')}`\n"
        f"- **Flutter test command:** `{result.get('flutter_test_command')}`\n\n"
        "## Screenshots or logs\n"
        "- **Terminal output:**\n"
        "```text\n"
        f"{result.get('flutter_test_output', '<missing output>')}\n"
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


def _combined_output(command: CliCommandResult) -> str:
    parts = [command.stdout.strip(), command.stderr.strip()]
    return "\n".join(part for part in parts if part)


def _jira_inline_code(text: str) -> str:
    return re.sub(r"`([^`]+)`", r"{{\1}}", text)


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


if __name__ == "__main__":
    main()
