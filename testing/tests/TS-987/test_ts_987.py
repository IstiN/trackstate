from __future__ import annotations

import json
import platform
import shutil
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherButtonStateObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherRowObservation,
)
from testing.components.pages.live_workspace_sync_page import (  # noqa: E402
    HeaderSyncStatusObservation,
    LiveWorkspaceSyncPage,
)
from testing.components.pages.trackstate_tracker_page import (  # noqa: E402
    StartupSurfaceObservation,
    TrackStateTrackerPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import WebAppTimeoutError  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-987"
TEST_CASE_TITLE = (
    "Workspace Switcher UI guard prioritizes recovery state after startup sync error"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-987/test_ts_987.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts987-mismatched-workspace"
LOCAL_DISPLAY_NAME = "Broken local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
LINKED_BUGS = ["TS-972"]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
EXPECTED_HEADER_ACCESSIBLE_LABEL = "Sync error, attention needed"
EXPECTED_HEADER_VISIBLE_LABEL = "Sync error, attention needed"
EXPECTED_SWITCHER_STATE = "Unavailable"
ACCEPTED_RECOVERY_ACTION_LABELS = ("Retry", "Re-authenticate")
DISALLOWED_ACTION_LABELS = ("Active",)
RECOVERY_ACTION_CALLBACK_WAIT_SECONDS = 20
REWORK_SUMMARY = (
    "Reused the live broken-local-workspace startup scenario from TS-964, then added "
    "the stricter UI-guard assertions TS-987 needs: the header must surface the exact "
    "sync error copy, and the Workspace switcher row must prioritize recovery over "
    "the persisted active state with a usable recovery action."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts987_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts987_failure.png"

REQUEST_STEPS = [
    "Launch the application.",
    "Observe the global sync status in the application header.",
    "Open the Workspace switcher component.",
    "Inspect the row corresponding to the broken local workspace.",
]
EXPECTED_RESULT = (
    "The global sync status reports 'Sync error, attention needed'. The Workspace "
    "switcher correctly renders the 'Unavailable' recovery state for the affected "
    "workspace, prioritising the error state over any persisted 'Active' status "
    "and displaying functional 'Retry' or 'Re-authenticate' actions."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)
    _cleanup_local_workspace()

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "linked_bugs": LINKED_BUGS,
        "steps": [],
        "human_verification": [],
    }
    page: LiveWorkspaceSwitcherPage | None = None

    try:
        config = load_live_setup_test_config()
        result["app_url"] = config.app_url

        service = LiveSetupRepositoryService(config=config)
        token = service.token
        if not token:
            raise RuntimeError(
                "TS-987 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        result["repository"] = service.repository
        result["repository_ref"] = service.ref

        workspace_state = _workspace_state(service.repository)
        result["preloaded_workspace_state"] = workspace_state

        runtime = StoredWorkspaceProfilesRuntime(
            repository=config.repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=(
                f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}",
            ),
        )
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            sync_page = LiveWorkspaceSyncPage(tracker_page)
            try:
                page.set_viewport(**DESKTOP_VIEWPORT)
                runtime_observation = tracker_page.open()
                page.set_viewport(**DESKTOP_VIEWPORT)
                result["runtime_state"] = runtime_observation.kind
                result["runtime_body_text"] = runtime_observation.body_text

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed app in a fresh Chromium session with a saved "
                        "active broken local workspace plus one hosted fallback workspace "
                        "preloaded in browser storage."
                    ),
                )

                shell_observation = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                )
                result["shell_observation"] = shell_observation
                startup_observation = _startup_surface_payload(
                    tracker_page.observe_startup_surface(),
                )
                result["startup_observation"] = startup_observation

                if runtime_observation.kind != "ready" or not bool(
                    shell_observation.get("shell_ready"),
                ):
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The application never reached the interactive shell state needed "
                            "to inspect the header sync status.\n"
                            f"runtime_state={runtime_observation.kind!r}\n"
                            f"shell_observation={json.dumps(shell_observation, indent=2)}\n"
                            f"startup_observation={json.dumps(startup_observation, indent=2)}"
                        ),
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "Not reached because startup did not leave the blocking surface and "
                            "never exposed the interactive header."
                        ),
                    )
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "Not reached because Workspace switcher could not be opened without "
                            "the interactive shell."
                        ),
                    )
                    raise AssertionError(
                        "Step 2 failed: the deployed app did not reach the interactive shell "
                        "needed for the header and Workspace switcher checks.\n"
                        f"runtime_state={runtime_observation.kind!r}\n"
                        f"shell_observation={json.dumps(shell_observation, indent=2)}\n"
                        f"startup_observation={json.dumps(startup_observation, indent=2)}"
                    )

                page.dismiss_connection_banner()

                failures: list[str] = []
                header_status = _observe_header_status(sync_page)
                result["header_status"] = _header_status_payload(header_status)
                if header_status is None:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The header never exposed the sync error status within the wait "
                            "window after the startup mismatch.\n"
                            f"startup_observation={json.dumps(startup_observation, indent=2)}\n"
                            f"shell_observation={json.dumps(shell_observation, indent=2)}"
                        ),
                    )
                    failures.append(
                        "Step 2 failed: the header never exposed the sync error status "
                        f"{EXPECTED_HEADER_ACCESSIBLE_LABEL!r}."
                    )
                else:
                    try:
                        _assert_header_status(header_status)
                    except AssertionError as error:
                        _record_step(
                            result,
                            step=2,
                            status="failed",
                            action=REQUEST_STEPS[1],
                            observed=(
                                "The header sync status remained readable, but it did not match "
                                "the recovery-prioritized sync error copy required by the "
                                "ticket.\n"
                                f"header_status={json.dumps(_header_status_payload(header_status), indent=2)}\n"
                                f"shell_observation={json.dumps(shell_observation, indent=2)}\n"
                                f"error={error}"
                            ),
                        )
                        failures.append(str(error))
                    else:
                        _record_step(
                            result,
                            step=2,
                            status="passed",
                            action=REQUEST_STEPS[1],
                            observed=(
                                "The application header exposed the expected sync error state "
                                "after startup mismatch recovery settled.\n"
                                f"header_status={json.dumps(_header_status_payload(header_status), indent=2)}"
                            ),
                        )
                        _record_human_verification(
                            result,
                            check=(
                                "Viewed the top bar exactly as a user would after startup and "
                                "checked the visible sync badge plus its accessible label."
                            ),
                            observed=(
                                f"visible_label={header_status.visible_label!r}; "
                                f"accessible_label={header_status.accessible_label!r}"
                            ),
                        )

                switcher: WorkspaceSwitcherObservation | None = None
                try:
                    switcher = page.open_and_observe(timeout_ms=30_000)
                except AssertionError as error:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "The interactive shell rendered, but Workspace switcher did not "
                            "open into a stable panel.\n"
                            f"error={error}\n"
                            f"shell_observation={json.dumps(shell_observation, indent=2)}"
                        ),
                    )
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "Not reached because Workspace switcher never opened into a stable "
                            "panel."
                        ),
                    )
                    failures.append(
                        "Step 3 failed: Workspace switcher did not open into a stable panel."
                    )
                else:
                    result["switcher_observation"] = _switcher_payload(switcher)
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "Opened Workspace switcher from the application header.\n"
                            f"switcher={json.dumps(result['switcher_observation'], indent=2)}"
                        ),
                    )

                if switcher is not None:
                    candidate_local_row = _find_seeded_local_row(switcher)
                    result["local_row"] = _row_payload(candidate_local_row)
                    try:
                        local_row = page.observe_saved_workspace_row(
                            display_name=LOCAL_DISPLAY_NAME,
                            target_path=LOCAL_TARGET,
                            target_type_label="Local",
                            expected_state_label=EXPECTED_SWITCHER_STATE,
                            accepted_action_labels=ACCEPTED_RECOVERY_ACTION_LABELS,
                            disallowed_action_labels=DISALLOWED_ACTION_LABELS,
                            timeout_ms=30_000,
                        )
                        result["local_row"] = _row_payload(local_row)
                        _assert_switcher_row(local_row)
                        recovery_action_label = _recovery_action_button_label(local_row)
                        result["recovery_action_label"] = recovery_action_label
                        recovery_button_state = _observe_recovery_action_button_state(
                            tracker_page,
                            action_label=recovery_action_label,
                            local_row=local_row,
                        )
                        result["recovery_action_button_state"] = _button_state_payload(
                            recovery_button_state,
                        )
                        _install_recovery_action_probe(tracker_page)
                        result["recovery_action_probe_before"] = _read_recovery_action_probe(
                            tracker_page,
                        )
                        page.click_saved_workspace_action_button(
                            recovery_action_label,
                            timeout_ms=10_000,
                        )
                        callback_observed, callback_observation = poll_until(
                            probe=lambda: _observe_recovery_action_callback(tracker_page),
                            is_satisfied=lambda observation: observation[
                                "browser_access_callback_observed"
                            ],
                            timeout_seconds=RECOVERY_ACTION_CALLBACK_WAIT_SECONDS,
                            interval_seconds=1,
                        )
                        result["recovery_action_callback_observation"] = callback_observation
                        result["recovery_action_probe_after"] = callback_observation["probe"]
                        _assert_recovery_action_usable(
                            button_state=recovery_button_state,
                            action_label=recovery_action_label,
                            callback_observed=callback_observed,
                            callback_observation=callback_observation,
                        )
                    except AssertionError as error:
                        _record_step(
                            result,
                            step=4,
                            status="failed",
                            action=REQUEST_STEPS[3],
                            observed=(
                                "Workspace switcher opened, but the broken local workspace row "
                                "did not prioritize the recovery state over the persisted "
                                "active state.\n"
                                f"switcher={json.dumps(result['switcher_observation'], indent=2)}\n"
                                f"local_row={json.dumps(result.get('local_row'), indent=2)}\n"
                                f"error={error}"
                            ),
                        )
                        _record_human_verification(
                            result,
                            check=(
                                "Opened Workspace switcher and visually inspected the broken "
                                "local workspace row exactly as a user would."
                            ),
                            observed=(
                                f"switcher_text={switcher.switcher_text!r}; "
                                f"local_row={json.dumps(result.get('local_row'), ensure_ascii=True)}"
                            ),
                        )
                        failures.append(str(error))
                    else:
                        _record_step(
                            result,
                            step=4,
                            status="passed",
                            action=REQUEST_STEPS[3],
                            observed=(
                                "The broken local workspace row rendered in the recovery state "
                                "instead of preserving the persisted active state, and its "
                                "visible recovery action remained usable.\n"
                                f"local_row={json.dumps(result['local_row'], indent=2)}\n"
                                f"recovery_action_label={result.get('recovery_action_label')!r}\n"
                                "recovery_action_button_state="
                                f"{json.dumps(result.get('recovery_action_button_state'), indent=2)}\n"
                                "recovery_action_probe_after="
                                f"{json.dumps(result.get('recovery_action_probe_after'), indent=2)}"
                            ),
                        )
                        _record_human_verification(
                            result,
                            check=(
                                "Opened Workspace switcher and visually verified the broken "
                                "workspace row text, state badge, and usable recovery action."
                            ),
                            observed=(
                                f"visible_text={local_row.visible_text!r}; "
                                f"state_label={local_row.state_label!r}; "
                                f"action_labels={json.dumps(list(local_row.action_labels), ensure_ascii=True)}; "
                                f"recovery_action_label={result.get('recovery_action_label')!r}"
                            ),
                        )

                if failures:
                    raise AssertionError("\n".join(failures))
            except Exception as error:
                try:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                except Exception as screenshot_error:
                    result["screenshot_error"] = (
                        f"{type(screenshot_error).__name__}: {screenshot_error}"
                    )
                raise error

            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _workspace_state(repository: str) -> dict[str, object]:
    local_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
    hosted_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": local_id,
        "migrationComplete": True,
        "unavailableLocalWorkspaceIds": [],
        "profiles": [
            {
                "id": local_id,
                "displayName": LOCAL_DISPLAY_NAME,
                "customDisplayName": LOCAL_DISPLAY_NAME,
                "targetType": "local",
                "target": LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-22T23:55:00.000Z",
            },
        ],
    }


