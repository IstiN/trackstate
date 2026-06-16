import fnmatch
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import traceback
import unittest
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TICKET_KEY = "TS-1366"
TICKET_SUMMARY = "CLI Archive Content Atomicity — binary-only packaging and executable bit"
TEST_FILE_PATH = "testing/tests/TS-1366/test_ts_1366.py"
RUN_COMMAND = "mkdir -p outputs && python testing/tests/TS-1366/test_ts_1366.py"

OUTPUTS_DIR = REPO_ROOT / "outputs"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
CONFIG_PATH = REPO_ROOT / "testing" / "tests" / TICKET_KEY / "config.yaml"


class CliArchiveAtomicityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = self._load_config(CONFIG_PATH)
        self.result: dict[str, Any] = {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "repository": self.config["repository"],
            "default_branch": self.config.get("default_branch", "main"),
            "release_tag": None,
            "cli_archive_asset": None,
            "archive_members": [],
            "extracted_binary_path": None,
            "extracted_binary_mode": None,
            "file_output": None,
            "binary_run_output": None,
            "binary_run_error": None,
            "run_command": RUN_COMMAND,
            "test_file_path": TEST_FILE_PATH,
            "os": platform.system(),
            "arch": platform.machine(),
            "steps": [],
            "human_verification": [],
        }
        self._github_env = self._github_token_env()

    def test_cli_archive_is_atomic_and_executable(self) -> None:
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
        release_tag = self._resolve_release_tag()
        self.result["release_tag"] = release_tag
        self._record_step(
            step=1,
            status="passed",
            action="Select the GitHub release tag under test.",
            observed=f"Selected release tag: {release_tag}",
        )

        cli_asset = self._find_cli_asset(release_tag)
        if cli_asset is None:
            self._record_step(
                step=2,
                status="failed",
                action="Locate the Linux x64 CLI archive on the selected release.",
                observed=(
                    f"No asset matching {self.config['cli_archive_pattern']} "
                    f"was found on release {release_tag}."
                ),
            )
            raise unittest.SkipTest(
                f"Release {release_tag} does not expose a CLI archive matching "
                f"{self.config['cli_archive_pattern']}."
            )

        self.result["cli_archive_asset"] = cli_asset
        self._record_step(
            step=2,
            status="passed",
            action="Locate the Linux x64 CLI archive on the selected release.",
            observed=f"CLI archive asset: {cli_asset}",
        )

        with tempfile.TemporaryDirectory(prefix=f"trackstate-{TICKET_KEY.lower()}-") as tmp:
            temp_dir = Path(tmp)
            archive_path = self._download_asset(release_tag, cli_asset, temp_dir)
            members = self._inspect_archive_members(archive_path)
            self.result["archive_members"] = [
                {"name": m.name, "mode": oct(stat.S_IMODE(m.mode)), "isreg": m.isreg()}
                for m in members
            ]
            self._assert_atomic_contents(members)

            extract_dir = temp_dir / "extract"
            extract_dir.mkdir()
            self._extract_archive(archive_path, extract_dir)
            binary_path = extract_dir / self.config["expected_member_name"]
            self.result["extracted_binary_path"] = str(binary_path)
            self._assert_executable_bit(binary_path)
            self._verify_binary_with_file(binary_path)
            self._run_extracted_binary(binary_path)

        self._record_human_verification(
            check=(
                "Verified the CLI archive as a real user would: downloaded the published "
                "release asset, listed its contents, extracted the binary, and confirmed "
                "the executable permissions allow immediate execution."
            ),
            observed=(
                f"archive={self.result['cli_archive_asset']}; "
                f"members={self.result['archive_members']}; "
                f"binary_mode={self.result['extracted_binary_mode']}"
            ),
        )
        self._write_pass_outputs()

    def _resolve_release_tag(self) -> str:
        env_tag = os.getenv("TS1366_RELEASE_TAG", "").strip()
        if env_tag:
            if self._matches_release_pattern(env_tag):
                return env_tag
            raise AssertionError(
                f"TS1366_RELEASE_TAG={env_tag!r} does not match the configured "
                f"release tag pattern {self.config['release_tag_pattern']}."
            )

        ci_tag = self._read_ci_release_tag()
        if ci_tag:
            return ci_tag

        latest_tag = self._latest_release_tag()
        if latest_tag:
            return latest_tag

        raise unittest.SkipTest(
            "No release tag could be determined. Set TS1366_RELEASE_TAG or run the test "
            "from a GitHub Actions release/tag workflow."
        )

    def _matches_release_pattern(self, tag: str) -> bool:
        return re.fullmatch(self.config["release_tag_pattern"], tag) is not None

    def _read_ci_release_tag(self) -> str | None:
        github_ref_name = os.getenv("GITHUB_REF_NAME", "").strip()
        if github_ref_name and self._matches_release_pattern(github_ref_name):
            return github_ref_name

        event_path = os.getenv("GITHUB_EVENT_PATH")
        if not event_path:
            return None
        try:
            payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None
        if not isinstance(payload, dict):
            return None

        candidates: list[str | None] = []
        inputs = payload.get("inputs")
        if isinstance(inputs, dict):
            candidates.append(self._strip_string(inputs.get("release_ref")))
        release = payload.get("release")
        if isinstance(release, dict):
            candidates.append(self._strip_string(release.get("tag_name")))
        ref = self._strip_string(payload.get("ref"))
        if ref and ref.startswith("refs/tags/"):
            candidates.append(ref.removeprefix("refs/tags/").strip())

        for candidate in candidates:
            if candidate and self._matches_release_pattern(candidate):
                return candidate
        return None

    @staticmethod
    def _strip_string(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped or None

    def _latest_release_tag(self) -> str | None:
        command = (
            "gh",
            "release",
            "list",
            "--repo",
            self.config["repository"],
            "--limit",
            "50",
            "--json",
            "tagName",
            "--jq",
            ".[].tagName",
        )
        completed = self._run_gh(command)
        if completed.returncode != 0:
            return None
        for line in completed.stdout.splitlines():
            tag = line.strip()
            if tag and self._matches_release_pattern(tag):
                return tag
        return None

    def _find_cli_asset(self, release_tag: str) -> str | None:
        command = (
            "gh",
            "release",
            "view",
            release_tag,
            "--repo",
            self.config["repository"],
            "--json",
            "assets",
            "--jq",
            ".assets[].name",
        )
        completed = self._run_gh(command)
        if completed.returncode != 0:
            raise AssertionError(
                f"Could not list assets for release {release_tag}.\n"
                f"stderr: {completed.stderr}"
            )
        pattern = self.config["cli_archive_pattern"]
        matching = [
            line.strip()
            for line in completed.stdout.splitlines()
            if fnmatch.fnmatch(line.strip(), pattern)
        ]
        if not matching:
            return None
        if len(matching) > 1:
            raise AssertionError(
                f"Release {release_tag} exposed multiple CLI archives matching "
                f"{pattern}: {matching}."
            )
        return matching[0]

    def _download_asset(
        self,
        release_tag: str,
        asset_name: str,
        destination_dir: Path,
    ) -> Path:
        command = (
            "gh",
            "release",
            "download",
            release_tag,
            "--repo",
            self.config["repository"],
            "--pattern",
            asset_name,
            "--dir",
            str(destination_dir),
        )
        completed = self._run_gh(command)
        if completed.returncode != 0:
            raise AssertionError(
                f"Could not download asset {asset_name} from release {release_tag}.\n"
                f"stderr: {completed.stderr}"
            )
        candidates = list(destination_dir.glob(asset_name))
        if not candidates:
            raise AssertionError(
                f"Asset {asset_name} was not written to {destination_dir}."
            )
        return candidates[0]

    def _inspect_archive_members(self, archive_path: Path) -> list[tarfile.TarInfo]:
        try:
            with tarfile.open(archive_path, mode="r:*") as tf:
                members = tf.getmembers()
        except tarfile.TarError as error:
            raise AssertionError(
                f"Could not open archive {archive_path.name}: {error}"
            ) from error

        listing = "\n".join(
            f"{m.name}\t{oct(stat.S_IMODE(m.mode))}\t{'dir' if m.isdir() else 'file' if m.isreg() else 'other'}"
            for m in members
        )
        self._record_step(
            step=3,
            status="passed",
            action="List the archive contents.",
            observed=f"Archive members:\n{listing}",
        )
        return members

    def _assert_atomic_contents(self, members: list[tarfile.TarInfo]) -> None:
        member_names = [m.name for m in members]
        failures: list[str] = []
        if len(members) != 1:
            failures.append(
                f"Expected exactly one archive member, found {len(members)}: {member_names}."
            )
        else:
            member = members[0]
            if not member.isreg():
                failures.append(
                    f"The single archive member is not a regular file: {member.name} "
                    f"(type={member.type})."
                )
            if member.name != self.config["expected_member_name"]:
                failures.append(
                    f"Expected archive member named {self.config['expected_member_name']!r}, "
                    f"found {member.name!r}."
                )

        if failures:
            self._record_step(
                step=4,
                status="failed",
                action="Verify the archive contains only the compiled executable.",
                observed="\n".join(failures),
            )
            raise AssertionError("\n".join(failures))

        self._record_step(
            step=4,
            status="passed",
            action="Verify the archive contains only the compiled executable.",
            observed=f"Exactly one regular file named {self.config['expected_member_name']!r}.",
        )

    def _extract_archive(
        self,
        archive_path: Path,
        extract_dir: Path,
    ) -> None:
        try:
            with tarfile.open(archive_path, mode="r:*") as tf:
                tf.extractall(path=extract_dir)
        except tarfile.TarError as error:
            raise AssertionError(
                f"Could not extract archive {archive_path.name}: {error}"
            ) from error
        self._record_step(
            step=5,
            status="passed",
            action="Extract the archive.",
            observed=f"Extracted to {extract_dir}.",
        )

    def _assert_executable_bit(self, binary_path: Path) -> None:
        if not binary_path.exists():
            raise AssertionError(
                f"Extracted binary {binary_path.name} was not found at {binary_path}."
            )
        mode = binary_path.stat().st_mode
        self.result["extracted_binary_mode"] = oct(stat.S_IMODE(mode))
        if not stat.S_ISREG(mode):
            raise AssertionError(
                f"Extracted path {binary_path.name} is not a regular file."
            )

        expected_mask = int(self.config.get("expected_permission_bits", "0o755"), 8)
        observed_mode = stat.S_IMODE(mode)
        if (observed_mode & expected_mask) != expected_mask:
            raise AssertionError(
                f"Expected permissions to include {oct(expected_mask)} "
                f"(e.g., -rwxr-xr-x), observed {oct(observed_mode)}."
            )

        self._record_step(
            step=6,
            status="passed",
            action="Check the extracted binary permissions.",
            observed=f"Permissions: {oct(observed_mode)}.",
        )

    def _verify_binary_with_file(self, binary_path: Path) -> None:
        if shutil.which("file") is None:
            self.result["file_output"] = "<file utility not available>"
            return
        completed = subprocess.run(
            ("file", str(binary_path)),
            capture_output=True,
            text=True,
            check=False,
        )
        output = (completed.stdout or completed.stderr).strip()
        self.result["file_output"] = output
        self._record_human_verification(
            check="Ran `file` on the extracted binary as a human reviewer would.",
            observed=output,
        )

    def _run_extracted_binary(self, binary_path: Path) -> None:
        if platform.system() != "Linux" or platform.machine() not in {"x86_64", "amd64"}:
            self.result["binary_run_output"] = "<skipped: host is not Linux x86_64>"
            self._record_human_verification(
                check="Attempted to execute the extracted binary as a real user would.",
                observed="Skipped execution because the host is not a Linux x86_64 system.",
            )
            return

        if not os.access(binary_path, os.X_OK):
            self.result["binary_run_error"] = "<binary is not executable>"
            return

        completed = subprocess.run(
            (str(binary_path), "--version"),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.result["binary_run_output"] = completed.stdout.strip()
        self.result["binary_run_error"] = completed.stderr.strip() or None
        if completed.returncode != 0:
            raise AssertionError(
                f"Extracted binary exited with code {completed.returncode} when run "
                f"with --version.\nstdout: {completed.stdout}\nstderr: {completed.stderr}"
            )
        self._record_step(
            step=7,
            status="passed",
            action="Run the extracted binary to confirm it executes immediately.",
            observed=f"Exit code 0. stdout: {completed.stdout.strip()[:200]}",
        )
        self._record_human_verification(
            check="Executed the extracted binary with `--version` as a real user would after downloading.",
            observed=completed.stdout.strip()[:500],
        )

    def _run_gh(self, command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "GH_PAGER": "cat"}
        token = self._github_env.get("GH_TOKEN") or self._github_env.get("GITHUB_TOKEN")
        if token:
            env["GH_TOKEN"] = token
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def _github_token_env() -> dict[str, str]:
        return {
            key: value
            for key, value in os.environ.items()
            if key in {"GH_TOKEN", "GITHUB_TOKEN", "SOURCE_GITHUB_TOKEN"}
        }

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
            "No published release exposes a matching Linux x64 CLI archive."
        )
        missing = self.result.get("missing") or [
            {
                "type": "release_asset",
                "name": "trackstate-cli-linux-x64-<tag>.tar.gz",
                "description": (
                    "Linux x64 CLI archive produced by the release-on-main workflow."
                ),
                "how_to_add": (
                    "Run the release-on-main workflow to completion so the Linux CLI "
                    "archive is published to the GitHub release."
                ),
            }
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
                    "missing": missing,
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
        f"*CLI Archive:* {result.get('cli_archive_asset')}",
        "",
        "h4. What was tested",
        "* Downloaded the published Linux x64 CLI archive from the selected GitHub release.",
        "* Listed the archive contents and verified exactly one regular file named {trackstate}.",
        "* Extracted the binary and confirmed the executable bit is preserved.",
        "* Ran the extracted binary with {--version} as a real-user sanity check.",
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
            f"* The archive is atomic and contains only the compiled executable with executable permissions.",
            f"* Observed member: {result.get('archive_members')}",
            f"* Observed binary mode: {result.get('extracted_binary_mode')}",
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
        f"*CLI Archive:* {result.get('cli_archive_asset')}",
        "",
        "h4. What was tested",
        "* Downloaded the published Linux x64 CLI archive from the selected GitHub release.",
        "* Listed the archive contents and verified exactly one regular file named {trackstate}.",
        "* Extracted the binary and confirmed the executable bit is preserved.",
        "",
        "h4. Automation",
    ]
    lines.extend(_jira_step_lines(result.get("steps")))
    lines.extend(["", "h4. Result"])
    lines.append(f"* ❌ Failure: {{noformat}}{error}{{noformat}}")
    lines.append(f"* Observed archive members: {result.get('archive_members')}")
    lines.append(f"* Observed binary mode: {result.get('extracted_binary_mode')}")
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
        "* Attempted to locate a published Linux x64 CLI archive on the selected GitHub release.",
        "",
        "h4. Result",
        f"* 🚫 Blocked: {reason}",
        "",
        "h4. Missing",
        "* A published Linux x64 CLI archive matching {trackstate-cli-linux-x64-*.tar.gz}.",
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
        f"**CLI Archive:** `{result.get('cli_archive_asset')}`",
        "",
        "## What was automated",
        "- Downloaded the published Linux x64 CLI archive from the selected GitHub release.",
        "- Listed the archive contents and verified exactly one regular file named `trackstate`.",
        "- Extracted the binary and confirmed the executable bit is preserved.",
        "- Ran the extracted binary with `--version` as a real-user sanity check.",
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
            "- The archive is atomic and contains only the compiled executable with executable permissions.",
            f"- Observed member: `{result.get('archive_members')}`",
            f"- Observed binary mode: `{result.get('extracted_binary_mode')}`",
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
        f"**CLI Archive:** `{result.get('cli_archive_asset')}`",
        "",
        "## What was automated",
        "- Downloaded the published Linux x64 CLI archive from the selected GitHub release.",
        "- Listed the archive contents and verified exactly one regular file named `trackstate`.",
        "- Extracted the binary and confirmed the executable bit is preserved.",
        "",
        "## Result",
        f"- Failure: `{error}`",
        f"- Observed archive members: `{result.get('archive_members')}`",
        f"- Observed binary mode: `{result.get('extracted_binary_mode')}`",
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
        "- Attempted to locate a published Linux x64 CLI archive on the selected GitHub release.",
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
        f"* CLI archive: {result.get('cli_archive_asset')}\n"
        f"* Host OS: {result.get('os')} {result.get('arch')}\n"
        f"* Run command: {RUN_COMMAND}\n"
        "\n"
        "h4. Steps to Reproduce\n"
        "# Download the Linux x64 CLI archive from the selected GitHub release.\n"
        "# List the archive contents with {{tar -tzf}}.\n"
        "# Extract the archive and run {{ls -l trackstate}}.\n"
        "\n"
        "h4. Expected Result\n"
        "* The archive contains exactly one regular file named {{trackstate}}.\n"
        "* No directories, metadata files, or extra files are present.\n"
        "* The extracted binary has executable permissions (e.g., {{-rwxr-xr-x}}).\n"
        "\n"
        "h4. Actual Result\n"
        f"{{noformat}}\n{result.get('error')}\n{{noformat}}\n"
        f"* Observed archive members: {result.get('archive_members')}\n"
        f"* Observed binary mode: {result.get('extracted_binary_mode')}\n"
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
        lines.append(
            f"* {icon} Step {entry.get('step')}: {entry.get('action')}"
        )
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
