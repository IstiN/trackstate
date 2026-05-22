from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import traceback
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.core.models.cli_command_result import CliCommandResult  # noqa: E402

TICKET_KEY = "TS-926"
TEST_CASE_TITLE = (
    "UI element with exactly 4.5:1 contrast — axe-core audit identifies as compliant"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-926/test_ts_926.py"
CONFIG_PATH = REPO_ROOT / "testing/tests/TS-926/config.yaml"
PLAYWRIGHT_CONFIG_PATH = REPO_ROOT / "testing/tests/TS-926/playwright.config.js"
PLAYWRIGHT_SPEC_PATH = REPO_ROOT / "testing/tests/TS-926/ts926_accessibility_boundary.spec.js"
PLAYWRIGHT_SPEC_ARG = "ts926_accessibility_boundary.spec.js"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

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


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = _load_config(CONFIG_PATH)
    screenshot_path = OUTPUTS_DIR / str(config["screenshot_name"])
    observation_path = OUTPUTS_DIR / str(config["observation_name"])
    screenshot_path.unlink(missing_ok=True)
    observation_path.unlink(missing_ok=True)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "run_command": RUN_COMMAND,
        "test_file_path": str(Path("testing/tests/TS-926/test_ts_926.py")),
        "spec_file_path": str(Path("testing/tests/TS-926/ts926_accessibility_boundary.spec.js")),
        "config_path": str(Path("testing/tests/TS-926/config.yaml")),
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "expected_result": EXPECTED_RESULT,
        "exact_contrast_ratio": config["exact_contrast_ratio"],
        "contrast_tolerance": config["contrast_tolerance"],
        "text_color": config["text_color"],
        "background_color": config["background_color"],
        "visible_text": config["visible_text"],
        "accessible_button_label": config["accessible_button_label"],
        "steps": [],
        "human_verification": [],
    }

    install_result: CliCommandResult | None = None
    browser_install_result: CliCommandResult | None = None
    playwright_result: CliCommandResult | None = None
    observation: dict[str, object] = {}

    try:
        install_result = _run_command(("npm", "ci"))
        browser_install_result = _run_command(
            ("npx", "playwright", "install", "--with-deps", "chromium")
        )
        playwright_result = _run_command(
            (
                "npm",
                "run",
                "test:a11y",
                "--",
                f"--config={PLAYWRIGHT_CONFIG_PATH}",
                PLAYWRIGHT_SPEC_ARG,
                "--reporter=line",
            ),
            extra_env={
                "TS926_SCREENSHOT_PATH": str(screenshot_path),
                "TS926_OBSERVATION_PATH": str(observation_path),
            },
        )
        if observation_path.exists():
            observation = json.loads(observation_path.read_text(encoding="utf-8"))
        result["playwright_stdout"] = playwright_result.stdout
        result["playwright_stderr"] = playwright_result.stderr
        result["playwright_exit_code"] = playwright_result.exit_code
        result["screenshot_path"] = str(screenshot_path)
        result["observation_path"] = str(observation_path)
        result["observation"] = observation

        _evaluate_step_1(result, observation=observation, config=config)
        _evaluate_step_2(result, playwright_result=playwright_result)
        _evaluate_step_3(result, playwright_result=playwright_result)
        _record_human_verification(
            result,
            check=(
                "Viewed the rendered boundary probe the same way a user would, using the "
                "saved Playwright screenshot plus the visible-text capture from the live page."
            ),
            observed=(
                f"Screenshot: `{screenshot_path}`. Visible text: "
                f"`{observation.get('visibleText', '<missing>')}` inside the boundary card; "
                f"button label: `{observation.get('buttonAriaLabel', '<missing>')}`; "
                f"card background: `{observation.get('renderedBackground', '<missing>')}`; "
                f"computed contrast: `{observation.get('contrastRatio', '<missing>')}:1`."
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Reviewed the Playwright terminal output exactly as a developer or CI user "
                "would see it after the accessibility audit finished."
            ),
            observed=(
                f"Exit code: {playwright_result.exit_code}; output included "
                f"`{_passed_summary(playwright_result)}` and did not surface "
                "`color-contrast` or `non-descriptive-label` failures."
            ),
        )

        failures = _failed_steps(result)
        if failures:
            raise AssertionError("\n".join(failures))
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        if install_result is not None:
            result["npm_ci"] = _command_payload(install_result)
        if browser_install_result is not None:
            result["playwright_install"] = _command_payload(browser_install_result)
        if playwright_result is not None:
            result["playwright_command"] = _command_payload(playwright_result)
        _write_failure_outputs(result)
        raise

    result["npm_ci"] = _command_payload(install_result)
    result["playwright_install"] = _command_payload(browser_install_result)
    result["playwright_command"] = _command_payload(playwright_result)
    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _load_config(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    runtime_inputs = payload.get("runtime_inputs") or {}
    if not isinstance(runtime_inputs, dict):
        raise ValueError(f"{path} must contain a runtime_inputs mapping.")
    return runtime_inputs


def _run_command(
    command: tuple[str, ...],
    *,
    extra_env: dict[str, str] | None = None,
) -> CliCommandResult:
    env = os.environ.copy()
    env.setdefault("CI", "1")
    if extra_env:
        env.update(extra_env)

    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return CliCommandResult(
        command=command,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _evaluate_step_1(
    result: dict[str, object],
    *,
    observation: dict[str, object],
    config: dict[str, object],
) -> None:
    tolerance = float(config["contrast_tolerance"])
    expected_ratio = float(config["exact_contrast_ratio"])
    observed_text = str(observation.get("visibleText", ""))
    observed_label = str(observation.get("buttonAriaLabel", ""))
    observed_ratio = observation.get("contrastRatio")

    if not observation:
        observed = (
            "The Playwright probe did not write its boundary observation file, so the "
            "automation could not confirm the rendered text, label, or contrast ratio."
        )
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=observed)
        return

    if observed_text != str(config["visible_text"]):
        observed = (
            "The boundary probe rendered, but the visible text did not match the expected "
            f"user-facing sample.\nExpected: {config['visible_text']!r}\nObserved: {observed_text!r}"
        )
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=observed)
        return

    if observed_label != str(config["accessible_button_label"]):
        observed = (
            "The boundary probe rendered, but the interactive control did not expose the "
            "expected descriptive accessible label.\n"
            f"Expected: {config['accessible_button_label']!r}\nObserved: {observed_label!r}"
        )
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=observed)
        return

    if not isinstance(observed_ratio, (int, float)):
        observed = (
            "The boundary probe rendered, but it did not report a numeric contrast ratio.\n"
            f"Observation payload: {json.dumps(observation, indent=2)}"
        )
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=observed)
        return

    if abs(float(observed_ratio) - expected_ratio) > tolerance:
        observed = (
            "The rendered probe did not stay on the exact boundary ratio required by the "
            "ticket.\n"
            f"Expected ratio: {expected_ratio}:1 (+/- {tolerance})\n"
            f"Observed ratio: {observed_ratio}:1\n"
            f"Rendered foreground: {observation.get('renderedForeground', '<missing>')}\n"
            f"Rendered background: {observation.get('renderedBackground', '<missing>')}"
        )
        _record_step(result, step=1, status="failed", action=REQUEST_STEPS[0], observed=observed)
        return

    _record_step(
        result,
        step=1,
        status="passed",
        action=REQUEST_STEPS[0],
        observed=(
            "Rendered the boundary probe page with the expected visible text and a "
            "descriptive interactive label, and measured the actual rendered contrast at "
            f"{float(observed_ratio):.4f}:1.\n"
            f"Rendered foreground: {observation.get('renderedForeground', '<missing>')}\n"
            f"Rendered background: {observation.get('renderedBackground', '<missing>')}"
        ),
    )


