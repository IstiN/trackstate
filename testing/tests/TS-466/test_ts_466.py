from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_settings_locales_page import (  # noqa: E402
    LiveSettingsLocalesPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-466"
PROJECT_PATH = "DEMO"
TARGET_LOCALE = "es"
EXPECTED_CATALOG_TITLES = [
    "Statuses",
    "Issue Types",
    "Fields",
    "Priorities",
    "Components",
    "Versions",
    "Resolutions",
]
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts466_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts466_success.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-466 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    default_locale = _project_default_locale(service)
    priority_seed = _first_catalog_entry(
        service._read_repo_json(f"{PROJECT_PATH}/config/priorities.json"),
        subject="priority",
    )
    status_seed = _first_catalog_entry(
        service._read_repo_json(f"{PROJECT_PATH}/config/statuses.json"),
        subject="status",
    )
    locale_state_before = _locale_state(service, TARGET_LOCALE)
    expected_priority_translation = f"{priority_seed['name']} ES TS-466"
    expected_status_warning = (
        f'Missing translation. Using fallback "{status_seed["name"]}" from '
        f"{default_locale}."
    )

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "project": PROJECT_PATH,
        "target_locale": TARGET_LOCALE,
        "default_locale": default_locale,
        "expected_catalog_titles": EXPECTED_CATALOG_TITLES,
        "priority_entry": priority_seed,
        "status_entry": status_seed,
        "expected_priority_translation": expected_priority_translation,
        "expected_status_warning": expected_status_warning,
        "locale_state_before": locale_state_before,
        "steps": [],
    }

    locale_saved = False
    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            page = LiveSettingsLocalesPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the Locales scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the hosted tracker.",
                    observed=runtime.body_text,
                )

                page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Confirm the hosted session is connected with GitHub access.",
                    observed=page.current_body_text(),
                )

                settings_text = page.open_settings_admin()
                locales_text = page.open_locales_tab()
                result["settings_body_text"] = settings_text
                result["locales_body_text"] = locales_text
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Navigate to Settings > Locales.",
                    observed=locales_text,
                )

                if not page.locale_exists(TARGET_LOCALE):
                    page.add_locale(TARGET_LOCALE)
                    result["locale_added_in_test"] = True
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action=f'Add the secondary locale "{TARGET_LOCALE}" to satisfy the precondition.',
                        observed=page.current_body_text(),
                    )
                else:
                    page.select_locale(TARGET_LOCALE)
                    result["locale_added_in_test"] = False
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action=f'Select the existing "{TARGET_LOCALE}" locale.',
                        observed=page.current_body_text(),
                    )

                observed_titles = page.catalog_titles()
                result["observed_catalog_titles"] = observed_titles
                if observed_titles != EXPECTED_CATALOG_TITLES:
                    raise AssertionError(
                        "Step 5 failed: Settings > Locales did not expose the seven "
                        "mandatory editable catalogs in the expected live UI order.\n"
                        f"Expected titles: {EXPECTED_CATALOG_TITLES}\n"
                        f"Observed titles: {observed_titles}\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Verify that statuses, issue types, fields, priorities, components, versions, and resolutions are all editable.",
                    observed=", ".join(observed_titles),
                )

                priority_before = page.entry_observation(
                    section_title="Priorities",
                    locale=TARGET_LOCALE,
                    entry_id=str(priority_seed["id"]),
                )
                status_before = page.entry_observation(
                    section_title="Statuses",
                    locale=TARGET_LOCALE,
                    entry_id=str(status_seed["id"]),
                )
                result["priority_before"] = _entry_payload(priority_before)
                result["status_before"] = _entry_payload(status_before)

                priority_after = page.fill_translation(
                    section_title="Priorities",
                    locale=TARGET_LOCALE,
                    entry_id=str(priority_seed["id"]),
                    value=expected_priority_translation,
                )
                if priority_after.translation != expected_priority_translation:
                    raise AssertionError(
                        "Step 6 failed: the Priority translation field did not keep the "
                        "typed value in the live Locales editor.\n"
                        f'Expected translation: "{expected_priority_translation}"\n'
                        f'Observed translation: "{priority_after.translation}"\n'
                        f"Observed row: {priority_after.row_label}",
                    )
                result["priority_after_edit"] = _entry_payload(priority_after)
                _record_step(
                    result,
                    step=6,
                    status="passed",
                    action=f'Enter a translation for Priority ID {priority_seed["id"]}.',
                    observed=priority_after.row_label,
                )

                status_after = page.fill_translation(
                    section_title="Statuses",
                    locale=TARGET_LOCALE,
                    entry_id=str(status_seed["id"]),
                    value="",
                )
                result["status_after_edit"] = _entry_payload(status_after)
                if status_after.warning_text != expected_status_warning:
                    raise AssertionError(
                        "Step 7 failed: leaving the Status translation empty did not show "
                        "the expected inline fallback warning in the live Locales editor.\n"
                        f'Expected warning: "{expected_status_warning}"\n'
                        f'Observed warning: "{status_after.warning_text}"\n'
                        f"Observed row: {status_after.row_label}\n"
                        f"Observed body text:\n{page.current_body_text()}",
                    )
                _record_step(
                    result,
                    step=7,
                    status="passed",
                    action=f'Leave Status ID {status_seed["id"]} empty and observe the inline warning state.',
                    observed=status_after.warning_text or "",
                )

                page.save_settings()
                _wait_for_locale_repo_state(
                    service=service,
                    locale=TARGET_LOCALE,
                    expected_locale_present=True,
                    expected_priority_translation=expected_priority_translation,
                    expected_priority_id=str(priority_seed["id"]),
                    expected_status_translation=None,
                    expected_status_id=str(status_seed["id"]),
                )
                locale_saved = True
                _record_step(
                    result,
                    step=8,
                    status="passed",
                    action="Save the live project settings.",
                    observed="The saved locale file persisted the edited priority translation while keeping the status translation empty.",
                )

                page.open_locales_tab()
                page.select_locale(TARGET_LOCALE)
                priority_saved = page.entry_observation(
                    section_title="Priorities",
                    locale=TARGET_LOCALE,
                    entry_id=str(priority_seed["id"]),
                )
                status_saved = page.entry_observation(
                    section_title="Statuses",
                    locale=TARGET_LOCALE,
                    entry_id=str(status_seed["id"]),
                )
                result["priority_after_save"] = _entry_payload(priority_saved)
                result["status_after_save"] = _entry_payload(status_saved)
                if priority_saved.translation != expected_priority_translation:
                    raise AssertionError(
                        "Step 9 failed: after saving, the Priority translation was not "
                        "visibly preserved in Settings > Locales.\n"
                        f'Expected translation: "{expected_priority_translation}"\n'
                        f'Observed translation: "{priority_saved.translation}"\n'
                        f"Observed row: {priority_saved.row_label}",
                    )
                if status_saved.warning_text != expected_status_warning:
                    raise AssertionError(
                        "Step 9 failed: after saving, the empty Status translation no "
                        "longer showed the expected inline fallback warning.\n"
                        f'Expected warning: "{expected_status_warning}"\n'
                        f'Observed warning: "{status_saved.warning_text}"\n'
                        f"Observed row: {status_saved.row_label}",
                    )
                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                result["human_verification"] = {
                    "checked": [
                        "the visible Locales tab headings for all seven catalogs",
                        f'the Priority row for ID {priority_seed["id"]}',
                        f'the Status row for ID {status_seed["id"]}',
                        "the inline fallback warning text shown under the empty Status field",
                    ],
                    "observed": {
                        "priority_row_label": priority_saved.row_label,
                        "priority_translation": priority_saved.translation,
                        "status_row_label": status_saved.row_label,
                        "status_warning": status_saved.warning_text,
                    },
                }
                _record_step(
                    result,
                    step=9,
                    status="passed",
                    action="Re-open the saved Locales screen and verify the persisted user-visible state.",
                    observed=(
                        f'Priority "{priority_saved.translation}" remained visible and '
                        f'the Status warning stayed visible as "{status_saved.warning_text}".'
                    ),
                )
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
        cleanup_result = _restore_locale_state(
            config=config,
            service=service,
            token=token,
            user_login=user.login,
            locale_state_before=locale_state_before,
            priority_entry_id=str(priority_seed["id"]),
            status_entry_id=str(status_seed["id"]),
            locale_saved=locale_saved,
        )
        result["cleanup"] = cleanup_result

    result["status"] = "passed"
    result["summary"] = (
        "Verified that Settings > Locales exposes all seven editable catalogs, "
        "accepts a live Priority translation, shows the inline fallback warning for "
        "an empty Status translation, and still saves the visible result."
    )
    _write_result_if_requested(result)
    print(json.dumps(result, indent=2))


