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

from testing.components.pages.live_settings_locales_page import (  # noqa: E402
    LiveSettingsLocalesPage,
)
from testing.components.services.live_locale_warning_visual_probe import (  # noqa: E402
    LiveLocaleWarningVisualProbe,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedCatalogEntry,
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
EXPECTED_WARNING_COLORS = {
    "rgb(193, 179, 65)",
    "rgb(247, 201, 102)",
}
EXPECTED_WARNING_BACKGROUND_COLORS = {
    "rgb(241, 228, 213)",
    "rgb(36, 40, 39)",
}
WARNING_MIN_CONTRAST_RATIO = 4.5
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts466_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts466_success.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    warning_visual_probe = LiveLocaleWarningVisualProbe()
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-466 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    project_locale_configuration = service.fetch_project_locale_configuration(PROJECT_PATH)
    default_locale = project_locale_configuration.default_locale
    requested_target_locale = TARGET_LOCALE
    target_locale = requested_target_locale
    priority_seed = _first_catalog_entry(
        service.fetch_catalog_entries(PROJECT_PATH, "priorities"),
        subject="priority",
    )
    status_seed = _first_catalog_entry(
        service.fetch_catalog_entries(PROJECT_PATH, "statuses"),
        subject="status",
    )
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
        "requested_target_locale": requested_target_locale,
        "target_locale": target_locale,
        "default_locale": default_locale,
        "expected_catalog_titles": EXPECTED_CATALOG_TITLES,
        "priority_entry": priority_seed,
        "status_entry": status_seed,
        "expected_priority_translation": expected_priority_translation,
        "expected_status_warning": expected_status_warning,
        "steps": [],
    }

    locale_added_in_test = False
    cleanup_target_locale: str | None = None
    cleanup_priority_translation: str | None = None
    cleanup_status_translation: str | None = None
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

                existing_secondary_locales = [
                    locale
                    for locale in page.locale_codes()
                    if locale != default_locale
                ]
                if page.locale_exists(requested_target_locale):
                    target_locale = requested_target_locale
                    page.select_locale(target_locale)
                    step_4_action = f'Select the existing "{target_locale}" locale.'
                elif existing_secondary_locales:
                    target_locale = existing_secondary_locales[0]
                    page.select_locale(target_locale)
                    step_4_action = (
                        f'Select the existing secondary locale "{target_locale}" to '
                        "satisfy the precondition."
                    )
                else:
                    target_locale = page.add_locale(requested_target_locale)
                    page.select_locale(target_locale)
                    locale_added_in_test = True
                    step_4_action = (
                        f'Add the requested secondary locale "{requested_target_locale}" '
                        "to satisfy the precondition."
                    )
                    if target_locale != requested_target_locale:
                        step_4_action = (
                            f'Add a secondary locale to satisfy the precondition '
                            f'(requested "{requested_target_locale}", observed "{target_locale}").'
                        )

                result["target_locale"] = target_locale
                result["locale_added_in_test"] = locale_added_in_test
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=step_4_action,
                    observed=page.current_body_text(),
                )

                observed_titles = page.catalog_titles()
                result["observed_catalog_titles"] = observed_titles
                missing_titles = [
                    title for title in EXPECTED_CATALOG_TITLES if title not in observed_titles
                ]
                extra_titles = [
                    title for title in observed_titles if title not in EXPECTED_CATALOG_TITLES
                ]
                result["missing_catalog_titles"] = missing_titles
                result["extra_catalog_titles"] = extra_titles
                if missing_titles:
                    extra_titles_note = (
                        f"\nAdditional titles: {extra_titles}" if extra_titles else ""
                    )
                    raise AssertionError(
                        "Step 5 failed: Settings > Locales did not expose all seven "
                        "mandatory editable catalogs.\n"
                        f"Missing titles: {missing_titles}\n"
                        f"Observed titles: {observed_titles}"
                        f"{extra_titles_note}\n"
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
                    locale=target_locale,
                    entry_id=str(priority_seed["id"]),
                )
                status_before = page.entry_observation(
                    section_title="Statuses",
                    locale=target_locale,
                    entry_id=str(status_seed["id"]),
                )
                result["priority_before"] = _entry_payload(priority_before)
                result["status_before"] = _entry_payload(status_before)
                cleanup_target_locale = target_locale
                cleanup_priority_translation = priority_before.translation
                cleanup_status_translation = status_before.translation

                priority_after = page.fill_translation(
                    section_title="Priorities",
                    locale=target_locale,
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
                    locale=target_locale,
                    entry_id=str(status_seed["id"]),
                    value="",
                )
                result["status_after_edit"] = _entry_payload(status_after)
                status_after_warning_visual = _assert_warning_state(
                    page=page,
                    step=7,
                    entry=status_after,
                    expected_warning_text=expected_status_warning,
                    page_body_text=page.current_body_text(),
                    warning_visual_probe=warning_visual_probe,
                )
                result["status_after_edit_warning_visual"] = status_after_warning_visual
                _record_step(
                    result,
                    step=7,
                    status="passed",
                    action=f'Leave Status ID {status_seed["id"]} empty and observe the inline warning state.',
                    observed=_warning_state_summary(status_after),
                )

                page.save_settings()
                _record_step(
                    result,
                    step=8,
                    status="passed",
                    action="Save the live project settings.",
                    observed=(
                        "The UI accepted the save action without blocking the empty "
                        "Status translation warning."
                    ),
                )

                page.open_locales_tab()
                page.select_locale(target_locale)
                priority_saved = page.entry_observation(
                    section_title="Priorities",
                    locale=target_locale,
                    entry_id=str(priority_seed["id"]),
                )
                status_saved = page.entry_observation(
                    section_title="Statuses",
                    locale=target_locale,
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
                status_after_save_warning_visual = _assert_warning_state(
                    page=page,
                    step=9,
                    entry=status_saved,
                    expected_warning_text=expected_status_warning,
                    page_body_text=page.current_body_text(),
                    warning_visual_probe=warning_visual_probe,
                )
                result["status_after_save_warning_visual"] = status_after_save_warning_visual
                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                result["human_verification"] = {
                    "checked": [
                        "the visible Locales tab headings for all seven catalogs",
                        f'the Priority row for ID {priority_seed["id"]}',
                        f'the Status row for ID {status_seed["id"]}',
                        "the inline fallback warning text shown under the empty Status field",
                        "the warning pill styling for the empty Status field",
                    ],
                    "observed": {
                        "priority_row_label": priority_saved.row_label,
                        "priority_translation": priority_saved.translation,
                        "status_row_label": status_saved.row_label,
                        "status_warning": status_saved.warning_text,
                        "status_warning_text_color": status_saved.warning_text_color,
                        "status_warning_border_color": status_saved.warning_border_color,
                        "status_warning_background_color": (
                            status_saved.warning_background_color
                        ),
                        "status_warning_border_width": status_saved.warning_border_width,
                    },
                }
                _record_step(
                    result,
                    step=9,
                    status="passed",
                    action="Re-open the saved Locales screen and verify the persisted user-visible state.",
                    observed=(
                        f'Priority "{priority_saved.translation}" remained visible and '
                        f"the Status warning stayed visible with "
                        f"{_warning_state_summary(status_saved)}."
                    ),
                )
            except Exception:
                page.screenshot(str(SCREENSHOT_PATH))
                result["screenshot"] = str(SCREENSHOT_PATH)
                raise
            finally:
                result["cleanup"] = _restore_ui_state(
                    page=page,
                    locale=cleanup_target_locale,
                    locale_added_in_test=locale_added_in_test,
                    priority_entry_id=str(priority_seed["id"]),
                    priority_translation=cleanup_priority_translation,
                    status_entry_id=str(status_seed["id"]),
                    status_translation=cleanup_status_translation,
                )
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

    result["status"] = "passed"
    result["summary"] = (
        "Verified that Settings > Locales exposes all seven editable catalogs, "
        "accepts a live Priority translation, shows the inline fallback warning for "
        "an empty Status translation, and still saves the visible result."
    )
    _write_result_if_requested(result)
    print(json.dumps(result, indent=2))

def _first_catalog_entry(
    entries: list[LiveHostedCatalogEntry],
    *,
    subject: str,
) -> dict[str, str]:
    for item in entries:
        if item.id and item.name:
            return {"id": item.id, "name": item.name}
    raise AssertionError(
        f"Precondition failed: the live repository does not expose any seeded {subject} entries.",
    )


def _restore_ui_state(
    *,
    page: LiveSettingsLocalesPage | None,
    locale: str | None,
    locale_added_in_test: bool,
    priority_entry_id: str,
    priority_translation: str | None,
    status_entry_id: str,
    status_translation: str | None,
) -> dict[str, object]:
    if page is None or locale is None:
        return {"status": "not-needed", "reason": "No live page was available for cleanup."}

    try:
        page.open_locales_tab()
        if locale_added_in_test:
            if page.locale_exists(locale):
                page.remove_locale(locale)
                page.save_settings()
            return {
                "status": "restored",
                "target_locale": locale,
                "locale_removed": True,
            }

        if priority_translation is None or status_translation is None:
            return {
                "status": "not-needed",
                "reason": "No editable locale values were captured before mutation.",
            }

        if not page.locale_exists(locale):
            return {
                "status": "failed",
                "reason": f'Cleanup could not find the "{locale}" locale chip.',
            }

        page.select_locale(locale)
        page.fill_translation(
            section_title="Priorities",
            locale=locale,
            entry_id=priority_entry_id,
            value=priority_translation,
        )
        page.fill_translation(
            section_title="Statuses",
            locale=locale,
            entry_id=status_entry_id,
            value=status_translation,
        )
        page.save_settings()
        return {
            "status": "restored",
            "target_locale": locale,
            "priority_translation": priority_translation,
            "status_translation": status_translation,
        }
    except Exception as error:
        return {
            "status": "failed",
            "reason": f"{type(error).__name__}: {error}",
        }


def _entry_payload(entry) -> dict[str, object]:
    return {
        "section_title": entry.section_title,
        "row_label": entry.row_label,
        "entry_name": entry.entry_name,
        "entry_id": entry.entry_id,
        "translation": entry.translation,
        "warning_text": entry.warning_text,
        "warning_text_color": entry.warning_text_color,
        "warning_border_color": entry.warning_border_color,
        "warning_background_color": entry.warning_background_color,
        "warning_border_width": entry.warning_border_width,
        "input_index": entry.input_index,
        "input_rect": {
            "left": entry.input_rect.left,
            "top": entry.input_rect.top,
            "width": entry.input_rect.width,
            "height": entry.input_rect.height,
        },
    }


def _assert_warning_state(
    *,
    page: LiveSettingsLocalesPage,
    step: int,
    entry,
    expected_warning_text: str,
    page_body_text: str,
    warning_visual_probe: LiveLocaleWarningVisualProbe,
) -> dict[str, object] | None:
    if entry.warning_text != expected_warning_text:
        raise AssertionError(
            f"Step {step} failed: the empty Status translation did not show the "
            "expected inline fallback warning in the live Locales editor.\n"
            f'Expected warning: "{expected_warning_text}"\n'
            f'Observed warning: "{entry.warning_text}"\n'
            f"Observed row: {entry.row_label}\n"
            f"Observed body text:\n{page_body_text}",
        )

    normalized_text_color = _normalize_css_color(entry.warning_text_color)
    normalized_border_color = _normalize_css_color(entry.warning_border_color)
    normalized_background_color = _normalize_css_color(entry.warning_background_color)
    border_width = _parse_css_pixels(entry.warning_border_width)
    if (
        normalized_text_color is None
        or normalized_border_color is None
        or normalized_background_color is None
        or border_width <= 0
    ):
        warning_screenshot_path = OUTPUTS_DIR / f"ts466_warning_step_{step}.png"
        page.screenshot(str(warning_screenshot_path))
        visual_observation = warning_visual_probe.observe(
            screenshot_path=warning_screenshot_path,
            input_rect=entry.input_rect,
        )
        if visual_observation.foreground_contrast_ratio < WARNING_MIN_CONTRAST_RATIO:
            raise AssertionError(
                f"Step {step} failed: the visible warning pill did not keep enough "
                "foreground contrast for the fallback warning.\n"
                f"Observed warning visual: {visual_observation.describe()}\n"
                f"Minimum contrast: {WARNING_MIN_CONTRAST_RATIO:.1f}:1\n"
                f"Observed body text:\n{page_body_text}",
            )
        return {
            "background_hex": visual_observation.background_hex,
            "expected_background_hex": visual_observation.expected_background_hex,
            "foreground_hex": visual_observation.foreground_hex,
            "foreground_contrast_ratio": round(
                visual_observation.foreground_contrast_ratio,
                2,
            ),
            "screenshot_path": visual_observation.screenshot_path,
            "crop_box": visual_observation.crop_box,
            "warning_box": visual_observation.warning_box,
        }
    if (
        normalized_text_color not in EXPECTED_WARNING_COLORS
        or normalized_border_color not in EXPECTED_WARNING_COLORS
        or normalized_background_color not in EXPECTED_WARNING_BACKGROUND_COLORS
        or border_width <= 0
    ):
        raise AssertionError(
            f"Step {step} failed: the empty Status translation warning did not use "
            "the TrackState warning treatment.\n"
            f"Expected warning colors: {sorted(EXPECTED_WARNING_COLORS)}\n"
            f"Expected warning background colors: "
            f"{sorted(EXPECTED_WARNING_BACKGROUND_COLORS)}\n"
            f"Observed warning text color: {entry.warning_text_color!r}\n"
            f"Observed warning border color: {entry.warning_border_color!r}\n"
            f"Observed warning background color: {entry.warning_background_color!r}\n"
            f"Observed warning border width: {entry.warning_border_width!r}\n"
                f"Observed row: {entry.row_label}\n"
                f"Observed body text:\n{page_body_text}",
            )
    return {
        "text_color": normalized_text_color,
        "border_color": normalized_border_color,
        "background_color": normalized_background_color,
        "border_width": border_width,
    }


def _warning_state_summary(entry) -> str:
    return (
        f'warning "{entry.warning_text}" '
        f"(text color: {entry.warning_text_color}, "
        f"border color: {entry.warning_border_color}, "
        f"background color: {entry.warning_background_color}, "
        f"border width: {entry.warning_border_width})"
    )


def _normalize_css_color(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().lower().split())
    rgba_match = re.fullmatch(
        r"rgba\((\d+), (\d+), (\d+), (1(?:\.0+)?)\)",
        normalized,
    )
    if rgba_match:
        red, green, blue, _ = rgba_match.groups()
        return f"rgb({red}, {green}, {blue})"
    return normalized


def _parse_css_pixels(value: str | None) -> float:
    if value is None:
        return 0.0
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)px\s*", value)
    if not match:
        return 0.0
    return float(match.group(1))


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