def _evaluate_step_2(
    result: dict[str, object],
    *,
    playwright_result: CliCommandResult,
) -> None:
    if not playwright_result.succeeded:
        observed = (
            "The Playwright accessibility audit returned a non-zero exit code instead of "
            "passing like the CI gate should for a compliant 4.5:1 boundary sample.\n"
            f"Command: {playwright_result.command_text}\n"
            f"Exit code: {playwright_result.exit_code}\n"
            f"stdout:\n{playwright_result.stdout}\n"
            f"stderr:\n{playwright_result.stderr}"
        )
        _record_step(result, step=2, status="failed", action=REQUEST_STEPS[1], observed=observed)
        return

    _record_step(
        result,
        step=2,
        status="passed",
        action=REQUEST_STEPS[1],
        observed=(
            "Ran the same Playwright accessibility command shape that the CI job uses, and "
            f"it exited successfully with code {playwright_result.exit_code}.\n"
            f"Command: {playwright_result.command_text}"
        ),
    )


def _evaluate_step_3(
    result: dict[str, object],
    *,
    playwright_result: CliCommandResult,
) -> None:
    combined_output = f"{playwright_result.stdout}\n{playwright_result.stderr}".lower()
    forbidden_markers = ["color-contrast", "non-descriptive-label"]
    found_markers = [marker for marker in forbidden_markers if marker in combined_output]
    passed_summary = _passed_summary(playwright_result)

    if found_markers:
        observed = (
            "The Playwright accessibility audit logs still mentioned violation markers even "
            "though this boundary sample should be compliant.\n"
            f"Found markers: {found_markers}\n"
            f"stdout:\n{playwright_result.stdout}\n"
            f"stderr:\n{playwright_result.stderr}"
        )
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=observed)
        return

    if not playwright_result.succeeded:
        observed = (
            "The Playwright audit logs were available, but the run itself failed, so the "
            "user-visible audit result did not match the expected compliant pass state.\n"
            f"stdout:\n{playwright_result.stdout}\n"
            f"stderr:\n{playwright_result.stderr}"
        )
        _record_step(result, step=3, status="failed", action=REQUEST_STEPS[2], observed=observed)
        return

    _record_step(
        result,
        step=3,
        status="passed",
        action=REQUEST_STEPS[2],
        observed=(
            "Reviewed the Playwright accessibility audit logs and confirmed the run stayed "
            "clean: no `color-contrast` or `non-descriptive-label` markers appeared, and "
            f"the runner reported `{passed_summary}`."
        ),
    )


