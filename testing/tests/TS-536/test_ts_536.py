from __future__ import annotations

import json
import platform
import sys
import traceback
import urllib.error
import uuid
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedRelease,
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.ts501_release_lifecycle_probe import (  # noqa: E402
    Ts501ReleaseLifecycleProbe,
    Ts501ReleaseLifecycleProbeRequest,
    Ts501ReleaseLifecycleProbeResult,
)
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.ts501_release_lifecycle_probe_factory import (  # noqa: E402
    create_ts501_release_lifecycle_probe,
)

TICKET_KEY = "TS-536"
PROJECT_KEY = "DEMO"
PROJECT_JSON_PATH = f"{PROJECT_KEY}/project.json"
INDEX_PATH = f"{PROJECT_KEY}/.trackstate/index/issues.json"
ISSUE_KEY = "TS-50"
ISSUE_SUMMARY = "Release body normalization fixture"
ISSUE_PATH = f"{PROJECT_KEY}/{ISSUE_KEY}"
ISSUE_MAIN_PATH = f"{ISSUE_PATH}/main.md"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
RELEASE_TAG_PREFIX = "trackstate-attachments-"
EXPECTED_RELEASE_TAG = f"{RELEASE_TAG_PREFIX}{ISSUE_KEY}"
EXPECTED_RELEASE_TITLE = f"Attachments for {ISSUE_KEY}"
SEEDED_RELEASE_BODY = "Manual Notes"
STANDARD_RELEASE_BODY = f"TrackState-managed attachment container for {ISSUE_KEY}.\n"
RUN_SUFFIX = uuid.uuid4().hex[:8]
ATTACHMENT_NAME = f"ts536-release-reuse-{RUN_SUFFIX}.txt"
ATTACHMENT_TEXT = (
    f"TS-536 release reuse verification payload {RUN_SUFFIX}.\n"
    "The seeded release should be reused even when its body was edited manually.\n"
)

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


@dataclass(frozen=True)
class ReleaseSnapshot:
    id: int
    tag_name: str
    name: str
    body: str
    draft: bool
    target_commitish: str
    asset_names: tuple[str, ...]


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-536 requires GH_TOKEN or GITHUB_TOKEN to exercise the live GitHub "
            "Releases attachment flow.",
        )

    original_release = service.fetch_release_by_tag_any_state(EXPECTED_RELEASE_TAG)
    release_snapshot = _snapshot_release(original_release)
    mutations = _collect_original_files(
        service,
        (PROJECT_JSON_PATH, INDEX_PATH, ISSUE_MAIN_PATH, MANIFEST_PATH),
    )
    probe = create_ts501_release_lifecycle_probe(REPO_ROOT)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "project_key": PROJECT_KEY,
        "issue_key": ISSUE_KEY,
        "issue_summary": ISSUE_SUMMARY,
        "issue_path": ISSUE_PATH,
        "manifest_path": MANIFEST_PATH,
        "attachment_name": ATTACHMENT_NAME,
        "attachment_size_bytes": len(ATTACHMENT_TEXT.encode("utf-8")),
        "release_tag": EXPECTED_RELEASE_TAG,
        "release_title": EXPECTED_RELEASE_TITLE,
        "seeded_release_body": SEEDED_RELEASE_BODY,
        "allowed_release_bodies": [SEEDED_RELEASE_BODY, STANDARD_RELEASE_BODY],
        "steps": [],
        "human_verification": [],
        "original_release": _release_payload(original_release),
    }

    scenario_error: Exception | None = None
    cleanup_error: Exception | None = None
    try:
        fixture_setup = _seed_fixture(
            service=service,
            original_release=original_release,
        )
        result["fixture_setup"] = fixture_setup
        result["seeded_release_id"] = fixture_setup["release_id"]

        execution = _run_probe(
            probe=probe,
            service=service,
            token=token,
        )
        result["probe_analyze_output"] = execution.analyze_output
        result["probe_run_output"] = execution.run_output
        payload = execution.session_payload or {}
        result["probe_payload"] = payload

        failures = _build_failures(
            execution=execution,
            payload=payload,
            result=result,
            service=service,
            seeded_release_id=int(fixture_setup["release_id"]),
        )
        if failures:
            raise AssertionError("\n".join(failures))
    except Exception as error:
        scenario_error = error
        failed_step = _extract_failed_step_number(str(error))
        if failed_step is not None and not _has_step(result, failed_step):
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
                original_release=release_snapshot,
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


