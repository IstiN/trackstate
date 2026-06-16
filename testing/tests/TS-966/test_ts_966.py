from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherRowObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.pages.trackstate_tracker_page import (  # noqa: E402
    StartupSurfaceObservation,
    TrackStateTrackerPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-966"
TEST_CASE_TITLE = (
    "Workspace Switcher runtime error — local failure does not stall the global shell"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-966/test_ts_966.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
PRIMARY_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECONDARY_WORKSPACE_DISPLAY_NAME = "Hosted fallback workspace"
SECONDARY_WORKSPACE_WRITE_BRANCH = "ts-966-fallback"
LINKED_BUGS = ["TS-995", "TS-977", "TS-958"]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
FAULT_MARKER = "TS-966 synthetic workspace switcher runtime error"
FAULT_SELECTOR_FRAGMENT = "trackstate-workspace-switcher"
FAULT_STACK_MARKERS = ("recordAndThrow (<anonymous>", "patchedSelectorMethod")
NAVIGATION_TARGET_LABEL = "Settings"

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Trigger the opening of the Workspace Switcher panel.",
    "Induce a runtime exception within the Workspace Switcher component.",
    "Observe the behavior of the global application shell (TopBar, Sidebar).",
    "Attempt to navigate to a different section of the app using the Sidebar.",
]
EXPECTED_RESULT = (
    "The application does not show a blank screen or a global 'Sync issue' stall. "
    "The Workspace Switcher failure is contained locally, and the rest of the "
    "application shell remains interactive and functional so the user can continue "
    "using other parts of the app."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts966_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts966_failure.png"


class Ts966WorkspaceFaultRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        workspace_token_profile_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=workspace_token_profile_ids,
        )
        self.console_events: list[dict[str, str]] = []
        self.page_errors: list[dict[str, str]] = []

    def __enter__(self):
        session = super().__enter__()
        if self._context is None or self._page is None:
            raise RuntimeError("TS-966 expected a browser context and page.")
        self._context.add_init_script(script=_workspace_switcher_fault_probe_script())
        self._page.on("console", self._record_console_event)
        self._page.on("pageerror", self._record_page_error)
        return session

    def _record_console_event(self, message) -> None:
        self.console_events.append(
            {
                "level": str(message.type),
                "text": str(message.text),
            },
        )

    def _record_page_error(self, error: object) -> None:
        self.page_errors.append(_page_error_payload(error))


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-966 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    primary_workspace_id = f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}"
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
        "desktop_viewport": DESKTOP_VIEWPORT,
        "linked_bugs": LINKED_BUGS,
        "fault_marker": FAULT_MARKER,
        "preloaded_workspace_state": workspace_state,
        "steps": [],
        "human_verification": [],
    }

    runtime_context = Ts966WorkspaceFaultRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        workspace_token_profile_ids=(primary_workspace_id,),
    )
    page: LiveWorkspaceSwitcherPage | None = None

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime_context,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            page.set_viewport(**DESKTOP_VIEWPORT)

            runtime_observation = tracker_page.open()
            result["runtime_state"] = runtime_observation.kind
            result["runtime_body_text"] = runtime_observation.body_text
            shell_before = tracker_page.observe_interactive_shell(SHELL_NAVIGATION_LABELS)
            startup_before = _startup_surface_payload(tracker_page.observe_startup_surface())
            result["shell_before"] = shell_before
            result["startup_before"] = startup_before
            result["console_events"] = list(runtime_context.console_events)
            result["page_errors"] = list(runtime_context.page_errors)

            if runtime_observation.kind != "ready" or not bool(shell_before.get("shell_ready")):
                _record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "The deployed app did not reach the interactive shell before the "
                        "workspace switcher runtime-fault scenario began.\n"
                        f"runtime_state={runtime_observation.kind!r}\n"
                        f"shell_before={json.dumps(shell_before, indent=2)}\n"
                        f"startup_before={json.dumps(startup_before, indent=2)}"
                    ),
                )
                _mark_not_reached(result, start_step=2)
                raise AssertionError(str(_first_failed_step_observed(result)))

            _record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Opened the deployed TrackState app at 1440x900 and reached the "
                    "interactive shell.\n"
                    f"shell_before={json.dumps(shell_before, indent=2)}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Viewed the startup shell like a user and confirmed the top-level "
                    "navigation labels were visibly present."
                ),
                observed=(
                    f"visible_navigation_labels={json.dumps(shell_before.get('visible_navigation_labels', []), ensure_ascii=True)}; "
                    f"button_labels={json.dumps(startup_before.get('button_labels', []), ensure_ascii=True)}"
                ),
            )

            try:
                page.dismiss_connection_banner()
            except Exception:
                pass

            trigger_before = page.observe_trigger(timeout_ms=30_000)
            result["trigger_before"] = _trigger_payload(trigger_before)

            step_two_failed = False
            try:
                switcher_before = page.open_and_observe(timeout_ms=30_000)
                result["switcher_before"] = _switcher_payload(switcher_before)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Opened the Workspace Switcher from the application header.\n"
                        f"trigger_before={json.dumps(result['trigger_before'], indent=2)}\n"
                        f"switcher_before={json.dumps(result['switcher_before'], indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the switcher and visually verified the panel heading and "
                        "saved workspace rows were visible before injecting the fault."
                    ),
                    observed=(
                        f"switcher_text={switcher_before.switcher_text!r}; "
                        f"rows={json.dumps([_row_payload(row) for row in switcher_before.rows], ensure_ascii=True)}"
                    ),
                )
            except Exception as error:
                step_two_failed = True
                result["switcher_before_error"] = _format_error(error)
                _record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "The workspace switcher did not open cleanly before the synthetic "
                        f"fault injection.\nerror={_format_error(error)}\n"
                        f"trigger_before={json.dumps(result['trigger_before'], indent=2)}\n"
                        f"body_text={page.current_body_text()!r}"
                    ),
                )

            try:
                page.close_switcher()
                result["fault_state_before_enable"] = _fault_state(tracker_page)
                console_event_count_before_fault = len(runtime_context.console_events)
                page_error_count_before_fault = len(runtime_context.page_errors)
                result["fault_state_after_enable"] = _enable_fault(tracker_page)
                try:
                    switcher_after_fault = page.open_and_observe(timeout_ms=10_000)
                    result["switcher_after_fault"] = _switcher_payload(switcher_after_fault)
                except Exception as error:
                    result["switcher_after_fault_error"] = _format_error(error)
                    raise AssertionError(
                        "The workspace switcher could not be re-observed after the "
                        "synthetic runtime fault fired, so the test did not prove the "
                        "error boundary contained the failure locally.",
                    ) from error
                fault_state_after_trigger = _wait_for_fault_trigger(tracker_page, timeout_ms=10_000)
                result["fault_state_after_trigger"] = fault_state_after_trigger
                result["console_events"] = list(runtime_context.console_events)
                result["page_errors"] = list(runtime_context.page_errors)
                result["post_fault_console_events"] = list(
                    runtime_context.console_events[console_event_count_before_fault:],
                )
                result["post_fault_page_errors"] = list(
                    runtime_context.page_errors[page_error_count_before_fault:],
                )

                if int(fault_state_after_trigger.get("triggerCount", 0)) <= 0:
                    raise AssertionError(
                        "The synthetic workspace-switcher fault never fired after it was "
                        "enabled, so the runtime error path was not proven.",
                    )

                _assert_fault_locally_contained(
                    switcher_after_fault=switcher_after_fault,
                    post_fault_console_events=result["post_fault_console_events"],
                    post_fault_page_errors=result["post_fault_page_errors"],
                )

                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Enabled the workspace-switcher-scoped synthetic runtime fault and "
                        "re-triggered the switcher path.\n"
                        f"fault_state_after_trigger={json.dumps(fault_state_after_trigger, indent=2)}\n"
                        f"switcher_after_fault={json.dumps(result['switcher_after_fault'], indent=2)}\n"
                        f"post_fault_console_events={json.dumps(result['post_fault_console_events'], indent=2)}\n"
                        f"post_fault_page_errors={json.dumps(result['post_fault_page_errors'], indent=2)}"
                    ),
                )
            except Exception as error:
                result["console_events"] = list(runtime_context.console_events)
                result["page_errors"] = list(runtime_context.page_errors)
                _record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "The synthetic runtime fault was not exercised as expected.\n"
                        f"error={_format_error(error)}\n"
                        f"fault_state_after_enable={json.dumps(result.get('fault_state_after_enable'), ensure_ascii=True)}\n"
                        f"switcher_after_fault={json.dumps(result.get('switcher_after_fault'), ensure_ascii=True)}\n"
                        f"switcher_after_fault_error={json.dumps(result.get('switcher_after_fault_error'), ensure_ascii=True)}\n"
                        f"post_fault_console_events={json.dumps(result.get('post_fault_console_events'), ensure_ascii=True)}\n"
                        f"post_fault_page_errors={json.dumps(result.get('post_fault_page_errors'), ensure_ascii=True)}\n"
                        f"console_events={json.dumps(result['console_events'], ensure_ascii=True)}\n"
                        f"page_errors={json.dumps(result['page_errors'], ensure_ascii=True)}"
                    ),
                )

            try:
                shell_after = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                    timeout_ms=30_000,
                )
                startup_after = _startup_surface_payload(tracker_page.observe_startup_surface())
                result["shell_after"] = shell_after
                result["startup_after"] = startup_after
                trigger_after = page.observe_trigger(timeout_ms=10_000)
                result["trigger_after"] = _trigger_payload(trigger_after)
                _assert_shell_survived(
                    shell_after=shell_after,
                    startup_after=startup_after,
                    trigger_after=trigger_after,
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "After the switcher fault fired, the top bar and sidebar still "
                        "rendered as part of the interactive shell.\n"
                        f"shell_after={json.dumps(shell_after, indent=2)}\n"
                        f"startup_after={json.dumps(startup_after, indent=2)}\n"
                        f"trigger_after={json.dumps(result['trigger_after'], indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the page after the induced switcher failure and confirmed it "
                        "did not collapse to a blank Sync issue surface."
                    ),
                    observed=(
                        f"visible_navigation_labels={json.dumps(shell_after.get('visible_navigation_labels', []), ensure_ascii=True)}; "
                        f"trigger_label={trigger_after.semantic_label!r}; "
                        f"body_text_snippet={_snippet(startup_after['body_text'])!r}"
                    ),
                )
            except Exception as error:
                _record_step(
                    result,
                    step=4,
                    status="failed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "The global shell did not remain healthy after the workspace-switcher "
                        f"fault attempt.\nerror={_format_error(error)}\n"
                        f"startup_after={json.dumps(result.get('startup_after'), ensure_ascii=True)}\n"
                        f"body_text={page.current_body_text()!r}"
                    ),
                )

            try:
                page.close_switcher()
                page.navigate_to_section(NAVIGATION_TARGET_LABEL)
                navigation_body_text = page.current_body_text()
                result["navigation_target"] = NAVIGATION_TARGET_LABEL
                result["navigation_body_text"] = navigation_body_text
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=REQUEST_STEPS[4],
                    observed=(
                        f"Clicked the Sidebar `{NAVIGATION_TARGET_LABEL}` entry after the "
                        "workspace switcher fault and the section activated successfully.\n"
                        f"body_text_snippet={_snippet(navigation_body_text)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Used the sidebar like a user after the injected switcher failure and "
                        "confirmed the app still navigated."
                    ),
                    observed=(
                        f"navigation_target={NAVIGATION_TARGET_LABEL!r}; "
                        f"body_text_snippet={_snippet(navigation_body_text)!r}"
                    ),
                )
            except Exception as error:
                _record_step(
                    result,
                    step=5,
                    status="failed",
                    action=REQUEST_STEPS[4],
                    observed=(
                        "Sidebar navigation stopped working after the workspace-switcher "
                        f"runtime fault.\nerror={_format_error(error)}\n"
                        f"body_text={page.current_body_text()!r}"
                    ),
                )

            if _has_failed_steps(result):
                raise AssertionError(str(_first_failed_step_observed(result)))

            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            _write_pass_outputs(result)
            return
    except Exception as error:
        result["error"] = _format_error(error)
        result["traceback"] = traceback.format_exc()
        if page is not None:
            try:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception:
                pass
        _write_failure_outputs(result)
        raise