def _project_default_locale(service: LiveSetupRepositoryService) -> str:
    project_json = service._read_repo_json(f"{PROJECT_PATH}/project.json")
    return str(project_json.get("defaultLocale", "en"))


def _first_catalog_entry(entries: object, *, subject: str) -> dict[str, str]:
    if not isinstance(entries, list):
        raise AssertionError(
            f"Precondition failed: {subject} config did not load as a JSON array.",
        )
    for item in entries:
        if not isinstance(item, dict):
            continue
        entry_id = str(item.get("id", "")).strip()
        name = str(item.get("name", "")).strip()
        if entry_id and name:
            return {"id": entry_id, "name": name}
    raise AssertionError(
        f"Precondition failed: the live repository does not expose any seeded {subject} entries.",
    )


def _locale_state(
    service: LiveSetupRepositoryService,
    locale: str,
) -> dict[str, object]:
    project_json = service._read_repo_json(f"{PROJECT_PATH}/project.json")
    supported_locales = [
        str(value).strip()
        for value in project_json.get("supportedLocales", [])
        if str(value).strip()
    ]
    state: dict[str, object] = {
        "supported_locales": supported_locales,
        "locale_present": locale in supported_locales,
    }
    if locale in supported_locales:
        state["locale_payload"] = _read_locale_payload(service, locale)
    return state


