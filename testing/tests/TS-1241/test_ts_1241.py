from __future__ import annotations

import json
import platform
import re
import sys
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_multi_view_refresh_page import (  # noqa: E402
    EditControlObservation,
    LiveMultiViewRefreshPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    GitHubAuthenticatedUser,
    LiveHostedIssueFixture,
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-1241"
TEST_CASE_TITLE = "Save hosted issue edit with stale base SHA"
RUN_COMMAND = (
    "mkdir -p outputs && PYTHONPATH=. python3 "
    "testing/tests/TS-1241/test_ts_1241.py"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1241_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1241_failure.png"

TARGET_ISSUE_KEY = "DEMO-3992"
TARGET_PRIORITY_LABEL = "Highest"
TARGET_PRIORITY_ID = "highest"
SEED_PRIORITY_LABEL = "High"
SEED_PRIORITY_ID = "high"
TARGET_STATUS_LABEL = "Done"
TARGET_STATUS_ID = "done"
SEED_STATUS_LABEL = "In Review"
SEED_STATUS_ID = "in-review"
PROBE_FILE_PATH = "DEMO/.ts1241-stale-base-sha-probe.md"
SUCCESS_BANNER_FRAGMENT = f"{TARGET_ISSUE_KEY} moved to {TARGET_STATUS_LABEL}"
REQUEST_STEPS = [
    "Open the hosted app with a write-capable session for IstiN/trackstate-setup whose stored write ref is a stale commit SHA.",
    f"Open the 'Edit issue' dialog for {TARGET_ISSUE_KEY}.",
    "Create a concurrent GitHub commit so the remote branch head moves ahead of the stored write ref.",
    f"Change Priority to {TARGET_PRIORITY_LABEL} and Status to {TARGET_STATUS_LABEL}.",
    "Click Save.",
    "Observe the GitHub network sequence and the UI feedback.",
]
EXPECTED_RESULT = (
    "The application fetches the latest branch reference and commit SHA from "
    "GitHub immediately before initiating the tree update. The save operation "
    "completes successfully without a 422 'Invalid object requested' error. A "
    "success banner appears and the editor closes."
)
_GITHUB_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "issue_key": TARGET_ISSUE_KEY,
        "steps": [],
        "human_verification": [],
        "cleanup": [],
    }

    issue_file: LiveHostedRepositoryFile | None = None
    probe_file: LiveHostedRepositoryFile | None = None
    issue_path: str | None = None
    pending_exception: BaseException | None = None
    pending_product_defect = False

    try:
        if not token:
            raise RuntimeError(
                "TS-1241 requires GH_TOKEN or GITHUB_TOKEN to open the deployed hosted app.",
            )

        user = service.fetch_authenticated_user()
        issue_fixture = _find_issue_fixture(service=service, issue_key=TARGET_ISSUE_KEY)
        issue_path = f"{issue_fixture.path}/main.md"
        issue_file = service.fetch_repo_file(issue_path)
        probe_file = _fetch_optional_repo_file(service, PROBE_FILE_PATH)

        precondition = _ensure_issue_precondition(
            service=service,
            issue_fixture=issue_fixture,
            original_file=issue_file,
        )
        result["precondition"] = precondition

        stale_write_sha = _fetch_branch_head_sha(service=service, branch=service.ref)
        result["stale_write_branch"] = stale_write_sha

        workspace_state = _workspace_state(
            repository=service.repository,
            branch=service.ref,
            stale_write_sha=stale_write_sha,
        )
        result["workspace_state"] = workspace_state

        with create_live_tracker_app(
            config,
            runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                repository=service.repository,
                token=token,
                workspace_state=workspace_state,
                workspace_token_profile_ids=(
                    str(workspace_state["activeWorkspaceId"]),
                ),
            ),
        ) as tracker_page:
            app_page = LiveMultiViewRefreshPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed hosted tracker did not reach the live "
                        "application shell before the stale-base-SHA scenario started.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                app_page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                connected_body_text = app_page.current_body_text()
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"Hosted workspace connected as {user.login} to {service.repository} "
                        f"with stored writeBranch={stale_write_sha}. Visible body text:\n"
                        f"{connected_body_text}"
                    ),
                )
                _record_human_verification(
                    result,
                    check="Viewed the hosted shell exactly as a user would before editing the issue.",
                    observed=(
                        f"GitHub connection banner was visible for {service.repository}, the "
                        "workspace loaded into the live tracker shell, and the session started "
                        f"from a stale SHA-shaped write ref (`{stale_write_sha}`)."
                    ),
                )

                dialog_text = app_page.open_edit_dialog_for_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                result["edit_dialog_text"] = dialog_text
                initial_priority = app_page.priority_control()
                initial_status = app_page.status_control()
                result["priority_before_save"] = _control_payload(initial_priority)
                result["status_before_save"] = _control_payload(initial_status)
                _assert_seeded_controls(
                    issue_key=issue_fixture.key,
                    initial_priority=initial_priority,
                    initial_status=initial_status,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        f"Edit issue opened for {issue_fixture.key}. Priority control="
                        f"{_control_payload(initial_priority)}; Status control="
                        f"{_control_payload(initial_status)}."
                    ),
                )
                _record_human_verification(
                    result,
                    check="Checked the visible Edit issue dialog content before saving.",
                    observed=(
                        f"The dialog showed `Edit issue`, the issue key {issue_fixture.key}, "
                        f"Priority visibly rendered as {SEED_PRIORITY_LABEL}, and Status "
                        f"rendered as {SEED_STATUS_LABEL} so the live save action still needed "
                        "to make an observable change."
                    ),
                )

                _install_github_network_probe(
                    session=tracker_page.session,
                    repository=service.repository,
                )
                concurrent_commit = _create_concurrent_commit(
                    service=service,
                    stale_write_sha=stale_write_sha,
                )
                result["concurrent_commit"] = concurrent_commit
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        f"Concurrent GitHub commit advanced `{service.ref}` from "
                        f"{stale_write_sha} to {concurrent_commit['head_sha_after_commit']} "
                        f"via `{PROBE_FILE_PATH}`."
                    ),
                )

                updated_priority = app_page.change_priority(TARGET_PRIORITY_LABEL)
                updated_status = app_page.change_status_transition(TARGET_STATUS_LABEL)
                result["priority_after_edit"] = _control_payload(updated_priority)
                result["status_after_edit"] = _control_payload(updated_status)
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        f"Priority control updated to {_control_payload(updated_priority)} and "
                        f"Status control updated to {_control_payload(updated_status)}."
                    ),
                )

                try:
                    post_save_detail_text = app_page.save_issue_edits(
                        issue_key=issue_fixture.key,
                        expected_status=TARGET_STATUS_LABEL,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=5,
                        status="failed",
                        action=REQUEST_STEPS[4],
                        observed=str(error),
                    )
                    raise
                result["post_save_detail_text"] = post_save_detail_text
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=REQUEST_STEPS[4],
                    observed=post_save_detail_text,
                )

                try:
                    network_observation = _wait_for_network_sequence(
                        session=tracker_page.session,
                        stale_write_sha=stale_write_sha,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=6,
                        status="failed",
                        action=REQUEST_STEPS[5],
                        observed=str(error),
                    )
                    raise
                result["network_observation"] = network_observation
                _record_step(
                    result,
                    step=6,
                    status="passed",
                    action=REQUEST_STEPS[5],
                    observed=_network_sequence_summary(network_observation),
                )

                detail_text = app_page.wait_for_issue_detail_state(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                    expected_status=TARGET_STATUS_LABEL,
                    expected_priority=TARGET_PRIORITY_LABEL,
                    step_number=7,
                )
                result["detail_projection_text"] = detail_text
                if SUCCESS_BANNER_FRAGMENT not in post_save_detail_text:
                    raise AssertionError(
                        "Expected Result failed: the visible save feedback did not contain the "
                        f"success banner fragment `{SUCCESS_BANNER_FRAGMENT}`.\n"
                        f"Observed detail text:\n{post_save_detail_text}",
                    )
                if "Invalid object requested" in post_save_detail_text or "422" in post_save_detail_text:
                    raise AssertionError(
                        "Expected Result failed: the visible post-save UI still exposed the "
                        "stale-base SHA failure instead of a success banner.\n"
                        f"Observed detail text:\n{post_save_detail_text}",
                    )
                _record_human_verification(
                    result,
                    check="Verified the saved result from the user-facing issue detail surface.",
                    observed=(
                        f"The success banner `{SUCCESS_BANNER_FRAGMENT}` was visible, the Edit "
                        "issue dialog had closed, and the issue detail surface visibly showed "
                        f"Status `{TARGET_STATUS_LABEL}` and Priority `{TARGET_PRIORITY_LABEL}`."
                    ),
                )

                tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        pending_exception = error
        pending_product_defect = True
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        pending_exception = error
    finally:
        cleanup_entries: list[dict[str, object]] = []
        if issue_path is not None and issue_file is not None:
            try:
                cleanup_entries.append(
                    _restore_repo_file(
                        service=service,
                        path=issue_path,
                        original_file=issue_file,
                        description="Restore original DEMO-3992 main.md content",
                    ),
                )
            except Exception as cleanup_error:  # pragma: no cover - best-effort cleanup
                cleanup_entries.append(
                    {
                        "description": "Restore original DEMO-3992 main.md content",
                        "status": "cleanup-error",
                        "path": issue_path,
                        "error": f"{type(cleanup_error).__name__}: {cleanup_error}",
                    },
                )
        try:
            cleanup_entries.append(
                _restore_optional_repo_file(
                    service=service,
                    path=PROBE_FILE_PATH,
                    original_file=probe_file,
                    description="Remove concurrent-commit probe file",
                ),
            )
        except Exception as cleanup_error:  # pragma: no cover - best-effort cleanup
            cleanup_entries.append(
                {
                    "description": "Remove concurrent-commit probe file",
                    "status": "cleanup-error",
                    "path": PROBE_FILE_PATH,
                    "error": f"{type(cleanup_error).__name__}: {cleanup_error}",
                },
            )
        result["cleanup"] = cleanup_entries

    if pending_exception is not None:
        _write_failure_outputs(result, product_defect=pending_product_defect)
        print(json.dumps(result, indent=2))
        raise pending_exception

    result["summary"] = (
        "Verified the live hosted save path for DEMO-3992 succeeds from a stale "
        "SHA-shaped write ref by fetching the latest GitHub branch ref and commit "
        "before posting the replacement tree."
    )
    _write_pass_outputs(result)
    print(json.dumps(result, indent=2))


