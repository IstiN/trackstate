from __future__ import annotations

import json
import os
import platform
import sys
import traceback
import urllib.error
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveHostedRelease,
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.dart_probe_runtime import DartProbeExecution  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime  # noqa: E402

TICKET_KEY = "TS-501"
PROJECT_PATH = "DEMO"
PROJECT_JSON_PATH = f"{PROJECT_PATH}/project.json"
ISSUE_KEY = "DEMO-4"
ISSUE_PATH = f"{PROJECT_PATH}/DEMO-1/{ISSUE_KEY}"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
ATTACHMENT_NAME = "ts501-release-metadata.txt"
ATTACHMENT_TEXT = (
    "TS-501 release lifecycle verification payload.\n"
    "This attachment exists only to force creation of the per-issue release container.\n"
)
PROBE_ROOT = REPO_ROOT / "testing/tests/TS-501/dart_probe"
PROBE_ENTRYPOINT = Path("bin/ts501_release_lifecycle_probe.dart")

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


@dataclass(frozen=True)
class RepoMutation:
    path: str
    original_file: LiveHostedRepositoryFile | None


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture, service=service)
    release_tag_prefix = _current_release_tag_prefix(service)
    expected_release_tag = f"{release_tag_prefix}{ISSUE_KEY}"
    expected_release_name = f"Attachments for {ISSUE_KEY}"
    expected_release_body = f"TrackState-managed attachment container for {ISSUE_KEY}.\n"
    mutations = _collect_original_files(
        service,
        (MANIFEST_PATH,),
    )
    runtime = PythonDartProbeRuntime(REPO_ROOT)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "config_path": str(REPO_ROOT / "testing/tests/TS-501/config.yaml"),
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_path": issue_fixture.path,
        "manifest_path": MANIFEST_PATH,
        "attachment_name": ATTACHMENT_NAME,
        "attachment_size_bytes": len(ATTACHMENT_TEXT.encode("utf-8")),
        "release_tag_prefix": release_tag_prefix,
        "expected_release_tag": expected_release_tag,
        "expected_release_name": expected_release_name,
        "expected_release_body": expected_release_body,
        "steps": [],
        "human_verification": [],
        "precondition_attachment_paths": issue_fixture.attachment_paths,
        "precondition_comment_paths": issue_fixture.comment_paths,
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        _delete_release_if_present(
            service,
            service.fetch_release_by_tag(expected_release_tag),
        )
        fixture_setup = {
            "project_json": service.fetch_repo_text(PROJECT_JSON_PATH),
            "release_tag_prefix": release_tag_prefix,
        }
        result["fixture_setup"] = fixture_setup

        execution = _run_probe(runtime=runtime, service=service, release_tag_prefix=release_tag_prefix)
        result["probe_analyze_output"] = execution.analyze_output
        result["probe_run_output"] = execution.run_output
        payload = execution.session_payload or {}
        result["probe_payload"] = payload

        failures = _build_failures(
            execution=execution,
            payload=payload,
            result=result,
            service=service,
            expected_release_tag=expected_release_tag,
            expected_release_name=expected_release_name,
            expected_release_body=expected_release_body,
        )
        if failures:
            raise AssertionError("\n".join(failures))
    except Exception as error:
        scenario_error = error
        failed_step = _extract_failed_step_number(str(error))
        if failed_step is not None and _step_status(result, failed_step) == "failed":
            _record_step(
                result,
                step=failed_step,
                status="failed",
                action=_ticket_step_action(failed_step),
                observed=str(error),
            )
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
    finally:
        try:
            cleanup = _restore_fixture(
                service=service,
                mutations=mutations,
                release_tag=expected_release_tag,
            )
            result["cleanup"] = cleanup
        except Exception as error:
            cleanup_error = error
            result["cleanup"] = {
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
            }
            if scenario_error is None:
                scenario_error = error
                result["error"] = f"{type(error).__name__}: {error}"
                result["traceback"] = traceback.format_exc()

    if scenario_error is not None:
        if cleanup_error is not None and cleanup_error is not scenario_error:
            result["traceback"] = (
                str(result.get("traceback", ""))
                + "\nCleanup error:\n"
                + "".join(
                    traceback.format_exception(
                        type(cleanup_error),
                        cleanup_error,
                        cleanup_error.__traceback__,
                    ),
                )
            )
        _write_failure_outputs(result)
        raise scenario_error

    _write_pass_outputs(result)