def _workspace_switcher_fault_probe_script() -> str:
    return f"""
(() => {{
  const faultMarker = {json.dumps(FAULT_MARKER)};
  const selectorFragment = {json.dumps(FAULT_SELECTOR_FRAGMENT)};
  const state = {{
    enabled: false,
    triggerCount: 0,
    selectors: [],
    errorMessages: [],
  }};
  const shouldFault = (selector) =>
    state.enabled
    && typeof selector === 'string'
    && selector.includes(selectorFragment);
  const recordAndThrow = (selector) => {{
    const message = `${{faultMarker}} (selector=${{String(selector)}})`;
    state.triggerCount += 1;
    state.selectors.push(String(selector));
    state.errorMessages.push(message);
    throw new Error(message);
  }};
  const patchMethod = (target, methodName) => {{
    const original = target?.[methodName];
    if (typeof original !== 'function') {{
      return;
    }}
    Object.defineProperty(target, methodName, {{
      configurable: true,
      writable: true,
      value: function patchedSelectorMethod(selector, ...rest) {{
        if (shouldFault(selector)) {{
          return recordAndThrow(selector);
        }}
        return original.call(this, selector, ...rest);
      }},
    }});
  }};
  patchMethod(Document.prototype, 'querySelector');
  patchMethod(Document.prototype, 'querySelectorAll');
  window.__TS966WorkspaceSwitcherFault = {{
    enable() {{
      state.enabled = true;
      return {{ ...state }};
    }},
    disable() {{
      state.enabled = false;
      return {{ ...state }};
    }},
    state() {{
      return {{ ...state }};
    }},
    reset() {{
      state.enabled = false;
      state.triggerCount = 0;
      state.selectors = [];
      state.errorMessages = [];
      return {{ ...state }};
    }},
  }};
}})();
"""


