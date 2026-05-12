from __future__ import annotations

import json
import os
import re
import sys
import traceback
from pathlib import Path

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
PROJECT_PATH = "DEMO"
PRIORITIES_PATH = f"{PROJECT_PATH}/config/priorities.json"
COMPONENTS_PATH = f"{PROJECT_PATH}/config/components.json"
VERSIONS_PATH = f"{PROJECT_PATH}/config/versions.json"
PRIORITY_ID = "ultra"
PRIORITY_NAME = "Ultra High"
TEMP_VERSION_ID = "ts463-unused"
TEMP_VERSION_NAME = "TS-463 Disposable Version"
DESKTOP_VIEWPORT = {"width": 1440, "height": 1200}
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts463_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts463_success.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

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

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
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

                repo_after_save = _wait_for_catalog_repo_state(
                    service=service,
                    expected_component_id=str(target_component["id"]),
                    expected_component_name=target_component_name,
                )
                result["repo_after_save"] = repo_after_save
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
                    raise AssertionError(
                        "Human verification failed: the saved Settings tabs did not present "
                        "the same visible catalog state a user would expect after saving.\n"
                        f"Priorities text:\n{priorities_text_saved}\n\n"
                        f"Priority aria-labels:\n{priorities_labels_saved}\n\n"
                        f"Components text:\n{components_text_saved}\n\n"
                        f"Component aria-labels:\n{components_labels_saved}\n\n"
                        f"Versions text:\n{versions_text_saved}\n\n"
                        f"Version aria-labels:\n{versions_labels_saved}",
                    )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                result["human_verification"] = {
                    "checked": [
                        "the Project settings administration heading",
                        "the Priorities, Components, and Versions tabs",
                        "the Add priority drawer title plus ID/Name inputs",
                        f'the visible Priority row for "{PRIORITY_NAME}" with ID "{PRIORITY_ID}"',
                        (
                            f'the visible Component row for ID "{target_component["id"]}" '
                            f'after renaming it to "{target_component_name}"'
                        ),
                        f'that the deleted Version "{TEMP_VERSION_NAME}" no longer appears',
                        "that the editor stayed in a desktop drawer-style surface aligned to the right side",
                    ],
                    "observed": {
                        "priority_visible_text": priorities_text_saved,
                        "priority_visible_labels": priorities_labels_saved,
                        "component_visible_text": components_text_saved,
                        "component_visible_labels": components_labels_saved,
                        "versions_visible_text": versions_text_saved,
                        "versions_visible_labels": versions_labels_saved,
                        "priority_editor_presentation": _editor_payload(priority_editor),
                    },
                }
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
    _write_result_if_requested(result)
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


def _wait_for_catalog_repo_state(
    *,
    service: LiveSetupRepositoryService,
    expected_component_id: str,
    expected_component_name: str,
    timeout_seconds: int = 90,
) -> dict[str, object]:
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
    if not matched:
        raise AssertionError(
            "Step 6 failed: the hosted save path did not persist the expected catalog "
            "state within the timeout.\n"
            f"Last observed state: {last_observation}",
        )
    return last_observation


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
    configured_path = os.environ.get("TS463_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts463_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
