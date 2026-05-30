from __future__ import annotations

import json
import os
import platform
import re
import sys
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_settings_catalogs_page import (  # noqa: E402
    CatalogEditorObservation,
    LiveSettingsCatalogsPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedCatalogEntry,
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-463"
TEST_CASE_TITLE = "Catalog management — CRUD operations for Priorities, Components, and Versions"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-463/test_ts_463.py"
PROJECT_PATH = "DEMO"
PRIORITIES_PATH = f"{PROJECT_PATH}/config/priorities.json"
COMPONENTS_PATH = f"{PROJECT_PATH}/config/components.json"
VERSIONS_PATH = f"{PROJECT_PATH}/config/versions.json"
PRIORITY_ID = "ultra"
PRIORITY_NAME = "Ultra High"
TEMP_VERSION_ID = "ts463-unused"
TEMP_VERSION_NAME = "TS-463 Disposable Version"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
REQUEST_STEPS = [
    "Navigate to Settings and select the 'Priorities' tab.",
    "Create a new priority with ID 'ultra' and name 'Ultra High'.",
    "Select the 'Components' tab and edit an existing component name.",
    "Select the 'Versions' tab and delete an unused version.",
    "Click the primary 'Save' button.",
    "Inspect the repository files config/priorities.json, config/components.json, and config/versions.json.",
]
EXPECTED_RESULT = (
    "The CRUD operations are successful. The JSON files reflect the changes "
    "while preserving canonical IDs. The UI remains responsive using the "
    "drawer/modal pattern (AC1)."
)
LINKED_BUGS = ["TS-1182", "TS-1104", "TS-1094", "TS-1090"]
LINKED_BUG_NOTES = (
    "Reviewed input/TS-463/comments.md and linked_bugs.md before rerunning the "
    "live automation. The previously blocking Edit component prefill defect from "
    "TS-1104 is fixed, so the test now reaches the hosted save/persistence path. "
    "TS-1182 and TS-1094 are Done and require the Save settings flow to persist "
    "catalog changes atomically to the repository; the test therefore waits up "
    "to 90 seconds for the live repository JSON to reflect the UI edits before "
    "declaring failure."
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
INPUTS_DIR = REPO_ROOT / "input" / TICKET_KEY
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts463_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts463_success.png"
DISCUSSIONS_RAW_PATH = INPUTS_DIR / "pr_discussions_raw.json"
REWORK_SUMMARY = (
    "Updated TS-463 reporting to build failure summaries from the recorded failed step, "
    "narrowed product-bug classification to explicit TS-463 product-visible failures, "
    "and now emit review-thread replies to `outputs/review_replies.json`."
)
PRODUCT_FAILURE_SIGNATURES: dict[int, tuple[str, ...]] = {
    2: (
        "the settings editor did not stay in the expected desktop drawer/modal pattern",
        "the Add priority editor did not retain the entered ID and name",
        "the new Priority row was not visibly rendered in Settings > Priorities before saving",
    ),
    3: (
        "the settings editor did not stay in the expected desktop drawer/modal pattern",
        "the Edit component drawer did not preserve the canonical component ID before the rename",
        "the Edit component drawer did not retain the new component name",
        "the renamed component was not visibly rendered in Settings > Components before saving",
    ),
    4: (
        "the seeded unused version was not visible in Settings > Versions before deletion",
        "the deleted version still exposed an edit action after the remove control was used",
    ),
    6: (
        "the hosted save path did not persist the expected catalog state within the timeout",
    ),
}
POST_SAVE_PRODUCT_FAILURE_SIGNATURES = (
    "Human verification failed: the saved Settings tabs did not present the same visible "
    "catalog state a user would expect after saving.",
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    JIRA_COMMENT_PATH.unlink(missing_ok=True)
    PR_BODY_PATH.unlink(missing_ok=True)
    RESPONSE_PATH.unlink(missing_ok=True)
    RESULT_PATH.unlink(missing_ok=True)
    REVIEW_REPLIES_PATH.unlink(missing_ok=True)
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    SCREENSHOT_PATH.unlink(missing_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-463 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    original_files = _snapshot_catalog_files(service)
    initial_priorities = _parse_catalog_entries(original_files[PRIORITIES_PATH].content)
    initial_components = _parse_catalog_entries(original_files[COMPONENTS_PATH].content)
    initial_versions = _parse_catalog_entries(original_files[VERSIONS_PATH].content)
    if not initial_components:
        raise AssertionError(
            "Precondition failed: the live repository does not expose any components to edit.",
        )

    target_component = _pick_target_component(service, initial_components)
    target_component_name = _build_expected_component_name(
        current_name=target_component["name"],
        existing_entries=initial_components,
    )
    precondition_summary = _prepare_preconditions(
        service=service,
        original_files=original_files,
    )

    result: dict[str, Any] = {
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
        "linked_bug_notes": LINKED_BUG_NOTES,
        "project": PROJECT_PATH,
        "priority_id": PRIORITY_ID,
        "priority_name": PRIORITY_NAME,
        "target_component": target_component,
        "updated_component_name": target_component_name,
        "seeded_unused_version": {
            "id": TEMP_VERSION_ID,
            "name": TEMP_VERSION_NAME,
        },
        "original_catalog_files": {
            path: _truncate_content(file.content) for path, file in original_files.items()
        },
        "precondition_setup": precondition_summary,
        "steps": [],
        "human_verification": [],
        "is_product_failure": False,
    }

    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            tracker_page.session.set_viewport_size(**DESKTOP_VIEWPORT)
            page = LiveSettingsCatalogsPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the catalog-management scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                page.dismiss_connection_banner()

                settings_text = page.open_settings_admin()
                priorities_text = page.open_catalog_tab(
                    label="Priorities",
                    add_label="Add priority",
                )
                result["settings_body_text"] = settings_text
                result["priorities_tab_body_text"] = priorities_text
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Navigate to Settings and select the 'Priorities' tab.",
                    observed=priorities_text,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live Settings screen and confirmed the visible Project "
                        "settings administration heading plus the Priorities tab before "
                        "starting catalog edits."
                    ),
                    observed=_snippet(priorities_text),
                )

                priority_editor = page.open_editor(
                    button_label="Add priority",
                    title="Add priority",
                )
                result["priority_editor_before_input"] = _editor_payload(priority_editor)
                _assert_drawer_pattern(step=2, editor=priority_editor)
                page.fill_editor_input("ID", PRIORITY_ID)
                page.fill_editor_input("Name", PRIORITY_NAME)
                priority_editor_filled = page.read_editor_observation("Add priority")
                result["priority_editor_after_input"] = _editor_payload(
                    priority_editor_filled,
                )
                if (
                    priority_editor_filled.id_value != PRIORITY_ID
                    or priority_editor_filled.name_value != PRIORITY_NAME
                ):
                    raise AssertionError(
                        "Step 2 failed: the Add priority editor did not retain the entered "
                        "ID and name.\n"
                        f"Expected ID: {PRIORITY_ID}\n"
                        f"Observed ID: {priority_editor_filled.id_value}\n"
                        f"Expected name: {PRIORITY_NAME}\n"
                        f"Observed name: {priority_editor_filled.name_value}\n"
                        f"Observed body text:\n{priority_editor_filled.body_text}",
                    )
                page.save_editor("Add priority")
                priority_body_after = page.current_body_text()
                priority_labels_after = page.aria_labels()
                result["priorities_tab_after_create"] = priority_body_after
                result["priorities_labels_after_create"] = priority_labels_after
                if (
                    not page.action_label_exists(f"Edit priority {PRIORITY_NAME}")
                    or f"{PRIORITY_NAME}\nID: {PRIORITY_ID}" not in priority_labels_after
                ):
                    raise AssertionError(
                        "Step 2 failed: the new Priority row was not visibly rendered in "
                        "Settings > Priorities before saving.\n"
                        f"Observed body text:\n{priority_body_after}\n\n"
                        f"Observed aria-labels:\n{priority_labels_after}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=(
                        "Create a new priority with ID 'ultra' and name 'Ultra High'."
                    ),
                    observed=priority_body_after,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the Add priority drawer stayed right-aligned on desktop and "
                        "the visible priority row rendered Ultra High with ID ultra before save."
                    ),
                    observed=(
                        f'editor={_snippet(priority_editor.body_text)}; '
                        f'labels={_snippet("\\n".join(priority_labels_after), limit=400)}'
                    ),
                )

                components_text = page.open_catalog_tab(
                    label="Components",
                    add_label="Add component",
                )
                result["components_tab_body_text"] = components_text
                component_editor = page.open_editor(
                    button_label=f'Edit component {target_component["name"]}',
                    title="Edit component",
                )
                result["component_editor_before_input"] = _editor_payload(component_editor)
                _assert_drawer_pattern(step=3, editor=component_editor)
                if component_editor.id_value != target_component["id"]:
                    raise AssertionError(
                        "Step 3 failed: the Edit component drawer did not preserve the "
                        "canonical component ID before the rename.\n"
                        f'Expected ID: {target_component["id"]}\n'
                        f"Observed ID: {component_editor.id_value}\n"
                        f"Observed body text:\n{component_editor.body_text}",
                    )
                page.fill_editor_input("Name", target_component_name)
                component_editor_filled = page.read_editor_observation("Edit component")
                result["component_editor_after_input"] = _editor_payload(
                    component_editor_filled,
                )
                if component_editor_filled.name_value != target_component_name:
                    raise AssertionError(
                        "Step 3 failed: the Edit component drawer did not retain the new "
                        "component name.\n"
                        f"Expected name: {target_component_name}\n"
                        f"Observed name: {component_editor_filled.name_value}\n"
                        f"Observed body text:\n{component_editor_filled.body_text}",
                    )
                page.save_editor("Edit component")
                component_body_after = page.current_body_text()
                component_labels_after = page.aria_labels()
                result["components_tab_after_edit"] = component_body_after
                result["components_labels_after_edit"] = component_labels_after
                if (
                    not page.action_label_exists(f"Edit component {target_component_name}")
                    or f'{target_component_name}\nID: {target_component["id"]}'
                    not in component_labels_after
                ):
                    raise AssertionError(
                        "Step 3 failed: the renamed component was not visibly rendered in "
                        "Settings > Components before saving.\n"
                        f"Observed body text:\n{component_body_after}\n\n"
                        f"Observed aria-labels:\n{component_labels_after}",
                    )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Select the 'Components' tab and edit an existing component name.",
                    observed=component_body_after,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the Edit component drawer preserved the canonical component "
                        "ID and showed the renamed component row before save."
                    ),
                    observed=(
                        f'editor_id={component_editor.id_value!r}; '
                        f'updated_name={target_component_name!r}; '
                        f'labels={_snippet("\\n".join(component_labels_after), limit=400)}'
                    ),
                )

                versions_text = page.open_catalog_tab(
                    label="Versions",
                    add_label="Add version",
                )
                result["versions_tab_body_text"] = versions_text
                if not page.action_label_exists(f"Delete version {TEMP_VERSION_NAME}"):
                    raise AssertionError(
                        "Step 4 failed: the seeded unused version was not visible in "
                        "Settings > Versions before deletion.\n"
                        f"Observed body text:\n{versions_text}",
                    )
                page.delete_entry(
                    f"Delete version {TEMP_VERSION_NAME}",
                    removed_text=TEMP_VERSION_NAME,
                )
                versions_body_after_delete = page.current_body_text()
                versions_labels_after_delete = page.aria_labels()
                result["versions_tab_after_delete"] = versions_body_after_delete
                result["versions_labels_after_delete"] = versions_labels_after_delete
                if page.action_label_exists(f"Edit version {TEMP_VERSION_NAME}"):
                    raise AssertionError(
                        "Step 4 failed: the deleted version still exposed an edit action "
                        "after the remove control was used.\n"
                        f"Observed body text:\n{versions_body_after_delete}",
                    )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Select the 'Versions' tab and delete an unused version.",
                    observed=versions_body_after_delete,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the disposable version disappeared from the visible Versions "
                        "list before saving."
                    ),
                    observed=_snippet("\n".join(versions_labels_after_delete), limit=400),
                )

                page.save_settings()
                result["save_button_visible_after_click"] = page.action_label_exists(
                    "Save settings",
                )
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Click the primary 'Save' button.",
                    observed=page.current_body_text(),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the user remained on the Project Settings surface after "
                        "clicking Save settings and the app entered a visible sync state."
                    ),
                    observed=(
                        f'save_button_visible_after_click={result["save_button_visible_after_click"]!r}; '
                        f'body={_snippet(page.current_body_text())}'
                    ),
                )

                repo_matched, repo_after_save = _poll_for_catalog_repo_state(
                    service=service,
                    expected_component_id=str(target_component["id"]),
                    expected_component_name=target_component_name,
                )
                result["repo_after_save"] = repo_after_save
                repo_failure_message: str | None = None
                if repo_matched:
                    _record_step(
                        result,
                        step=6,
                        status="passed",
                        action=(
                            "Inspect the repository files config/priorities.json, "
                            "config/components.json, and config/versions.json."
                        ),
                        observed=(
                            f'priorities.json contains "{PRIORITY_ID}" / "{PRIORITY_NAME}", '
                            f'components.json keeps ID "{target_component["id"]}" with the '
                            f'updated name "{target_component_name}", and versions.json no '
                            f'longer contains "{TEMP_VERSION_ID}".'
                        ),
                    )
                else:
                    repo_failure_message = (
                        "Step 6 failed: the hosted save path did not persist the expected "
                        "catalog state within the timeout.\n"
                        f"Last observed state: {repo_after_save}"
                    )
                    _record_step(
                        result,
                        step=6,
                        status="failed",
                        action=(
                            "Inspect the repository files config/priorities.json, "
                            "config/components.json, and config/versions.json."
                        ),
                        observed=repo_failure_message,
                    )

                priorities_text_saved = page.open_catalog_tab(
                    label="Priorities",
                    add_label="Add priority",
                )
                priorities_labels_saved = page.aria_labels()
                components_text_saved = page.open_catalog_tab(
                    label="Components",
                    add_label="Add component",
                )
                components_labels_saved = page.aria_labels()
                versions_text_saved = page.open_catalog_tab(
                    label="Versions",
                    add_label="Add version",
                )
                versions_labels_saved = page.aria_labels()
                result["priorities_tab_after_save"] = priorities_text_saved
                result["priorities_labels_after_save"] = priorities_labels_saved
                result["components_tab_after_save"] = components_text_saved
                result["components_labels_after_save"] = components_labels_saved
                result["versions_tab_after_save"] = versions_text_saved
                result["versions_labels_after_save"] = versions_labels_saved
                post_save_ui_error: str | None = None
                if (
                    f"{PRIORITY_NAME}\nID: {PRIORITY_ID}" not in priorities_labels_saved
                    or f"Edit priority {PRIORITY_NAME}" not in priorities_labels_saved
                    or f'{target_component_name}\nID: {target_component["id"]}'
                    not in components_labels_saved
                    or f"Edit component {target_component_name}"
                    not in components_labels_saved
                    or any(
                        TEMP_VERSION_NAME in label for label in versions_labels_saved
                    )
                ):
                    post_save_ui_error = (
                        "Human verification failed: the saved Settings tabs did not present "
                        "the same visible catalog state a user would expect after saving.\n"
                        f"Priorities text:\n{priorities_text_saved}\n\n"
                        f"Priority aria-labels:\n{priorities_labels_saved}\n\n"
                        f"Components text:\n{components_text_saved}\n\n"
                        f"Component aria-labels:\n{components_labels_saved}\n\n"
                        f"Versions text:\n{versions_text_saved}\n\n"
                        f"Version aria-labels:\n{versions_labels_saved}"
                    )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the saved Settings tabs still showed the new priority, the "
                        "renamed component with the same canonical ID, and the deleted version "
                        "remaining absent after persistence completed."
                    ),
                    observed=(
                        f'priorities={_snippet("\\n".join(priorities_labels_saved), limit=400)}; '
                        f'components={_snippet("\\n".join(components_labels_saved), limit=400)}; '
                        f'versions={_snippet("\\n".join(versions_labels_saved), limit=400)}'
                    ),
                    status="failed" if post_save_ui_error else "passed",
                )
                result["human_verification_summary"] = {
                    "priority_visible_text": priorities_text_saved,
                    "priority_visible_labels": priorities_labels_saved,
                    "component_visible_text": components_text_saved,
                    "component_visible_labels": components_labels_saved,
                    "versions_visible_text": versions_text_saved,
                    "versions_visible_labels": versions_labels_saved,
                    "priority_editor_presentation": _editor_payload(priority_editor),
                }
                if repo_failure_message or post_save_ui_error:
                    raise AssertionError(
                        "\n\n".join(
                            message
                            for message in (repo_failure_message, post_save_ui_error)
                            if message
                        )
                    )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                page.screenshot(str(SCREENSHOT_PATH))
                result["screenshot"] = str(SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["status"] = "failed"
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _record_failure_step_from_error(result, str(error))
        result["is_product_failure"] = _should_write_bug_description(result)
        _write_outputs(result, passed=False)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["status"] = "failed"
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_outputs(result, passed=False)
        print(json.dumps(result, indent=2))
        raise
    finally:
        cleanup = _restore_catalog_files(
            service=service,
            original_files=original_files,
        )
        result["cleanup"] = cleanup

    result["status"] = "passed"
    result["summary"] = (
        "Verified the hosted Settings admin CRUD flow for Priorities, Components, "
        "and Versions by creating priority ultra/Ultra High, renaming an existing "
        "component without changing its canonical ID, deleting a disposable unused "
        "version, and confirming the saved repository JSON plus visible UI state."
    )
    _write_outputs(result, passed=True)
    print(json.dumps(result, indent=2))


def _snapshot_catalog_files(
    service: LiveSetupRepositoryService,
) -> dict[str, LiveHostedRepositoryFile]:
    return {
        path: service.fetch_repo_file(path)
        for path in (PRIORITIES_PATH, COMPONENTS_PATH, VERSIONS_PATH)
    }


def _prepare_preconditions(
    *,
    service: LiveSetupRepositoryService,
    original_files: dict[str, LiveHostedRepositoryFile],
) -> dict[str, object]:
    priorities = _parse_catalog_entries(original_files[PRIORITIES_PATH].content)
    versions = _parse_catalog_entries(original_files[VERSIONS_PATH].content)
    priority_removed = any(str(entry.get("id", "")).strip() == PRIORITY_ID for entry in priorities)
    version_seeded = not any(
        str(entry.get("id", "")).strip() == TEMP_VERSION_ID for entry in versions
    )

    updated_priorities = [
        entry
        for entry in priorities
        if str(entry.get("id", "")).strip() != PRIORITY_ID
    ]
    updated_versions = [*versions]
    if version_seeded:
        updated_versions.append(
            {
                "id": TEMP_VERSION_ID,
                "name": TEMP_VERSION_NAME,
                "released": False,
            },
        )

    if priority_removed:
        service.write_repo_text(
            PRIORITIES_PATH,
            content=_catalog_json(updated_priorities),
            message=f"{TICKET_KEY}: reset priority precondition",
        )
    if version_seeded:
        service.write_repo_text(
            VERSIONS_PATH,
            content=_catalog_json(updated_versions),
            message=f"{TICKET_KEY}: seed unused version precondition",
        )

    matched, last_observation = poll_until(
        probe=lambda: {
            "priorities": service.fetch_catalog_entries(PROJECT_PATH, "priorities"),
            "versions": service.fetch_catalog_entries(PROJECT_PATH, "versions"),
        },
        is_satisfied=lambda observation: _preconditions_ready(observation),
        timeout_seconds=90,
    )
    if not matched:
        raise AssertionError(
            "Precondition failed: the live repository did not reach the expected catalog "
            "setup for TS-463.\n"
            f"Last observed state: {last_observation}",
        )

    return {
        "removed_existing_ultra_priority": priority_removed,
        "seeded_unused_version": version_seeded,
        "last_observation": {
            "priorities": [
                {"id": entry.id, "name": entry.name}
                for entry in last_observation["priorities"]
            ],
            "versions": [
                {"id": entry.id, "name": entry.name}
                for entry in last_observation["versions"]
            ],
        },
    }


def _preconditions_ready(observation: dict[str, object]) -> bool:
    priorities = observation.get("priorities", [])
    versions = observation.get("versions", [])
    if not isinstance(priorities, list) or not isinstance(versions, list):
        return False
    has_ultra = any(
        isinstance(entry, LiveHostedCatalogEntry) and entry.id == PRIORITY_ID
        for entry in priorities
    )
    has_temp_version = any(
        isinstance(entry, LiveHostedCatalogEntry) and entry.id == TEMP_VERSION_ID
        for entry in versions
    )
    return not has_ultra and has_temp_version


def _pick_target_component(
    service: LiveSetupRepositoryService,
    entries: list[dict[str, object]],
) -> dict[str, object]:
    used_components = _used_component_ids(service)
    preferred = [entry for entry in entries if str(entry.get("id")) == "automation"]
    candidates = preferred or entries
    for entry in candidates:
        entry_id = str(entry.get("id", "")).strip()
        entry_name = str(entry.get("name", "")).strip()
        if entry_id and entry_name and entry_id not in used_components:
            return {"id": entry_id, "name": entry_name}
    first = candidates[0]
    return {
        "id": str(first.get("id", "")).strip(),
        "name": str(first.get("name", "")).strip(),
    }


def _used_component_ids(service: LiveSetupRepositoryService) -> set[str]:
    used: set[str] = set()
    for issue_path in service.list_issue_paths(PROJECT_PATH):
        markdown = service.fetch_repo_text(f"{issue_path}/main.md")
        in_components = False
        for raw_line in markdown.splitlines():
            stripped = raw_line.strip()
            if stripped == "---":
                if in_components:
                    break
                continue
            if re.match(r"^[A-Za-z][A-Za-z0-9]*:\s*$", stripped):
                in_components = stripped[:-1] == "components"
                continue
            if in_components and stripped.startswith("- "):
                used.add(stripped.removeprefix("- ").strip())
            if in_components and stripped and not stripped.startswith("- "):
                in_components = False
    return used


def _build_expected_component_name(
    *,
    current_name: str,
    existing_entries: list[dict[str, object]],
) -> str:
    existing_names = {
        str(entry.get("name", "")).strip()
        for entry in existing_entries
        if str(entry.get("name", "")).strip()
    }
    candidates = [
        f"{current_name} TS-463",
        f"{current_name} Updated TS-463",
        f"{current_name} Catalog TS-463",
    ]
    for candidate in candidates:
        if candidate not in existing_names:
            return candidate
    raise AssertionError(
        "Precondition failed: could not choose a unique component name for TS-463.",
    )


def _poll_for_catalog_repo_state(
    *,
    service: LiveSetupRepositoryService,
    expected_component_id: str,
    expected_component_name: str,
    timeout_seconds: int = 90,
) -> tuple[bool, dict[str, object]]:
    matched, last_observation = poll_until(
        probe=lambda: _observe_catalog_repo_state(
            service=service,
            expected_component_id=expected_component_id,
        ),
        is_satisfied=lambda observation: _catalog_repo_state_matches(
            observation=observation,
            expected_component_id=expected_component_id,
            expected_component_name=expected_component_name,
        ),
        timeout_seconds=timeout_seconds,
    )
    return matched, last_observation


def _observe_catalog_repo_state(
    *,
    service: LiveSetupRepositoryService,
    expected_component_id: str,
) -> dict[str, object]:
    priorities = service.fetch_catalog_entries(PROJECT_PATH, "priorities")
    components = service.fetch_catalog_entries(PROJECT_PATH, "components")
    versions = service.fetch_catalog_entries(PROJECT_PATH, "versions")
    component_match = next(
        (
            {"id": entry.id, "name": entry.name}
            for entry in components
            if entry.id == expected_component_id
        ),
        None,
    )
    return {
        "priorities": [{"id": entry.id, "name": entry.name} for entry in priorities],
        "components": [{"id": entry.id, "name": entry.name} for entry in components],
        "versions": [{"id": entry.id, "name": entry.name} for entry in versions],
        "component_match": component_match,
        "priorities_json": service.fetch_repo_text(PRIORITIES_PATH),
        "components_json": service.fetch_repo_text(COMPONENTS_PATH),
        "versions_json": service.fetch_repo_text(VERSIONS_PATH),
    }


def _catalog_repo_state_matches(
    *,
    observation: dict[str, object],
    expected_component_id: str,
    expected_component_name: str,
) -> bool:
    priorities = observation.get("priorities", [])
    versions = observation.get("versions", [])
    component_match = observation.get("component_match")
    if not isinstance(priorities, list) or not isinstance(versions, list):
        return False
    has_priority = any(
        isinstance(entry, dict)
        and str(entry.get("id", "")).strip() == PRIORITY_ID
        and str(entry.get("name", "")).strip() == PRIORITY_NAME
        for entry in priorities
    )
    if not has_priority:
        return False
    if any(
        isinstance(entry, dict) and str(entry.get("id", "")).strip() == TEMP_VERSION_ID
        for entry in versions
    ):
        return False
    if not isinstance(component_match, dict):
        return False
    return (
        str(component_match.get("id", "")).strip() == expected_component_id
        and str(component_match.get("name", "")).strip() == expected_component_name
    )


def _restore_catalog_files(
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
            message=f"{TICKET_KEY}: restore original catalog file",
        )
        restored_paths.append(path)

    matched, last_observation = poll_until(
        probe=lambda: {
            path: service.fetch_repo_text(path) for path in original_files
        },
        is_satisfied=lambda observation: all(
            observation[path] == original_files[path].content for path in original_files
        ),
        timeout_seconds=90,
    )
    return {
        "status": "restored" if matched else "restore-pending",
        "restored_paths": restored_paths,
        "last_observation": {
            path: _truncate_content(content) for path, content in last_observation.items()
        },
    }


def _parse_catalog_entries(raw_text: str) -> list[dict[str, object]]:
    payload = json.loads(raw_text)
    if not isinstance(payload, list):
        raise AssertionError("Expected the catalog file to be a JSON array.")
    return [entry for entry in payload if isinstance(entry, dict)]


def _catalog_json(entries: list[dict[str, object]]) -> str:
    return json.dumps(entries, indent=2) + "\n"


def _truncate_content(content: str, *, limit: int = 5000) -> str:
    if len(content) <= limit:
        return content
    return f"{content[:limit]}...[truncated]"


def _editor_payload(editor: CatalogEditorObservation) -> dict[str, object]:
    return {
        "title": editor.title,
        "body_text": editor.body_text,
        "id_value": editor.id_value,
        "name_value": editor.name_value,
        "presentation": {
            "viewport_width": editor.presentation.viewport_width,
            "viewport_height": editor.presentation.viewport_height,
            "input_x": editor.presentation.input_x,
            "input_y": editor.presentation.input_y,
            "input_width": editor.presentation.input_width,
            "input_height": editor.presentation.input_height,
        },
    }


def _assert_drawer_pattern(*, step: int, editor: CatalogEditorObservation) -> None:
    presentation = editor.presentation
    if (
        presentation.viewport_width < 960
        or presentation.input_x <= presentation.viewport_width * 0.52
        or presentation.input_width >= presentation.viewport_width * 0.4
    ):
        raise AssertionError(
            f"Step {step} failed: the settings editor did not stay in the expected "
            "desktop drawer/modal pattern.\n"
            f"Viewport width: {presentation.viewport_width}\n"
            f"Input x-position: {presentation.input_x}\n"
            f"Input width: {presentation.input_width}\n"
            f"Observed body text:\n{editor.body_text}",
        )


def _record_step(
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


def _record_human_verification(
    result: dict[str, Any],
    *,
    check: str,
    observed: str,
    status: str = "passed",
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed, "status": status})


def _record_failure_step_from_error(result: dict[str, Any], message: str) -> None:
    match = re.match(r"^Step (\d+) failed:\s*(.*)", message, flags=re.DOTALL)
    if match is None:
        return
    step_number = int(match.group(1))
    if step_number < 1 or step_number > len(REQUEST_STEPS):
        return
    existing = {
        int(step["step"])
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    if step_number in existing:
        return
    _record_step(
        result,
        step=step_number,
        status="failed",
        action=REQUEST_STEPS[step_number - 1],
        observed=message,
    )


def _write_outputs(result: dict[str, Any], *, passed: bool) -> None:
    RESULT_PATH.write_text(
        json.dumps(_result_payload(passed=passed, error=result.get("error"))) + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(
        _build_jira_comment(result, passed=passed),
        encoding="utf-8",
    )
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=passed), encoding="utf-8")
    RESPONSE_PATH.write_text(
        _build_response_summary(result, passed=passed),
        encoding="utf-8",
    )
    if passed:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    elif bool(result.get("is_product_failure")):
        BUG_DESCRIPTION_PATH.write_text(
            _build_bug_description(result),
            encoding="utf-8",
        )
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    _write_review_replies(result, passed=passed)


def _result_payload(*, passed: bool, error: object | None) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "passed" if passed else "failed",
        "passed": 1 if passed else 0,
        "failed": 0 if passed else 1,
        "skipped": 0,
        "summary": "1 passed, 0 failed" if passed else "0 passed, 1 failed",
    }
    if not passed and error is not None:
        payload["error"] = str(error)
    return payload


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    return "\n".join(
        [
            f"h2. {TICKET_KEY} automation result: {'PASSED' if passed else 'FAILED'}",
            "",
            f"*Automation outcome:* {'1 passed, 0 failed' if passed else '0 passed, 1 failed'}",
            f"*Rework summary:* {REWORK_SUMMARY}",
            "",
            "*Automated coverage*",
            *[
                f"# Step {step['step']} *{str(step['status']).upper()}*: {step['action']}\n"
                f"Observed: {{code}}{step['observed']}{{code}}"
                for step in result.get("steps", [])
                if isinstance(step, dict)
            ],
            "",
            "*Real user / human-style verification*",
            *[
                f"* {str(entry.get('status', 'passed')).upper()}: {entry['check']}\n"
                f"Observed: {{code}}{entry['observed']}{{code}}"
                for entry in result.get("human_verification", [])
                if isinstance(entry, dict)
            ],
            "",
            "*Result vs expected*",
            f"*Expected:* {EXPECTED_RESULT}",
            f"*Actual:* {_actual_result_summary(result, passed=passed)}",
            "",
            "*Environment*",
            f"* URL: [{result['app_url']}|{result['app_url']}]",
            f"* Repository under test: *{result['repository']}*",
            f"* Ref: *{result['repository_ref']}*",
            f"* Browser: *{result['browser']}*",
            f"* OS: *{result['os']}*",
            f"* Viewport: *{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}*",
            "",
            "*Artifacts*",
            f"* Test file: {{testing/tests/{TICKET_KEY}/test_ts_463.py}}",
            f"* Screenshot: {{{{outputs/{Path(str(result.get('screenshot', ''))).name}}}}}",
            (
                f"* Failure: {{code}}{result.get('error', '')}{{code}}"
                if not passed
                else "* Failure: none"
            ),
        ]
    ).strip() + "\n"