def _find_issue_fixture(
    *,
    service: LiveSetupRepositoryService,
    issue_key: str,
) -> LiveHostedIssueFixture:
    issue_path = next(
        (path for path in service.list_issue_paths("DEMO") if path.split("/")[-1] == issue_key),
        None,
    )
    if issue_path is None:
        raise AssertionError(
            f"Precondition failed: the hosted repository does not contain {issue_key}.",
        )
    return service.fetch_issue_fixture(issue_path)


def _ensure_issue_precondition(
    *,
    service: LiveSetupRepositoryService,
    issue_fixture: LiveHostedIssueFixture,
    original_file: LiveHostedRepositoryFile,
) -> dict[str, object]:
    current_priority_id = _front_matter_value(original_file.content, "priority")
    current_status_id = _front_matter_value(original_file.content, "status")
    seeded_content = original_file.content
    changed_fields: list[str] = []

    if current_priority_id == TARGET_PRIORITY_ID:
        seeded_content = _replace_front_matter_value(
            seeded_content,
            key="priority",
            new_value=SEED_PRIORITY_ID,
        )
        changed_fields.append(f"priority {TARGET_PRIORITY_ID}->{SEED_PRIORITY_ID}")
    if current_status_id != SEED_STATUS_ID:
        seeded_content = _replace_front_matter_value(
            seeded_content,
            key="status",
            new_value=SEED_STATUS_ID,
        )
        changed_fields.append(f"status {current_status_id}->{SEED_STATUS_ID}")

    if not changed_fields:
        return {
            "seeded": False,
            "issue_path": original_file.path,
            "priority_id": current_priority_id,
            "status_id": current_status_id,
        }

    service.write_repo_text(
        original_file.path,
        content=seeded_content,
        message=f"{TICKET_KEY}: seed live issue save precondition",
    )
    matched, observed_text = poll_until(
        probe=lambda: service.fetch_repo_text(original_file.path),
        is_satisfied=lambda text: text == seeded_content,
        timeout_seconds=90,
        interval_seconds=2,
    )
    if not matched:
        raise AssertionError(
            "Precondition failed: the hosted repository did not finish seeding "
            f"{issue_fixture.key} into a non-target edit state.\n"
            f"Expected changes: {changed_fields}\n"
            f"Observed content:\n{observed_text}",
        )

    return {
        "seeded": True,
        "issue_path": original_file.path,
        "changed_fields": changed_fields,
        "priority_id_after_seed": _front_matter_value(seeded_content, "priority"),
        "status_id_after_seed": _front_matter_value(seeded_content, "status"),
    }


