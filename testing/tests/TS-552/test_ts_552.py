from __future__ import annotations

import json
import platform
import sys
import traceback
from dataclasses import asdict, is_dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_release_foreign_asset_conflict_validator import (  # noqa: E402
    TrackStateCliReleaseForeignAssetConflictValidator,
)
from testing.core.config.trackstate_cli_release_foreign_asset_conflict_config import (  # noqa: E402
    TrackStateCliReleaseForeignAssetConflictConfig,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_foreign_asset_conflict_result import (  # noqa: E402
    TrackStateCliReleaseForeignAssetConflictGhReleaseViewObservation,
    TrackStateCliReleaseForeignAssetConflictReleaseState,
    TrackStateCliReleaseForeignAssetConflictRepositoryState,
    TrackStateCliReleaseForeignAssetConflictValidationResult,
)
from testing.tests.support.trackstate_cli_release_foreign_asset_conflict_probe_factory import (  # noqa: E402
    create_trackstate_cli_release_foreign_asset_conflict_probe,
)

TICKET_KEY = "TS-552"
TICKET_SUMMARY = (
    "Local release-backed upload fails with an asset container conflict when the "
    "release already contains a foreign asset"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-552/test_ts_552.py"
RUN_COMMAND = "python testing/tests/TS-552/test_ts_552.py"


class Ts552LocalForeignAssetConflictScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-552/config.yaml"
        self.config = TrackStateCliReleaseForeignAssetConflictConfig.from_file(
            self.config_path,
        )
        self.validator = TrackStateCliReleaseForeignAssetConflictValidator(
            probe=create_trackstate_cli_release_foreign_asset_conflict_probe(
                self.repository_root,
            ),
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_result(validation)
        failures: list[str] = []

        failures.extend(self._assert_exact_command(validation.observation))

        fixture_failures = self._assert_fixture_state(
            initial_state=validation.initial_state,
            fixture_state=validation.fixture_release_state,
            gh_view=validation.preflight_gh_release_view,
        )
        failures.extend(fixture_failures)
        if not fixture_failures:
            _record_step(
                result,
                step=1,
                status="passed",
                action=(
                    "Seed a disposable local TrackState repository plus a real GitHub "
                    "Release fixture with a foreign asset."
                ),
                observed=(
                    f"remote_origin_url={validation.initial_state.remote_origin_url}; "
                    f"manifest_text={validation.initial_state.manifest_text!r}; "
                    f"release_asset_names={list(validation.fixture_release_state.release_asset_names)}"
                ),
            )

        runtime_failures = self._assert_runtime_expectations(result)
        failures.extend(runtime_failures)
        if runtime_failures:
            _mark_product_failure(
                result,
                "The local github-releases upload flow did not present the expected "
                "foreign-asset/manual-cleanup conflict for TS-552.",
            )
        else:
            _record_step(
                result,
                step=2,
                status="passed",
                action=self.config.ticket_command,
                observed=(
                    f"exit_code={result.get('exit_code')}; "
                    f"error_code={result.get('observed_error_code')}; "
                    f"error_category={result.get('observed_error_category')}; "
                    f"visible_output={_compact_text(_as_text(result.get('visible_output')))}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the exact terminal output shown to a user named the foreign "
                    "release asset conflict and required manual cleanup."
                ),
                observed=_as_text(result.get("visible_output")),
            )

        local_failures = self._assert_local_state(validation.final_state)
        failures.extend(local_failures)
        if local_failures:
            _mark_product_failure(
                result,
                "The failed local github-releases upload mutated local attachment state "
                "even though the foreign release asset should block the operation.",
            )
        else:
            _record_step(
                result,
                step=3,
                status="passed",
                action="Inspect the local repository after the failed upload attempt.",
                observed=(
                    f"manifest_text={validation.final_state.manifest_text!r}; "
                    f"stored_files={list(validation.final_state.stored_files)}; "
                    f"git_status_lines={list(validation.final_state.git_status_lines)}"
                ),
            )

        remote_failures = self._assert_remote_state(
            remote_state=validation.remote_state_after_command,
            gh_view=validation.gh_release_view,
        )
        failures.extend(remote_failures)
        if remote_failures:
            _mark_product_failure(
                result,
                "The failed local github-releases upload changed the live release asset "
                "container instead of preserving only the pre-existing foreign asset.",
            )
        else:
            _record_step(
                result,
                step=4,
                status="passed",
                action="Check the release state after the failed upload attempt.",
                observed=(
                    f"release_asset_names={list(validation.remote_state_after_command.release_asset_names)}; "
                    f"gh_asset_names={list(validation.gh_release_view.asset_names)}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified as a user through `gh release view` that the release still "
                    "showed only the foreign asset and did not absorb `report.pdf`."
                ),
                observed=validation.gh_release_view.stdout,
            )

        cleanup_failures = self._assert_cleanup(result)
        failures.extend(cleanup_failures)
        return result, failures

    def _build_result(
        self,
        validation: TrackStateCliReleaseForeignAssetConflictValidationResult,
    ) -> dict[str, object]:
        payload = validation.observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        error = payload_dict.get("error") if isinstance(payload_dict, dict) else None
        error_dict = error if isinstance(error, dict) else None
        details = error_dict.get("details") if isinstance(error_dict, dict) else None
        return {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "ticket_command": self.config.ticket_command,
            "requested_command": validation.observation.requested_command_text,
            "executed_command": validation.observation.executed_command_text,
            "compiled_binary_path": validation.observation.compiled_binary_path,
            "repository_path": validation.observation.repository_path,
            "config_path": str(self.config_path),
            "os": platform.system(),
            "repository": self.config.repository,
            "repository_ref": self.config.branch,
            "project_key": self.config.project_key,
            "project_name": self.config.project_name,
            "issue_key": self.config.issue_key,
            "issue_summary": self.config.issue_summary,
            "manifest_path": self.config.manifest_path,
            "source_file_name": self.config.source_file_name,
            "foreign_asset_name": self.config.foreign_asset_name,
            "release_tag_prefix": validation.release_tag_prefix,
            "release_tag": validation.release_tag,
            "release_title": validation.fixture_release_state.release_title
            or self.config.expected_release_title,
            "remote_origin_url": validation.remote_origin_url,
            "stdout": validation.observation.result.stdout,
            "stderr": validation.observation.result.stderr,
            "exit_code": validation.observation.result.exit_code,
            "payload": payload_dict,
            "observed_error_code": error_dict.get("code")
            if isinstance(error_dict, dict)
            else None,
            "observed_error_category": error_dict.get("category")
            if isinstance(error_dict, dict)
            else None,
            "observed_error_message": error_dict.get("message")
            if isinstance(error_dict, dict)
            else None,
            "observed_error_details": details if isinstance(details, dict) else None,
            "observed_error_reason": details.get("reason")
            if isinstance(details, dict)
            else None,
            "visible_output": _visible_output(
                payload=payload,
                stdout=validation.observation.result.stdout,
                stderr=validation.observation.result.stderr,
            ),
            "initial_state": serialize(validation.initial_state),
            "fixture_release_state": serialize(validation.fixture_release_state),
            "preflight_gh_release_view": serialize(validation.preflight_gh_release_view),
            "final_state": serialize(validation.final_state),
            "remote_state_after_command": serialize(validation.remote_state_after_command),
            "gh_release_view": serialize(validation.gh_release_view),
            "cleanup": serialize(validation.cleanup),
            "steps": [],
            "human_verification": [],
        }

    def _assert_exact_command(
        self,
        observation: TrackStateCliCommandObservation,
    ) -> list[str]:
        failures: list[str] = []
        if observation.requested_command != self.config.requested_command:
            failures.append(
                "Precondition failed: TS-552 did not execute the exact ticket command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}",
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-552 must run a repository-local compiled binary "
                "from the disposable repository working directory.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}",
            )
        return failures

    def _assert_fixture_state(
        self,
        *,
        initial_state: TrackStateCliReleaseForeignAssetConflictRepositoryState,
        fixture_state: TrackStateCliReleaseForeignAssetConflictReleaseState,
        gh_view: TrackStateCliReleaseForeignAssetConflictGhReleaseViewObservation,
    ) -> list[str]:
        failures: list[str] = []
        if not initial_state.issue_main_exists:
            failures.append(
                "Precondition failed: the disposable local repository did not contain "
                f"{self.config.issue_key}/main.md.\n"
                f"Observed state: {json.dumps(serialize(initial_state), indent=2, sort_keys=True)}",
            )
        if not initial_state.source_file_exists:
            failures.append(
                "Precondition failed: the disposable local repository did not contain "
                f"{self.config.source_file_name}.\n"
                f"Observed state: {json.dumps(serialize(initial_state), indent=2, sort_keys=True)}",
            )
        if initial_state.manifest_text != self.config.seeded_manifest_text:
            failures.append(
                "Precondition failed: local attachments.json was not seeded with the expected "
                "empty manifest.\n"
                f"Expected:\n{self.config.seeded_manifest_text}\n"
                f"Observed:\n{initial_state.manifest_text}",
            )
        if initial_state.stored_files:
            failures.append(
                "Precondition failed: the disposable local repository already contained "
                "attachment files before the upload attempt.\n"
                f"Observed stored files: {list(initial_state.stored_files)}",
            )
        if initial_state.remote_origin_url != validation_remote_origin(self.config.repository):
            failures.append(
                "Precondition failed: the disposable local repository origin did not point "
                "at the live setup repository.\n"
                f"Expected origin: {validation_remote_origin(self.config.repository)}\n"
                f"Observed origin: {initial_state.remote_origin_url}",
            )
        if fixture_state.release_title != self.config.expected_release_title:
            failures.append(
                "Precondition failed: the seeded release title did not match the issue "
                "contract.\n"
                f"Expected title: {self.config.expected_release_title}\n"
                f"Observed state: {json.dumps(serialize(fixture_state), indent=2, sort_keys=True)}",
            )
        if fixture_state.release_asset_names != (self.config.foreign_asset_name,):
            failures.append(
                "Precondition failed: the seeded release did not contain exactly the "
                "expected foreign asset.\n"
                f"Observed state: {json.dumps(serialize(fixture_state), indent=2, sort_keys=True)}",
            )
        if gh_view.asset_names != (self.config.foreign_asset_name,):
            failures.append(
                "Precondition failed: `gh release view` did not expose exactly the seeded "
                "foreign asset before the upload attempt.\n"
                f"Observed gh view: {json.dumps(serialize(gh_view), indent=2, sort_keys=True)}",
            )
        return failures

    def _assert_runtime_expectations(self, result: dict[str, object]) -> list[str]:
        failures: list[str] = []
        exit_code = result.get("exit_code")
        payload = result.get("payload")
        visible_output = _as_text(result.get("visible_output"))
        if exit_code != self.config.expected_exit_code:
            failures.append(
                "Step 2 failed: the exact local upload command did not exit with the "
                "expected repository conflict code.\n"
                f"Expected exit code: {self.config.expected_exit_code}\n"
                f"Observed exit code: {exit_code}\n"
                f"{_observed_command_output(result)}",
            )
            return failures

        required_fragments = (result.get("release_tag"), *self.config.required_reason_fragments)
        lowered_output = visible_output.lower()
        missing_fragments = [
            fragment
            for fragment in required_fragments
            if isinstance(fragment, str) and fragment.lower() not in lowered_output
        ]
        if missing_fragments:
            failures.append(
                "Step 2 failed: the visible CLI output did not expose the expected foreign "
                "asset conflict details.\n"
                f"Missing visible fragments: {missing_fragments}\n"
                f"Visible output:\n{visible_output}\n"
                f"{_observed_command_output(result)}",
            )

        if isinstance(payload, dict):
            if payload.get("ok") is not False:
                failures.append(
                    "Expected result failed: the local upload payload did not stay in an "
                    "error state.\n"
                    f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}",
                )
            error = payload.get("error")
            if not isinstance(error, dict):
                failures.append(
                    "Step 2 failed: the JSON payload did not include an `error` object.\n"
                    f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}",
                )
            else:
                if error.get("code") != self.config.expected_error_code:
                    failures.append(
                        "Step 2 failed: the JSON payload did not expose the expected error "
                        "code.\n"
                        f"Expected code: {self.config.expected_error_code}\n"
                        f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}",
                    )
                if error.get("category") != self.config.expected_error_category:
                    failures.append(
                        "Step 2 failed: the JSON payload did not expose the expected error "
                        "category.\n"
                        f"Expected category: {self.config.expected_error_category}\n"
                        f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}",
                    )
        return failures

    def _assert_local_state(
        self,
        final_state: TrackStateCliReleaseForeignAssetConflictRepositoryState,
    ) -> list[str]:
        failures: list[str] = []
        if final_state.manifest_text != self.config.seeded_manifest_text:
            failures.append(
                "Step 3 failed: local attachments.json changed even though the upload "
                "should have been blocked by the foreign asset conflict.\n"
                f"Expected manifest:\n{self.config.seeded_manifest_text}\n"
                f"Observed manifest:\n{final_state.manifest_text}",
            )
        if final_state.stored_files:
            failures.append(
                "Step 3 failed: the local repository wrote attachment files even though the "
                "upload should have failed before any local attachment mutation.\n"
                f"Observed stored files: {list(final_state.stored_files)}",
            )
        if final_state.git_status_lines:
            failures.append(
                "Step 3 failed: the local repository was left dirty after the failed upload.\n"
                f"Observed git status: {list(final_state.git_status_lines)}",
            )
        return failures

    def _assert_remote_state(
        self,
        *,
        remote_state: TrackStateCliReleaseForeignAssetConflictReleaseState,
        gh_view: TrackStateCliReleaseForeignAssetConflictGhReleaseViewObservation,
    ) -> list[str]:
        failures: list[str] = []
        if remote_state.release_asset_names != (self.config.foreign_asset_name,):
            failures.append(
                "Step 4 failed: the live release did not preserve exactly the seeded foreign "
                "asset after the failed upload attempt.\n"
                f"Observed state: {json.dumps(serialize(remote_state), indent=2, sort_keys=True)}",
            )
        if gh_view.asset_names != (self.config.foreign_asset_name,):
            failures.append(
                "Human-style verification failed: `gh release view` did not show exactly the "
                "expected foreign asset after the failed upload.\n"
                f"Observed gh view: {json.dumps(serialize(gh_view), indent=2, sort_keys=True)}",
            )
        return failures

    def _assert_cleanup(self, result: dict[str, object]) -> list[str]:
        cleanup = _as_dict(result.get("cleanup"))
        if cleanup.get("status") == "failed":
            return [
                "Cleanup failed after the TS-552 observation completed.\n"
                f"Observed cleanup: {json.dumps(cleanup, indent=2, sort_keys=True)}",
            ]
        return []


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts552LocalForeignAssetConflictScenario()

    result: dict[str, object] = {}
    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        if not result:
            result = {
                "ticket": TICKET_KEY,
                "ticket_summary": TICKET_SUMMARY,
            }
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


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
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(result, passed=True), encoding="utf-8")


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
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(result, passed=False), encoding="utf-8")
    if _should_write_bug_description(result):
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _should_write_bug_description(result: dict[str, object]) -> bool:
    return bool(result.get("product_failure")) and _step_status(result, 1) == "passed"


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {'✅' if passed else '❌'} {status}",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Executed {{{{{_as_text(result.get('ticket_command'))}}}}} from a disposable "
            f"local TrackState repository configured for "
            f"{{{{attachmentStorage.mode = github-releases}}}} with Git origin "
            f"{{{{{_as_text(result.get('remote_origin_url'))}}}}}."
        ),
        (
            f"* Seeded GitHub Release {{{{{_as_text(result.get('release_tag'))}}}}} titled "
            f"{{{{{_as_text(result.get('release_title'))}}}}} with the foreign asset "
            f"{{{{{_as_text(result.get('foreign_asset_name'))}}}}} while local "
            f"{{{{{_as_text(result.get('manifest_path'))}}}}} stayed empty."
        ),
        "* Verified both the visible CLI output and the post-run release state via {{gh release view}}.",
        "",
        "h4. Observed result",
        (
            "* The observed behavior matched the expected result."
            if passed
            else "* The observed behavior did not match the expected result."
        ),
        (
            f"* Environment: repository {{{{{_as_text(result.get('repository'))}}}}} @ "
            f"{{{{{_as_text(result.get('repository_ref'))}}}}}, OS "
            f"{{{{{platform.system()}}}}}, runtime {{Dart CLI compiled locally}}."
        ),
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Exact error",
                "{code}",
                _as_text(result.get("traceback")) or _as_text(result.get("error")),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        (
            f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable local "
            f"TrackState repository configured for `attachmentStorage.mode = github-releases` "
            f"with Git origin `{_as_text(result.get('remote_origin_url'))}`."
        ),
        (
            f"- Seeded GitHub Release `{_as_text(result.get('release_tag'))}` titled "
            f"`{_as_text(result.get('release_title'))}` with the foreign asset "
            f"`{_as_text(result.get('foreign_asset_name'))}` while local "
            f"`{_as_text(result.get('manifest_path'))}` stayed empty."
        ),
        "- Verified both the visible CLI output and the post-run release state via `gh release view`.",
        "",
        "### Observed result",
        (
            "- The observed behavior matched the expected result."
            if passed
            else "- The observed behavior did not match the expected result."
        ),
        (
            f"- Environment: repository `{_as_text(result.get('repository'))}` @ "
            f"`{_as_text(result.get('repository_ref'))}`, OS `{platform.system()}`, runtime "
            "`Dart CLI compiled locally`."
        ),
        "",
        "### Step results",
        *_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "### Exact error",
                "```text",
                _as_text(result.get("traceback")) or _as_text(result.get("error")),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _response(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            f"Ran `{_as_text(result.get('ticket_command'))}` from a disposable local "
            f"repository backed by GitHub Releases after seeding release "
            f"`{_as_text(result.get('release_tag'))}` with "
            f"`{_as_text(result.get('foreign_asset_name'))}`."
        ),
        "",
        "## Observed",
        f"- Repository: `{_as_text(result.get('repository'))}` @ `{_as_text(result.get('repository_ref'))}`",
        f"- Release tag: `{_as_text(result.get('release_tag'))}`",
        f"- Cleanup: `{json.dumps(result.get('cleanup', {}), sort_keys=True)}`",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                _as_text(result.get("traceback")) or _as_text(result.get("error")),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    visible_output = _as_text(result.get("visible_output"))
    gh_stdout = _as_text(_as_dict(result.get("gh_release_view")).get("stdout"))
    actual_result = _as_text(result.get("product_gap")) or _as_text(result.get("error"))
    return "\n".join(
        [
            "# TS-552 - Local release-backed upload does not preserve the expected foreign-asset conflict behavior",
            "",
            "## Steps to reproduce",
            (
                "1. Execute `trackstate attachment upload --issue TS-123 --file report.pdf "
                "--target local` from a local TrackState repository configured with "
                "`attachmentStorage.mode = github-releases`."
            ),
            (
                f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} "
                "Precondition: the disposable local repository used Git origin "
                f"`{_as_text(result.get('remote_origin_url'))}`, local "
                f"`{_as_text(result.get('manifest_path'))}` contained `[]`, and release "
                f"`{_as_text(result.get('release_tag'))}` already contained "
                f"`{_as_text(result.get('foreign_asset_name'))}`."
            ),
            (
                f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} "
                f"Command outcome: {_step_observation(result, 2) or visible_output or _as_text(result.get('error'))}"
            ),
            "2. Inspect the command output.",
            (
                f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} "
                f"Observed visible output:\n{visible_output or '<empty>'}"
            ),
            "3. Verify the release and local manifest state after the failed attempt.",
            (
                f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} "
                f"Local state: {_step_observation(result, 3)}"
            ),
            (
                f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} "
                f"Release state: {_step_observation(result, 4)}"
            ),
            "",
            "## Exact error message or assertion failure",
            "```text",
            _as_text(result.get("traceback")) or _as_text(result.get("error")),
            "```",
            "",
            "## Actual vs Expected",
            (
                f"- Expected: the local upload should fail with a visible foreign-asset "
                f"conflict that names `{_as_text(result.get('foreign_asset_name'))}`, requires "
                "manual cleanup, leaves local `attachments.json` unchanged, and keeps the "
                "release limited to the foreign asset."
            ),
            f"- Actual: {actual_result}",
            "",
            "## Environment details",
            f"- Repository: `{_as_text(result.get('repository'))}`",
            f"- Branch: `{_as_text(result.get('repository_ref'))}`",
            f"- Remote origin: `{_as_text(result.get('remote_origin_url'))}`",
            f"- Release tag: `{_as_text(result.get('release_tag'))}`",
            f"- Local repository path: `{_as_text(result.get('repository_path'))}`",
            f"- OS: `{platform.system()}`",
            f"- Command: `{_as_text(result.get('executed_command')) or _as_text(result.get('requested_command'))}`",
            "",
            "## Relevant logs",
            "### Visible CLI output",
            "```text",
            visible_output,
            "```",
            "### stdout",
            "```text",
            _as_text(result.get("stdout")),
            "```",
            "### stderr",
            "```text",
            _as_text(result.get("stderr")),
            "```",
            "### gh release view",
            "```text",
            gh_stdout,
            "```",
        ],
    ) + "\n"