def _cleanup_local_workspace() -> None:
    shutil.rmtree(LOCAL_TARGET, ignore_errors=True)


def _observe_header_status(
    page: LiveWorkspaceSyncPage,
) -> HeaderSyncStatusObservation | None:
    def _probe() -> HeaderSyncStatusObservation | None:
        try:
            return page.observe_header_status(timeout_ms=5_000)
        except (AssertionError, WebAppTimeoutError):
            return None

    ready, observation = poll_until(
        probe=_probe,
        is_satisfied=lambda current: (
            current is not None
            and
            current.accessible_label == EXPECTED_HEADER_ACCESSIBLE_LABEL
            and current.visible_label in {
                EXPECTED_HEADER_ACCESSIBLE_LABEL,
                EXPECTED_HEADER_VISIBLE_LABEL,
            }
        ),
        timeout_seconds=120,
        interval_seconds=2,
    )
    return observation if ready else None


def _assert_header_status(observation: HeaderSyncStatusObservation) -> None:
    errors: list[str] = []
    if observation.accessible_label != EXPECTED_HEADER_ACCESSIBLE_LABEL:
        errors.append(
            "the header sync status accessible label was "
            f"{observation.accessible_label!r} instead of {EXPECTED_HEADER_ACCESSIBLE_LABEL!r}"
        )
    if observation.visible_label not in {
        EXPECTED_HEADER_VISIBLE_LABEL,
        EXPECTED_HEADER_ACCESSIBLE_LABEL,
    }:
        errors.append(
            "the visible header sync status text was "
            f"{observation.visible_label!r} instead of {EXPECTED_HEADER_VISIBLE_LABEL!r}"
        )
    if errors:
        raise AssertionError(
            "Step 2 failed: " + "; ".join(errors) + "."
        )