def _assert_preconditions(
    issue_fixture: LiveHostedIssueFixture,
    *,
    service: LiveSetupRepositoryService,
) -> None:
    if issue_fixture.key != ISSUE_KEY:
        raise AssertionError(
            "Precondition failed: TS-501 expected the stable DEMO-4 live issue.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if issue_fixture.attachment_paths:
        raise AssertionError(
            "Precondition failed: the chosen live issue already had repository-path "
            "attachments, so the first-attachment release lifecycle would no longer be "
            "isolated.\n"
            f"Observed attachment paths: {issue_fixture.attachment_paths}",
        )
    manifest_file = _fetch_repo_file_if_exists(service, MANIFEST_PATH)
    if manifest_file is not None:
        manifest_entries = json.loads(manifest_file.content)
        if isinstance(manifest_entries, list) and manifest_entries:
            raise AssertionError(
                "Precondition failed: the chosen live issue already had attachment manifest "
                "entries, so the first-attachment release lifecycle would no longer be "
                "isolated.\n"
                f"Observed manifest text:\n{manifest_file.content}",
            )


def _collect_original_files(
    service: LiveSetupRepositoryService,
    paths: tuple[str, ...],
) -> list[RepoMutation]:
    return [
        RepoMutation(path=path, original_file=_fetch_repo_file_if_exists(service, path))
        for path in paths
    ]


def _fetch_repo_file_if_exists(
    service: LiveSetupRepositoryService,
    path: str,
) -> LiveHostedRepositoryFile | None:
    try:
        return service.fetch_repo_file(path)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def _current_release_tag_prefix(service: LiveSetupRepositoryService) -> str:
    project_payload = json.loads(service.fetch_repo_text(PROJECT_JSON_PATH))
    if not isinstance(project_payload, dict):
        raise AssertionError(
            f"Precondition failed: {PROJECT_JSON_PATH} did not deserialize to a JSON object.",
        )
    attachment_storage = project_payload.get("attachmentStorage")
    if not isinstance(attachment_storage, dict):
        raise AssertionError(
            "Precondition failed: the live project is not configured with attachmentStorage.",
        )
    mode = str(attachment_storage.get("mode", "")).strip()
    github_releases = attachment_storage.get("githubReleases")
    if mode != "github-releases" or not isinstance(github_releases, dict):
        raise AssertionError(
            "Precondition failed: the live project is not currently in github-releases mode.",
        )
    tag_prefix = str(github_releases.get("tagPrefix", "")).strip()
    if not tag_prefix:
        raise AssertionError(
            "Precondition failed: attachmentStorage.githubReleases.tagPrefix is empty.",
        )
    return tag_prefix


def _run_probe(
    *,
    runtime: PythonDartProbeRuntime,
    service: LiveSetupRepositoryService,
    release_tag_prefix: str,
) -> DartProbeExecution:
    original_values = {
        key: os.environ.get(key)
        for key in (
            "TS501_REPOSITORY",
            "TS501_REF",
            "TS501_TOKEN",
            "TS501_ISSUE_KEY",
            "TS501_ATTACHMENT_NAME",
            "TS501_ATTACHMENT_TEXT",
            "TS501_RELEASE_TAG_PREFIX",
        )
    }
    os.environ["TS501_REPOSITORY"] = service.repository
    os.environ["TS501_REF"] = service.ref
    token = service.token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("TS-501 requires GH_TOKEN or GITHUB_TOKEN for the Dart probe.")
    os.environ["TS501_TOKEN"] = token
    os.environ["TS501_ISSUE_KEY"] = ISSUE_KEY
    os.environ["TS501_ATTACHMENT_NAME"] = ATTACHMENT_NAME
    os.environ["TS501_ATTACHMENT_TEXT"] = ATTACHMENT_TEXT
    os.environ["TS501_RELEASE_TAG_PREFIX"] = release_tag_prefix
    try:
        return runtime.execute(probe_root=PROBE_ROOT, entrypoint=PROBE_ENTRYPOINT)
    finally:
        for key, value in original_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _build_failures(
    *,
    execution: DartProbeExecution,
    payload: dict[str, object],
    result: dict[str, object],
    service: LiveSetupRepositoryService,
    expected_release_tag: str,
    expected_release_name: str,
    expected_release_body: str,
) -> list[str]:
    failures: list[str] = []
    if not execution.succeeded:
        failures.append(
            "Precondition failed: the TS-501 Dart probe did not analyze cleanly.\n"
            f"{execution.analyze_output}",
        )
        return failures

    if payload.get("status") != "passed":
        details = [str(payload.get("error") or "The TS-501 Dart probe reported a failure.")]
        stack_trace = payload.get("stackTrace")
        if stack_trace:
            details.append(str(stack_trace))
        failures.append("\n".join(details))
        return failures

    result["probe_resolved_write_branch"] = payload.get("resolvedWriteBranch")
    result["probe_session"] = payload.get("providerSession")
    result["uploaded_issue"] = payload.get("uploadedIssue")

    matched_manifest, manifest_observation = poll_until(
        probe=lambda: _observe_manifest_state(
            service=service,
            expected_release_tag=expected_release_tag,
        ),
        is_satisfied=lambda state: state["single_entry_matches_release"] is True,
        timeout_seconds=120,
        interval_seconds=4,
    )
    result["manifest_after_upload"] = manifest_observation["manifest_text"]
    result["matching_manifest_entries"] = manifest_observation["matching_entries"]
    if not matched_manifest:
        failures.append(
            "Step 1 failed: the production upload did not update `attachments.json` with "
            "a single github-releases entry for the uploaded file within the timeout.\n"
            f"Observed manifest text:\n{manifest_observation['manifest_text']}\n"
            f"Observed matching entries: {manifest_observation['matching_entries']}",
        )
    else:
        _record_step(
            result,
            step=1,
            status="passed",
            action=f"Upload an attachment to '{ISSUE_KEY}'.",
            observed=(
                f"manifest_entries={manifest_observation['matching_entries']}; "
                f"release_asset_names={manifest_observation['release_asset_names']}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the issue manifest now exposes one release-backed attachment entry "
                "for the uploaded file, which is the client-visible state TrackState depends on."
            ),
            observed=manifest_observation["manifest_text"],
        )

    matched_release, release = poll_until(
        probe=lambda: service.fetch_release_by_tag(expected_release_tag),
        is_satisfied=lambda value: value is not None
        and any(asset.name == ATTACHMENT_NAME for asset in value.assets),
        timeout_seconds=120,
        interval_seconds=4,
    )
    result["release_after_upload"] = _release_payload(release)
    if not matched_release or release is None:
        failures.append(
            "Step 2 failed: the created GitHub release container was not visible through "
            "the live REST API with the uploaded asset within the timeout.\n"
            f"Observed release: {json.dumps(_release_payload(release), indent=2, sort_keys=True)}",
        )
        return failures

    _record_step(
        result,
        step=2,
        status="passed",
        action="Inspect the created GitHub Release via the live GitHub REST API.",
        observed=json.dumps(_release_payload(release), sort_keys=True),
    )

    expected_branch = str(payload.get("resolvedWriteBranch") or "")
    result["expected_target_commitish"] = expected_branch
    metadata_failures = _release_metadata_failures(
        release=release,
        expected_tag=expected_release_tag,
        expected_name=expected_release_name,
        expected_body=expected_release_body,
        expected_branch=expected_branch,
    )
    failures.extend(metadata_failures)
    if not metadata_failures:
        _record_step(
            result,
            step=3,
            status="passed",
            action="Check the `draft`, `target_commitish`, and `body` fields.",
            observed=(
                f"draft={release.draft}; "
                f"target_commitish={release.target_commitish!r}; "
                f"body={release.body!r}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the release container stayed draft-only in GitHub and used the "
                "machine-managed attachment note while targeting the active provider write branch."
            ),
            observed=(
                f"tag={release.tag_name}; branch={expected_branch}; "
                f"draft={release.draft}; body={release.body!r}"
            ),
        )
    return failures


def _observe_manifest_state(
    *,
    service: LiveSetupRepositoryService,
    expected_release_tag: str,
) -> dict[str, object]:
    manifest_text = service.fetch_repo_text(MANIFEST_PATH)
    entries = json.loads(manifest_text)
    if not isinstance(entries, list):
        raise AssertionError(
            f"{MANIFEST_PATH} was not a JSON array.\nObserved text:\n{manifest_text}",
        )
    matching_entries = [
        entry
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("name", "")) == ATTACHMENT_NAME
    ]
    release = service.fetch_release_by_tag(expected_release_tag)
    release_asset_names = [
        asset.name
        for asset in (release.assets if release is not None else [])
        if asset.name
    ]
    return {
        "manifest_text": manifest_text,
        "matching_entries": matching_entries,
        "release_asset_names": release_asset_names,
        "single_entry_matches_release": len(matching_entries) == 1
        and str(matching_entries[0].get("storageBackend", "")) == "github-releases"
        and str(matching_entries[0].get("githubReleaseTag", "")) == expected_release_tag
        and str(matching_entries[0].get("githubReleaseAssetName", "")) == ATTACHMENT_NAME
        and ATTACHMENT_NAME in release_asset_names,
    }