def _mark_product_failure(result: dict[str, object], message: str) -> None:
    result["product_failure"] = True
    if not result.get("product_gap"):
        result["product_gap"] = message


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
        },
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


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "#" if jira else "1."
    lines: list[str] = []
    for entry in sorted(
        result.get("steps", []),
        key=lambda item: item.get("step", 0),
    ):
        lines.append(
            f"{prefix} Step {entry.get('step')} — {str(entry.get('status', '')).upper()}: "
            f"{entry.get('action', '')}",
        )
        if jira:
            lines.append(f"*Observed:* {{noformat}}{entry.get('observed', '')}{{noformat}}")
        else:
            lines.append(f"   - Observed: `{entry.get('observed', '')}`")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "#" if jira else "1."
    lines: list[str] = []
    for entry in result.get("human_verification", []):
        lines.append(f"{prefix} {entry.get('check', '')}")
        if jira:
            lines.append(f"*Observed:* {{noformat}}{entry.get('observed', '')}{{noformat}}")
        else:
            lines.append(f"   - Observed: `{entry.get('observed', '')}`")
    return lines


def _step_status(result: dict[str, object], step: int) -> str | None:
    for entry in result.get("steps", []):
        if entry.get("step") == step:
            return str(entry.get("status"))
    return None


def _step_observation(result: dict[str, object], step: int) -> str:
    for entry in result.get("steps", []):
        if entry.get("step") == step:
            return str(entry.get("observed", ""))
    return ""


def _visible_output(
    *,
    payload: object | None,
    stdout: str,
    stderr: str,
) -> str:
    if isinstance(payload, dict):
        return json.dumps(payload, indent=2, sort_keys=True)
    stdout_text = stdout.strip()
    stderr_text = stderr.strip()
    if stdout_text and stderr_text:
        return f"{stdout_text}\n{stderr_text}"
    return stdout_text or stderr_text


def _observed_command_output(result: dict[str, object]) -> str:
    return (
        "stdout:\n"
        f"{_as_text(result.get('stdout'))}\n"
        "stderr:\n"
        f"{_as_text(result.get('stderr'))}"
    )


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def _as_text(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _as_dict(value: object | None) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def serialize(value: object) -> object:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(item) for item in value]
    return value


def validation_remote_origin(repository: str) -> str:
    return f"https://github.com/{repository}.git"


if __name__ == "__main__":
    main()
