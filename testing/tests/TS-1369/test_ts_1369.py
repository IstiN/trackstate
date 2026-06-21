from __future__ import annotations

import json
import platform
import re
import sys
import traceback
import unittest
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_release_artifact_validator import (  # noqa: E402
    TrackStateReleaseArtifactValidator,
)
from testing.core.config.trackstate_release_artifact_config import (  # noqa: E402
    TrackStateReleaseArtifactConfig,
)
from testing.core.models.trackstate_release_artifact_result import (  # noqa: E402
    TrackStateReleaseArtifactObservation,
)
from testing.tests.support.github_release_tag_resolver_factory import (  # noqa: E402
    create_github_release_tag_resolver,
)
from testing.tests.support.trackstate_release_artifact_probe_factory import (  # noqa: E402
    create_trackstate_release_artifact_probe,
)

TICKET_KEY = "TS-1369"
TICKET_SUMMARY = "Release Note Artifact Table — platform and architecture details are accurate"
TEST_FILE_PATH = "testing/tests/TS-1369/test_ts_1369.py"
RUN_COMMAND = "mkdir -p outputs && python testing/tests/TS-1369/test_ts_1369.py"

OUTPUTS_DIR = REPO_ROOT / "outputs"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
CONFIG_PATH = REPO_ROOT / "testing" / "tests" / TICKET_KEY / "config.yaml"


class ReleaseNoteArtifactTableTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = self._load_config(CONFIG_PATH)
        self.result: dict[str, Any] = {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "repository": self.config["repository"],
            "default_branch": self.config.get("default_branch", "main"),
            "release_tag": None,
            "release_body": None,
            "table_found": False,
            "parsed_table": None,
            "missing_artifacts": [],
            "wrong_architectures": [],
            "run_command": RUN_COMMAND,
            "test_file_path": TEST_FILE_PATH,
            "os": platform.system(),
            "arch": platform.machine(),
            "steps": [],
            "human_verification": [],
        }

    def test_release_notes_contain_compiled_artifacts_table(self) -> None:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self._run_test()
        except unittest.SkipTest:
            self._write_blocked_outputs()
            raise
        except Exception as error:
            self._write_failure_outputs(str(error))
            raise

    def _run_test(self) -> None:
        base_config = TrackStateReleaseArtifactConfig.from_file_without_release_tag(CONFIG_PATH)
        resolver = create_github_release_tag_resolver(REPO_ROOT)
        release_tag = resolver.resolve_release_tag(
            repository=base_config.repository,
            pattern=base_config.release_tag_pattern,
            env_key="TS1369_RELEASE_TAG",
        )
        if release_tag is None:
            raise unittest.SkipTest(
                "No release tag could be determined. Set TS1369_RELEASE_TAG or run the test "
                "from a GitHub Actions release/tag workflow."
            )

        config = base_config.with_release_tag(release_tag)
        self.result["release_tag"] = release_tag
        self._record_step(
            step=1,
            status="passed",
            action="Select the GitHub release tag under test.",
            observed=f"Selected release tag: {release_tag}",
        )

        validator = TrackStateReleaseArtifactValidator(
            create_trackstate_release_artifact_probe(REPO_ROOT, config=config)
        )
        observation = validator.validate(config=config)

        if observation.selected_release is None:
            self.result["blocked_reason"] = (
                f"No published release matched the selected tag {release_tag}."
            )
            self._record_step(
                step=2,
                status="failed",
                action="Fetch the release body from GitHub.",
                observed=self.result["blocked_reason"],
            )
            raise unittest.SkipTest(self.result["blocked_reason"])

        release_body = observation.release_body or ""
        if not release_body:
            self.result["blocked_reason"] = (
                f"Could not fetch release body for {release_tag}."
            )
            self._record_step(
                step=2,
                status="failed",
                action="Fetch the release body from GitHub.",
                observed="The release body could not be retrieved.",
            )
            raise unittest.SkipTest(self.result["blocked_reason"])

        self.result["release_body"] = release_body
        self._record_step(
            step=2,
            status="passed",
            action="Fetch the release body from GitHub.",
            observed=f"Release body length: {len(release_body)} characters.",
        )

        table = self._extract_artifacts_table(release_body)
        if table is None:
            self._record_step(
                step=3,
                status="failed",
                action="Locate the compiled artifacts table in the release notes.",
                observed=f"No Markdown table found under heading '{self.config['expected_table_header']}'.",
            )
            raise AssertionError(
                f"Release notes for {release_tag} do not contain a compiled artifacts table."
            )

        self.result["table_found"] = True
        self.result["parsed_table"] = table
        self._record_step(
            step=3,
            status="passed",
            action="Locate the compiled artifacts table in the release notes.",
            observed=f"Found table with {len(table['rows'])} data rows.",
        )

        self._assert_table_contents(release_tag, table)

        self._record_human_verification(
            check=(
                "Verified the release notes as a real user would: opened the release page, "
                "located the compiled artifacts table, and confirmed every platform and "
                "architecture is listed correctly."
            ),
            observed=(
                f"table_heading={self.config['expected_table_header']}; "
                f"rows={table['rows']}"
            ),
        )
        self._write_pass_outputs()

    def _extract_artifacts_table(self, body: str) -> dict[str, Any] | None:
        lines = body.splitlines()
        heading_index: int | None = None
        expected_heading = self.config["expected_table_header"]
        for i, line in enumerate(lines):
            if re.search(rf"^#+\s+{re.escape(expected_heading)}\s*$", line):
                heading_index = i
                break

        if heading_index is None:
            return None

        table_lines: list[str] = []
        for line in lines[heading_index + 1 :]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                break
            if stripped.startswith("|"):
                table_lines.append(stripped)
            else:
                break

        if len(table_lines) < 3:
            return None

        header_line = table_lines[0]
        separator_line = table_lines[1]
        data_lines = table_lines[2:]

        headers = [cell.strip() for cell in header_line.split("|")[1:-1]]
        rows = []
        for row_line in data_lines:
            cells = [cell.strip() for cell in row_line.split("|")[1:-1]]
            rows.append(cells)

        return {
            "headers": headers,
            "separator": separator_line,
            "rows": rows,
            "raw": "\n".join(table_lines),
        }

    def _assert_table_contents(self, release_tag: str, table: dict[str, Any]) -> None:
        expected = self._expand_expected_artifacts(release_tag)
        rows = table.get("rows", [])

        missing: list[str] = []
        wrong_arch: list[str] = []
        found_platforms: set[str] = set()

        for platform_key, expected_values in expected.items():
            found_row = None
            for row in rows:
                if not row:
                    continue
                first_cell = row[0].lower()
                if platform_key in first_cell:
                    found_row = row
                    found_platforms.add(platform_key)
                    break

            if found_row is None:
                missing.append(f"{platform_key} row")
                continue

            desktop_cell = found_row[1] if len(found_row) > 1 else ""
            cli_cell = found_row[2] if len(found_row) > 2 else ""

            if expected_values["desktop"] not in desktop_cell:
                missing.append(f"{platform_key} desktop artifact {expected_values['desktop']}")
            if expected_values["cli"] not in cli_cell:
                missing.append(f"{platform_key} CLI artifact {expected_values['cli']}")

            arch_found = False
            for cell in found_row:
                if expected_values["architecture"] in cell:
                    arch_found = True
                    break
            if not arch_found:
                wrong_arch.append(
                    f"{platform_key}: expected architecture {expected_values['architecture']}"
                )

        self.result["missing_artifacts"] = missing
        self.result["wrong_architectures"] = wrong_arch

        failures = missing + wrong_arch
        if failures:
            self._record_step(
                step=4,
                status="failed",
                action="Verify the table lists all artifacts with correct architectures.",
                observed="; ".join(failures),
            )
            raise AssertionError("\n".join(failures))

        self._record_step(
            step=4,
            status="passed",
            action="Verify the table lists all artifacts with correct architectures.",
            observed=f"All platforms found with correct artifacts and architectures: {sorted(found_platforms)}.",
        )

    def _expand_expected_artifacts(self, release_tag: str) -> dict[str, dict[str, str]]:
        result: dict[str, dict[str, str]] = {}
        for platform_key, values in self.config["expected_artifacts"].items():
            result[platform_key] = {
                "desktop": values["desktop"].format(tag=release_tag),
                "cli": values["cli"].format(tag=release_tag),
                "architecture": values["architecture"],
            }
        return result

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"{path} must deserialize to a mapping.")
        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(f"{path} runtime_inputs must be a mapping.")
        return runtime_inputs

    def _record_step(
        self,
        *,
        step: int,
        status: str,
        action: str,
        observed: str,
    ) -> None:
        steps = self.result.setdefault("steps", [])
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
        self,
        *,
        check: str,
        observed: str,
    ) -> None:
        checks = self.result.setdefault("human_verification", [])
        assert isinstance(checks, list)
        checks.append({"check": check, "observed": observed})

    def _write_pass_outputs(self) -> None:
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
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        jira = _jira_pass_summary(self.result)
        RESPONSE_PATH.write_text(jira, encoding="utf-8")
        JIRA_COMMENT_PATH.write_text(jira, encoding="utf-8")
        PR_BODY_PATH.write_text(_markdown_pass_summary(self.result), encoding="utf-8")

    def _write_blocked_outputs(self) -> None:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
        reason = self.result.get("blocked_reason") or (
            "The selected release cannot be inspected."
        )
        RESULT_PATH.write_text(
            json.dumps(
                {
                    "status": "blocked_by_human",
                    "passed": 0,
                    "failed": 0,
                    "skipped": 1,
                    "summary": "0 passed, 0 failed, 1 skipped",
                    "blocked_reason": reason,
                    "missing": [
                        {
                            "type": "release_data",
                            "name": "release_body",
                            "description": "Release body with compiled artifacts table.",
                            "how_to_add": (
                                "Run the release-on-main workflow to completion so the release "
                                "notes and compiled artifacts table are published."
                            ),
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        jira = _jira_blocked_summary(self.result, reason)
        RESPONSE_PATH.write_text(jira, encoding="utf-8")
        JIRA_COMMENT_PATH.write_text(jira, encoding="utf-8")
        PR_BODY_PATH.write_text(_markdown_blocked_summary(self.result, reason), encoding="utf-8")

    def _write_failure_outputs(self, error: str) -> None:
        self.result["error"] = error
        self.result["traceback"] = traceback.format_exc()
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
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        jira = _jira_failure_summary(self.result, error)
        RESPONSE_PATH.write_text(jira, encoding="utf-8")
        JIRA_COMMENT_PATH.write_text(jira, encoding="utf-8")
        PR_BODY_PATH.write_text(_markdown_failure_summary(self.result, error), encoding="utf-8")
        BUG_DESCRIPTION_PATH.write_text(_bug_description(self.result), encoding="utf-8")


def _jira_pass_summary(result: dict[str, Any]) -> str:
    lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        f"*Repository:* {result['repository']}",
        f"*Release:* {result.get('release_tag')}",
        "",
        "h4. What was tested",
        "* Fetched the release body from the selected GitHub release.",
        "* Located the compiled artifacts Markdown table.",
        "* Verified the table lists Linux, Windows, and macOS desktop and CLI artifacts with correct architectures.",
        "",
        "h4. Automation",
    ]
    lines.extend(_jira_step_lines(result.get("steps")))
    lines.extend(["", "h4. Human-style verification"])
    lines.extend(_jira_human_lines(result.get("human_verification")))
    lines.extend(
        [
            "",
            "h4. Result",
            "* The release notes contain a compiled artifacts table with accurate platform and architecture details.",
            f"* Parsed table rows: {result.get('parsed_table', {}).get('rows')}",
            "",
            "h4. Test file",
            "{code}",
            TEST_FILE_PATH,
            "{code}",
            "",
            "h4. Run command",
            "{code:bash}",
            RUN_COMMAND,
            "{code}",
        ]
    )
    return "\n".join(lines) + "\n"


def _jira_failure_summary(result: dict[str, Any], error: str) -> str:
    lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        f"*Repository:* {result['repository']}",
        f"*Release:* {result.get('release_tag')}",
        "",
        "h4. What was tested",
        "* Fetched the release body and inspected the compiled artifacts table.",
        "",
        "h4. Automation",
    ]
    lines.extend(_jira_step_lines(result.get("steps")))
    lines.extend(["", "h4. Result"])
    lines.append(f"* ❌ Failure: {{noformat}}{error}{{noformat}}")
    lines.append(f"* Missing artifacts: {result.get('missing_artifacts')}")
    lines.append(f"* Wrong architectures: {result.get('wrong_architectures')}")
    lines.extend(
        [
            "",
            "h4. Test file",
            "{code}",
            TEST_FILE_PATH,
            "{code}",
            "",
            "h4. Run command",
            "{code:bash}",
            RUN_COMMAND,
            "{code}",
        ]
    )
    return "\n".join(lines) + "\n"


def _jira_blocked_summary(result: dict[str, Any], reason: str) -> str:
    lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* 🚫 BLOCKED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        f"*Repository:* {result['repository']}",
        f"*Release:* {result.get('release_tag') or '<none selected>'}",
        "",
        "h4. What was tested",
        "* Attempted to fetch the release body and locate the compiled artifacts table.",
        "",
        "h4. Result",
        f"* 🚫 Blocked: {reason}",
        "",
        "h4. Test file",
        "{code}",
        TEST_FILE_PATH,
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]
    return "\n".join(lines) + "\n"


def _markdown_pass_summary(result: dict[str, Any]) -> str:
    lines = [
        "## Test Automation Result",
        "",
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        f"**Repository:** `{result['repository']}`",
        f"**Release:** `{result.get('release_tag')}`",
        "",
        "## What was automated",
        "- Fetched the release body from the selected GitHub release.",
        "- Located the compiled artifacts Markdown table.",
        "- Verified the table lists Linux, Windows, and macOS desktop and CLI artifacts with correct architectures.",
        "",
        "## Automation details",
    ]
    lines.extend(_markdown_step_lines(result.get("steps")))
    lines.extend(["", "## Human-style verification"])
    lines.extend(_markdown_human_lines(result.get("human_verification")))
    lines.extend(
        [
            "",
            "## Result",
            "- The release notes contain a compiled artifacts table with accurate platform and architecture details.",
            f"- Parsed table rows: `{result.get('parsed_table', {}).get('rows')}`",
            "",
            "## How to run",
            "```bash",
            RUN_COMMAND,
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def _markdown_failure_summary(result: dict[str, Any], error: str) -> str:
    lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        f"**Repository:** `{result['repository']}`",
        f"**Release:** `{result.get('release_tag')}`",
        "",
        "## What was automated",
        "- Fetched the release body and inspected the compiled artifacts table.",
        "",
        "## Result",
        f"- Failure: `{error}`",
        f"- Missing artifacts: `{result.get('missing_artifacts')}`",
        f"- Wrong architectures: `{result.get('wrong_architectures')}`",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    return "\n".join(lines) + "\n"


def _markdown_blocked_summary(result: dict[str, Any], reason: str) -> str:
    lines = [
        "## Test Automation Result",
        "",
        "**Status:** 🚫 BLOCKED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        f"**Repository:** `{result['repository']}`",
        f"**Release:** `{result.get('release_tag') or '<none selected>'}`",
        "",
        "## What was automated",
        "- Attempted to fetch the release body and locate the compiled artifacts table.",
        "",
        "## Result",
        f"- 🚫 Blocked: {reason}",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, Any]) -> str:
    return (
        f"h4. Environment\n"
        f"* Repository: {result['repository']}\n"
        f"* Release: {result.get('release_tag')}\n"
        f"* Host OS: {result.get('os')} {result.get('arch')}\n"
        f"* Run command: {RUN_COMMAND}\n"
        "\n"
        "h4. Steps to Reproduce\n"
        "# Open the Releases page for the repository.\n"
        "# Select the target release.\n"
        "# Locate the 'Compiled artifacts' table in the release body.\n"
        "\n"
        "h4. Expected Result\n"
        "* The release notes include a Markdown table under 'Compiled artifacts'.\n"
        "* The table lists Linux, Windows, and macOS rows.\n"
        "* Each row contains the desktop artifact, CLI artifact, and correct architecture label.\n"
        "\n"
        "h4. Actual Result\n"
        f"{{noformat}}\n{result.get('error')}\n{{noformat}}\n"
        f"* Missing artifacts: {result.get('missing_artifacts')}\n"
        f"* Wrong architectures: {result.get('wrong_architectures')}\n"
        "\n"
        "h4. Logs / Error Output\n"
        "{code}\n"
        f"{result.get('traceback', '')}\n"
        "{code}\n"
    )


def _jira_step_lines(steps: Any) -> list[str]:
    if not isinstance(steps, list) or not steps:
        return ["* No automation steps were recorded."]
    lines: list[str] = []
    for entry in steps:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status", "")).strip().lower()
        icon = "✅" if status == "passed" else "❌"
        lines.append(f"* {icon} Step {entry.get('step')}: {entry.get('action')}")
        lines.append(f"** Observed: {entry.get('observed')}")
    return lines


def _jira_human_lines(checks: Any) -> list[str]:
    if not isinstance(checks, list) or not checks:
        return ["* No additional human-style verification was recorded."]
    lines: list[str] = []
    for entry in checks:
        if not isinstance(entry, dict):
            continue
        lines.append(f"* {entry.get('check')}")
        lines.append(f"** Observed: {entry.get('observed')}")
    return lines


def _markdown_step_lines(steps: Any) -> list[str]:
    if not isinstance(steps, list) or not steps:
        return ["- No automation steps were recorded."]
    lines: list[str] = []
    for entry in steps:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status", "")).strip().lower()
        icon = "✅" if status == "passed" else "❌"
        lines.append(
            f"- {icon} **Step {entry.get('step')}:** {entry.get('action')} "
            f"Observed: `{entry.get('observed')}`"
        )
    return lines


def _markdown_human_lines(checks: Any) -> list[str]:
    if not isinstance(checks, list) or not checks:
        return ["- No additional human-style verification was recorded."]
    lines: list[str] = []
    for entry in checks:
        if not isinstance(entry, dict):
            continue
        lines.append(
            f"- **Check:** {entry.get('check')} **Observed:** `{entry.get('observed')}`"
        )
    return lines


if __name__ == "__main__":
    unittest.main()