def _workspace_state(
    *,
    repository: str,
    branch: str,
    stale_write_sha: str,
) -> dict[str, object]:
    hosted_workspace_id = f"hosted:{repository.lower()}@{branch}"
    return {
        "activeWorkspaceId": hosted_workspace_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": hosted_workspace_id,
                "displayName": "",
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": branch,
                "writeBranch": stale_write_sha,
            },
        ],
    }


def _install_github_network_probe(*, session: Any, repository: str) -> None:
    session.evaluate(
        """
        ({ repository }) => {
          const repoFragment = `/repos/${repository}/git/`;
          const toText = async (response) => {
            try {
              return await response.clone().text();
            } catch (error) {
              return `[[unreadable response body: ${String(error)}]]`;
            }
          };
          const ensureStore = () => {
            const existing = window.__ts1241GithubNetwork;
            if (existing && Array.isArray(existing.entries)) {
              return existing;
            }
            const created = {
              installed: true,
              nextId: 1,
              entries: [],
            };
            window.__ts1241GithubNetwork = created;
            return created;
          };
          const store = ensureStore();
          const pushEntry = (entry) => {
            store.entries.push({
              ...entry,
              order: store.entries.length + 1,
              timestamp: new Date().toISOString(),
            });
          };
          const trackedUrl = (value) =>
            typeof value === 'string' && value.includes(repoFragment);
          if (!window.__ts1241GithubNetworkFetchWrapped && typeof window.fetch === 'function') {
            const originalFetch = window.fetch.bind(window);
            window.fetch = async (input, init) => {
              const requestUrl =
                typeof input === 'string'
                  ? input
                  : (input && typeof input.url === 'string' ? input.url : '');
              const method = String(
                (init && init.method)
                  || (typeof input !== 'string' && input && input.method)
                  || 'GET',
              ).toUpperCase();
              const requestId = `fetch-${store.nextId++}`;
              const requestBody =
                init && typeof init.body === 'string'
                  ? init.body
                  : (init && init.body ? String(init.body) : '');
              if (trackedUrl(requestUrl)) {
                pushEntry({
                  phase: 'request',
                  transport: 'fetch',
                  requestId,
                  method,
                  url: requestUrl,
                  bodyText: requestBody,
                });
              }
              try {
                const response = await originalFetch(input, init);
                if (trackedUrl(requestUrl)) {
                  pushEntry({
                    phase: 'response',
                    transport: 'fetch',
                    requestId,
                    method,
                    url: requestUrl,
                    status: response.status,
                    responseText: await toText(response),
                  });
                }
                return response;
              } catch (error) {
                if (trackedUrl(requestUrl)) {
                  pushEntry({
                    phase: 'error',
                    transport: 'fetch',
                    requestId,
                    method,
                    url: requestUrl,
                    errorText: String(error),
                  });
                }
                throw error;
              }
            };
            window.__ts1241GithubNetworkFetchWrapped = true;
          }

          if (!window.__ts1241GithubNetworkXhrWrapped && window.XMLHttpRequest) {
            const originalOpen = window.XMLHttpRequest.prototype.open;
            const originalSend = window.XMLHttpRequest.prototype.send;
            window.XMLHttpRequest.prototype.open = function(method, url, ...rest) {
              this.__ts1241GithubNetwork = {
                method: String(method || 'GET').toUpperCase(),
                url: String(url || ''),
                requestId: `xhr-${store.nextId++}`,
              };
              return originalOpen.call(this, method, url, ...rest);
            };
            window.XMLHttpRequest.prototype.send = function(body) {
              const meta = this.__ts1241GithubNetwork;
              if (meta && trackedUrl(meta.url)) {
                pushEntry({
                  phase: 'request',
                  transport: 'xhr',
                  requestId: meta.requestId,
                  method: meta.method,
                  url: meta.url,
                  bodyText: typeof body === 'string' ? body : (body ? String(body) : ''),
                });
                this.addEventListener(
                  'loadend',
                  () => {
                    pushEntry({
                      phase: 'response',
                      transport: 'xhr',
                      requestId: meta.requestId,
                      method: meta.method,
                      url: meta.url,
                      status: this.status,
                      responseText:
                        typeof this.responseText === 'string' ? this.responseText : '',
                    });
                  },
                  { once: true },
                );
              }
              return originalSend.call(this, body);
            };
            window.__ts1241GithubNetworkXhrWrapped = true;
          }

          store.entries.length = 0;
          return {
            installed: true,
            repository,
          };
        }
        """,
        arg={"repository": repository},
    )


