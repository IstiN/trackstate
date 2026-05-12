from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_issue_detail_collaboration_page import (  # noqa: E402
    CommentCardObservation,
    LiveIssueDetailCollaborationPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-391"
OUTPUTS_DIR = REPO_ROOT / "outputs"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts391_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts391_success.png"
TARGET_ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
EDITED_COMMENT_PATH = f"{TARGET_ISSUE_PATH}/comments/0001.md"
NEW_COMMENT_PATH = f"{TARGET_ISSUE_PATH}/comments/0002.md"
EDITED_AUTHOR = "demo-edited"
EDITED_CREATED_AT = "2026-05-05T00:10:00Z"
EDITED_UPDATED_AT = "2026-05-12T08:12:15Z"
EDITED_BODY = "TS-391 edited comment proves updated metadata visibility."
NEW_AUTHOR = "demo-new"
NEW_CREATED_AT = "2026-05-12T08:12:16Z"
NEW_UPDATED_AT = NEW_CREATED_AT
NEW_BODY = "TS-391 new comment proves unchanged metadata visibility."
COMMENTS_TAB_LABEL = "Comments"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-391 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    metadata = service.fetch_demo_metadata()
    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(TARGET_ISSUE_PATH)
    original_files = _snapshot_comment_files(service)
    _assert_preconditions(issue_fixture=issue_fixture)
    precondition_setup = _prepare_comment_preconditions(
        service=service,
        original_files=original_files,
    )

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": metadata.repository,
        "repository_ref": metadata.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "comment_paths": [EDITED_COMMENT_PATH, NEW_COMMENT_PATH],
        "precondition_setup": precondition_setup,
        "steps": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveIssueDetailCollaborationPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the comment metadata scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the hosted tracker shell for the live DEMO project.",
                    observed=runtime.body_text,
                )

                page.ensure_connected(
                    token=token,
                    repository=metadata.repository,
                    user_login=user.login,
                )
                page.open_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                if page.issue_detail_count(issue_fixture.key) == 0:
                    raise AssertionError(
                        "Step 1 failed: the hosted app did not open the requested issue "
                        f"detail for {issue_fixture.key}.\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=f"Open issue {issue_fixture.key} in the live issue detail view.",
                    observed=page.current_body_text(),
                )

                page.open_collaboration_tab(COMMENTS_TAB_LABEL)
                page.wait_for_selected_tab(COMMENTS_TAB_LABEL, timeout_ms=30_000)

                new_comment_card = page.wait_for_comment_card(
                    NEW_BODY,
                    timeout_ms=120_000,
                )
                edited_comment_card = page.wait_for_comment_card(
                    EDITED_BODY,
                    timeout_ms=120_000,
                )
                result["new_comment_card"] = _comment_payload(new_comment_card)
                result["edited_comment_card"] = _comment_payload(edited_comment_card)
                result["comments_tab_body_text"] = page.current_body_text()
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Open the Comments tab and inspect the two prepared comment rows.",
                    observed=(
                        f"New comment row: {new_comment_card.visible_text}\n"
                        f"Edited comment row: {edited_comment_card.visible_text}"
                    ),
                )

                _assert_new_comment_card(new_comment_card)
                _assert_edited_comment_card(edited_comment_card)
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Verify the untouched comment shows only author plus created time, "
                        "while the edited comment shows the edited timestamp marker."
                    ),
                    observed=(
                        f"New comment row: {new_comment_card.visible_text}\n"
                        f"Edited comment row: {edited_comment_card.visible_text}"
                    ),
                )

                result["human_verification"] = {
                    "checked": [
                        "the Comments tab remained visibly selected in the issue detail view",
                        "the untouched comment row showed the author, body text, and created timestamp only",
                        "the edited comment row showed the author, body text, created timestamp, and visible Edited timestamp marker",
                        "the metadata appeared inside each visible comment row, not only somewhere else in the page body",
                    ],
                    "observed": {
                        "new_comment_row_text": new_comment_card.visible_text,
                        "edited_comment_row_text": edited_comment_card.visible_text,
                        "new_comment_row_accessible_label": new_comment_card.accessible_label,
                        "edited_comment_row_accessible_label": edited_comment_card.accessible_label,
                    },
                }
                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
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
    finally:
        cleanup = _restore_comment_files(
            service=service,
            original_files=original_files,
        )
        result["cleanup"] = cleanup

    result["status"] = "passed"
    result["summary"] = (
        "Verified the live hosted Comments tab hides the updated timestamp when a "
        "comment was not edited and shows an Edited timestamp marker only when the "
        "comment metadata contains a later updated value."
    )
    _write_result_if_requested(result)
    print(json.dumps(result, indent=2))