def _assert_switcher_row(local_row: WorkspaceSwitcherRowObservation) -> None:
    errors: list[str] = []
    if local_row.display_name != LOCAL_DISPLAY_NAME or LOCAL_TARGET not in local_row.detail_text:
        errors.append(
            "the broken local workspace row did not match the seeded workspace identity"
        )
    if local_row.state_label != EXPECTED_SWITCHER_STATE:
        errors.append(
            "the broken local workspace row state was "
            f"{local_row.state_label!r} instead of {EXPECTED_SWITCHER_STATE!r}"
        )
    if local_row.selected or "Active" in local_row.visible_text:
        errors.append(
            "the broken local workspace row still appeared selected as Active"
        )
    if "Active" in local_row.action_labels:
        errors.append(
            "the broken local workspace row still exposed the persisted Active action"
        )
    if not any(
        label in ACCEPTED_RECOVERY_ACTION_LABELS for label in local_row.action_labels
    ):
        errors.append(
            "the broken local workspace row did not expose Retry or Re-authenticate"
        )
    if errors:
        raise AssertionError(
            "Step 4 failed: " + "; ".join(errors) + "."
        )


def _recovery_action_button_label(local_row: WorkspaceSwitcherRowObservation) -> str:
    for label in local_row.button_labels:
        if any(label.startswith(f"{action}:") for action in ACCEPTED_RECOVERY_ACTION_LABELS):
            return label
    for label in local_row.action_labels:
        if label in ACCEPTED_RECOVERY_ACTION_LABELS:
            return label
    raise AssertionError(
        "Step 4 failed: the broken local workspace row did not expose a recovery "
        "button label that could be clicked."
    )