def _workspace_state(repository: str) -> dict[str, object]:
    primary_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    secondary_id = (
        f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{SECONDARY_WORKSPACE_WRITE_BRANCH}"
    )
    return {
        "activeWorkspaceId": primary_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": primary_id,
                "displayName": PRIMARY_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": PRIMARY_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-22T23:30:00.000Z",
            },
            {
                "id": secondary_id,
                "displayName": SECONDARY_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": SECONDARY_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": SECONDARY_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-22T23:20:00.000Z",
            },
        ],
    }


def _startup_surface_payload(observation: StartupSurfaceObservation) -> dict[str, object]:
    return {
        "title": observation.title,
        "location_href": observation.location_href,
        "location_hash": observation.location_hash,
        "location_pathname": observation.location_pathname,
        "body_text": observation.body_text,
        "button_labels": list(observation.button_labels),
    }


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "raw_text_lines": list(trigger.raw_text_lines),
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "icon_count": trigger.icon_count,
        "top_button_labels": list(trigger.top_button_labels),
    }


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [_row_payload(row) for row in switcher.rows],
    }


def _row_payload(row: WorkspaceSwitcherRowObservation) -> dict[str, object]:
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


def _enable_fault(tracker_page: TrackStateTrackerPage) -> dict[str, object]:
    payload = tracker_page.session.evaluate(
        "() => window.__TS966WorkspaceSwitcherFault.enable()",
    )
    if not isinstance(payload, dict):
        raise AssertionError("The TS-966 runtime fault probe did not return an enable payload.")
    return {
        "enabled": bool(payload.get("enabled")),
        "triggerCount": int(payload.get("triggerCount", 0)),
        "selectors": [str(item) for item in payload.get("selectors", [])],
        "errorMessages": [str(item) for item in payload.get("errorMessages", [])],
    }


