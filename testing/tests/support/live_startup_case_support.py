from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from testing.components.pages.live_workspace_switcher_page import (
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage
from testing.core.interfaces.web_app_session import WebAppTimeoutError
from testing.tests.support.delayed_auth_workspace_profiles_runtime import (
    DelayedAuthWorkspaceProfilesRuntime,
)


@dataclass
class ShellReadyTransitionTracker:
    first_shell_ready_at_monotonic: float | None = None
    first_shell_ready_observed_while_auth_pending: bool | None = None
    observed_pending_samples: int = 0
    observed_samples: int = 0

    def record(
        self,
        *,
        shell_ready: bool,
        auth_pending: bool,
        observed_at_monotonic: float,
    ) -> None:
        self.observed_samples += 1
        if auth_pending:
            self.observed_pending_samples += 1
        if not shell_ready or self.first_shell_ready_at_monotonic is not None:
            return
        self.first_shell_ready_at_monotonic = observed_at_monotonic
        self.first_shell_ready_observed_while_auth_pending = auth_pending


def build_workspace_state(
    repository: str,
    *,
    local_target: str,
    default_branch: str,
    local_display_name: str,
    hosted_display_name: str,
) -> dict[str, object]:
    local_id = f"local:{local_target}@{default_branch}"
    hosted_id = f"hosted:{repository.lower()}@{default_branch}"
    return {
        "activeWorkspaceId": local_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": local_id,
                "displayName": local_display_name,
                "customDisplayName": local_display_name,
                "targetType": "local",
                "target": local_target,
                "defaultBranch": default_branch,
                "writeBranch": default_branch,
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": hosted_display_name,
                "customDisplayName": hosted_display_name,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": default_branch,
                "writeBranch": default_branch,
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
            },
        ],
    }