def _observe_recovery_action_button_state(
    tracker_page: TrackStateTrackerPage,
    *,
    action_label: str,
    local_row: WorkspaceSwitcherRowObservation,
) -> WorkspaceSwitcherButtonStateObservation:
    payload = tracker_page.session.evaluate(
        """
        ({ actionLabel, displayName, acceptedActionLabels }) => {
          const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
          const isVisible = (element) => {
            if (!element) {
              return false;
            }
            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            return rect.width > 0
              && rect.height > 0
              && style.visibility !== 'hidden'
              && style.display !== 'none';
          };
          const labelFor = (element) =>
            normalize(
              element?.getAttribute?.('aria-label')
              || element?.getAttribute?.('title')
              || element?.innerText
              || element?.textContent
              || '',
            );
          const visibleText = (element) =>
            normalize(element?.innerText || element?.textContent || '');
          const matchesAcceptedAction = (value) =>
            acceptedActionLabels.includes(value.split(':', 1)[0].trim());
          const candidates = Array.from(
            document.querySelectorAll('button,[role="button"],flt-semantics[role="button"]'),
          ).filter((element) => isVisible(element));
          const candidate = candidates.find((element) => {
            const elementLabel = labelFor(element);
            const elementText = visibleText(element);
            const combined = normalize(`${elementLabel} ${elementText}`);
            return elementLabel === actionLabel
              || elementText === actionLabel
              || (
                matchesAcceptedAction(elementLabel)
                && combined.includes(displayName)
              );
          });
          if (!candidate) {
            return null;
          }
          const tabindex = candidate.getAttribute('tabindex');
          const tabIndexValue = Number.isFinite(candidate.tabIndex)
            ? candidate.tabIndex
            : -1;
          const ariaDisabled = normalize(candidate.getAttribute('aria-disabled'));
          const disabled =
            typeof candidate.disabled === 'boolean'
              ? candidate.disabled
              : candidate.hasAttribute('disabled');
          const active = document.activeElement instanceof Element
            ? document.activeElement
            : null;
          return {
            label: labelFor(candidate),
            visibleText: visibleText(candidate),
            role: candidate.getAttribute('role'),
            tagName: candidate.tagName,
            tabindex,
            tabIndexValue,
            ariaDisabled: ariaDisabled.length > 0 ? ariaDisabled : null,
            disabled,
            keyboardFocusable: tabIndexValue >= 0,
            activeWithin: Boolean(active && (active === candidate || candidate.contains(active))),
            outerHTML: candidate.outerHTML,
          };
        }
        """,
        arg={
            "actionLabel": action_label,
            "displayName": local_row.display_name or LOCAL_DISPLAY_NAME,
            "acceptedActionLabels": list(ACCEPTED_RECOVERY_ACTION_LABELS),
        },
    )
    if not isinstance(payload, dict):
        raise AssertionError(
            "Step 4 failed: the open Workspace switcher did not expose a visible recovery "
            f"button matching {action_label!r}.\n"
            f"Observed body text:\n{tracker_page.session.evaluate('() => document.body?.innerText || \"\"')}"
        )
    return WorkspaceSwitcherButtonStateObservation(
        label=str(payload.get("label", action_label)),
        visible_text=str(payload.get("visibleText", "")),
        role=str(payload.get("role")) if payload.get("role") is not None else None,
        tag_name=str(payload.get("tagName", "")),
        tabindex=(
            str(payload.get("tabindex"))
            if payload.get("tabindex") is not None
            else None
        ),
        tab_index_value=int(payload.get("tabIndexValue", -1)),
        aria_disabled=(
            None if payload.get("ariaDisabled") is None else str(payload.get("ariaDisabled"))
        ),
        disabled=bool(payload.get("disabled")),
        keyboard_focusable=bool(payload.get("keyboardFocusable")),
        active_within=bool(payload.get("activeWithin")),
        outer_html=str(payload.get("outerHTML", "")),
    )