def _assert_preconditions(*, issue_fixture: LiveHostedIssueFixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-391 expected the seeded DEMO-2 fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    expected_paths = {EDITED_COMMENT_PATH, NEW_COMMENT_PATH}
    observed_paths = set(issue_fixture.comment_paths)
    if not expected_paths.issubset(observed_paths):
        raise AssertionError(
            "Precondition failed: DEMO-2 does not expose the expected seeded comment files.\n"
            f"Expected paths: {sorted(expected_paths)}\n"
            f"Observed paths: {sorted(observed_paths)}",
        )


def _snapshot_comment_files(
    service: LiveSetupRepositoryService,
) -> dict[str, LiveHostedRepositoryFile]:
    return {
        path: service.fetch_repo_file(path)
        for path in (EDITED_COMMENT_PATH, NEW_COMMENT_PATH)
    }


def _prepare_comment_preconditions(
    *,
    service: LiveSetupRepositoryService,
    original_files: dict[str, LiveHostedRepositoryFile],
) -> dict[str, object]:
    edited_markdown = _comment_markdown(
        author=EDITED_AUTHOR,
        created_at=EDITED_CREATED_AT,
        updated_at=EDITED_UPDATED_AT,
        body=EDITED_BODY,
    )
    new_markdown = _comment_markdown(
        author=NEW_AUTHOR,
        created_at=NEW_CREATED_AT,
        updated_at=NEW_UPDATED_AT,
        body=NEW_BODY,
    )

    writes: list[str] = []
    if original_files[EDITED_COMMENT_PATH].content != edited_markdown:
        service.write_repo_text(
            EDITED_COMMENT_PATH,
            content=edited_markdown,
            message=f"{TICKET_KEY}: seed edited comment metadata precondition",
        )
        writes.append(EDITED_COMMENT_PATH)
    if original_files[NEW_COMMENT_PATH].content != new_markdown:
        service.write_repo_text(
            NEW_COMMENT_PATH,
            content=new_markdown,
            message=f"{TICKET_KEY}: seed unchanged comment metadata precondition",
        )
        writes.append(NEW_COMMENT_PATH)

    matched, last_observation = poll_until(
        probe=lambda: _observe_comment_repo_state(service),
        is_satisfied=lambda observation: observation == {
            EDITED_COMMENT_PATH: edited_markdown,
            NEW_COMMENT_PATH: new_markdown,
        },
        timeout_seconds=90,
    )
    if not matched:
        raise AssertionError(
            "Precondition failed: the live repository did not reach the expected TS-391 "
            "comment metadata state.\n"
            f"Last observed state: {last_observation}",
        )

    return {
        "updated_paths": writes,
        "edited_comment": {
            "author": EDITED_AUTHOR,
            "created_at": EDITED_CREATED_AT,
            "updated_at": EDITED_UPDATED_AT,
            "body": EDITED_BODY,
        },
        "new_comment": {
            "author": NEW_AUTHOR,
            "created_at": NEW_CREATED_AT,
            "updated_at": NEW_UPDATED_AT,
            "body": NEW_BODY,
        },
    }


def _observe_comment_repo_state(
    service: LiveSetupRepositoryService,
) -> dict[str, str]:
    return {
        EDITED_COMMENT_PATH: service.fetch_repo_text(EDITED_COMMENT_PATH),
        NEW_COMMENT_PATH: service.fetch_repo_text(NEW_COMMENT_PATH),
    }


def _restore_comment_files(
    *,
    service: LiveSetupRepositoryService,
    original_files: dict[str, LiveHostedRepositoryFile],
) -> dict[str, object]:
    restored_paths: list[str] = []
    for path, original_file in original_files.items():
        current_content = service.fetch_repo_text(path)
        if current_content == original_file.content:
            continue
        service.write_repo_text(
            path,
            content=original_file.content,
            message=f"{TICKET_KEY}: restore original comment metadata fixture",
        )
        restored_paths.append(path)

    matched, last_observation = poll_until(
        probe=lambda: _observe_comment_repo_state(service),
        is_satisfied=lambda observation: all(
            observation[path] == original_files[path].content for path in original_files
        ),
        timeout_seconds=90,
    )
    return {
        "status": "restored" if matched else "restore-pending",
        "restored_paths": restored_paths,
        "last_observation": {
            path: _truncate_content(content)
            for path, content in last_observation.items()
        },
    }


def _assert_new_comment_card(observation: CommentCardObservation) -> None:
    if NEW_AUTHOR not in observation.visible_text:
        raise AssertionError(
            "Step 4 failed: the untouched comment row did not show the prepared author.\n"
            f"Expected author: {NEW_AUTHOR}\n"
            f"Observed row text: {observation.visible_text}",
        )
    if NEW_CREATED_AT not in observation.visible_text:
        raise AssertionError(
            "Step 4 failed: the untouched comment row did not show the prepared created "
            "timestamp.\n"
            f"Expected created timestamp: {NEW_CREATED_AT}\n"
            f"Observed row text: {observation.visible_text}",
        )
    if observation.visible_text.count(NEW_CREATED_AT) != 1:
        raise AssertionError(
            "Step 4 failed: the untouched comment row exposed the timestamp more than "
            "once instead of showing only the created time.\n"
            f"Expected single timestamp: {NEW_CREATED_AT}\n"
            f"Observed row text: {observation.visible_text}",
        )
    if "Edited " in observation.visible_text:
        raise AssertionError(
            "Step 4 failed: the untouched comment row still rendered an Edited marker "
            "even though updated matched created.\n"
            f"Observed row text: {observation.visible_text}",
        )


def _assert_edited_comment_card(observation: CommentCardObservation) -> None:
    expected_marker = f"Edited {EDITED_UPDATED_AT}"
    if EDITED_AUTHOR not in observation.visible_text:
        raise AssertionError(
            "Step 4 failed: the edited comment row did not show the prepared author.\n"
            f"Expected author: {EDITED_AUTHOR}\n"
            f"Observed row text: {observation.visible_text}",
        )
    if EDITED_CREATED_AT not in observation.visible_text:
        raise AssertionError(
            "Step 4 failed: the edited comment row did not preserve the created "
            "timestamp.\n"
            f"Expected created timestamp: {EDITED_CREATED_AT}\n"
            f"Observed row text: {observation.visible_text}",
        )
    if expected_marker not in observation.visible_text:
        raise AssertionError(
            "Step 4 failed: the edited comment row did not render the visible Edited "
            "timestamp marker.\n"
            f"Expected marker: {expected_marker}\n"
            f"Observed row text: {observation.visible_text}",
        )


def _comment_markdown(
    *,
    author: str,
    created_at: str,
    updated_at: str,
    body: str,
) -> str:
    return (
        "---\n"
        f"author: {author}\n"
        f"created: {created_at}\n"
        f"updated: {updated_at}\n"
        "---\n\n"
        f"{body}\n"
    )


def _comment_payload(observation: CommentCardObservation) -> dict[str, object]:
    return {
        "body_fragment": observation.body_fragment,
        "visible_text": observation.visible_text,
        "accessible_label": observation.accessible_label,
    }


def _truncate_content(content: str, *, limit: int = 500) -> str:
    if len(content) <= limit:
        return content
    return f"{content[:limit]}...[truncated]"


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
    configured_path = os.environ.get("TS391_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts391_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