def prepare_local_workspace_repository(
    *,
    local_target: str,
    default_branch: str,
    marker_filename: str,
    marker_contents: str,
    commit_author_name: str,
    commit_author_email: str,
    commit_message: str,
) -> dict[str, object]:
    local_path = Path(local_target)
    local_path.mkdir(parents=True, exist_ok=True)

    is_repo = subprocess.run(
        ["git", "-C", str(local_path), "rev-parse", "--is-inside-work-tree"],
        check=False,
        capture_output=True,
        text=True,
    )
    if is_repo.returncode != 0:
        subprocess.run(
            ["git", "init", "--initial-branch", default_branch, str(local_path)],
            check=True,
            capture_output=True,
            text=True,
        )

    marker_path = local_path / marker_filename
    marker_path.write_text(marker_contents, encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(local_path), "add", marker_path.name],
        check=True,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "-C", str(local_path), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = subprocess.run(
        ["git", "-C", str(local_path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip() or head.returncode != 0:
        subprocess.run(
            [
                "git",
                "-C",
                str(local_path),
                "-c",
                f"user.name={commit_author_name}",
                "-c",
                f"user.email={commit_author_email}",
                "commit",
                "--allow-empty",
                "-m",
                commit_message,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    branch = subprocess.run(
        ["git", "-C", str(local_path), "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = subprocess.run(
        ["git", "-C", str(local_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "-C", str(local_path), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "path": str(local_path),
        "branch": branch.stdout.strip(),
        "head": head.stdout.strip(),
        "status": status.stdout.strip(),
        "marker_path": str(marker_path),
    }


def observe_live_startup_shell_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: DelayedAuthWorkspaceProfilesRuntime,
    startup_started_at_monotonic: float,
    shell_navigation_labels: tuple[str, ...],
    branding_texts: tuple[str, ...],
    transition_tracker: ShellReadyTransitionTracker | None = None,
) -> dict[str, Any]:
    shell_observation = tracker_page.observe_interactive_shell(
        shell_navigation_labels,
        timeout_ms=1_000,
    )
    startup_observation = startup_surface_payload(tracker_page)
    trigger = safe_trigger_payload(page)
    body_text = str(shell_observation.get("body_text", ""))
    visible_shell_text = "\n".join(
        text
        for text in (body_text, str(startup_observation.get("body_text", "")))
        if text
    )
    auth_pending = runtime.auth_probe_pending
    observed_at_monotonic = time.monotonic()
    shell_ready = bool(shell_observation.get("shell_ready"))
    if transition_tracker is not None:
        transition_tracker.record(
            shell_ready=shell_ready,
            auth_pending=auth_pending,
            observed_at_monotonic=observed_at_monotonic,
        )
        shell_ready_event_monotonic = transition_tracker.first_shell_ready_at_monotonic
    else:
        shell_ready_event_monotonic = observed_at_monotonic if shell_ready else None
    return {
        "shell_observation": shell_observation,
        "startup_observation": startup_observation,
        "trigger": trigger,
        "branding_visible": any(
            branding_text in visible_shell_text for branding_text in branding_texts
        ),
        "auth_pending": auth_pending,
        "auth_probe_started_after_start_seconds": relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.auth_probe_started_at_monotonic,
        ),
        "auth_probe_released_after_start_seconds": relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.auth_probe_released_at_monotonic,
        ),
        "auth_probe_release_after_auth_start_seconds": relative_event_seconds(
            runtime.auth_probe_started_at_monotonic,
            runtime.auth_probe_released_at_monotonic,
        ),
        "elapsed_since_auth_start_seconds": elapsed_since(runtime.auth_probe_started_at_monotonic),
        "shell_ready_after_start_seconds": relative_startup_event_seconds(
            startup_started_at_monotonic,
            shell_ready_event_monotonic,
        ),
        "shell_ready_after_probe_release_seconds": relative_event_seconds(
            runtime.auth_probe_released_at_monotonic,
            shell_ready_event_monotonic,
        ),
        "observed_pending_shell_samples": (
            transition_tracker.observed_pending_samples
            if transition_tracker is not None
            else None
        ),
        "shell_ready_observed_while_auth_pending": (
            transition_tracker.first_shell_ready_observed_while_auth_pending
            if transition_tracker is not None
            else None
        ),
    }


def elapsed_since(event_monotonic: float | None) -> float | None:
    if event_monotonic is None:
        return None
    return round(time.monotonic() - event_monotonic, 2)


def relative_startup_event_seconds(
    startup_started_at_monotonic: float,
    event_monotonic: float | None,
) -> float | None:
    if event_monotonic is None:
        return None
    return round(event_monotonic - startup_started_at_monotonic, 2)


def relative_event_seconds(
    started_at_monotonic: float | None,
    event_monotonic: float | None,
) -> float | None:
    if started_at_monotonic is None or event_monotonic is None:
        return None
    return round(event_monotonic - started_at_monotonic, 2)


def startup_surface_payload(tracker_page: TrackStateTrackerPage) -> dict[str, Any]:
    observation = tracker_page.observe_startup_surface()
    return {
        "title": observation.title,
        "location_href": observation.location_href,
        "location_hash": observation.location_hash,
        "location_pathname": observation.location_pathname,
        "body_text": observation.body_text,
        "button_labels": list(observation.button_labels),
    }


def safe_trigger_payload(
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, Any] | None:
    try:
        trigger = page.observe_trigger(timeout_ms=1_000)
    except (AssertionError, WebAppTimeoutError):
        return None
    return trigger_payload(trigger)


def try_observe_trigger(
    page: LiveWorkspaceSwitcherPage,
) -> WorkspaceSwitcherTriggerObservation | None:
    try:
        return page.observe_trigger(timeout_ms=1_000)
    except (AssertionError, WebAppTimeoutError):
        return None


def trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, Any]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "top_button_labels": list(trigger.top_button_labels),
    }


def snippet(text: str, *, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def record_step(
    result: dict[str, Any],
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


def record_human_verification(
    result: dict[str, Any],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


def record_not_reached_steps(
    result: dict[str, Any],
    *,
    starting_step: int,
    request_steps: list[str],
) -> None:
    recorded = {
        int(step["step"])
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    for step_number in range(starting_step, len(request_steps) + 1):
        if step_number in recorded:
            continue
        record_step(
            result,
            step=step_number,
            status="failed",
            action=request_steps[step_number - 1],
            observed=f"Not reached because step {starting_step - 1} failed.",
        )


def write_test_automation_result(
    result_path: Path,
    *,
    passed: bool,
    error: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "status": "passed" if passed else "failed",
        "passed": 1 if passed else 0,
        "failed": 0 if passed else 1,
        "skipped": 0,
        "summary": "1 passed, 0 failed" if passed else "0 passed, 1 failed",
    }
    if not passed and error is not None:
        payload["error"] = error
    result_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def format_step_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
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


def format_human_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
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


def build_annotated_steps(
    result: dict[str, Any],
    *,
    request_steps: list[str],
) -> list[str]:
    annotated_steps: list[str] = []
    steps = result.get("steps", [])
    for index, action in enumerate(request_steps, start=1):
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
    return annotated_steps