def _release_metadata_failures(
    *,
    release: LiveHostedRelease,
    expected_tag: str,
    expected_name: str,
    expected_body: str,
    expected_branch: str,
) -> list[str]:
    failures: list[str] = []
    if release.tag_name != expected_tag:
        failures.append(
            "Step 2 failed: the created release tag did not match the expected "
            "attachment-container tag.\n"
            f"Expected tag: {expected_tag}\n"
            f"Observed tag: {release.tag_name}",
        )
    if release.name != expected_name:
        failures.append(
            "Step 2 failed: the created release title did not match the expected "
            "attachment-container title.\n"
            f"Expected title: {expected_name}\n"
            f"Observed title: {release.name}",
        )
    if not release.draft:
        failures.append(
            "Step 3 failed: the attachment container release was not left in draft state.\n"
            f"Observed release: {json.dumps(_release_payload(release), indent=2, sort_keys=True)}",
        )
    if release.target_commitish != expected_branch:
        failures.append(
            "Step 3 failed: the created release targeted the wrong write branch.\n"
            f"Expected target_commitish: {expected_branch}\n"
            f"Observed target_commitish: {release.target_commitish}\n"
            f"Observed release: {json.dumps(_release_payload(release), indent=2, sort_keys=True)}",
        )
    if release.body != expected_body:
        failures.append(
            "Step 3 failed: the created release body did not keep the standardized "
            "machine-managed attachment note.\n"
            f"Expected body: {expected_body!r}\n"
            f"Observed body: {release.body!r}\n"
            f"Observed release: {json.dumps(_release_payload(release), indent=2, sort_keys=True)}",
        )
    return failures