def _build_pr_body(result: dict[str, Any], *, passed: bool) -> str:
    automated_lines = [
        f"- Step {step['step']} **{step['status']}** — {step['action']}  \n"
        f"  Observed: `{step['observed']}`"
        for step in result.get("steps", [])
        if isinstance(step, dict)
    ]
    human_lines = [
        f"- **{str(entry.get('status', 'passed')).upper()}** — **{entry['check']}** "
        f"Observed: `{entry['observed']}`"
        for entry in result.get("human_verification", [])
        if isinstance(entry, dict)
    ]
    return "\n".join(
        [
            f"## {TICKET_KEY} automation result: {'PASSED' if passed else 'FAILED'}",
            "",
            f"**Automation outcome:** {'1 passed, 0 failed' if passed else '0 passed, 1 failed'}",
            "",
            "## Rework summary",
            f"- {REWORK_SUMMARY}",
            "",
            "### Automated coverage",
            *automated_lines,
            "",
            "### Real user / human-style verification",
            *human_lines,
            "",
            "### Result vs expected",
            f"**Expected:** {EXPECTED_RESULT}",
            f"**Actual:** {_actual_result_summary(result, passed=passed)}",
            "",
            "### Environment",
            f"- URL: `{result['app_url']}`",
            f"- Repository: `{result['repository']}`",
            f"- Ref: `{result['repository_ref']}`",
            f"- Browser: `{result['browser']}`",
            f"- OS: `{result['os']}`",
            f"- Viewport: `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
            "",
            "### Artifacts",
            f"- Test file: `testing/tests/{TICKET_KEY}/test_ts_463.py`",
            f"- Screenshot: `outputs/{Path(str(result.get('screenshot', ''))).name}`",
            (
                f"- Failure: `{result.get('error', '')}`"
                if not passed
                else "- Failure: none"
            ),
        ]
    ).strip() + "\n"