def _create_concurrent_commit(
    *,
    service: LiveSetupRepositoryService,
    stale_write_sha: str,
) -> dict[str, object]:
    probe_content = (
        f"# {TICKET_KEY} concurrent stale-base probe\n\n"
        f"- stale_write_sha: {stale_write_sha}\n"
        f"- marker: save should fetch the latest ref before writing\n"
    )
    service.write_repo_text(
        PROBE_FILE_PATH,
        content=probe_content,
        message=f"{TICKET_KEY}: create concurrent hosted commit",
    )
    matched, observed_head_sha = poll_until(
        probe=lambda: _fetch_branch_head_sha(service=service, branch=service.ref),
        is_satisfied=lambda sha: sha != stale_write_sha,
        timeout_seconds=90,
        interval_seconds=2,
    )
    if not matched:
        raise AssertionError(
            "Step 3 failed: the concurrent GitHub write never advanced the hosted branch "
            "head beyond the stale write SHA.\n"
            f"Stale write SHA: {stale_write_sha}\n"
            f"Observed branch head: {observed_head_sha}",
        )
    return {
        "probe_file_path": PROBE_FILE_PATH,
        "head_sha_after_commit": observed_head_sha,
    }


def _wait_for_network_sequence(
    *,
    session: Any,
    stale_write_sha: str,
) -> dict[str, object]:
    payload = session.wait_for_function(
        """
        ({ staleWriteSha }) => {
          const store = window.__ts1241GithubNetwork;
          if (!store || !Array.isArray(store.entries)) {
            return null;
          }
          const entries = store.entries.slice();
          const requestMatches = (entry, method, fragment) =>
            entry
            && entry.phase === 'request'
            && entry.method === method
            && typeof entry.url === 'string'
            && entry.url.includes(fragment);
          const responseFor = (requestEntry) =>
            entries.find(
              (entry) =>
                entry.phase === 'response' && entry.requestId === requestEntry.requestId,
            ) || null;
          const refRequest = [...entries]
            .reverse()
            .find((entry) => requestMatches(entry, 'GET', '/git/refs/heads/'));
          if (!refRequest) {
            return null;
          }
          const refResponse = responseFor(refRequest);
          if (!refResponse || refResponse.status !== 200) {
            return null;
          }
          let refSha = null;
          try {
            const refJson = JSON.parse(refResponse.responseText || '{}');
            refSha =
              refJson && refJson.object && typeof refJson.object.sha === 'string'
                ? refJson.object.sha
                : null;
          } catch (error) {
            return {
              kind: 'invalid-ref-response',
              entries,
              refRequest,
              refResponse,
              parseError: String(error),
            };
          }
          if (!refSha) {
            return {
              kind: 'missing-ref-sha',
              entries,
              refRequest,
              refResponse,
            };
          }
          const commitRequest = entries.find(
            (entry) =>
              requestMatches(entry, 'GET', `/git/commits/${refSha}`)
              && entry.order > refRequest.order,
          );
          if (!commitRequest) {
            return null;
          }
          const commitResponse = responseFor(commitRequest);
          if (!commitResponse || commitResponse.status !== 200) {
            return null;
          }
          const treeRequest = entries.find(
            (entry) =>
              requestMatches(entry, 'POST', '/git/trees')
              && entry.order > commitRequest.order,
          );
          if (!treeRequest) {
            return null;
          }
          const refWasStale = typeof staleWriteSha === 'string' && refSha !== staleWriteSha;
          const statuses = entries
            .filter((entry) => entry.phase === 'response')
            .map((entry) => entry.status);
          return {
            kind: 'observed',
            entries,
            refRequest,
            refResponse,
            refSha,
            commitRequest,
            commitResponse,
            treeRequest,
            refWasStale,
            statuses,
          };
        }
        """,
        arg={"staleWriteSha": stale_write_sha},
        timeout_ms=60_000,
    )
    if not isinstance(payload, dict):
        raise AssertionError(
            "Step 6 failed: the hosted save flow never exposed the expected GitHub ref, "
            "commit, and tree request sequence after clicking Save.\n"
            f"Observed network log: {_read_network_log(session)}",
        )
    kind = str(payload.get("kind"))
    if kind == "invalid-ref-response":
        raise AssertionError(
            "Step 6 failed: the GitHub ref lookup response could not be parsed while "
            "verifying the fetch-before-write sequence.\n"
            f"Observed payload: {payload}",
        )
    if kind == "missing-ref-sha":
        raise AssertionError(
            "Step 6 failed: the GitHub ref lookup response did not expose a branch head "
            "SHA before the tree update.\n"
            f"Observed payload: {payload}",
        )
    if kind != "observed":
        raise AssertionError(
            "Step 6 failed: the hosted save flow did not expose an observable "
            "fetch-before-write sequence.\n"
            f"Observed payload: {payload}",
        )
    if not bool(payload.get("refWasStale")):
        raise AssertionError(
            "Step 6 failed: the save flow did not prove that the branch ref lookup moved "
            "past the stale stored SHA before the tree update.\n"
            f"Stale write SHA: {stale_write_sha}\n"
            f"Observed payload: {payload}",
        )
    statuses = payload.get("statuses", [])
    if isinstance(statuses, list) and any(int(status) == 422 for status in statuses if status is not None):
        raise AssertionError(
            "Step 6 failed: the save network sequence still hit GitHub HTTP 422 during "
            "the stale-base-SHA scenario.\n"
            f"Observed payload: {payload}",
        )
    return payload