def _install_recovery_action_probe(tracker_page: TrackStateTrackerPage) -> None:
    tracker_page.session.evaluate(
        """
        () => {
          if (window.__ts987RecoveryActionProbeInstalled) {
            return;
          }
          const state = window.__ts987RecoveryActionProbe = window.__ts987RecoveryActionProbe || {
            showDirectoryPickerCalls: [],
            requestPermissionCalls: [],
            installErrors: [],
          };
          const normalizeArgs = (args) => {
            try {
              return JSON.parse(JSON.stringify(args));
            } catch (_) {
              return Array.from(args, (value) => String(value));
            }
          };
          try {
            const fileSystemHandleProto = globalThis.FileSystemHandle?.prototype;
            if (fileSystemHandleProto && typeof fileSystemHandleProto.requestPermission === 'function') {
              fileSystemHandleProto.requestPermission = async function(...args) {
                state.requestPermissionCalls.push({
                  callNumber: state.requestPermissionCalls.length + 1,
                  args: normalizeArgs(args),
                });
                return 'denied';
              };
            }
            if (typeof globalThis.showDirectoryPicker === 'function') {
              globalThis.showDirectoryPicker = async (...args) => {
                state.showDirectoryPickerCalls.push({
                  callNumber: state.showDirectoryPickerCalls.length + 1,
                  args: normalizeArgs(args),
                });
                throw new DOMException('The user aborted a request.', 'AbortError');
              };
            }
          } catch (error) {
            state.installErrors.push(String(error));
          }
          window.__ts987RecoveryActionProbeInstalled = true;
        }
        """,
    )