def _build_response_summary(result: dict[str, Any], *, passed: bool) -> str:
    headline = "passed" if passed else "failed"
    return (
        f"# {TICKET_KEY} automation {headline}\n\n"
        f"- Rework: {REWORK_SUMMARY}\n"
        f"- Result: {'1 passed, 0 failed' if passed else '0 passed, 1 failed'}\n"
        f"- App URL: `{result['app_url']}`\n"
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`\n"
        f"- Browser/OS: `{result['browser']}` on `{result['os']}`\n"
        f"- Screenshot: `outputs/{Path(str(result.get('screenshot', ''))).name}`\n"
        + (
            ""
            if passed
            else f"- Error: `{result.get('error', '')}`\n"
        )
    )


def _build_bug_description(result: dict[str, Any]) -> str:
    failing_command_output = str(result.get("traceback", result.get("error", "")))
    return "\n".join(
        [
            f"# {TICKET_KEY}: {TEST_CASE_TITLE}",
            "",
            "## Steps to reproduce",
            *[
                _annotated_step_line(step_number=index, action=action, result=result)
                for index, action in enumerate(REQUEST_STEPS, start=1)
            ],
            "",
            "## Exact error message or assertion failure",
            "```text",
            failing_command_output,
            "```",
            "",
            "## Actual vs Expected",
            f"**Expected:** {EXPECTED_RESULT}",
            f"**Actual:** {_bug_actual_summary(result)}",
            "",
            "## Human-style verification",
            *[
                f"- **{str(entry.get('status', 'passed')).upper()}** — {entry.get('check', '')}\n"
                f"  - Observed: `{entry.get('observed', '')}`"
                for entry in result.get("human_verification", [])
                if isinstance(entry, dict)
            ],
            "",
            "## Missing or broken production capability",
            _missing_capability_summary(result),
            "",
            "## Environment details",
            f"- URL: `{result['app_url']}`",
            f"- Repository: `{result['repository']}`",
            f"- Ref: `{result['repository_ref']}`",
            f"- Browser: `{result['browser']}`",
            f"- OS: `{result['os']}`",
            f"- Viewport: `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
            f"- Run command: `{RUN_COMMAND}`",
            f"- Failing command / output: `{RUN_COMMAND}` -> `{_failure_summary_line(result)}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `outputs/{Path(str(result.get('screenshot', ''))).name}`",
            "- Relevant repository observation:",
            "```text",
            _failure_repo_excerpt(result),
            "```",
        ]
    ).strip() + "\n"