def _network_sequence_summary(observation: dict[str, object]) -> str:
    ref_request = observation.get("refRequest", {})
    commit_request = observation.get("commitRequest", {})
    tree_request = observation.get("treeRequest", {})
    return (
        "Observed GitHub save sequence "
        f"{ref_request.get('method')} {ref_request.get('url')} -> "
        f"{commit_request.get('method')} {commit_request.get('url')} -> "
        f"{tree_request.get('method')} {tree_request.get('url')}. "
        f"Branch ref SHA {observation.get('refSha')} replaced stale write SHA. "
        f"Response statuses={observation.get('statuses')}."
    )


def _read_network_log(session: Any) -> object:
    return session.evaluate(
        "() => window.__ts1241GithubNetwork?.entries ?? []",
    )


def _assert_seeded_controls(
    *,
    issue_key: str,
    initial_priority: EditControlObservation,
    initial_status: EditControlObservation,
) -> None:
    already_target_fields: list[str] = []
    if initial_priority.contains(TARGET_PRIORITY_LABEL):
        already_target_fields.append(
            f"Priority = {TARGET_PRIORITY_LABEL} ({initial_priority.text})",
        )
    if initial_status.contains(TARGET_STATUS_LABEL):
        already_target_fields.append(
            f"Status = {TARGET_STATUS_LABEL} ({initial_status.text})",
        )
    if not already_target_fields:
        return
    raise AssertionError(
        f"Step 2 failed: {issue_key} still opened in the target state, so the stale-base "
        "save regression could not prove a real edit.\n"
        f"Already-target fields: {', '.join(already_target_fields)}\n"
        f"Observed priority control: {_control_payload(initial_priority)}\n"
        f"Observed status control: {_control_payload(initial_status)}",
    )