def _read_recovery_action_probe(tracker_page: TrackStateTrackerPage) -> dict[str, object]:
    payload = tracker_page.session.evaluate(
        """
        () => {
          const probe = window.__ts987RecoveryActionProbe || {};
          return {
            showDirectoryPickerCalls: Array.isArray(probe.showDirectoryPickerCalls)
              ? probe.showDirectoryPickerCalls
              : [],
            requestPermissionCalls: Array.isArray(probe.requestPermissionCalls)
              ? probe.requestPermissionCalls
              : [],
            installErrors: Array.isArray(probe.installErrors)
              ? probe.installErrors
              : [],
          };
        }
        """,
    )
    if not isinstance(payload, dict):
        return {
            "showDirectoryPickerCalls": [],
            "requestPermissionCalls": [],
            "installErrors": ["Recovery-action probe payload was not a dict."],
        }
    return {
        "showDirectoryPickerCalls": list(payload.get("showDirectoryPickerCalls", [])),
        "requestPermissionCalls": list(payload.get("requestPermissionCalls", [])),
        "installErrors": list(payload.get("installErrors", [])),
    }


def _observe_recovery_action_callback(
    tracker_page: TrackStateTrackerPage,
) -> dict[str, object]:
    probe = _read_recovery_action_probe(tracker_page)
    return {
        "probe": probe,
        "browser_access_callback_observed": bool(
            probe["showDirectoryPickerCalls"] or probe["requestPermissionCalls"]
        ),
    }


def _assert_recovery_action_usable(
    *,
    button_state: WorkspaceSwitcherButtonStateObservation,
    action_label: str,
    callback_observed: bool,
    callback_observation: dict[str, object],
) -> None:
    errors: list[str] = []
    if button_state.disabled or button_state.aria_disabled == "true":
        errors.append(
            f"the recovery action {action_label!r} was rendered disabled"
        )
    if not button_state.keyboard_focusable:
        errors.append(
            f"the recovery action {action_label!r} was not keyboard focusable"
        )
    if not callback_observed:
        errors.append(
            "clicking the recovery action did not trigger any browser recovery flow "
            "(`showDirectoryPicker()` or `requestPermission()`).\n"
            f"callback_observation={json.dumps(callback_observation, indent=2)}"
        )
    if errors:
        raise AssertionError("Step 4 failed: " + "; ".join(errors) + ".")


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    if not isinstance(steps, list):
        raise TypeError("result['steps'] must be a list")
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
    lines = result.setdefault("human_verification", [])
    if not isinstance(lines, list):
        raise TypeError("result['human_verification'] must be a list")
    lines.append(
        {
            "check": check,
            "observed": observed,
        },
    )


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
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
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
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")