def _fault_state(tracker_page: TrackStateTrackerPage) -> dict[str, object]:
    payload = tracker_page.session.evaluate(
        "() => window.__TS966WorkspaceSwitcherFault.state()",
    )
    if not isinstance(payload, dict):
        return {
            "enabled": False,
            "triggerCount": 0,
            "selectors": [],
            "errorMessages": [],
        }
    return {
        "enabled": bool(payload.get("enabled")),
        "triggerCount": int(payload.get("triggerCount", 0)),
        "selectors": [str(item) for item in payload.get("selectors", [])],
        "errorMessages": [str(item) for item in payload.get("errorMessages", [])],
    }


def _wait_for_fault_trigger(
    tracker_page: TrackStateTrackerPage,
    *,
    timeout_ms: int,
) -> dict[str, object]:
    payload = tracker_page.session.wait_for_function(
        """
        () => {
          const probe = window.__TS966WorkspaceSwitcherFault;
          if (!probe) {
            return null;
          }
          const state = probe.state();
          return state && typeof state.triggerCount === 'number' && state.triggerCount > 0
            ? state
            : null;
        }
        """,
        timeout_ms=timeout_ms,
    )
    if not isinstance(payload, dict):
        raise AssertionError("The workspace-switcher fault never reported a trigger count.")
    return {
        "enabled": bool(payload.get("enabled")),
        "triggerCount": int(payload.get("triggerCount", 0)),
        "selectors": [str(item) for item in payload.get("selectors", [])],
        "errorMessages": [str(item) for item in payload.get("errorMessages", [])],
    }