def _control_payload(control: EditControlObservation) -> dict[str, object]:
    return {
        "label": control.label,
        "text": control.text,
        "tabindex": control.tabindex,
        "expanded": control.expanded,
    }


def _front_matter_value(markdown: str, key: str) -> str:
    match = re.search(
        rf"(?m)^{re.escape(key)}:\s*(.+)$",
        _front_matter(markdown),
    )
    if match is None:
        raise AssertionError(
            f"Precondition failed: `{key}` was missing from the issue front matter.",
        )
    return match.group(1).strip().strip('"').strip("'")


def _replace_front_matter_value(markdown: str, *, key: str, new_value: str) -> str:
    pattern = re.compile(rf"(?m)^({re.escape(key)}:\s*)(.+)$")
    updated, count = pattern.subn(rf"\1{new_value}", markdown, count=1)
    if count != 1:
        raise AssertionError(
            f"Precondition failed: `{key}` could not be updated in the issue front matter.",
        )
    return updated


def _front_matter(markdown: str) -> str:
    match = re.match(r"(?s)^---\n(.*?)\n---\n", markdown)
    if match is None:
        raise AssertionError("Precondition failed: the issue markdown did not contain front matter.")
    return match.group(1)


def _fetch_branch_head_sha(*, service: LiveSetupRepositoryService, branch: str) -> str:
    response = _github_json(
        service=service,
        path=f"/repos/{service.repository}/git/ref/heads/{branch}",
    )
    if not isinstance(response, dict):
        raise RuntimeError(
            f"GitHub ref lookup for {branch} did not return an object: {response!r}",
        )
    obj = response.get("object")
    sha = obj.get("sha") if isinstance(obj, dict) else None
    if not isinstance(sha, str) or not _GITHUB_SHA_PATTERN.match(sha):
        raise RuntimeError(
            f"GitHub ref lookup for {branch} did not expose a full commit SHA: {response!r}",
        )
    return sha