def _build_jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Environment*: URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport*: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        "",
        "h4. What was automated",
        "* Preloaded the broken saved local workspace as the active startup target, plus one hosted fallback workspace, in browser storage.",
        "* Opened the deployed app and waited for startup mismatch handling to settle in the interactive shell.",
        "* Verified the application header sync status exposed the sync-error recovery state instead of a healthy or generic state.",
        "* Opened Workspace switcher and checked that the seeded broken local workspace row prioritized the Unavailable recovery state over any persisted Active status.",
        "",
        "h4. Automation checks",
        *_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Expected result",
        EXPECTED_RESULT,
        "",
        "h4. Actual result",
        _actual_result_summary(result, passed=passed),
    ]
    if result.get("screenshot"):
        lines.extend(["", f"*Screenshot*: {result['screenshot']}"])
    if not passed:
        lines.extend(
            [
                "",
                "h4. Assertion / error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_pr_body(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        f"## {TICKET_KEY} passed" if passed else f"## {TICKET_KEY} failed",
        "",
        "## Rework summary",
        f"- {REWORK_SUMMARY}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## What was automated",
        "- Preloaded the broken local workspace as the active startup target plus a hosted fallback workspace.",
        "- Verified the deployed app reached the interactive shell instead of stalling before the header rendered.",
        "- Checked the header sync status for the exact recovery-oriented sync error label.",
        "- Opened Workspace switcher and required the broken local workspace row to render `Unavailable` with a recovery action instead of preserving `Active`.",
        "",
        "## Automation checks",
        *_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *_human_lines(result, jira=False),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Actual result",
        _actual_result_summary(result, passed=passed),
    ]
    if result.get("screenshot"):
        lines.extend(["", f"**Screenshot:** `{result['screenshot']}`"])
    if not passed:
        lines.extend(
            [
                "",
                "## Assertion / error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_response_summary(result: dict[str, object], *, passed: bool) -> str:
    if passed:
        return (
            f"{TICKET_KEY} passed.\n\n"
            f"{REWORK_SUMMARY}\n\n"
            "The deployed app surfaced the sync error in the header and rendered the "
            "broken local workspace as Unavailable with recovery actions instead of "
            "preserving the persisted Active state.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The deployed app did not prioritize the recovery state in the header or Workspace switcher.')}\n"
    )


def _build_bug_description(result: dict[str, object]) -> str:
    annotated_steps: list[str] = []
    steps = result.get("steps", [])
    for index, action in enumerate(REQUEST_STEPS, start=1):
        matching = next(
            (
                step
                for step in steps
                if isinstance(step, dict) and int(step.get("step", -1)) == index
            ),
            None,
        )
        if matching is None:
            annotated_steps.append(f"{index}. ⏭️ {action} Not reached.")
            continue
        icon = "✅" if str(matching.get("status")) == "passed" else "❌"
        annotated_steps.append(
            f"{index}. {icon} {action} Observed: {matching.get('observed', '')}"
        )

    lines = [
        f"# {TICKET_KEY} bug report",
        "",
        "## Steps to reproduce",
        *annotated_steps,
        "",
        "## Exact error message or assertion failure",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Actual vs Expected",
        f"- **Expected:** {EXPECTED_RESULT}",
        (
            "- **Actual:** The deployed app starts, but either the header never exposes "
            f"`{EXPECTED_HEADER_ACCESSIBLE_LABEL}` or the broken local workspace row stays "
            "Active / Local Git instead of being rendered as Unavailable with Retry or "
            "Re-authenticate."
        ),
        "",
        "## Exact missing/broken production capability",
        (
            "- The Workspace switcher recovery guard does not fully prioritize the live "
            "startup sync error over the persisted active local-workspace state. Users do "
            "not get the expected recovery-first status in the header and/or the saved "
            "workspace row still behaves like the active workspace instead of surfacing "
            "manual recovery actions."
        ),
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"- Run command: `{RUN_COMMAND}`",
        "",
        "## Failing command",
        f"- `{RUN_COMMAND}`",
        "",
        "## Observed state",
        f"- Startup observation: `{json.dumps(result.get('startup_observation'), ensure_ascii=True)}`",
        f"- Shell observation: `{json.dumps(result.get('shell_observation'), ensure_ascii=True)}`",
        f"- Header status: `{json.dumps(result.get('header_status'), ensure_ascii=True)}`",
        f"- Switcher observation: `{json.dumps(result.get('switcher_observation'), ensure_ascii=True)}`",
        f"- Broken local row: `{json.dumps(result.get('local_row'), ensure_ascii=True)}`",
    ]
    if result.get("screenshot"):
        lines.extend(["", "## Screenshots or logs", f"- Screenshot: `{result['screenshot']}`"])
    return "\n".join(lines) + "\n"


def _find_seeded_local_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    for row in switcher.rows:
        if (
            row.display_name == LOCAL_DISPLAY_NAME
            and row.target_type_label == "Local"
            and LOCAL_TARGET in row.detail_text
        ):
            return row
    return None


def _actual_result_summary(result: dict[str, object], *, passed: bool) -> str:
    if passed:
        return (
            "Startup reached the interactive shell, the header sync status exposed "
            f"`{EXPECTED_HEADER_ACCESSIBLE_LABEL}`, and Workspace switcher rendered the "
            "broken local workspace as Unavailable with recovery actions instead of "
            "preserving Active."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not prioritize the recovery state in the header or Workspace switcher.",
        ),
    )


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return []
    lines: list[str] = []
    for item in steps:
        if not isinstance(item, dict):
            continue
        icon = "✅" if item.get("status") == "passed" else "❌"
        prefix = "#" if jira else "-"
        lines.append(
            f"{prefix} {icon} Step {item.get('step')}: {item.get('action')} "
            f"Observed: {item.get('observed')}"
        )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    checks = result.get("human_verification", [])
    if not isinstance(checks, list):
        return []
    prefix = "#" if jira else "-"
    lines: list[str] = []
    for item in checks:
        if not isinstance(item, dict):
            continue
        lines.append(
            f"{prefix} {item.get('check')} Observed: {item.get('observed')}"
        )
    return lines


def _startup_surface_payload(observation: StartupSurfaceObservation) -> dict[str, object]:
    return {
        "title": observation.title,
        "location_href": observation.location_href,
        "location_hash": observation.location_hash,
        "location_pathname": observation.location_pathname,
        "body_text": observation.body_text,
        "button_labels": list(observation.button_labels),
    }


def _header_status_payload(
    observation: HeaderSyncStatusObservation | None,
) -> dict[str, object] | None:
    if observation is None:
        return None
    return {
        "body_text": observation.body_text,
        "accessible_label": observation.accessible_label,
        "visible_label": observation.visible_label,
    }


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [_row_payload(row) for row in switcher.rows],
    }


def _row_payload(row: WorkspaceSwitcherRowObservation | None) -> dict[str, object] | None:
    if row is None:
        return None
    return {
        "display_name": row.display_name,
        "target_type_label": row.target_type_label,
        "state_label": row.state_label,
        "detail_text": row.detail_text,
        "visible_text": row.visible_text,
        "selected": row.selected,
        "semantics_label": row.semantics_label,
        "icon_accessibility_label": row.icon_accessibility_label,
        "action_labels": list(row.action_labels),
        "button_labels": list(row.button_labels),
    }


def _button_state_payload(
    button_state: WorkspaceSwitcherButtonStateObservation | None,
) -> dict[str, object] | None:
    if button_state is None:
        return None
    return {
        "label": button_state.label,
        "visible_text": button_state.visible_text,
        "role": button_state.role,
        "tag_name": button_state.tag_name,
        "tabindex": button_state.tabindex,
        "tab_index_value": button_state.tab_index_value,
        "aria_disabled": button_state.aria_disabled,
        "disabled": button_state.disabled,
        "keyboard_focusable": button_state.keyboard_focusable,
        "active_within": button_state.active_within,
        "outer_html": button_state.outer_html,
    }


if __name__ == "__main__":
    main()