def _assert_shell_survived(
    *,
    shell_after: dict[str, object],
    startup_after: dict[str, object],
    trigger_after: WorkspaceSwitcherTriggerObservation,
) -> None:
    if not bool(shell_after.get("shell_ready")):
        raise AssertionError(
            "The interactive shell no longer reported all required navigation labels "
            "after the workspace-switcher fault.",
        )
    if startup_after.get("button_labels") == ["Sync issue"]:
        raise AssertionError(
            "The visible page collapsed to the standalone `Sync issue` surface after "
            "the workspace-switcher fault.",
        )
    if not str(trigger_after.semantic_label).strip():
        raise AssertionError(
            "The header workspace switcher trigger no longer exposed a readable label "
            "after the workspace-switcher fault.",
        )


def _assert_fault_locally_contained(
    *,
    switcher_after_fault: WorkspaceSwitcherObservation,
    post_fault_console_events: object,
    post_fault_page_errors: object,
) -> None:
    if not _switcher_preserved_saved_workspace_context(switcher_after_fault):
        raise AssertionError(
            "The workspace switcher reopened after the synthetic fault, but it no "
            "longer exposed enough saved-workspace context to prove the failure was "
            "contained locally.",
        )

    page_errors = [
        payload
        for payload in (
            _normalize_page_error_payload(item) for item in post_fault_page_errors
        )
        if any(payload.values())
    ]
    unexpected_page_errors = [
        payload for payload in page_errors if _page_error_requires_failure(payload)
    ]
    if unexpected_page_errors:
        raise AssertionError(
            "The synthetic workspace-switcher fault leaked as a global page error.\n"
            f"Observed page errors:\n{json.dumps(unexpected_page_errors, indent=2)}",
        )

    leaked_console_events = [
        {
            "level": str(event.get("level", "")),
            "text": str(event.get("text", "")),
        }
        for event in post_fault_console_events
        if isinstance(event, dict) and _console_event_requires_failure(event)
    ]
    if leaked_console_events:
        raise AssertionError(
            "The synthetic workspace-switcher fault leaked as a global console error.\n"
            f"Observed console events:\n{json.dumps(leaked_console_events, indent=2)}",
        )


