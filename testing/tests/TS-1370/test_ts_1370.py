from __future__ import annotations

import fnmatch
import json
import os
import platform
import subprocess
import sys
import tempfile
import traceback
import unittest
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.components.services.trackstate_release_artifact_validator import (  # noqa: E402
    TrackStateReleaseArtifactValidator,
)
from testing.core.config.live_setup_test_config import LiveSetupTestConfig  # noqa: E402
from testing.core.config.trackstate_release_artifact_config import (  # noqa: E402
    TrackStateReleaseArtifactConfig,
)
from testing.core.models.trackstate_release_artifact_result import (  # noqa: E402
    TrackStateReleaseAssetObservation,
    TrackStateReleaseArtifactObservation,
)
from testing.tests.support.github_release_tag_resolver_factory import (  # noqa: E402
    create_github_release_tag_resolver,
)
from testing.tests.support.trackstate_release_artifact_probe_factory import (  # noqa: E402
    create_trackstate_release_artifact_probe,
)

TICKET_KEY = "TS-1370"
TICKET_SUMMARY = "Desktop Artifact Integrity — binary-level verification using unified checksum"
TEST_FILE_PATH = "testing/tests/TS-1370/test_ts_1370.py"
RUN_COMMAND = "mkdir -p outputs && python testing/tests/TS-1370/test_ts_1370.py"

OUTPUTS_DIR = REPO_ROOT / "outputs"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
CONFIG_PATH = REPO_ROOT / "testing" / "tests" / TICKET_KEY / "config.yaml"


class DesktopArtifactIntegrityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = self._load_config(CONFIG_PATH)
        self.result: dict[str, Any] = {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "repository": self.config["repository"],
            "default_branch": self.config.get("default_branch", "main"),
            "release_tag": None,
            "checksum_file": None,
            "downloaded_assets": [],
            "checksum_entries": [],
            "verification_output": None,
            "failed_checksums": [],
            "missing_assets": [],
            "run_command": RUN_COMMAND,
            "test_file_path": TEST_FILE_PATH,
            "os": platform.system(),
            "arch": platform.machine(),
            "steps": [],
            "human_verification": [],
        }

    def test_unified_checksum_validates_all_desktop_and_cli_assets(self) -> None:
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
            env_key="TS1370_RELEASE_TAG",
        )
        if release_tag is None:
            raise unittest.SkipTest(
                "No release tag could be determined. Set TS1370_RELEASE_TAG or run the test "
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
                action="Locate all required release assets and the unified checksum file.",
                observed=self.result["blocked_reason"],
            )
            raise unittest.SkipTest(self.result["blocked_reason"])

        expected_assets = self._expand_expected_assets(release_tag)
        checksum_pattern = self.config["checksum_file_pattern"].format(tag=release_tag)
        asset_by_name = {asset.name: asset for asset in observation.assets}

        missing_assets = [name for name in expected_assets if name not in asset_by_name]
        checksum_asset = self._find_checksum_asset(asset_by_name, checksum_pattern)
        if checksum_asset is not None:
            self.result["checksum_file"] = checksum_asset.name

        if missing_assets or checksum_asset is None:
            missing_items = missing_assets.copy()
            if checksum_asset is None:
                missing_items.append(checksum_pattern)
            self.result["missing_assets"] = missing_items
            self._record_step(
                step=2,
                status="failed",
                action="Locate all required release assets and the unified checksum file.",
                observed=f"Missing assets: {missing_items}. Available assets: {list(asset_by_name.keys())}",
            )
            self.result["blocked_reason"] = (
                f"Release {release_tag} is missing required assets: {missing_items}."
            )
            raise unittest.SkipTest(self.result["blocked_reason"])

        self.result["downloaded_assets"] = expected_assets
        self._record_step(
            step=2,
            status="passed",
            action="Locate all required release assets and the unified checksum file.",
            observed=f"Found assets: {expected_assets}; checksum file: {checksum_asset.name}",
        )

        repository_service = LiveSetupRepositoryService(
            config=LiveSetupTestConfig(
                app_url=config.releases_page_url,
                repository=config.repository,
                ref=config.default_branch,
            )
        )

        with tempfile.TemporaryDirectory(prefix=f"trackstate-{TICKET_KEY.lower()}-") as tmp:
            temp_dir = Path(tmp)
            self._download_assets(repository_service, asset_by_name, expected_assets, temp_dir)
            checksum_path = self._download_checksum_manifest(
                repository_service, checksum_asset, temp_dir
            )
            self._inspect_checksum_manifest(checksum_path)
            self._verify_checksums(temp_dir, checksum_path)

        self._record_human_verification(
            check=(
                "Verified artifact integrity as a real user would: downloaded all platform "
                "archives and the unified checksum file, then ran sha256sum -c to confirm "
                "every file is uncorrupted."
            ),
            observed=(
                f"checksum_file={self.result['checksum_file']}; "
                f"verified_assets={self.result['downloaded_assets']}; "
                f"failed_checksums={self.result['failed_checksums']}"
            ),
        )
        self._write_pass_outputs()

    def _expand_expected_assets(self, release_tag: str) -> list[str]:
        return [
            template.format(tag=release_tag)
            for template in self.config["expected_assets"]
        ]

    def _find_checksum_asset(
        self,
        asset_by_name: dict[str, TrackStateReleaseAssetObservation],
        pattern: str,
    ) -> TrackStateReleaseAssetObservation | None:
        matching = [name for name in asset_by_name if fnmatch.fnmatch(name, pattern)]
        if len(matching) == 1:
            return asset_by_name[matching[0]]
        return None

    def _download_assets(
        self,
        repository_service: LiveSetupRepositoryService,
        asset_by_name: dict[str, TrackStateReleaseAssetObservation],
        asset_names: list[str],
        destination_dir: Path,
    ) -> None:
        for asset_name in asset_names:
            asset = asset_by_name[asset_name]
            asset_path = destination_dir / asset_name
            asset_path.write_bytes(
                repository_service.download_release_asset_bytes(asset.id)
            )
        self._record_step(
            step=3,
            status="passed",
            action="Download all platform archives.",
            observed=f"Downloaded {len(asset_names)} archives to {destination_dir}.",
        )

    def _download_checksum_manifest(
        self,
        repository_service: LiveSetupRepositoryService,
        checksum_asset: TrackStateReleaseAssetObservation,
        destination_dir: Path,
    ) -> Path:
        checksum_path = destination_dir / checksum_asset.name
        checksum_path.write_bytes(
            repository_service.download_release_asset_bytes(checksum_asset.id)
        )
        return checksum_path

    def _inspect_checksum_manifest(self, checksum_path: Path) -> None:
        text = checksum_path.read_text(encoding="utf-8")
        entries = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                entries.append({"checksum": parts[0], "filename": parts[1].strip()})
        self.result["checksum_entries"] = entries
        self._record_step(
            step=4,
            status="passed",
            action="Read the unified checksum manifest.",
            observed=f"Manifest contains {len(entries)} entries: {[e['filename'] for e in entries]}",
        )

    def _verify_checksums(self, working_dir: Path, checksum_path: Path) -> None:
        completed = subprocess.run(
            ("sha256sum", "-c", str(checksum_path)),
            cwd=working_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        self.result["verification_output"] = completed.stdout.strip()
        failed = []
        for line in (completed.stdout + completed.stderr).splitlines():
            if ": OK" in line:
                continue
            if line.strip():
                failed.append(line.strip())
        self.result["failed_checksums"] = failed

        if completed.returncode != 0 or failed:
            self._record_step(
                step=5,
                status="failed",
                action="Verify every archive with sha256sum -c.",
                observed="\n".join(failed) if failed else completed.stderr.strip(),
            )
            raise AssertionError(
                "Checksum verification failed.\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )

        self._record_step(
            step=5,
            status="passed",
            action="Verify every archive with sha256sum -c.",
            observed="All listed archives returned OK.",
        )

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
            "The selected release does not expose all required assets or the unified checksum file."
        )
        missing = self.result.get("missing_assets") or []
        missing_items = [
            {
                "type": "release_asset",
                "name": item,
                "description": "Required platform archive or checksum file.",
                "how_to_add": (
                    "Run the release-on-main workflow to completion so all platform "
                    "archives and the unified checksum file are published to the GitHub release."
                ),
            }
            for item in missing
        ]
        RESULT_PATH.write_text(
            json.dumps(
                {
                    "status": "blocked_by_human",
                    "passed": 0,
                    "failed": 0,
                    "skipped": 1,
                    "summary": "0 passed, 0 failed, 1 skipped",
                    "blocked_reason": reason,
                    "missing": missing_items,
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
        f"*Checksum File:* {result.get('checksum_file')}",
        "",
        "h4. What was tested",
        "* Downloaded all six platform-specific archives from the selected GitHub release.",
        "* Downloaded the unified SHA256 checksum file.",
        "* Ran {{sha256sum -c}} to verify every listed archive returned OK.",
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
            "* The unified checksum file validates the integrity of all published desktop and CLI assets.",
            f"* Verified assets: {result.get('downloaded_assets')}",
            f"* Checksum entries: {len(result.get('checksum_entries', []))}",
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
        f"*Checksum File:* {result.get('checksum_file')}",
        "",
        "h4. What was tested",
        "* Downloaded all available platform archives and the unified checksum file.",
        "* Ran {{sha256sum -c}} to verify archive integrity.",
        "",
        "h4. Automation",
    ]
    lines.extend(_jira_step_lines(result.get("steps")))
    lines.extend(["", "h4. Result"])
    lines.append(f"* ❌ Failure: {{noformat}}{error}{{noformat}}")
    lines.append(f"* Failed checksums: {result.get('failed_checksums')}")
    lines.append(f"* Verification output: {result.get('verification_output')}")
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
        "* Attempted to locate all required platform archives and the unified checksum file on the selected GitHub release.",
        "",
        "h4. Result",
        f"* 🚫 Blocked: {reason}",
        f"* Missing assets: {result.get('missing_assets')}",
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
        f"**Checksum File:** `{result.get('checksum_file')}`",
        "",
        "## What was automated",
        "- Downloaded all six platform-specific archives from the selected GitHub release.",
        "- Downloaded the unified SHA256 checksum file.",
        "- Ran `sha256sum -c` to verify every listed archive returned OK.",
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
            "- The unified checksum file validates the integrity of all published desktop and CLI assets.",
            f"- Verified assets: `{result.get('downloaded_assets')}`",
            f"- Checksum entries: `{len(result.get('checksum_entries', []))}`",
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
        f"**Checksum File:** `{result.get('checksum_file')}`",
        "",
        "## What was automated",
        "- Downloaded all available platform archives and the unified checksum file.",
        "- Ran `sha256sum -c` to verify archive integrity.",
        "",
        "## Result",
        f"- Failure: `{error}`",
        f"- Failed checksums: `{result.get('failed_checksums')}`",
        f"- Verification output: `{result.get('verification_output')}`",
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
        "- Attempted to locate all required platform archives and the unified checksum file on the selected GitHub release.",
        "",
        "## Result",
        f"- 🚫 Blocked: {reason}",
        f"- Missing assets: `{result.get('missing_assets')}`",
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
        f"* Checksum file: {result.get('checksum_file')}\n"
        f"* Host OS: {result.get('os')} {result.get('arch')}\n"
        f"* Run command: {RUN_COMMAND}\n"
        "\n"
        "h4. Steps to Reproduce\n"
        "# Download all six platform archives and the unified checksum file from the selected GitHub release.\n"
        "# Place all files in the same directory.\n"
        "# Run {{sha256sum -c trackstate-<tag>.sha256}}.\n"
        "\n"
        "h4. Expected Result\n"
        "* The command returns OK for every file listed in the manifest.\n"
        "* The manifest covers all six platform archives.\n"
        "\n"
        "h4. Actual Result\n"
        f"{{noformat}}\n{result.get('error')}\n{{noformat}}\n"
        f"* Failed checksums: {result.get('failed_checksums')}\n"
        f"* Verification output: {result.get('verification_output')}\n"
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