def _passed_summary(playwright_result: CliCommandResult) -> str:
    combined = f"{playwright_result.stdout}\n{playwright_result.stderr}"
    for marker in ("1 passed", "1 test passed"):
        if marker in combined:
            return marker
    return "successful Playwright completion"


def _command_payload(command_result: CliCommandResult | None) -> dict[str, object] | None:
    if command_result is None:
        return None
    return {
        "command": command_result.command_text,
        "exit_code": command_result.exit_code,
        "stdout": command_result.stdout,
        "stderr": command_result.stderr,
    }


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
        "* Rendered a local boundary-condition probe page that uses the same Playwright + axe-core helper as the CI accessibility gate.",
        "* Verified the user-visible text, descriptive button label, and measured rendered contrast ratio before running the audit.",
        "* Executed the Playwright accessibility audit and treated its exit code as the CI-gate outcome for this scanner-behavior ticket.",
        "* Reviewed the audit logs for any color-contrast or non-descriptive-label failures.",
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
            f"* Environment: browser Chromium (Playwright), OS {{{{{result['os']}}}}}, "
            f"spec {{{{testing/tests/TS-926/ts926_accessibility_boundary.spec.js}}}}."
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
        "- Rendered a local boundary-condition probe page that uses the same Playwright + axe-core helper as the CI accessibility gate.",
        "- Verified the visible text, descriptive button label, and measured rendered contrast ratio before the audit ran.",
        "- Executed the Playwright accessibility audit and used its exit code as the CI-gate result for this scanner-behavior ticket.",
        "- Reviewed the audit logs to confirm no `color-contrast` or `non-descriptive-label` failures appeared.",
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
            f"- Environment: browser `Chromium (Playwright)`, OS `{result['os']}`, "
            "spec `testing/tests/TS-926/ts926_accessibility_boundary.spec.js`."
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
        "- Added an isolated TS-926 Playwright boundary probe for the shared axe-core accessibility runner.",
        "- The probe renders visible text at the 4.5:1 WCAG AA boundary and keeps the interactive control label descriptive.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        f"- Browser: `Chromium (Playwright)` on `{result['os']}`.",
        (
            "- Outcome: the shared accessibility runner treated the exact 4.5:1 boundary as compliant and exited successfully."
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
    return "\n".join(
        [
            f"# {TICKET_KEY} - Axe-core boundary contrast sample is not treated as compliant",
            "",
            "## Steps to reproduce",
            (
                "1. Create a Pull Request with a UI component where the text color and "
                "background color provide a contrast ratio of exactly 4.5:1. "
                + _step_status_summary(result, 1)
            ),
            (
                "2. Push the changes to trigger the CI pipeline. "
                + _step_status_summary(result, 2)
            ),
            (
                "3. Review the logs of the Playwright accessibility audit. "
                + _step_status_summary(result, 3)
            ),
            "",
            "## Exact test reproduction",
            (
                "1. The automation rendered `Boundary contrast sample` with "
                f"`{result.get('text_color', '')}` on `{result.get('background_color', '')}` "
                "and exposed a descriptive button label."
            ),
            (
                "2. It ran the shared axe-core helper through Playwright using:\n"
                f"   `{result.get('playwright_command', {}).get('command', RUN_COMMAND)}`"
            ),
            (
                "3. It captured the rendered probe screenshot at "
                f"`{result.get('screenshot_path', '<missing>')}` and the observation JSON at "
                f"`{result.get('observation_path', '<missing>')}`."
            ),
            "",
            "## Expected result",
            f"- {EXPECTED_RESULT}",
            "",
            "## Actual result",
            (
                "- The accessibility runner did not treat the boundary sample as a clean "
                "pass. See the failing step details, command output, and recorded "
                "observation below."
            ),
            "",
            "## Actual observed data",
            f"- Observation: `{json.dumps(result.get('observation', {}), ensure_ascii=True)}`",
            f"- Screenshot: `{result.get('screenshot_path', '<missing>')}`",
            "",
            "## Environment",
            "- Browser: `Chromium (Playwright)`",
            f"- OS: `{result.get('os', '')}`",
            f"- Spec: `{result.get('spec_file_path', '')}`",
            "",
            "## Exact error message / assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", "<missing traceback>"))),
            "```",
            "",
            "## Relevant command output",
            "```text",
            _combined_command_output(result),
            "```",
        ]
    ) + "\n"