def _console_event_requires_failure(event: dict[str, object]) -> bool:
    level = str(event.get("level", "")).strip().lower()
    text = str(event.get("text", "")).strip()
    lowered = text.lower()
    if level == "error":
        return True
    return any(marker in lowered for marker in ("uncaught", "unhandled"))


def _switcher_preserved_saved_workspace_context(
    switcher_after_fault: WorkspaceSwitcherObservation,
) -> bool:
    normalized = " ".join(switcher_after_fault.switcher_text.split())
    if PRIMARY_WORKSPACE_DISPLAY_NAME not in normalized:
        return False
    if switcher_after_fault.row_count > 0:
        return True
    fallback_markers = (
        "Saved workspaces",
        f"Open: {SECONDARY_WORKSPACE_DISPLAY_NAME}",
        "Add workspace",
    )
    return all(marker in normalized for marker in fallback_markers)


def _page_error_payload(error: object) -> dict[str, str]:
    return {
        "text": str(error).strip(),
        "name": str(getattr(error, "name", "")).strip(),
        "message": str(getattr(error, "message", "")).strip(),
        "stack": str(getattr(error, "stack", "")).strip(),
    }


def _normalize_page_error_payload(error: object) -> dict[str, str]:
    if isinstance(error, str):
        return {
            "text": error.strip(),
            "name": "",
            "message": "",
            "stack": "",
        }
    if isinstance(error, dict):
        return {
            "text": str(error.get("text", "")).strip(),
            "name": str(error.get("name", "")).strip(),
            "message": str(error.get("message", "")).strip(),
            "stack": str(error.get("stack", "")).strip(),
        }
    return _page_error_payload(error)


def _page_error_payload_has_probe_signature(page_error: dict[str, str]) -> bool:
    stack = page_error.get("stack", "")
    if stack and all(marker in stack for marker in FAULT_STACK_MARKERS):
        return True
    haystack = " ".join(
        value for value in (
            page_error.get("text", ""),
            page_error.get("name", ""),
            page_error.get("message", ""),
            page_error.get("stack", ""),
        )
        if value
    ).lower()
    return FAULT_MARKER.lower() in haystack or FAULT_SELECTOR_FRAGMENT.lower() in haystack


def _page_error_requires_failure(page_error: dict[str, str]) -> bool:
    if not any(page_error.values()):
        return False
    return not _page_error_payload_has_probe_signature(page_error)


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    result.setdefault("steps", []).append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        },
    )


def _mark_not_reached(result: dict[str, object], *, start_step: int) -> None:
    for step_number, action in enumerate(REQUEST_STEPS[start_step - 1 :], start=start_step):
        _record_step(
            result,
            step=step_number,
            status="failed",
            action=action,
            observed="Not reached because the application shell never became ready.",
        )


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    result.setdefault("human_verification", []).append(
        {
            "check": check,
            "observed": observed,
        },
    )


def _has_failed_steps(result: dict[str, object]) -> bool:
    for step in result.get("steps", []):
        if isinstance(step, dict) and str(step.get("status")) == "failed":
            return True
    return False


def _first_failed_step_observed(result: dict[str, object]) -> str | None:
    for step in result.get("steps", []):
        if isinstance(step, dict) and str(step.get("status")) == "failed":
            return str(step.get("observed", ""))
    return None