def _seed_fixture(
    *,
    service: LiveSetupRepositoryService,
    original_release: LiveHostedRelease | None,
) -> dict[str, object]:
    project_payload = json.loads(service.fetch_repo_text(PROJECT_JSON_PATH))
    if not isinstance(project_payload, dict):
        raise AssertionError(
            f"Precondition failed: {PROJECT_JSON_PATH} did not deserialize to a JSON object.",
        )
    project_payload["attachmentStorage"] = {
        "mode": "github-releases",
        "githubReleases": {"tagPrefix": RELEASE_TAG_PREFIX},
    }
    service.write_repo_text(
        PROJECT_JSON_PATH,
        content=json.dumps(project_payload, indent=2) + "\n",
        message=f"{TICKET_KEY}: enable github-releases storage",
    )

    issues_index = json.loads(service.fetch_repo_text(INDEX_PATH))
    if not isinstance(issues_index, list):
        raise AssertionError(
            f"Precondition failed: {INDEX_PATH} did not deserialize to a JSON array.",
        )
    filtered_entries = [
        entry
        for entry in issues_index
        if not isinstance(entry, dict) or str(entry.get("key", "")) != ISSUE_KEY
    ]
    filtered_entries.append(_issue_index_entry())
    service.write_repo_text(
        INDEX_PATH,
        content=json.dumps(filtered_entries, indent=2) + "\n",
        message=f"{TICKET_KEY}: seed {ISSUE_KEY} index entry",
    )
    service.write_repo_text(
        ISSUE_MAIN_PATH,
        content=_issue_main_markdown(),
        message=f"{TICKET_KEY}: seed {ISSUE_KEY} issue fixture",
    )
    service.write_repo_text(
        MANIFEST_PATH,
        content="[]\n",
        message=f"{TICKET_KEY}: seed empty attachment manifest",
    )

    if original_release is None:
        seeded_release = service.create_release(
            tag_name=EXPECTED_RELEASE_TAG,
            name=EXPECTED_RELEASE_TITLE,
            body=SEEDED_RELEASE_BODY,
            target_commitish=service.ref,
            draft=True,
            prerelease=False,
        )
        release_setup = "created"
    else:
        seeded_release = service.update_release(
            original_release.id,
            name=EXPECTED_RELEASE_TITLE,
            body=SEEDED_RELEASE_BODY,
            target_commitish=service.ref,
            draft=True,
            prerelease=False,
        )
        release_setup = "updated"

    matched_issue, issue_fixture = poll_until(
        probe=lambda: service.fetch_issue_fixture(ISSUE_PATH),
        is_satisfied=lambda value: value.key == ISSUE_KEY and value.summary == ISSUE_SUMMARY,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched_issue:
        raise AssertionError(
            "Precondition failed: the hosted repository did not expose the seeded "
            f"{ISSUE_KEY} issue before the upload scenario began.\n"
            f"Observed issue fixture: {issue_fixture}",
        )

    matched_release, observed_release = poll_until(
        probe=lambda: service.fetch_release_by_tag(EXPECTED_RELEASE_TAG),
        is_satisfied=lambda value: value is not None
        and value.name == EXPECTED_RELEASE_TITLE
        and value.body == SEEDED_RELEASE_BODY
        and value.draft is True,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched_release or observed_release is None:
        raise AssertionError(
            "Precondition failed: the seeded draft release with manual body text was not "
            "visible through the live GitHub API.\n"
            f"Observed release: {_release_payload(observed_release)}",
        )

    matched_manifest, manifest_text = poll_until(
        probe=lambda: service.fetch_repo_text(MANIFEST_PATH),
        is_satisfied=lambda value: value == "[]\n",
        timeout_seconds=60,
        interval_seconds=3,
    )
    if not matched_manifest:
        raise AssertionError(
            "Precondition failed: the seeded attachments.json manifest did not remain empty "
            "before the upload attempt.\n"
            f"Observed manifest text:\n{manifest_text}",
        )

    return {
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "release_setup": release_setup,
        "project_attachment_storage": project_payload["attachmentStorage"],
        "manifest_text": manifest_text,
        "release_id": observed_release.id,
        "release_tag": observed_release.tag_name,
        "release_title": observed_release.name,
        "release_body": observed_release.body,
        "release_draft": observed_release.draft,
        "release_asset_names": [asset.name for asset in observed_release.assets],
    }


def _run_probe(
    *,
    probe: Ts501ReleaseLifecycleProbe,
    service: LiveSetupRepositoryService,
    token: str,
) -> Ts501ReleaseLifecycleProbeResult:
    return probe.execute(
        request=Ts501ReleaseLifecycleProbeRequest(
            repository=service.repository,
            ref=service.ref,
            token=token,
            issue_key=ISSUE_KEY,
            attachment_name=ATTACHMENT_NAME,
            attachment_text=ATTACHMENT_TEXT,
            release_tag_prefix=RELEASE_TAG_PREFIX,
        ),
    )


def _build_failures(
    *,
    execution: Ts501ReleaseLifecycleProbeResult,
    payload: dict[str, object],
    result: dict[str, object],
    service: LiveSetupRepositoryService,
    seeded_release_id: int,
) -> list[str]:
    failures: list[str] = []
    if not execution.succeeded:
        failures.append(
            "Precondition failed: the TS-536 Dart probe did not analyze cleanly.\n"
            f"{execution.analyze_output}",
        )
        return failures

    if payload.get("status") != "passed":
        details = [str(payload.get("error") or "The TS-536 Dart probe reported a failure.")]
        stack_trace = payload.get("stackTrace")
        if stack_trace:
            details.append(str(stack_trace))
        failures.append("\n".join(details))
        return failures

    uploaded_attachment = payload.get("uploadedAttachment")
    result["uploaded_attachment"] = uploaded_attachment
    result["probe_resolved_write_branch"] = payload.get("resolvedWriteBranch")
    result["uploaded_issue"] = payload.get("uploadedIssue")

    matched_manifest, manifest_observation = poll_until(
        probe=lambda: _observe_manifest_state(service),
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
            action=f"Upload a new attachment to issue `{ISSUE_KEY}`.",
            observed=(
                f"manifest_entries={manifest_observation['matching_entries']}; "
                f"release_asset_names={manifest_observation['release_asset_names']}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the issue manifest now exposes the uploaded file as a visible "
                "GitHub Releases-backed attachment entry for TS-50."
            ),
            observed=manifest_observation["manifest_text"],
        )

    matched_release_candidates, release_candidates = poll_until(
        probe=lambda: service.fetch_releases_by_tag_any_state(EXPECTED_RELEASE_TAG),
        is_satisfied=lambda value: any(
            ATTACHMENT_NAME in [asset.name for asset in candidate.assets]
            for candidate in value
        ),
        timeout_seconds=120,
        interval_seconds=4,
    )
    result["release_candidates_after_upload"] = [
        _release_payload(candidate) for candidate in release_candidates
    ]
    release_with_asset = next(
        (
            candidate
            for candidate in release_candidates
            if ATTACHMENT_NAME in [asset.name for asset in candidate.assets]
        ),
        None,
    )
    seeded_release = next(
        (candidate for candidate in release_candidates if candidate.id == seeded_release_id),
        None,
    )
    result["release_after_upload"] = _release_payload(release_with_asset)
    result["seeded_release_after_upload"] = _release_payload(seeded_release)
    if not matched_release_candidates or release_with_asset is None:
        failures.append(
            "Step 2 failed: GitHub never exposed a release carrying the uploaded asset for "
            "the expected tag within the timeout.\n"
            f"Observed release candidates: {json.dumps([_release_payload(item) for item in release_candidates], indent=2, sort_keys=True)}",
        )
        return failures

    metadata_failures = _release_reuse_failures(
        release_with_asset=release_with_asset,
        seeded_release=seeded_release,
        release_candidates=release_candidates,
        seeded_release_id=seeded_release_id,
        uploaded_attachment=uploaded_attachment,
    )
    failures.extend(metadata_failures)
    if not metadata_failures:
        body_outcome = (
            "normalized"
            if release_with_asset.body == STANDARD_RELEASE_BODY
            else "preserved-manual-body"
        )
        result["observed_release_body"] = release_with_asset.body
        result["release_body_outcome"] = body_outcome
        _record_step(
            result,
            step=2,
            status="passed",
            action="Inspect the release on GitHub after the operation completes.",
            observed=(
                f"release_id={release_with_asset.id}; "
                f"tag={release_with_asset.tag_name}; "
                f"title={release_with_asset.name!r}; "
                f"body={release_with_asset.body!r}; "
                f"draft={release_with_asset.draft}; "
                f"assets={[asset.name for asset in release_with_asset.assets]}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the GitHub release still showed the same release object with "
                "title `Attachments for TS-50`, contained the new asset, and displayed either "
                "the preserved `Manual Notes` body or the normalized machine-managed note."
            ),
            observed=json.dumps(_release_payload(release_with_asset), indent=2, sort_keys=True),
        )
    return failures


def _observe_manifest_state(service: LiveSetupRepositoryService) -> dict[str, object]:
    manifest_text = service.fetch_repo_text(MANIFEST_PATH)
    entries = json.loads(manifest_text)
    if not isinstance(entries, list):
        raise AssertionError(
            f"{MANIFEST_PATH} was not a JSON array.\nObserved text:\n{manifest_text}",
        )
    matching_entries = [
        entry for entry in entries if isinstance(entry, dict) and entry.get("name") == ATTACHMENT_NAME
    ]
    release = service.fetch_release_by_tag(EXPECTED_RELEASE_TAG)
    release_asset_names = [
        asset.name for asset in (release.assets if release is not None else []) if asset.name
    ]
    return {
        "manifest_text": manifest_text,
        "matching_entries": matching_entries,
        "release_asset_names": release_asset_names,
        "single_entry_matches_release": len(matching_entries) == 1
        and str(matching_entries[0].get("storageBackend", "")) == "github-releases"
        and str(matching_entries[0].get("githubReleaseTag", "")) == EXPECTED_RELEASE_TAG
        and str(matching_entries[0].get("githubReleaseAssetName", "")) == ATTACHMENT_NAME
        and str(matching_entries[0].get("storagePath", "")) == f"{ISSUE_PATH}/attachments/{ATTACHMENT_NAME}",
    }


def _release_reuse_failures(
    *,
    release_with_asset: LiveHostedRelease,
    seeded_release: LiveHostedRelease | None,
    release_candidates: list[LiveHostedRelease],
    seeded_release_id: int,
    uploaded_attachment: object,
) -> list[str]:
    failures: list[str] = []
    if len(release_candidates) != 1:
        failures.append(
            "Step 2 failed: GitHub exposed more than one release candidate for the "
            "expected tag after the upload, so the system created a duplicate release "
            "instead of reusing the seeded one.\n"
            f"Observed releases: {json.dumps([_release_payload(item) for item in release_candidates], indent=2, sort_keys=True)}",
        )
    if release_with_asset.id != seeded_release_id:
        failures.append(
            "Step 2 failed: the uploaded asset landed on a different release object than "
            "the seeded draft release.\n"
            f"Seeded release id: {seeded_release_id}\n"
            f"Seeded release after upload: {json.dumps(_release_payload(seeded_release), indent=2, sort_keys=True)}\n"
            f"Release carrying uploaded asset: {json.dumps(_release_payload(release_with_asset), indent=2, sort_keys=True)}",
        )
    if release_with_asset.tag_name != EXPECTED_RELEASE_TAG:
        failures.append(
            "Step 2 failed: the observed release tag did not match the seeded issue identity.\n"
            f"Expected tag: {EXPECTED_RELEASE_TAG}\n"
            f"Observed tag: {release_with_asset.tag_name}",
        )
    if release_with_asset.name != EXPECTED_RELEASE_TITLE:
        failures.append(
            "Step 2 failed: the observed release title did not match the seeded issue identity.\n"
            f"Expected title: {EXPECTED_RELEASE_TITLE}\n"
            f"Observed title: {release_with_asset.name}",
        )
    if release_with_asset.body not in {SEEDED_RELEASE_BODY, STANDARD_RELEASE_BODY}:
        failures.append(
            "Step 2 failed: the release body was neither preserved as the manual note nor "
            "normalized to the standard machine-managed note.\n"
            f"Allowed bodies: {[SEEDED_RELEASE_BODY, STANDARD_RELEASE_BODY]}\n"
            f"Observed body: {release_with_asset.body!r}\n"
            f"Observed release: {json.dumps(_release_payload(release_with_asset), indent=2, sort_keys=True)}",
        )
    if ATTACHMENT_NAME not in [asset.name for asset in release_with_asset.assets]:
        failures.append(
            "Step 2 failed: the uploaded asset was not present on the reused release.\n"
            f"Observed assets: {[asset.name for asset in release_with_asset.assets]}",
        )

    if isinstance(uploaded_attachment, dict):
        if uploaded_attachment.get("githubReleaseTag") != EXPECTED_RELEASE_TAG:
            failures.append(
                "Step 1 failed: the production upload payload did not report the expected "
                "GitHub release tag for the uploaded attachment.\n"
                f"Observed attachment payload: {json.dumps(uploaded_attachment, indent=2, sort_keys=True)}",
            )
        if uploaded_attachment.get("githubReleaseAssetName") != ATTACHMENT_NAME:
            failures.append(
                "Step 1 failed: the production upload payload did not report the expected "
                "GitHub release asset name.\n"
                f"Observed attachment payload: {json.dumps(uploaded_attachment, indent=2, sort_keys=True)}",
            )
    return failures


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


def _restore_fixture(
    *,
    service: LiveSetupRepositoryService,
    mutations: list[RepoMutation],
    original_release: ReleaseSnapshot | None,
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
            service.write_repo_text(
                mutation.path,
                content=mutation.original_file.content,
                message=f"{TICKET_KEY}: restore original fixture",
            )
        restored_paths.append(mutation.path)

    release_actions: list[str] = []
    current_releases = service.fetch_releases_by_tag_any_state(EXPECTED_RELEASE_TAG)
    if original_release is None:
        for current_release in current_releases:
            for asset in current_release.assets:
                service.delete_release_asset(asset.id)
                release_actions.append(
                    f"deleted asset {asset.name} from release {current_release.id}",
                )
            service.delete_release(current_release.id)
            release_actions.append(f"deleted release {current_release.id}")
        matched, remaining_releases = poll_until(
            probe=lambda: service.fetch_releases_by_tag_any_state(EXPECTED_RELEASE_TAG),
            is_satisfied=lambda value: len(value) == 0,
            timeout_seconds=60,
            interval_seconds=3,
        )
        if not matched:
            raise AssertionError(
                "Cleanup failed: one or more seeded releases still exist after delete.\n"
                f"Remaining releases: {json.dumps([_release_payload(item) for item in remaining_releases], indent=2, sort_keys=True)}",
            )
    else:
        if not current_releases:
            raise AssertionError(
                f"Cleanup failed: original release {EXPECTED_RELEASE_TAG} disappeared and could not be restored.",
            )
        current_release = None
        for candidate in current_releases:
            if candidate.id == original_release.id:
                current_release = candidate
                continue
            for asset in candidate.assets:
                service.delete_release_asset(asset.id)
                release_actions.append(
                    f"deleted duplicate asset {asset.name} from release {candidate.id}",
                )
            service.delete_release(candidate.id)
            release_actions.append(f"deleted duplicate release {candidate.id}")
        if current_release is None:
            raise AssertionError(
                f"Cleanup failed: original release id {original_release.id} could not be found among current releases.",
            )
        original_asset_names = set(original_release.asset_names)
        for asset in current_release.assets:
            if asset.name not in original_asset_names:
                service.delete_release_asset(asset.id)
                release_actions.append(f"deleted test asset {asset.name}")
        remaining_releases = service.fetch_releases_by_tag_any_state(EXPECTED_RELEASE_TAG)
        current_release = next(
            (candidate for candidate in remaining_releases if candidate.id == original_release.id),
            None,
        )
        if current_release is None:
            raise AssertionError(
                f"Cleanup failed: release {EXPECTED_RELEASE_TAG} disappeared after asset cleanup.",
            )
        if (
            current_release.name != original_release.name
            or current_release.body != original_release.body
            or current_release.draft != original_release.draft
            or current_release.target_commitish != original_release.target_commitish
        ):
            restored_release = service.update_release(
                current_release.id,
                name=original_release.name,
                body=original_release.body,
                target_commitish=original_release.target_commitish,
                draft=original_release.draft,
            )
            release_actions.append(
                f"restored release {restored_release.id} metadata to "
                f"name={restored_release.name!r}, body={restored_release.body!r}, draft={restored_release.draft}"
            )

    return {
        "status": "restored",
        "restored_paths": restored_paths,
        "deleted_paths": deleted_paths,
        "release_actions": release_actions,
    }


def _snapshot_release(release: LiveHostedRelease | None) -> ReleaseSnapshot | None:
    if release is None:
        return None
    return ReleaseSnapshot(
        id=release.id,
        tag_name=release.tag_name,
        name=release.name,
        body=release.body,
        draft=release.draft,
        target_commitish=release.target_commitish,
        asset_names=tuple(asset.name for asset in release.assets),
    )


def _issue_index_entry() -> dict[str, object]:
    return {
        "key": ISSUE_KEY,
        "path": ISSUE_MAIN_PATH,
        "parent": None,
        "epic": None,
        "parentPath": None,
        "epicPath": None,
        "summary": ISSUE_SUMMARY,
        "issueType": "story",
        "status": "todo",
        "priority": "medium",
        "assignee": "demo-user",
        "labels": ["ts-536", "attachments", "github-releases"],
        "updated": "2026-05-13T00:00:00Z",
        "progress": 0.0,
        "children": [],
        "archived": False,
    }


def _issue_main_markdown() -> str:
    return (
        "---\n"
        f"key: {ISSUE_KEY}\n"
        "project: DEMO\n"
        "issueType: story\n"
        "status: todo\n"
        f"summary: {ISSUE_SUMMARY}\n"
        "priority: medium\n"
        "assignee: demo-user\n"
        "reporter: demo-admin\n"
        "updated: 2026-05-13T00:00:00Z\n"
        "---\n\n"
        "# Description\n\n"
        "Hosted release body normalization fixture for TS-536.\n"
    )


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
            f"* Seeded {{{{{ISSUE_PATH}}}}} and draft release "
            f"{{{{{EXPECTED_RELEASE_TAG}}}}} / {{{{{EXPECTED_RELEASE_TITLE}}}}} with body "
            f"{{{{{SEEDED_RELEASE_BODY}}}}}, then executed the real provider-backed attachment "
            "upload path through the production Dart repository code."
        ),
        (
            f"* Inspected {{{{{MANIFEST_PATH}}}}} and the live GitHub release "
            f"{{{{{EXPECTED_RELEASE_TAG}}}}} after the upload completed."
        ),
        "",
        "*Observed result*",
        (
            f"* Matched the expected result: the upload reused release id "
            f"{{{{{result.get('seeded_release_id', '')}}}}}, uploaded asset "
            f"{{{{{result.get('attachment_name', '')}}}}}, and the release body "
            f"was {{{{{result.get('observed_release_body', SEEDED_RELEASE_BODY)}}}}}."
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
            f"- Seeded `{ISSUE_PATH}` and draft release `{EXPECTED_RELEASE_TAG}` / "
            f"`{EXPECTED_RELEASE_TITLE}` with body `{SEEDED_RELEASE_BODY}`, then executed "
            "the real provider-backed attachment upload path through the production Dart repository code."
        ),
        (
            f"- Inspected `{MANIFEST_PATH}` and the live GitHub release "
            f"`{EXPECTED_RELEASE_TAG}` after the upload completed."
        ),
        "",
        "### Observed result",
        (
            f"- Matched the expected result: the upload reused release id "
            f"`{result.get('seeded_release_id', '')}`, uploaded asset "
            f"`{result.get('attachment_name', '')}`, and the release body was "
            f"`{result.get('observed_release_body', SEEDED_RELEASE_BODY)}`."
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
            f"Ran the production GitHub release-backed upload path for `{ISSUE_KEY}` and "
            f"checked that release `{EXPECTED_RELEASE_TAG}` kept the same release id, "
            f"contained `{ATTACHMENT_NAME}`, and exposed body "
            f"`{result.get('observed_release_body', SEEDED_RELEASE_BODY)}` after the upload."
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
            "# TS-536 - Matching release with manual body was not reused correctly",
            "",
            "## Steps to reproduce",
            f"1. Upload a new attachment to `{ISSUE_KEY}`.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Inspect the release on GitHub after the operation completes.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "",
            "## Actual vs Expected",
            (
                f"- Expected: upload should succeed, `{EXPECTED_RELEASE_TAG}` should stay the "
                f"same release object with title `{EXPECTED_RELEASE_TITLE}`, include asset "
                f"`{ATTACHMENT_NAME}`, and keep the body as either `{SEEDED_RELEASE_BODY}` or "
                f"`{STANDARD_RELEASE_BODY!r}`."
            ),
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the seeded release was not reused with an acceptable body outcome."
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
            f"- Issue: `{ISSUE_KEY}` (`{ISSUE_SUMMARY}`)",
            f"- Manifest path: `{MANIFEST_PATH}`",
            f"- Release tag: `{EXPECTED_RELEASE_TAG}`",
            f"- Live app URL: `{result['app_url']}`",
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
            "### All release candidates for the tag",
            "```json",
            json.dumps(result.get("release_candidates_after_upload", []), indent=2, sort_keys=True),
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


def _has_step(result: dict[str, object], step_number: int) -> bool:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return True
    return False


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
        1: f"Upload a new attachment to issue `{ISSUE_KEY}`.",
        2: "Inspect the release on GitHub after the operation completes.",
    }.get(step_number, "Ticket step")


if __name__ == "__main__":
    main()
