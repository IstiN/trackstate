from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_multi_view_refresh_page import (  # noqa: E402
    EditSurfaceObservation,
    LiveMultiViewRefreshPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import (  # noqa: E402
    load_live_setup_test_config,
)
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-396"
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts396_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts396_success.png"
TARGET_ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
COMPACT_VIEWPORT = {"width": 390, "height": 844}


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-396 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    metadata = service.fetch_demo_metadata()
    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(TARGET_ISSUE_PATH)
    _assert_preconditions(issue_fixture=issue_fixture)

    expected_priority_label = _display_label(issue_fixture.priority_id)
    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": metadata.repository,
        "repository_ref": metadata.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_description": issue_fixture.description,
        "issue_priority_id": issue_fixture.priority_id,
        "expected_priority_label": expected_priority_label,
        "steps": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveMultiViewRefreshPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the shared edit-surface scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the hosted tracker shell.",
                    observed=runtime.body_text,
                )

                page.ensure_connected(
                    token=token,
                    repository=metadata.repository,
                    user_login=user.login,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Confirm the hosted session is connected to the deployed repository.",
                    observed=page.current_body_text(),
                )

                page.set_viewport(**DESKTOP_VIEWPORT)
                board_detail_text = page.open_issue_from_board(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Open the issue from Board and reach the board-origin issue detail view.",
                    observed=board_detail_text,
                )

                page.open_edit_dialog_from_current_issue_detail(issue_key=issue_fixture.key)
                desktop_board_observation = page.observe_edit_surface(
                    viewport_width=DESKTOP_VIEWPORT["width"],
                    viewport_height=DESKTOP_VIEWPORT["height"],
                )
                _assert_edit_surface_preloaded(
                    observation=desktop_board_observation,
                    issue_fixture=issue_fixture,
                    expected_priority_label=expected_priority_label,
                    step_number=4,
                    layout_mode="desktop Board-origin",
                )
                _assert_desktop_drawer_layout(
                    observation=desktop_board_observation,
                    step_number=4,
                )
                result["desktop_board_observation"] = _observation_payload(
                    desktop_board_observation,
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Open Edit from the Board-origin issue detail and verify the desktop "
                        "drawer layout plus the preloaded Summary, Description, and Priority."
                    ),
                    observed=_format_observation(desktop_board_observation),
                )
                page.close_edit_dialog()

                page.open_edit_dialog_for_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                desktop_detail_observation = page.observe_edit_surface(
                    viewport_width=DESKTOP_VIEWPORT["width"],
                    viewport_height=DESKTOP_VIEWPORT["height"],
                )
                _assert_edit_surface_preloaded(
                    observation=desktop_detail_observation,
                    issue_fixture=issue_fixture,
                    expected_priority_label=expected_priority_label,
                    step_number=5,
                    layout_mode="desktop issue detail",
                )
                result["desktop_issue_detail_observation"] = _observation_payload(
                    desktop_detail_observation,
                )
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=(
                        "Open Edit from the issue detail pane and verify the same issue "
                        "metadata is preloaded on desktop."
                    ),
                    observed=_format_observation(desktop_detail_observation),
                )
                page.close_edit_dialog()

                page.set_viewport(**COMPACT_VIEWPORT)
                page.open_edit_dialog_for_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                compact_observation = page.observe_edit_surface(
                    viewport_width=COMPACT_VIEWPORT["width"],
                    viewport_height=COMPACT_VIEWPORT["height"],
                )
                _assert_edit_surface_preloaded(
                    observation=compact_observation,
                    issue_fixture=issue_fixture,
                    expected_priority_label=expected_priority_label,
                    step_number=6,
                    layout_mode="compact issue detail",
                )
                _assert_compact_sheet_layout(
                    observation=compact_observation,
                    step_number=6,
                )
                result["compact_observation"] = _observation_payload(compact_observation)
                _record_step(
                    result,
                    step=6,
                    status="passed",
                    action=(
                        "Resize to 390px, open Edit again, and verify the compact sheet stays "
                        "nearly full-width with the same preloaded issue metadata."
                    ),
                    observed=_format_observation(compact_observation),
                )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                page.screenshot(str(SCREENSHOT_PATH))
                result["screenshot"] = str(SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    else:
        result["status"] = "passed"
        result["summary"] = (
            "Verified the deployed Edit issue surface opens from the Board-origin and "
            "issue-detail flows with preloaded Summary, Description, and Priority; "
            "desktop stays right-docked and compact expands to a near full-width sheet."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_preconditions(*, issue_fixture: LiveHostedIssueFixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-396 expected the seeded DEMO-2 fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.summary.strip():
        raise AssertionError(
            "Precondition failed: DEMO-2 does not expose a non-empty summary.",
        )
    if not issue_fixture.description.strip():
        raise AssertionError(
            "Precondition failed: DEMO-2 does not expose a non-empty description.",
        )
    if not issue_fixture.priority_id.strip():
        raise AssertionError(
            "Precondition failed: DEMO-2 does not expose a priority in front matter.",
        )


def _assert_edit_surface_preloaded(
    *,
    observation: EditSurfaceObservation,
    issue_fixture: LiveHostedIssueFixture,
    expected_priority_label: str,
    step_number: int,
    layout_mode: str,
) -> None:
    if "Edit issue" not in observation.body_text:
        raise AssertionError(
            f"Step {step_number} failed: the {layout_mode} flow did not leave the user on "
            "the visible Edit issue surface.\n"
            f"Observed page text:\n{observation.body_text}",
        )
    if observation.summary_value != issue_fixture.summary:
        raise AssertionError(
            f"Step {step_number} failed: the visible Summary field on the {layout_mode} "
            "Edit surface was not preloaded with the selected issue summary.\n"
            f"Expected Summary: {issue_fixture.summary!r}\n"
            f"Actual Summary: {observation.summary_value!r}\n"
            f"Observed page text:\n{observation.body_text}",
        )
    if observation.description_value != issue_fixture.description:
        raise AssertionError(
            f"Step {step_number} failed: the visible Description field on the {layout_mode} "
            "Edit surface was not preloaded with the selected issue description.\n"
            f"Expected Description: {issue_fixture.description!r}\n"
            f"Actual Description: {observation.description_value!r}\n"
            f"Observed page text:\n{observation.body_text}",
        )
    priority_payload = "\n".join(
        [
            f"Priority label: {observation.priority_label!r}",
            f"Priority text: {observation.priority_text!r}",
        ],
    )
    if expected_priority_label not in observation.priority_text and (
        observation.priority_label is None
        or expected_priority_label not in observation.priority_label
    ):
        raise AssertionError(
            f"Step {step_number} failed: the visible Priority control on the {layout_mode} "
            "Edit surface did not show the selected issue priority.\n"
            f"Expected Priority label: {expected_priority_label!r}\n"
            f"{priority_payload}\n"
            f"Observed page text:\n{observation.body_text}",
        )


def _assert_desktop_drawer_layout(
    *,
    observation: EditSurfaceObservation,
    step_number: int,
) -> None:
    if observation.width_fraction > 0.55:
        raise AssertionError(
            f"Step {step_number} failed: on desktop the Edit issue surface should dock like "
            "a right-side drawer instead of expanding too wide.\n"
            f"Observed width fraction: {observation.width_fraction:.3f}\n"
            f"Observed geometry: {_format_geometry(observation)}",
        )
    if observation.right_inset > 48:
        raise AssertionError(
            f"Step {step_number} failed: on desktop the Edit issue surface was not docked "
            "close enough to the right edge.\n"
            f"Observed right inset: {observation.right_inset:.1f}\n"
            f"Observed geometry: {_format_geometry(observation)}",
        )
    if observation.left < 200:
        raise AssertionError(
            f"Step {step_number} failed: on desktop the Edit issue surface started too far "
            "left to behave like a drawer.\n"
            f"Observed left inset: {observation.left:.1f}\n"
            f"Observed geometry: {_format_geometry(observation)}",
        )


def _assert_compact_sheet_layout(
    *,
    observation: EditSurfaceObservation,
    step_number: int,
) -> None:
    if observation.width_fraction < 0.88:
        raise AssertionError(
            f"Step {step_number} failed: at 390px the Edit issue surface did not expand to "
            "a near full-width sheet.\n"
            f"Observed width fraction: {observation.width_fraction:.3f}\n"
            f"Observed geometry: {_format_geometry(observation)}",
        )
    if observation.height_fraction < 0.88:
        raise AssertionError(
            f"Step {step_number} failed: at 390px the Edit issue surface did not expand "
            "vertically like a full-height sheet.\n"
            f"Observed height fraction: {observation.height_fraction:.3f}\n"
            f"Observed geometry: {_format_geometry(observation)}",
        )
    for label, value in (
        ("left inset", observation.left),
        ("right inset", observation.right_inset),
        ("top inset", observation.top),
        ("bottom inset", observation.bottom_inset),
    ):
        if value > 24:
            raise AssertionError(
                f"Step {step_number} failed: at 390px the Edit issue surface left too much "
                f"space for a compact full-width sheet ({label} = {value:.1f}).\n"
                f"Observed geometry: {_format_geometry(observation)}",
            )


def _display_label(value: str) -> str:
    compact = value.replace("-", " ").replace("_", " ").strip()
    return " ".join(fragment.capitalize() for fragment in compact.split())


def _format_geometry(observation: EditSurfaceObservation) -> str:
    return (
        f"viewport={observation.viewport_width:.0f}x{observation.viewport_height:.0f}, "
        f"left={observation.left:.1f}, top={observation.top:.1f}, "
        f"width={observation.width:.1f}, height={observation.height:.1f}, "
        f"rightInset={observation.right_inset:.1f}, "
        f"bottomInset={observation.bottom_inset:.1f}"
    )


def _observation_payload(observation: EditSurfaceObservation) -> dict[str, object]:
    return {
        "viewport_width": observation.viewport_width,
        "viewport_height": observation.viewport_height,
        "left": observation.left,
        "top": observation.top,
        "width": observation.width,
        "height": observation.height,
        "width_fraction": observation.width_fraction,
        "height_fraction": observation.height_fraction,
        "right_inset": observation.right_inset,
        "bottom_inset": observation.bottom_inset,
        "summary_value": observation.summary_value,
        "description_value": observation.description_value,
        "priority_label": observation.priority_label,
        "priority_text": observation.priority_text,
    }


def _format_observation(observation: EditSurfaceObservation) -> str:
    return (
        f"Summary={observation.summary_value!r}; "
        f"Description={observation.description_value!r}; "
        f"Priority={observation.priority_label or observation.priority_text!r}; "
        f"{_format_geometry(observation)}"
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


def _write_result_if_requested(payload: dict[str, object]) -> None:
    configured_path = os.environ.get("TS396_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts396_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
