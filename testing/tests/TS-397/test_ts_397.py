from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_multi_view_refresh_page import (
    ConstrainedChipFieldObservation,
    LiveMultiViewRefreshPage,
)
from testing.components.services.live_setup_repository_service import (
    LiveHostedIssueFixture,
    LiveHostedRepositoryMetadata,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-397"
OUTPUTS_DIR = REPO_ROOT / "outputs"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts397_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts397_success.png"
TARGET_ISSUE_PATH = "DEMO/DEMO-1/DEMO-2/DEMO-3"
NON_EXISTENT_COMPONENT = "Database"
NON_EXISTENT_FIX_VERSION = "2026.2"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-397 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    metadata = service.fetch_demo_metadata()
    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(TARGET_ISSUE_PATH)
    _assert_preconditions(metadata=metadata, issue_fixture=issue_fixture)

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": metadata.repository,
        "repository_ref": metadata.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "expected_component_options": metadata.components,
        "expected_fix_version_options": metadata.versions,
        "non_existent_component": NON_EXISTENT_COMPONENT,
        "non_existent_fix_version": NON_EXISTENT_FIX_VERSION,
        "steps": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            page = LiveMultiViewRefreshPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the constrained metadata scenario began.\n"
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
                    repository=metadata.repository,
                    user_login=user.login,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Confirm the hosted session is connected with GitHub access.",
                    observed=page.current_body_text(),
                )

                dialog_text = page.open_edit_dialog_for_issue(
                    issue_key=issue_fixture.key,
                    issue_summary=issue_fixture.summary,
                )
                result["edit_dialog_text"] = dialog_text
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Open the Edit issue surface for DEMO-3 from JQL Search.",
                    observed=dialog_text,
                )

                components_observation = page.constrained_chip_field("Components")
                result["components_observation"] = _field_payload(
                    components_observation,
                )
                _assert_constrained_chip_field(
                    observation=components_observation,
                    expected_options=metadata.components,
                    forbidden_option=NON_EXISTENT_COMPONENT,
                    step_number=4,
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Verify Components shows only project-defined values and exposes no "
                        "inline ad-hoc entry surface."
                    ),
                    observed=_format_field_observation(components_observation),
                )

                fix_versions_observation = page.constrained_chip_field("Fix versions")
                result["fix_versions_observation"] = _field_payload(
                    fix_versions_observation,
                )
                _assert_constrained_chip_field(
                    observation=fix_versions_observation,
                    expected_options=metadata.versions,
                    forbidden_option=NON_EXISTENT_FIX_VERSION,
                    step_number=5,
                )
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=(
                        "Verify Fix versions shows only project-defined values and exposes "
                        "no inline ad-hoc entry surface."
                    ),
                    observed=_format_field_observation(fix_versions_observation),
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
            "Verified the live hosted Edit issue surface constrains Components and "
            "Fix versions to the deployed project-config values and exposes no inline "
            "ad-hoc metadata entry path."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_preconditions(
    *,
    metadata: LiveHostedRepositoryMetadata,
    issue_fixture: LiveHostedIssueFixture,
) -> None:
    if issue_fixture.key != "DEMO-3":
        raise AssertionError(
            "Precondition failed: TS-397 expected the seeded DEMO-3 fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not metadata.components:
        raise AssertionError(
            "Precondition failed: the live setup repository does not define any "
            "project Components in DEMO/config/components.json.",
        )
    if not metadata.versions:
        raise AssertionError(
            "Precondition failed: the live setup repository does not define any "
            "project Fix versions in DEMO/config/versions.json.",
        )


def _assert_constrained_chip_field(
    *,
    observation: ConstrainedChipFieldObservation,
    expected_options: list[str],
    forbidden_option: str,
    step_number: int,
) -> None:
    if observation.semantics_label is None or observation.label not in observation.semantics_label:
        raise AssertionError(
            f"Step {step_number} failed: the visible {observation.label} field did not "
            "expose a stable semantics label in the hosted Edit issue dialog.\n"
            f"Observed semantics label: {observation.semantics_label}\n"
            f"Observed field text: {observation.field_text}",
        )

    if observation.input_count != 0:
        raise AssertionError(
            f"Step {step_number} failed: the {observation.label} field exposed "
            f"{observation.input_count} inline editable input(s), so the user could "
            "attempt ad-hoc entry instead of being constrained to project-defined values.\n"
            f"Observed field text: {observation.field_text}",
        )

    if observation.listbox_count != 0 or observation.menu_item_count != 0:
        raise AssertionError(
            f"Step {step_number} failed: the {observation.label} field exposed an "
            "unexpected picker overlay surface while the edit dialog was idle.\n"
            f"Observed listbox count: {observation.listbox_count}\n"
            f"Observed menu item count: {observation.menu_item_count}\n"
            f"Observed field text: {observation.field_text}",
        )

    expected_set = set(expected_options)
    observed_set = set(observation.option_labels)
    if observed_set != expected_set or len(observation.option_labels) != len(expected_options):
        raise AssertionError(
            f"Step {step_number} failed: the visible {observation.label} values did not "
            "match the deployed project configuration.\n"
            f"Expected options: {expected_options}\n"
            f"Observed options: {list(observation.option_labels)}\n"
            f"Observed field text: {observation.field_text}",
        )

    if forbidden_option in observed_set:
        raise AssertionError(
            f"Step {step_number} failed: the visible {observation.label} values included "
            f"the non-existent ad-hoc option {forbidden_option!r}.\n"
            f"Observed options: {list(observation.option_labels)}",
        )


def _field_payload(
    observation: ConstrainedChipFieldObservation,
) -> dict[str, object]:
    return {
        "label": observation.label,
        "semantics_label": observation.semantics_label,
        "field_text": observation.field_text,
        "option_labels": list(observation.option_labels),
        "input_count": observation.input_count,
        "listbox_count": observation.listbox_count,
        "menu_item_count": observation.menu_item_count,
    }


def _format_field_observation(observation: ConstrainedChipFieldObservation) -> str:
    return (
        f"{observation.label}: options={list(observation.option_labels)}, "
        f"input_count={observation.input_count}, "
        f"listbox_count={observation.listbox_count}, "
        f"menu_item_count={observation.menu_item_count}"
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
    configured_path = os.environ.get("TS397_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts397_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