def _release_payload(release: LiveHostedRelease | None) -> dict[str, object]:
    if release is None:
        return {}
    return {
        "id": release.id,
        "tag_name": release.tag_name,
        "name": release.name,
        "draft": release.draft,
        "target_commitish": release.target_commitish,
        "body": release.body,
        "assets": [asset.name for asset in release.assets],
    }


def _restore_fixture(
    *,
    service: LiveSetupRepositoryService,
    mutations: list[RepoMutation],
    release_tag: str,
) -> dict[str, object]:
    restored_paths: list[str] = []
    deleted_paths: list[str] = []
    for mutation in reversed(mutations):
        if mutation.original_file is None:
            current = _fetch_repo_file_if_exists(service, mutation.path)
            if current is not None:
                service.delete_repo_file(
                    mutation.path,
                    message=f"{TICKET_KEY}: cleanup seeded fixture",
                )
                deleted_paths.append(mutation.path)
            continue
        current = service.fetch_repo_text(mutation.path)
        if current != mutation.original_file.content:
            _write_repo_text_with_retry(
                service=service,
                path=mutation.path,
                content=mutation.original_file.content,
                message=f"{TICKET_KEY}: restore original fixture",
            )
        restored_paths.append(mutation.path)

    release_after_test = service.fetch_release_by_tag(release_tag)
    _delete_release_if_present(service, release_after_test)
    return {
        "status": "restored",
        "restored_paths": restored_paths,
        "deleted_paths": deleted_paths,
        "release_cleanup": "deleted-created-release",
    }