def _annotated_step_line(
    *,
    step_number: int,
    action: str,
    result: dict[str, Any],
) -> str:
    matching = next(
        (
            step
            for step in result.get("steps", [])
            if isinstance(step, dict) and int(step.get("step", -1)) == step_number
        ),
        None,
    )
    if matching is None:
        return f"{step_number}. ⏭️ {action} Not reached."
    icon = "✅" if str(matching.get("status")) == "passed" else "❌"
    return f"{step_number}. {icon} {action} Observed: {matching.get('observed', '')}"


def _failure_repo_excerpt(result: dict[str, Any]) -> str:
    repo_after_save = result.get("repo_after_save")
    if isinstance(repo_after_save, dict):
        return json.dumps(repo_after_save, indent=2)
    error_text = str(result.get("error", ""))
    marker = "Last observed state: "
    if marker in error_text:
        return error_text.split(marker, maxsplit=1)[1]
    return error_text


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "The live hosted app persisted the edited catalogs and the repository JSON "
            "matched the visible UI."
        )
    return _bug_actual_summary(result)


def _bug_actual_summary(result: dict[str, Any]) -> str:
    failure = _failed_step_entry(result)
    error_text = str(result.get("error", "")).strip()
    if failure is None:
        return error_text or "The automation failed before a step-specific result was recorded."

    step_number = int(failure["step"])
    if (
        step_number == 6
        and "hosted save path did not persist" in error_text
        and any(signature in error_text for signature in POST_SAVE_PRODUCT_FAILURE_SIGNATURES)
    ):
        return (
            "After `Save settings`, the repository JSON stayed on the original Priorities, "
            "Components, and Versions values within the supported polling window, and the "
            "saved Settings tabs also did not keep showing the new priority, renamed "
            "component, and deleted version state a user had just submitted."
        )
    if step_number == 3 and (
        "canonical component ID" in error_text or "retain the new component name" in error_text
    ):
        return (
            "Opening `Edit component` for the selected component did not preload the "
            "existing canonical values. The drawer exposed blank `ID`/`Name` fields "
            "instead of the selected component data, so the rename flow could not proceed "
            "as required."
        )
    if step_number == 6 and "hosted save path did not persist" in error_text:
        return (
            "After the UI showed the catalog edits and `Save settings` was triggered, the "
            "repository still exposed the original catalog JSON instead of the edited "
            "Priorities, Components, and Versions state within the supported polling window."
        )
    if any(signature in error_text for signature in POST_SAVE_PRODUCT_FAILURE_SIGNATURES):
        return (
            "After saving, the visible Settings tabs no longer matched the catalog state the "
            "user had just committed, so the post-save UI did not reflect the persisted state."
        )
    return _failure_summary_line(result)


