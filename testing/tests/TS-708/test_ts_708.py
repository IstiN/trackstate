from __future__ import annotations

from dataclasses import asdict
import json
import platform
import re
import sys
import traceback
from pathlib import Path

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
    TrackStateReleaseAssetObservation,
)
from testing.tests.support.trackstate_release_artifact_probe_factory import (  # noqa: E402
    create_trackstate_release_artifact_probe,
)

TICKET_KEY = "TS-708"
TICKET_SUMMARY = (
    "Generate Apple Silicon release artifacts — zipped .app and CLI binary produced for arm64"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-708/test_ts_708.py"
RUN_COMMAND = "python testing/tests/TS-708/test_ts_708.py"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts708ReleaseArtifactScenario()

    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        failure_result = locals().get("result", {}) if "result" in locals() else {}
        if not isinstance(failure_result, dict):
            failure_result = {}
        failure_result.update(
            {
                "ticket": TICKET_KEY,
                "ticket_summary": TICKET_SUMMARY,
                "error": f"{type(error).__name__}: {error}",
                "traceback": traceback.format_exc(),
            }
        )
        _write_failure_outputs(failure_result)
        raise


class Ts708ReleaseArtifactScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-708/config.yaml"
        self.config = TrackStateReleaseArtifactConfig.from_file(self.config_path)
        self.validator = TrackStateReleaseArtifactValidator(
            create_trackstate_release_artifact_probe(self.repository_root)
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        observation = self.validator.validate(config=self.config)
        result = self._build_result(observation)
        failures: list[str] = []

        release_failures = self._assert_selected_release(observation, result)
        failures.extend(release_failures)
        if release_failures:
            _record_step(
                result,
                step=1,
                status="failed",
                action="Inspect the Apple release published for the explicit version tag under test.",
                observed="\n".join(release_failures),
            )
        else:
            _record_step(
                result,
                step=1,
                status="passed",
                action="Inspect the Apple release published for the explicit version tag under test.",
                observed=(
                    f"selected_release={result.get('selected_release_tag')}; "
                    f"published_at={result.get('selected_release_published_at')}; "
                    f"asset_names={result.get('asset_names')}"
                ),
            )

        view_failures = self._assert_release_view(observation, result)
        failures.extend(view_failures)
        if view_failures:
            _record_step(
                result,
                step=2,
                status="failed",
                action="Navigate to the GitHub Release and inspect the published assets.",
                observed="\n".join(view_failures),
            )
        else:
            _record_step(
                result,
                step=2,
                status="passed",
                action="Navigate to the GitHub Release and inspect the published assets.",
                observed=_compact_text(_as_text(result.get("gh_release_view_stdout"))),
            )
            _record_human_verification(
                result,
                check=(
                    "Viewed the selected release through `gh release view` as a human-facing "
                    "release summary and compared the visible asset list to the ticket."
                ),
                observed=_compact_text(_as_text(result.get("gh_release_view_stdout"))),
            )

        asset_failures = self._assert_release_assets(observation, result)
        failures.extend(asset_failures)
        if asset_failures:
            _record_step(
                result,
                step=3,
                status="failed",
                action="Download the published app archive, CLI archive, and checksum manifest.",
                observed="\n".join(asset_failures),
            )
        else:
            _record_step(
                result,
                step=3,
                status="passed",
                action="Download the published app archive, CLI archive, and checksum manifest.",
                observed=f"asset_names={result.get('asset_names')}",
            )

        binary_failures = self._assert_binary_architectures(observation, result)
        failures.extend(binary_failures)
        if binary_failures:
            _record_step(
                result,
                step=4,
                status="failed",
                action="Run `file` for both extracted binaries.",
                observed="\n".join(binary_failures),
            )
        else:
            _record_step(
                result,
                step=4,
                status="passed",
                action="Run `file` for both extracted binaries.",
                observed=(
                    f"app_file_output={result.get('app_file_output')!r}; "
                    f"cli_file_output={result.get('cli_file_output')!r}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Confirmed the `file` output a user would read for the extracted desktop "
                    "binary and CLI binary both reported Apple Silicon arm64 executables."
                ),
                observed=(
                    f"app={result.get('app_file_output')}; "
                    f"cli={result.get('cli_file_output')}"
                ),
            )

        checksum_failures = self._assert_checksum_manifest(observation, result)
        failures.extend(checksum_failures)
        if checksum_failures:
            _record_step(
                result,
                step=5,
                status="failed",
                action="Verify the SHA256 checksum manifest.",
                observed="\n".join(checksum_failures),
            )
        else:
            _record_step(
                result,
                step=5,
                status="passed",
                action="Verify the SHA256 checksum manifest.",
                observed=_compact_text(_as_text(result.get("checksum_manifest_text"))),
            )

        return result, failures

    def _build_result(
        self,
        observation: TrackStateReleaseArtifactObservation,
    ) -> dict[str, object]:
        selected_release = observation.selected_release
        assets = list(observation.assets)
        app_asset = _first_asset(assets, "app-archive")
        cli_asset = _first_asset(assets, "cli-archive")
        checksum_asset = _first_asset(assets, "checksum")
        forbidden_assets = [asset.name for asset in assets if asset.classification == "forbidden"]
        other_assets = [
            asset.name
            for asset in assets
            if asset.classification not in {"app-archive", "cli-archive", "checksum", "forbidden"}
        ]
        return {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "config_path": str(self.config_path),
            "repository": self.config.repository,
            "repository_url": f"https://github.com/{self.config.repository}",
            "releases_page_url": observation.releases_page_url,
            "run_command": (
                f"TS708_RELEASE_TAG={self.config.release_tag} "
                "python testing/tests/TS-708/test_ts_708.py"
            ),
            "os": platform.system(),
            "expected_release_tag": self.config.release_tag,
            "selected_release_tag": selected_release.tag_name if selected_release else None,
            "selected_release_name": selected_release.name if selected_release else None,
            "selected_release_url": selected_release.html_url if selected_release else None,
            "selected_release_published_at": (
                selected_release.published_at if selected_release else None
            ),
            "asset_names": [asset.name for asset in assets],
            "forbidden_assets": forbidden_assets,
            "other_assets": other_assets,
            "candidate_release_tags": [release.tag_name for release in observation.candidate_releases],
            "gh_release_view_command": " ".join(observation.gh_release_view_command),
            "gh_release_view_exit_code": observation.gh_release_view_exit_code,
            "gh_release_view_stdout": observation.gh_release_view_stdout,
            "gh_release_view_stderr": observation.gh_release_view_stderr,
            "expected_architecture_fragment": self.config.expected_architecture_fragment,
            "checksum_manifest_text": observation.checksum_manifest_text,
            "app_asset": asdict(app_asset) if app_asset is not None else None,
            "cli_asset": asdict(cli_asset) if cli_asset is not None else None,
            "checksum_asset": asdict(checksum_asset) if checksum_asset is not None else None,
            "app_file_output": app_asset.file_output if app_asset is not None else None,
            "cli_file_output": cli_asset.file_output if cli_asset is not None else None,
            "observation": observation.to_dict(),
            "steps": [],
            "human_verification": [],
        }

    def _assert_selected_release(
        self,
        observation: TrackStateReleaseArtifactObservation,
        result: dict[str, object],
    ) -> list[str]:
        if observation.selected_release is not None:
            return []
        return [
            "Step 1 failed: the explicit workflow release tag was not published in the "
            f"selected repository.\nExpected release tag: {result.get('expected_release_tag')}\n"
            f"Candidate releases: {result.get('candidate_release_tags')}\n"
            f"Releases page: {result.get('releases_page_url')}"
        ]

    def _assert_release_view(
        self,
        observation: TrackStateReleaseArtifactObservation,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        selected_release = observation.selected_release
        if selected_release is None:
            return failures
        if observation.gh_release_view_exit_code != 0:
            failures.append(
                "Step 2 failed: `gh release view` could not render the selected release summary.\n"
                f"Command: {result.get('gh_release_view_command')}\n"
                f"Exit code: {observation.gh_release_view_exit_code}\n"
                f"stdout:\n{observation.gh_release_view_stdout}\n"
                f"stderr:\n{observation.gh_release_view_stderr}"
            )
        if selected_release.tag_name not in observation.gh_release_view_stdout:
            failures.append(
                "Step 2 failed: the user-facing release view did not show the selected tag.\n"
                f"Selected tag: {selected_release.tag_name}\n"
                f"Observed output:\n{observation.gh_release_view_stdout}"
            )
        return failures

    def _assert_release_assets(
        self,
        observation: TrackStateReleaseArtifactObservation,
        result: dict[str, object],
    ) -> list[str]:
        assets = list(observation.assets)
        app_assets = [asset for asset in assets if asset.classification == "app-archive"]
        cli_assets = [asset for asset in assets if asset.classification == "cli-archive"]
        checksum_assets = [asset for asset in assets if asset.classification == "checksum"]
        forbidden_assets = [asset.name for asset in assets if asset.classification == "forbidden"]
        other_assets = [
            asset.name
            for asset in assets
            if asset.classification not in {"app-archive", "cli-archive", "checksum", "forbidden"}
        ]
        failures: list[str] = []
        if len(assets) != 3:
            failures.append(
                "Step 3 failed: the release did not expose exactly three published assets.\n"
                "Expected assets: one app archive, one CLI archive, and one .sha256 manifest.\n"
                f"Observed asset names: {result.get('asset_names')}"
            )
        if len(app_assets) != 1:
            failures.append(
                "Step 3 failed: the release did not expose exactly one downloadable app archive "
                "containing a macOS .app bundle.\n"
                f"Observed asset names: {result.get('asset_names')}"
            )
        if len(cli_assets) != 1:
            failures.append(
                "Step 3 failed: the release did not expose exactly one downloadable standalone "
                "CLI archive.\n"
                f"Observed asset names: {result.get('asset_names')}"
            )
        if len(checksum_assets) != 1:
            failures.append(
                "Step 3 failed: the release did not expose exactly one SHA256 checksum manifest.\n"
                f"Observed asset names: {result.get('asset_names')}"
            )
        if forbidden_assets:
            failures.append(
                "Expected result failed: the MVP release published forbidden installer assets.\n"
                "Expected no .dmg or .pkg files.\n"
                f"Observed forbidden assets: {forbidden_assets}"
            )
        if other_assets:
            failures.append(
                "Expected result failed: the release exposed unexpected extra assets outside the "
                "ticketed app archive, CLI archive, and checksum manifest.\n"
                f"Observed unexpected assets: {other_assets}"
            )
        if failures:
            _record_human_verification(
                result,
                check=(
                    "Compared the visible release asset list to the ticket expectation of "
                    "three unsigned MVP assets and no installer packages."
                ),
                observed=f"visible_assets={result.get('asset_names')}",
            )
        return failures

    def _assert_binary_architectures(
        self,
        observation: TrackStateReleaseArtifactObservation,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        app_asset = _first_asset(list(observation.assets), "app-archive")
        cli_asset = _first_asset(list(observation.assets), "cli-archive")
        if app_asset is None or cli_asset is None:
            failures.append(
                "Step 4 failed: the required app archive and CLI archive were not both present, "
                "so `file` could not be executed on both binaries.\n"
                f"Observed asset names: {result.get('asset_names')}"
            )
            return failures
        for label, asset in (("desktop", app_asset), ("cli", cli_asset)):
            if asset.error:
                failures.append(
                    f"Step 4 failed: the {label} archive could not be inspected.\n"
                    f"Asset: {asset.name}\n"
                    f"Error: {asset.error}"
                )
                continue
            file_output = asset.file_output or ""
            if not _matches_expected_architecture(
                file_output,
                expected_fragment=self.config.expected_architecture_fragment,
            ):
                failures.append(
                    f"Step 4 failed: the {label} binary was not reported as "
                    f"{self.config.expected_architecture_fragment}.\n"
                    f"Asset: {asset.name}\n"
                    f"Observed `file` output: {file_output}"
                )
        return failures

    def _assert_checksum_manifest(
        self,
        observation: TrackStateReleaseArtifactObservation,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        app_asset = _first_asset(list(observation.assets), "app-archive")
        cli_asset = _first_asset(list(observation.assets), "cli-archive")
        checksum_asset = _first_asset(list(observation.assets), "checksum")
        manifest_text = observation.checksum_manifest_text
        if app_asset is None or cli_asset is None or checksum_asset is None:
            failures.append(
                "Step 5 failed: the app archive, CLI archive, and checksum manifest were not "
                "all available for checksum verification.\n"
                f"Observed asset names: {result.get('asset_names')}"
            )
            return failures
        if not manifest_text:
            failures.append(
                "Step 5 failed: the checksum manifest could not be downloaded or was empty.\n"
                f"Checksum asset: {checksum_asset.name}"
            )
            return failures
        parsed_manifest = _parse_checksum_manifest(manifest_text)
        for asset in (app_asset, cli_asset):
            observed_hash = parsed_manifest.get(asset.name)
            if observed_hash is None:
                failures.append(
                    "Step 5 failed: the checksum manifest did not include an entry for the "
                    "downloaded asset.\n"
                    f"Asset: {asset.name}\n"
                    f"Observed manifest:\n{manifest_text}"
                )
                continue
            if observed_hash != asset.sha256:
                failures.append(
                    "Step 5 failed: the checksum manifest hash did not match the downloaded "
                    "asset bytes.\n"
                    f"Asset: {asset.name}\n"
                    f"Expected SHA256: {asset.sha256}\n"
                    f"Observed SHA256: {observed_hash}\n"
                    f"Manifest:\n{manifest_text}"
                )
        return failures


def _first_asset(
    assets: list[TrackStateReleaseAssetObservation],
    classification: str,
) -> TrackStateReleaseAssetObservation | None:
    for asset in assets:
        if asset.classification == classification:
            return asset
    return None


def _parse_checksum_manifest(manifest_text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw_line in manifest_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        standard_match = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", line)
        if standard_match is not None:
            entries[standard_match.group(2).strip()] = standard_match.group(1).lower()
            continue
        shasum_match = re.match(r"^SHA256\s+\((.+)\)\s+=\s+([0-9a-fA-F]{64})$", line)
        if shasum_match is not None:
            entries[shasum_match.group(1).strip()] = shasum_match.group(2).lower()
    return entries


def _matches_expected_architecture(file_output: str, *, expected_fragment: str) -> bool:
    normalized_output = file_output.lower()
    if expected_fragment.lower() in normalized_output:
        return True
    if "mach-o 64-bit" not in normalized_output:
        return False
    if "arm64" not in normalized_output:
        return False
    if "universal binary" in normalized_output or "x86_64" in normalized_output:
        return False
    return "arm64 executable" in normalized_output or "executable arm64" in normalized_output


def _write_pass_outputs(result: dict[str, object]) -> None:
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
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    jira = _jira_comment(result, status="PASSED")
    markdown = _markdown_summary(result, status="PASSED")
    _write_text(JIRA_COMMENT_PATH, jira)
    _write_text(PR_BODY_PATH, markdown)
    _write_text(RESPONSE_PATH, markdown)


def _write_failure_outputs(result: dict[str, object]) -> None:
    error_message = _as_text(result.get("error")) or "AssertionError: unknown failure"
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_message,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    jira = _jira_comment(result, status="FAILED")
    markdown = _markdown_summary(result, status="FAILED")
    bug = _bug_description(result)
    _write_text(JIRA_COMMENT_PATH, jira)
    _write_text(PR_BODY_PATH, markdown)
    _write_text(RESPONSE_PATH, markdown)
    _write_text(BUG_DESCRIPTION_PATH, bug)


def _jira_comment(result: dict[str, object], *, status: str) -> str:
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {'✅ PASSED' if status == 'PASSED' else '❌ FAILED'}",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        f"*Repository:* {result.get('repository')}",
        f"*Release:* {_jira_inline(_release_label(result))}",
        f"*Release URL:* {_jira_inline(_as_text(result.get('selected_release_url')))}",
        "",
        "h4. What was tested",
        (
            "* Verified the explicit version-tag release selected for the live "
            "{IstiN/trackstate} Apple artifact ticket."
        ),
        (
            "* Checked the user-visible release summary, the published asset list, the "
            "extracted binary architecture reported by {file}, and the {.sha256} manifest."
        ),
        "",
        "h4. Automation",
    ]
    lines.extend(_jira_step_lines(result.get("steps")))
    lines.extend(["", "h4. Human-style verification"])
    lines.extend(_jira_human_lines(result.get("human_verification")))
    lines.extend(["", "h4. Result"])
    if status == "PASSED":
        lines.extend(
            [
                f"* Observed assets: {_jira_inline(str(result.get('asset_names')))}",
                (
                    "* The selected release matched the ticket: exactly one app archive, one "
                    "CLI archive, and one checksum manifest were published, both binaries "
                    "reported Apple Silicon arm64, and no installer packages were present."
                ),
            ]
        )
    else:
        lines.extend(
            [
                f"* ❌ Failure: {{noformat}}{_as_text(result.get('error'))}{{noformat}}",
                f"* Observed assets: {_jira_inline(str(result.get('asset_names')))}",
                f"* Release view output: {{noformat}}{_as_text(result.get('gh_release_view_stdout'))}{{noformat}}",
            ]
        )
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
            _as_text(result.get("run_command")) or RUN_COMMAND,
            "{code}",
        ]
    )
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, status: str) -> str:
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if status == 'PASSED' else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        f"**Repository:** `{result.get('repository')}`",
        f"**Release:** `{_release_label(result)}`",
        f"**Release URL:** `{_as_text(result.get('selected_release_url'))}`",
        "",
        "## What was automated",
        (
            "- Verified the explicit version-tag release selected for the live "
            "`IstiN/trackstate` Apple artifact ticket."
        ),
        (
            "- Checked the user-visible release summary, the published asset list, the "
            "extracted binary architecture reported by `file`, and the `.sha256` manifest."
        ),
        "",
        "## Automation details",
    ]
    lines.extend(_markdown_step_lines(result.get("steps")))
    lines.extend(["", "## Human-style verification"])
    lines.extend(_markdown_human_lines(result.get("human_verification")))
    lines.extend(["", "## Result"])
    if status == "PASSED":
        lines.extend(
            [
                f"- Observed assets: `{result.get('asset_names')}`",
                (
                    "- The selected release matched the ticket: exactly one app archive, one "
                    "CLI archive, and one checksum manifest were published, both binaries "
                    "reported Apple Silicon arm64, and no installer packages were present."
                ),
            ]
        )
    else:
        lines.extend(
            [
                f"- Failure: `{_as_text(result.get('error'))}`",
                f"- Observed assets: `{result.get('asset_names')}`",
                "",
                "### Release view output",
                "```text",
                _as_text(result.get("gh_release_view_stdout")),
                "```",
            ]
        )
    lines.extend(
        [
            "",
            "## How to run",
            "```bash",
            _as_text(result.get("run_command")) or RUN_COMMAND,
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    app_asset = result.get("app_asset") if isinstance(result.get("app_asset"), dict) else None
    cli_asset = result.get("cli_asset") if isinstance(result.get("cli_asset"), dict) else None
    checksum_asset = (
        result.get("checksum_asset") if isinstance(result.get("checksum_asset"), dict) else None
    )
    other_assets = result.get("other_assets") if isinstance(result.get("other_assets"), list) else []
    app_file_output = _as_text(result.get("app_file_output"))
    cli_file_output = _as_text(result.get("cli_file_output"))
    asset_names = result.get("asset_names")

    if app_asset is not None and cli_asset is not None:
        step_3_observation = (
            "❌ The release published the desktop zip and CLI archive, but the checksum "
            "manifest was not exposed as the required `.sha256` asset. "
            f"Observed asset names: `{asset_names}`. "
            f"Unexpected non-matching assets: `{other_assets}`."
        )
    else:
        step_3_observation = (
            "❌ The release did not expose the required zipped macOS `.app` bundle and "
            "standalone CLI archive as specified. "
            f"Observed asset names: `{asset_names}`."
        )

    if app_file_output or cli_file_output:
        step_4_observation = (
            "❌ Ran `file` on the extracted binaries and observed output that still "
            "contradicts the ticket expectation. "
            f"Desktop output: `{app_file_output}`. "
            f"CLI output: `{cli_file_output}`."
        )
    else:
        step_4_observation = (
            "❌ This could not be completed as specified because the release did not provide "
            "downloadable archives for both binaries."
        )

    if checksum_asset is None:
        step_5_observation = (
            "❌ No valid `.sha256` manifest was available for verification. "
            f"Observed asset names: `{asset_names}`."
        )
    else:
        step_5_observation = (
            "❌ The checksum manifest was present but did not match the downloaded archive "
            "bytes."
        )

    actual_summary = (
        f"- **Actual:** release `{_release_label(result)}` exposed `{asset_names}`. "
        "The desktop archive extracted to a non-arm64-only universal binary and the "
        "checksum manifest was not published as the required `.sha256` asset."
    )

    lines = [
        f"# Bug Report — {TICKET_KEY}",
        "",
        f"**Summary:** {_as_text(result.get('ticket_summary'))}",
        "",
        "## Steps to reproduce",
        (
            "1. **Trigger a successful Apple release workflow via a version tag.** "
            f"✅ Verified the live repository currently exposes the stable published release "
            f"`{_as_text(result.get('selected_release_tag'))}` at `{_as_text(result.get('selected_release_url'))}`."
        ),
        (
            "2. **Navigate to the resulting GitHub Release in the `IstiN/trackstate` repository.** "
            "✅ Opened the release with `gh release view` and confirmed the selected release "
            f"was `{_release_label(result)}`."
        ),
        f"3. **Download the published assets: the zipped macOS `.app` bundle and the standalone CLI archive.** {step_3_observation}",
        f"4. **Execute `file [binary_name]` in a terminal for both the desktop binary and the CLI binary.** {step_4_observation}",
        f"5. **Verify the contents of the generated SHA256 checksum manifest.** {step_5_observation}",
        "",
        "## Actual vs Expected",
        actual_summary,
        (
            "- **Expected:** exactly three assets should be published: a zipped `.app`, a "
            "standalone CLI archive, and a `.sha256` file. Both extracted binaries should "
            "report `Mach-O 64-bit executable arm64`, and no `.dmg` or `.pkg` files should exist."
        ),
        "",
        "## Exact error message / assertion failure",
        "```text",
        _as_text(result.get("traceback")),
        "```",
        "",
        "## Environment",
        f"- Repository: `{result.get('repository')}`",
        f"- Release URL: `{_as_text(result.get('selected_release_url'))}`",
        f"- OS: `{result.get('os')}`",
        f"- Run command: `{_as_text(result.get('run_command')) or RUN_COMMAND}`",
        "",
        "## Logs",
        "### `gh release view` output",
        "```text",
        _as_text(result.get("gh_release_view_stdout")),
        "```",
        "",
        "### STDERR",
        "```text",
        _as_text(result.get("gh_release_view_stderr")),
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


def _jira_step_lines(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["* No automation steps were recorded."]
    lines: list[str] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        step = entry.get("step")
        status = str(entry.get("status", "")).strip().lower()
        icon = "✅" if status == "passed" else "❌"
        lines.append(f"* {icon} Step {step}: {_jira_inline(_as_text(entry.get('action')))}")
        lines.append(f"** Observed: {_jira_inline(_as_text(entry.get('observed')))}")
    return lines


def _jira_human_lines(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["* No additional human-style verification was recorded."]
    lines: list[str] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        lines.append(f"* {_jira_inline(_as_text(entry.get('check')))}")
        lines.append(f"** Observed: {_jira_inline(_as_text(entry.get('observed')))}")
    return lines


def _markdown_step_lines(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["- No automation steps were recorded."]
    lines: list[str] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status", "")).strip().lower()
        icon = "✅" if status == "passed" else "❌"
        lines.append(
            f"- {icon} **Step {entry.get('step')}:** {_as_text(entry.get('action'))} "
            f"Observed: `{_compact_text(_as_text(entry.get('observed')))}`"
        )
    return lines


def _markdown_human_lines(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["- No additional human-style verification was recorded."]
    lines: list[str] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        lines.append(
            f"- **Check:** {_as_text(entry.get('check'))} "
            f"**Observed:** `{_compact_text(_as_text(entry.get('observed')))}`"
        )
    return lines


def _jira_inline(value: str) -> str:
    return "{{" + value.replace("{", "(").replace("}", ")") + "}}"


def _release_label(result: dict[str, object]) -> str:
    tag = _as_text(result.get("selected_release_tag"))
    name = _as_text(result.get("selected_release_name"))
    if tag and name:
        return f"{tag} ({name})"
    return tag or name or "<no release selected>"


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
