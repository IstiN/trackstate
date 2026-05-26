from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (
    LiveIssueDetailCollaborationPage,
)
from testing.components.services.live_comment_metadata_contrast_probe import (
    CommentMetadataContrastObservation,
    LiveCommentMetadataContrastProbe,
)
from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)


TICKET_KEY = "TS-333"
OUTPUTS_DIR = REPO_ROOT / "outputs"
RESULT_PATH = OUTPUTS_DIR / "ts333_result.json"
LIGHT_SCREENSHOT_PATH = OUTPUTS_DIR / "ts333_comments_light.png"
DARK_SCREENSHOT_PATH = OUTPUTS_DIR / "ts333_comments_dark.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts333_failure.png"

ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
COMMENT_AUTHOR = "demo-admin"
COMMENT_BODY = "This comment demonstrates markdown-backed collaboration history."
COMMENT_TIMESTAMP = "2026-05-05T00:10:00Z"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    repository_service = LiveSetupRepositoryService(config=config)
    token = repository_service.token
    if not token:
        raise RuntimeError(
            "TS-333 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = repository_service.fetch_authenticated_user()
    issue_fixture = repository_service.fetch_issue_fixture(ISSUE_PATH)
    probe = LiveCommentMetadataContrastProbe()

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": repository_service.repository,
        "repository_ref": repository_service.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "steps": [],
        "observations": [],
    }
    failures: list[str] = []

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            live_issue_page = LiveIssueDetailCollaborationPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before collaboration metadata contrast was exercised.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the live app and reach the tracker shell.",
                    observed=runtime.body_text,
                )

                live_issue_page.ensure_connected(
                    token=token,
                    repository=repository_service.repository,
                    user_login=user.login,
                )
                live_issue_page.open_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                issue_text = live_issue_page.current_body_text()
                result["issue_body_text"] = issue_text
                if live_issue_page.issue_detail_count(issue_fixture.key) == 0:
                    raise AssertionError(
                        "Step 1 failed: the live app did not open the requested issue "
                        f"detail for {issue_fixture.key}.\n"
                        f"Observed body text:\n{issue_text}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Open the seeded issue detail that contains collaboration metadata.",
                    observed=issue_text,
                )

                live_issue_page.open_collaboration_tab("Comments")
                live_issue_page.wait_for_text(COMMENT_BODY, timeout_ms=60_000)
                comments_text = live_issue_page.current_body_text()
                result["comments_body_text_initial"] = comments_text
                for visible_text in (
                    "Comments",
                    COMMENT_AUTHOR,
                    COMMENT_BODY,
                    COMMENT_TIMESTAMP,
                ):
                    if visible_text not in comments_text:
                        failures.append(
                            "Step 3 failed: the Comments tab did not keep the expected "
                            f"user-visible text {visible_text!r} on screen.\n"
                            f"Observed body text:\n{comments_text}",
                        )

                initial_toggle_label = live_issue_page.theme_toggle_label()
                result["initial_theme_toggle_label"] = initial_toggle_label
                initial_theme_name = _theme_name_for_toggle_label(initial_toggle_label)
                result["initial_theme_name"] = initial_theme_name

                initial_observation = _observe_comment_metadata(
                    live_issue_page=live_issue_page,
                    probe=probe,
                    screenshot_path=_screenshot_path_for_theme(initial_theme_name),
                    theme_name=initial_theme_name,
                )
                result["observations"] = [
                    _observation_to_dict(initial_observation),
                ]
                result[f"comments_body_text_{initial_theme_name}"] = comments_text
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "Inspect the visible Comments metadata row in the current "
                        f"{initial_theme_name} theme."
                    ),
                    observed=comments_text,
                )
                if initial_observation.contrast_ratio < 4.5:
                    failures.append(
                        f"Step 3 failed: the visible Comments metadata in the current {initial_theme_name} "
                        "theme did not meet the required WCAG AA 4.5:1 contrast ratio.\n"
                        f"Observed {initial_observation.describe()}\n"
                        f"Visible body text:\n{comments_text}",
                    )

                toggled_label = live_issue_page.toggle_theme()
                result["toggled_theme_toggle_label"] = toggled_label
                toggled_theme_name = _theme_name_for_toggle_label(toggled_label)
                result["toggled_theme_name"] = toggled_theme_name
                if toggled_theme_name == initial_theme_name:
                    failures.append(
                        "Step 4 failed: toggling the theme did not switch the UI to the opposite theme.\n"
                        f"Initial toggle label: {initial_toggle_label}\n"
                        f"Toggle label after click: {toggled_label}\n"
                        f"Observed body text:\n{live_issue_page.current_body_text()}",
                    )
                live_issue_page.wait_for_text(COMMENT_BODY, timeout_ms=60_000)
                comments_text_toggled = live_issue_page.current_body_text()
                result[f"comments_body_text_{toggled_theme_name}"] = comments_text_toggled
                for visible_text in (
                    "Comments",
                    COMMENT_AUTHOR,
                    COMMENT_BODY,
                    COMMENT_TIMESTAMP,
                ):
                    if visible_text not in comments_text_toggled:
                        failures.append(
                            f"Step 4 failed: after switching to the {toggled_theme_name} theme, the Comments tab did "
                            f"not keep the expected user-visible text {visible_text!r} "
                            "on screen.\n"
                            f"Observed body text:\n{comments_text_toggled}",
                        )

                toggled_observation = _observe_comment_metadata(
                    live_issue_page=live_issue_page,
                    probe=probe,
                    screenshot_path=_screenshot_path_for_theme(toggled_theme_name),
                    theme_name=toggled_theme_name,
                )
                observations = result.setdefault("observations", [])
                assert isinstance(observations, list)
                observations.append(_observation_to_dict(toggled_observation))
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Switch themes and re-check the same visible Comments metadata row "
                        f"in the {toggled_theme_name} theme."
                    ),
                    observed=comments_text_toggled,
                )
                if toggled_observation.contrast_ratio < 4.5:
                    failures.append(
                        f"Step 4 failed: the visible Comments metadata in the {toggled_theme_name} theme "
                        "did not meet the required WCAG AA 4.5:1 contrast ratio.\n"
                        f"Observed {toggled_observation.describe()}\n"
                        f"Visible body text:\n{comments_text_toggled}",
                    )
            except Exception:
                live_issue_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["failure_screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_result(result)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_result(result)
        print(json.dumps(result, indent=2))
        raise
    else:
        if failures:
            error_message = "\n\n".join(failures)
            result["error"] = error_message
            result["summary"] = (
                "Observed visible comment metadata in both themes, but at least one "
                "theme missed the required WCAG AA contrast threshold."
            )
            _write_result(result)
            print(json.dumps(result, indent=2))
            raise AssertionError(error_message)

        result["status"] = "passed"
        result["summary"] = (
            "Verified in the live hosted tracker that the visible Comments metadata "
            "row stayed readable and met WCAG AA contrast in both light and dark themes."
        )
        _write_result(result)
        print(json.dumps(result, indent=2))


def _observe_comment_metadata(
    *,
    live_issue_page: LiveIssueDetailCollaborationPage,
    probe: LiveCommentMetadataContrastProbe,
    screenshot_path: Path,
    theme_name: str,
) -> CommentMetadataContrastObservation:
    row_rect = live_issue_page.find_semantics_rect_containing_text(COMMENT_TIMESTAMP)
    live_issue_page.screenshot(str(screenshot_path))
    return probe.observe(
        screenshot_path=screenshot_path,
        row_rect=row_rect,
        theme_name=theme_name,
    )


def _observation_to_dict(
    observation: CommentMetadataContrastObservation,
) -> dict[str, object]:
    return {
        "theme_name": observation.theme_name,
        "row_background_hex": observation.row_background_hex,
        "expected_background_hex": observation.expected_background_hex,
        "actual_foreground_hex": observation.actual_foreground_hex,
        "inferred_token_name": observation.inferred_token_name,
        "inferred_token_hex": observation.inferred_token_hex,
        "contrast_ratio": round(observation.contrast_ratio, 4),
        "screenshot_path": observation.screenshot_path,
        "timestamp_crop_box": list(observation.timestamp_crop_box),
    }


def _theme_name_for_toggle_label(toggle_label: str) -> str:
    return "light" if toggle_label == "Dark theme" else "dark"


def _screenshot_path_for_theme(theme_name: str) -> Path:
    if theme_name == "light":
        return LIGHT_SCREENSHOT_PATH
    return DARK_SCREENSHOT_PATH


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


def _write_result(payload: dict[str, object]) -> None:
    configured_path = os.environ.get("TS333_RESULT_PATH")
    result_path = Path(configured_path) if configured_path else RESULT_PATH
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