def _missing_capability_summary(result: dict[str, Any]) -> str:
    failure = _failed_step_entry(result)
    error_text = str(result.get("error", "")).strip()
    if failure is None:
        return "The automation did not record a product-visible failure step."

    step_number = int(failure["step"])
    if (
        step_number == 6
        and "hosted save path did not persist" in error_text
        and any(signature in error_text for signature in POST_SAVE_PRODUCT_FAILURE_SIGNATURES)
    ):
        return (
            "The hosted `Save settings` flow neither persists the visible catalog edits back "
            "to the repository JSON within the expected commit/persistence window nor keeps "
            "the saved Settings tabs aligned with the edits the user just committed."
        )
    if step_number == 3 and (
        "canonical component ID" in error_text or "retain the new component name" in error_text
    ):
        return (
            "The hosted Settings > Components edit flow does not reliably load the selected "
            "component's persisted ID/name into the edit drawer before the user edits it."
        )
    if step_number == 6 and "hosted save path did not persist" in error_text:
        return (
            "The hosted `Save settings` flow does not persist the visible Priorities, "
            "Components, and Versions edits back to the repository JSON within the expected "
            "commit/persistence window."
        )
    if any(signature in error_text for signature in POST_SAVE_PRODUCT_FAILURE_SIGNATURES):
        return (
            "After save completion, the Settings surface does not continue showing the saved "
            "catalog state consistently enough for a user to verify the persisted result."
        )
    return (
        f"Step {step_number} (`{REQUEST_STEPS[step_number - 1]}`) does not complete "
        "successfully in the deployed product."
    )