def _delete_release_if_present(
    service: LiveSetupRepositoryService,
    release: LiveHostedRelease | None,
) -> None:
    if release is None:
        return
    for asset in release.assets:
        service.delete_release_asset(asset.id)
    service.delete_release(release.id)
    matched, _ = poll_until(
        probe=lambda: service.fetch_release_by_tag(release.tag_name),
        is_satisfied=lambda value: value is None,
        timeout_seconds=60,
        interval_seconds=3,
    )
    if not matched:
        raise AssertionError(
            f"Cleanup failed: release tag {release.tag_name} still exists after delete.",
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
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: unknown failure"))
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
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            f"* Used the stable attachment-free live issue {{{{{result['issue_key']}}}}} as "
            "the first-attachment precondition, reused the current "
            f"{{{{{PROJECT_JSON_PATH}}}}} github-releases configuration, and executed the real "
            "provider-backed upload path through the production Dart repository code."
        ),
        (
            f"* Inspected {{{{{MANIFEST_PATH}}}}} and GitHub release "
            f"{{{{{result.get('expected_release_tag', '')}}}}} after the upload completed."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the first attachment created one draft "
            "attachment container release on the active write branch with the standardized "
            "machine-managed body note."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: repository {{{{{result['repository']}}}}} @ "
            f"{{{{{result['repository_ref']}}}}}, live app URL {{{{{result['app_url']}}}}}, "
            f"OS {{{{{platform.system()}}}}}."
        ),
        "",
        "*Step results*",
        *_step_lines(result, jira=True),
        "",
        "*Human-style verification*",
        *_human_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact error*",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
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
            f"- Used the stable attachment-free live issue `{result['issue_key']}` as the "
            "first-attachment precondition, reused the current "
            f"`{PROJECT_JSON_PATH}` github-releases configuration, and executed the real "
            "provider-backed upload path through the production Dart repository code."
        ),
        (
            f"- Inspected `{MANIFEST_PATH}` and GitHub release "
            f"`{result.get('expected_release_tag', '')}` after the upload completed."
        ),
        "",
        "### Observed result",
        (
            "- Matched the expected result: the first attachment created one draft "
            "attachment container release on the active write branch with the standardized "
            "machine-managed body note."
            if passed
            else "- Did not match the expected result."
        ),
        (
            f"- Environment: repository `{result['repository']}` @ `{result['repository_ref']}`, "
            f"live app URL `{result['app_url']}`, OS `{platform.system()}`."
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
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            f"Ran the production GitHub attachment upload path for `{result['issue_key']}` "
            f"and checked that the created GitHub release `{result.get('expected_release_tag', '')}` "
            f"stayed draft, targeted `{result.get('expected_target_commitish', '')}`, and "
            "kept the machine-managed attachment-container body."
        ),
        "",
        "## Observed",
        f"- Environment: `{result['repository']}` @ `{result['repository_ref']}` on {platform.system()}",
        f"- Cleanup: `{result.get('cleanup')}`",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            "# TS-501 - First attachment release container metadata is wrong on creation",
            "",
            "## Steps to reproduce",
            f"1. Upload an attachment to `{result['issue_key']}`.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Inspect the created GitHub Release via REST API or `gh release view`.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Check the `draft`, `target_commitish`, and `body` fields.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "",
            "## Actual vs Expected",
            (
                f"- Expected: uploading the first attachment to `{result['issue_key']}` "
                f"should create release `{result.get('expected_release_tag', '')}` in draft "
                f"state, target the active write branch `{result.get('expected_target_commitish', '')}`, "
                f"and set the body to `{result.get('expected_release_body', '')!r}`."
            ),
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the created release did not match the expected draft/body/branch metadata."
                )
            ),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment",
            f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
            f"- Issue: `{result['issue_key']}` (`{result['issue_summary']}`)",
            f"- Manifest path: `{result['manifest_path']}`",
            f"- Release tag: `{result.get('expected_release_tag', '')}`",
            f"- OS: `{platform.platform()}`",
            "",
            "## Screenshots or logs",
            "### Manifest after upload",
            "```json",
            str(result.get("manifest_after_upload", "")),
            "```",
            "### Matching manifest entries",
            "```json",
            json.dumps(result.get("matching_manifest_entries", []), indent=2, sort_keys=True),
            "```",
            "### Observed release payload",
            "```json",
            json.dumps(result.get("release_after_upload", {}), indent=2, sort_keys=True),
            "```",
            "### Dart probe payload",
            "```json",
            json.dumps(result.get("probe_payload", {}), indent=2, sort_keys=True),
            "```",
            f"- Cleanup: `{result.get('cleanup')}`",
        ],
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        status = str(step.get("status", "failed"))
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — "
            f"{status.upper() if jira else status}: {step['observed']}"
        )
    if not lines:
        lines.append("# No step details were recorded." if jira else "1. No step details were recorded.")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(f"{prefix} {check.get('check')}: {check.get('observed')}")
    if not lines:
        lines.append(
            "# No human-style verification data was recorded."
            if jira
            else "1. No human-style verification data was recorded."
        )
    return lines


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("observed", "No observation recorded."))
    previous_step = step_number - 1
    if previous_step >= 1 and _step_status(result, previous_step) != "passed":
        return (
            f"Not reached because Step {previous_step} failed: "
            f"{_step_observation(result, previous_step)}"
        )
    return str(result.get("error", "No observation recorded."))


def _extract_failed_step_number(message: str) -> int | None:
    for prefix in ("Step ", "step "):
        index = message.find(prefix)
        if index == -1:
            continue
        tail = message[index + len(prefix) :]
        digits = []
        for character in tail:
            if character.isdigit():
                digits.append(character)
                continue
            break
        if digits:
            return int("".join(digits))
    return None


def _ticket_step_action(step_number: int) -> str:
    return {
        1: f"Upload an attachment to '{ISSUE_KEY}'.",
        2: "Inspect the created GitHub Release via the live GitHub REST API.",
        3: "Check the `draft`, `target_commitish`, and `body` fields.",
    }.get(step_number, "Ticket step")


if __name__ == "__main__":
    main()