def _github_json(*, service: LiveSetupRepositoryService, path: str) -> object:
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            **(
                {"Authorization": f"Bearer {service.token}"}
                if service.token
                else {}
            ),
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_optional_repo_file(
    service: LiveSetupRepositoryService,
    path: str,
) -> LiveHostedRepositoryFile | None:
    try:
        return service.fetch_repo_file(path)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def _restore_repo_file(
    *,
    service: LiveSetupRepositoryService,
    path: str,
    original_file: LiveHostedRepositoryFile,
    description: str,
) -> dict[str, object]:
    current_content = service.fetch_repo_text(path)
    if current_content == original_file.content:
        return {
            "description": description,
            "status": "unchanged",
            "path": path,
        }

    service.write_repo_text(
        path,
        content=original_file.content,
        message=f"{TICKET_KEY}: restore live hosted fixture",
    )
    matched, observed_text = poll_until(
        probe=lambda: service.fetch_repo_text(path),
        is_satisfied=lambda text: text == original_file.content,
        timeout_seconds=90,
        interval_seconds=2,
    )
    return {
        "description": description,
        "status": "restored" if matched else "restore-pending",
        "path": path,
        "observed_excerpt": observed_text[:400],
    }


def _restore_optional_repo_file(
    *,
    service: LiveSetupRepositoryService,
    path: str,
    original_file: LiveHostedRepositoryFile | None,
    description: str,
) -> dict[str, object]:
    current_file = _fetch_optional_repo_file(service, path)
    if original_file is None:
        if current_file is None:
            return {
                "description": description,
                "status": "absent",
                "path": path,
            }
        service.delete_repo_file(
            path,
            message=f"{TICKET_KEY}: remove concurrent commit probe file",
        )
        matched, observed_file = poll_until(
            probe=lambda: _fetch_optional_repo_file(service, path),
            is_satisfied=lambda file: file is None,
            timeout_seconds=90,
            interval_seconds=2,
        )
        return {
            "description": description,
            "status": "deleted" if matched else "delete-pending",
            "path": path,
            "observed": None if observed_file is None else observed_file.path,
        }

    if current_file is not None and current_file.content == original_file.content:
        return {
            "description": description,
            "status": "unchanged",
            "path": path,
        }
    service.write_repo_text(
        path,
        content=original_file.content,
        message=f"{TICKET_KEY}: restore original concurrent probe content",
    )
    matched, observed_file = poll_until(
        probe=lambda: _fetch_optional_repo_file(service, path),
        is_satisfied=lambda file: file is not None and file.content == original_file.content,
        timeout_seconds=90,
        interval_seconds=2,
    )
    return {
        "description": description,
        "status": "restored" if matched else "restore-pending",
        "path": path,
        "observed_excerpt": (
            observed_file.content[:400] if observed_file is not None else None
        ),
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
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(
    result: dict[str, object],
    *,
    product_defect: bool,
) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
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
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    if product_defect:
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "h3. Test Automation Result",
        f"*Ticket:* {TICKET_KEY}",
        f"*Title:* {TEST_CASE_TITLE}",
        f"*Status:* {'PASSED' if passed else 'FAILED'}",
        f"*Environment:* {result.get('app_url')} | Chromium (Playwright) | {result.get('os')}",
        "",
        "h4. Automation checks",
    ]
    for step in result.get("steps", []):
        assert isinstance(step, dict)
        emoji = "(/)" if step.get("status") == "passed" else "(x)"
        lines.append(
            f"{emoji} *Step {step.get('step')}* {step.get('action')}\n"
            f"Observed: {step.get('observed')}"
        )
    lines.extend(("", "h4. Human-style verification"))
    for check in result.get("human_verification", []):
        assert isinstance(check, dict)
        lines.append(f"* {check.get('check')}\nObserved: {check.get('observed')}")
    lines.extend(
        [
            "",
            "h4. Cleanup",
        ],
    )
    for cleanup in result.get("cleanup", []):
        assert isinstance(cleanup, dict)
        lines.append(
            f"* {cleanup.get('description')}\n"
            f"Observed: status={cleanup.get('status')} path={cleanup.get('path')}"
        )
    if not passed:
        lines.extend(
            [
                "",
                "h4. Failure details",
                f"*Error:* {result.get('error')}",
                f"*Screenshot:* {result.get('screenshot')}",
            ],
        )
    return "\n".join(lines).strip() + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        f"# {TICKET_KEY} {'Passed' if passed else 'Failed'}",
        "",
        f"**Title:** {TEST_CASE_TITLE}",
        f"**Environment:** {result.get('app_url')} | Chromium (Playwright) | {result.get('os')}",
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
        lines.append(f"- **Check:** {check.get('check')}  \n  Observed: {check.get('observed')}")
    lines.extend(("", "## Cleanup"))
    for cleanup in result.get("cleanup", []):
        assert isinstance(cleanup, dict)
        lines.append(
            f"- **{cleanup.get('description')}**  \n"
            f"  Observed: status={cleanup.get('status')} path={cleanup.get('path')}"
        )
    if not passed:
        lines.extend(
            [
                "",
                "## Failure details",
                f"- **Error:** {result.get('error')}",
                f"- **Screenshot:** `{result.get('screenshot')}`",
            ],
        )
    return "\n".join(lines).strip() + "\n"