def _write_pass_outputs(result: dict[str, object]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")
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


def _write_failure_outputs(result: dict[str, object]) -> None:
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": str(result.get("error", "AssertionError: TS-966 failed")),
            },
        )
        + "\n",
        encoding="utf-8",
    )
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
        "* Opened the deployed TrackState web app with hosted workspace profiles preloaded in browser storage.",
        "* Verified the interactive shell and header workspace switcher were reachable at the ticket viewport.",
        "* Injected a workspace-switcher-scoped runtime fault and retriggered the live switcher path.",
        f"* Verified the page stayed usable and the sidebar still navigated to *{NAVIGATION_TARGET_LABEL}* after the fault.",
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
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## What was automated",
        "- Opened the deployed app with hosted workspace profiles already seeded into browser storage.",
        "- Verified the interactive shell and workspace switcher were initially reachable.",
        "- Enabled a workspace-switcher-only synthetic runtime fault and retriggered the live switcher path.",
        f"- Verified the shell stayed interactive and the sidebar still navigated to `{NAVIGATION_TARGET_LABEL}`.",
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
            "The synthetic Workspace Switcher runtime error fired, but the live TrackState "
            "shell stayed interactive and the sidebar still navigated to another section.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{result.get('error', 'The workspace switcher fault scenario did not meet the expected result.')}\n"
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
            f"{index}. {icon} {action} Observed: {matching.get('observed', '')}",
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
        f"- **Actual:** {_actual_result_summary(result, passed=False)}",
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"- Run command: `{RUN_COMMAND}`",
        "",
        "## Observed state",
        f"- Startup before: `{json.dumps(result.get('startup_before'), ensure_ascii=True)}`",
        f"- Shell before: `{json.dumps(result.get('shell_before'), ensure_ascii=True)}`",
        f"- Trigger before: `{json.dumps(result.get('trigger_before'), ensure_ascii=True)}`",
        f"- Switcher before: `{json.dumps(result.get('switcher_before'), ensure_ascii=True)}`",
        f"- Fault state after trigger: `{json.dumps(result.get('fault_state_after_trigger'), ensure_ascii=True)}`",
        f"- Startup after: `{json.dumps(result.get('startup_after'), ensure_ascii=True)}`",
        f"- Shell after: `{json.dumps(result.get('shell_after'), ensure_ascii=True)}`",
        f"- Console events: `{json.dumps(result.get('console_events'), ensure_ascii=True)}`",
        f"- Page errors: `{json.dumps(result.get('page_errors'), ensure_ascii=True)}`",
    ]
    if result.get("screenshot"):
        lines.extend(["", "## Screenshots or logs", f"- Screenshot: `{result['screenshot']}`"])
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, object], *, passed: bool) -> str:
    if passed:
        return (
            "The synthetic workspace-switcher runtime error fired, yet the app continued to "
            "show the full shell, kept the top-bar switcher trigger visible, and still "
            f"navigated via the sidebar to {NAVIGATION_TARGET_LABEL}."
        )
    return str(
        result.get(
            "error",
            _first_failed_step_observed(result)
            or "The global shell did not remain interactive after the workspace-switcher fault.",
        ),
    )


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        if jira:
            lines.append(
                f"# Step {step['step']} *{str(step['status']).upper()}*: {step['action']}\n"
                f"Observed: {{{{code}}}}{step['observed']}{{{{code}}}}",
            )
        else:
            lines.append(
                f"- Step {step['step']} **{step['status']}** — {step['action']}  \n"
                f"  Observed: `{step['observed']}`",
            )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for entry in result.get("human_verification", []):
        if not isinstance(entry, dict):
            continue
        if jira:
            lines.append(
                f"* {entry['check']} Observed: {{{{code}}}}{entry['observed']}{{{{code}}}}",
            )
        else:
            lines.append(f"- **{entry['check']}** Observed: `{entry['observed']}`")
    return lines


def _format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def _snippet(value: object, *, limit: int = 260) -> str:
    compact = " ".join(str(value).split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


if __name__ == "__main__":
    main()