def _combined_command_output(result: dict[str, object]) -> str:
    command = result.get("playwright_command")
    if not isinstance(command, dict):
        return "<missing command output>"
    return (
        f"stdout:\n{command.get('stdout', '')}\n\n"
        f"stderr:\n{command.get('stderr', '')}"
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


def _failed_steps(result: dict[str, object]) -> list[str]:
    failures: list[str] = []
    steps = result.get("steps")
    if not isinstance(steps, list):
        return failures
    for entry in steps:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status", "")).lower() == "failed":
            failures.append(f"Step {entry.get('step')} failed: {entry.get('observed')}")
    return failures


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
        prefix = "* " if jira else "- "
        lines.append(prefix + check)
        lines.append(prefix + observed)
    return lines


def _failed_step_summary(result: dict[str, object]) -> str:
    failures = _failed_steps(result)
    if failures:
        return failures[0]
    return str(result.get("error", "Unknown failure"))


def _step_status_summary(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return "❌ The automation did not record this step."
    for entry in steps:
        if not isinstance(entry, dict) or entry.get("step") != step_number:
            continue
        status = str(entry.get("status", "")).lower()
        observed = str(entry.get("observed", ""))
        icon = "✅" if status == "passed" else "❌"
        return f"{icon} {observed}"
    return "❌ The automation did not record this step."


def _format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def _jira_inline(value: str) -> str:
    return (
        value.replace("{", "\\{")
        .replace("}", "\\}")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("`", "")
    )


if __name__ == "__main__":
    main()