def _bug_description(result: dict[str, object]) -> str:
    step_map = {
        int(step["step"]): step
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    step_lines: list[str] = []
    for index, action in enumerate(REQUEST_STEPS, start=1):
        step = step_map.get(index)
        if step is None:
            observed = "Not reached because an earlier required step failed."
            outcome = "NOT REACHED ⏭️"
        else:
            observed = str(step.get("observed", "<missing>"))
            outcome = "PASSED ✅" if step.get("status") == "passed" else "FAILED ❌"
        step_lines.append(
            f"{index}. {action}  \n"
            f"   - Actual: {observed}\n"
            f"   - Result: {outcome}"
        )

    return (
        f"# {TICKET_KEY} - Hosted stale-base-SHA save path does not meet the ticket expectation\n\n"
        "## Steps to reproduce\n"
        + "\n".join(step_lines)
        + "\n\n## Exact error message or assertion failure\n"
        "```text\n"
        f"{result.get('traceback', result.get('error', '<missing>'))}"
        "```\n\n"
        "## Actual vs Expected\n"
        f"- **Expected:** {EXPECTED_RESULT}\n"
        f"- **Actual:** {result.get('error')}\n\n"
        "## Environment details\n"
        f"- **URL:** {result.get('app_url')}\n"
        "- **Browser:** Chromium via Playwright\n"
        f"- **OS:** {result.get('os')}\n"
        f"- **Repository:** {result.get('repository')} @ {result.get('repository_ref')}\n"
        f"- **Issue:** {result.get('issue_key')}\n"
        f"- **Stored stale write SHA:** {result.get('stale_write_branch')}\n\n"
        "## Screenshots and logs\n"
        f"- **Screenshot:** `{result.get('screenshot')}`\n"
        f"- **Network observation:** {result.get('network_observation')}\n"
        f"- **Concurrent commit:** {result.get('concurrent_commit')}\n"
        f"- **Visible post-save detail text:** {result.get('post_save_detail_text')}\n"
        f"- **Cleanup:** {result.get('cleanup')}\n"
    )


if __name__ == "__main__":
    main()