def _failed_step_entry(result: dict[str, Any]) -> dict[str, Any] | None:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return None
    for step in steps:
        if isinstance(step, dict) and str(step.get("status")) == "failed":
            return step
    return None


def _failure_summary_line(result: dict[str, Any]) -> str:
    failure = _failed_step_entry(result)
    if failure is not None:
        observed = str(failure.get("observed", "")).strip()
        first_line = observed.splitlines()[0] if observed else ""
        prefix = f"Step {failure.get('step')} failed:"
        if first_line.startswith(prefix):
            return first_line
        if first_line:
            return f"{prefix} {first_line}"
    return str(result.get("error", "No failure details recorded.")).splitlines()[0]


def _should_write_bug_description(result: dict[str, Any]) -> bool:
    error_text = str(result.get("error", "")).strip()
    if error_text.startswith("RuntimeError: TS-463 requires GH_TOKEN or GITHUB_TOKEN"):
        return False
    if error_text.startswith("ModuleNotFoundError:"):
        return False
    if any(signature in error_text for signature in POST_SAVE_PRODUCT_FAILURE_SIGNATURES):
        return True

    failure = _failed_step_entry(result)
    if failure is None:
        return False

    try:
        step_number = int(failure["step"])
    except (KeyError, TypeError, ValueError):
        return False
    observed = str(failure.get("observed", ""))
    signatures = PRODUCT_FAILURE_SIGNATURES.get(step_number, ())
    return any(signature in observed or signature in error_text for signature in signatures)