def _read_locale_payload(
    service: LiveSetupRepositoryService,
    locale: str,
) -> dict[str, object]:
    try:
        payload = service._read_repo_json(f"{PROJECT_PATH}/config/i18n/{locale}.json")
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _wait_for_locale_repo_state(
    *,
    service: LiveSetupRepositoryService,
    locale: str,
    expected_locale_present: bool,
    expected_priority_translation: str | None,
    expected_priority_id: str,
    expected_status_translation: str | None,
    expected_status_id: str,
    timeout_seconds: int = 90,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_observation: dict[str, object] | None = None
    while time.monotonic() < deadline:
        project_json = service._read_repo_json(f"{PROJECT_PATH}/project.json")
        supported_locales = [
            str(value).strip()
            for value in project_json.get("supportedLocales", [])
            if str(value).strip()
        ]
        locale_present = locale in supported_locales

        locale_payload = _read_locale_payload(service, locale) if locale_present else {}
        priorities = locale_payload.get("priorities", {})
        statuses = locale_payload.get("statuses", {})
        priority_translation = (
            str(priorities.get(expected_priority_id, ""))
            if isinstance(priorities, dict)
            else ""
        )
        status_translation = (
            str(statuses.get(expected_status_id, ""))
            if isinstance(statuses, dict)
            else ""
        )
        last_observation = {
            "supported_locales": supported_locales,
            "locale_payload": locale_payload,
            "priority_translation": priority_translation,
            "status_translation": status_translation,
        }

        if locale_present != expected_locale_present:
            time.sleep(2)
            continue

        priority_matches = priority_translation == (expected_priority_translation or "")
        status_matches = status_translation == (expected_status_translation or "")
        if expected_priority_translation is None:
            priority_matches = priority_translation == ""
        if expected_status_translation is None:
            status_matches = status_translation == ""

        if locale_present == expected_locale_present and priority_matches and status_matches:
            return
        time.sleep(2)

    raise AssertionError(
        "The hosted save path did not persist the expected locale state within the "
        f"timeout for locale {locale}.\n"
        f"Expected locale present: {expected_locale_present}\n"
        f'Expected priority translation for "{expected_priority_id}": '
        f'{expected_priority_translation!r}\n'
        f'Expected status translation for "{expected_status_id}": '
        f'{expected_status_translation!r}\n'
        f"Last observed state: {last_observation}",
    )


def _restore_locale_state(
    *,
    config,
    service: LiveSetupRepositoryService,
    token: str,
    user_login: str,
    locale_state_before: dict[str, object],
    priority_entry_id: str,
    status_entry_id: str,
    locale_saved: bool,
) -> dict[str, object]:
    if not locale_saved:
        return {"status": "not-needed", "reason": "No persisted locale mutation was observed."}

    supported_before = locale_state_before.get("supported_locales", [])
    locale_present_before = bool(locale_state_before.get("locale_present"))
    locale_payload_before = locale_state_before.get("locale_payload", {})
    if not isinstance(locale_payload_before, dict):
        locale_payload_before = {}

    priority_before = _lookup_translation(
        locale_payload_before,
        section="priorities",
        entry_id=priority_entry_id,
    )
    status_before = _lookup_translation(
        locale_payload_before,
        section="statuses",
        entry_id=status_entry_id,
    )

    with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
        page = LiveSettingsLocalesPage(tracker_page)
        runtime = tracker_page.open()
        if runtime.kind != "ready":
            return {
                "status": "failed",
                "reason": "Cleanup could not reopen the hosted tracker shell.",
                "runtime_state": runtime.kind,
                "runtime_body_text": runtime.body_text,
            }
        page.ensure_connected(
            token=token,
            repository=service.repository,
            user_login=user_login,
        )
        page.open_settings_admin()
        page.open_locales_tab()

        if locale_present_before:
            if not page.locale_exists(TARGET_LOCALE):
                page.add_locale(TARGET_LOCALE)
            page.select_locale(TARGET_LOCALE)
            page.fill_translation(
                section_title="Priorities",
                locale=TARGET_LOCALE,
                entry_id=priority_entry_id,
                value=priority_before or "",
            )
            page.fill_translation(
                section_title="Statuses",
                locale=TARGET_LOCALE,
                entry_id=status_entry_id,
                value=status_before or "",
            )
            page.save_settings()
            _wait_for_locale_repo_state(
                service=service,
                locale=TARGET_LOCALE,
                expected_locale_present=True,
                expected_priority_translation=priority_before or None,
                expected_priority_id=priority_entry_id,
                expected_status_translation=status_before or None,
                expected_status_id=status_entry_id,
            )
            return {
                "status": "restored",
                "supported_locales": supported_before,
                "priority_translation": priority_before or "",
                "status_translation": status_before or "",
            }

        if page.locale_exists(TARGET_LOCALE):
            page.remove_locale(TARGET_LOCALE)
            page.save_settings()
            _wait_for_locale_repo_state(
                service=service,
                locale=TARGET_LOCALE,
                expected_locale_present=False,
                expected_priority_translation=None,
                expected_priority_id=priority_entry_id,
                expected_status_translation=None,
                expected_status_id=status_entry_id,
            )
        return {
            "status": "restored",
            "supported_locales": supported_before,
            "priority_translation": "",
            "status_translation": "",
        }


def _lookup_translation(
    locale_payload: dict[str, object],
    *,
    section: str,
    entry_id: str,
) -> str:
    entries = locale_payload.get(section, {})
    if not isinstance(entries, dict):
        return ""
    return str(entries.get(entry_id, ""))


def _entry_payload(entry) -> dict[str, object]:
    return {
        "section_title": entry.section_title,
        "row_label": entry.row_label,
        "entry_name": entry.entry_name,
        "entry_id": entry.entry_id,
        "translation": entry.translation,
        "warning_text": entry.warning_text,
        "input_index": entry.input_index,
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


def _write_result_if_requested(payload: dict[str, object]) -> None:
    configured_path = os.environ.get("TS466_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts466_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