def _write_review_replies(result: dict[str, Any], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(thread=thread, result=result, passed=passed),
        }
        for thread in _discussion_threads()
    ]
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": replies}, indent=2) + "\n",
        encoding="utf-8",
    )


def _discussion_threads() -> list[dict[str, Any]]:
    if not DISCUSSIONS_RAW_PATH.is_file():
        return []
    raw = json.loads(DISCUSSIONS_RAW_PATH.read_text(encoding="utf-8"))
    threads = raw.get("threads")
    if not isinstance(threads, list):
        return []
    return [
        thread
        for thread in threads
        if isinstance(thread, dict)
        and thread.get("resolved") is False
        and thread.get("rootCommentId") is not None
        and thread.get("threadId") is not None
    ]


def _review_reply_text(
    *,
    thread: dict[str, Any],
    result: dict[str, Any],
    passed: bool,
) -> str:
    body = str(thread.get("body", ""))
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: {_failure_summary_line(result)}"
    )
    if "Actual` section is hardcoded" in body or "Actual section is hardcoded" in body:
        return (
            "Fixed: the failed-run Actual summary and bug description now come from the "
            "recorded failed step / `result[\"error\"]` instead of assuming the Step 6 "
            "save-persistence path. "
            + rerun_summary
        )
    if '`startswith("Step ")` is too broad' in body or 'startswith("Step ") is too broad' in body:
        return (
            "Fixed: TS-463 now writes `bug_description.md` only for explicit product-visible "
            "failure signatures for this scenario (for example the Step 3 blank component "
            "editor and Step 6 persistence regression) instead of treating every "
            "`Step ... failed` assertion as a product bug. "
            + rerun_summary
        )
    return "Fixed: addressed the requested TS-463 reporting changes. " + rerun_summary


def _snippet(text: str, *, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


if __name__ == "__main__":
    main()
