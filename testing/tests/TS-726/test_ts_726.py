from __future__ import annotations

from collections import Counter
from dataclasses import asdict, replace
import json
import math
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    FocusNavigationStep,
    LiveWorkspaceSwitcherPage,
    MobileTriggerFocusObservation,
    WorkspaceSwitcherBadgeObservation,
    WorkspaceSwitcherIconObservation,
    WorkspaceSwitcherInteractiveTextObservation,
    WorkspaceSwitcherSemanticsObservation,
    WorkspaceSwitcherSurfaceObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.color_contrast import (  # noqa: E402
    RgbColor,
    color_distance,
    contrast_ratio,
    rgb_to_hex,
)
from testing.core.utils.png_image import RgbImage  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-726"
TEST_CASE_TITLE = (
    "Switcher trigger and surface accessibility — focus order and WCAG compliance"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-726/test_ts_726.py"
REQUEST_STEPS = [
    "Use keyboard navigation (Tab) to reach the workspace switcher trigger in the top bar.",
    "Press Enter to open the surface.",
    "Tab through the list of workspaces, the Add workspace action, and the Remove icons.",
    "Inspect the contrast ratio of the state badges against the surface.",
    "Verify the focus ring visibility on the condensed mobile trigger.",
]
EXPECTED_RESULT = (
    "Focus order is logical. All interactive elements provide a 3:1 or higher "
    "contrast for icons and 4.5:1 for text. Every element in the panel/sheet has "
    "a descriptive semantics label."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts726_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts726_failure.png"
SURFACE_PROBE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts726_surface_probe.png"

HOSTED_TARGET = "IstiN/trackstate-setup"
LOCAL_TARGET = "/tmp/trackstate-demo"
DEFAULT_BRANCH = "main"
DESKTOP_TAB_COUNT = 12
SHEET_TAB_COUNT = 12
MOBILE_TAB_COUNT = 24
MIN_TEXT_CONTRAST = 4.5
MIN_GRAPHIC_CONTRAST = 3.0


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": "",
        "repository": "",
        "repository_ref": "",
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "preloaded_workspace_state": _workspace_state(),
        "steps": [],
        "human_verification": [],
    }

    try:
        config = load_live_setup_test_config()
        service = LiveSetupRepositoryService(config=config)
        token = service.token
        workspace_state = _workspace_state()
        result.update(
            {
                "app_url": config.app_url,
                "repository": service.repository,
                "repository_ref": service.ref,
                "preloaded_workspace_state": workspace_state,
            },
        )
        if not token:
            raise RuntimeError(
                "TS-726 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        errors: list[str] = []

        with create_live_tracker_app(
            config,
            runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                repository=config.repository,
                token=token,
                workspace_state=workspace_state,
            ),
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            runtime_state = tracker_page.open()
            result["runtime_state"] = runtime_state.kind
            result["runtime_body_text"] = runtime_state.body_text
            if runtime_state.kind != "ready":
                failure = (
                    "Step 1 failed: the deployed app did not reach the interactive "
                    "tracker shell before the workspace switcher accessibility scenario "
                    "started.\n"
                    f"Observed runtime state: {runtime_state.kind}\n"
                    f"Observed body text:\n{runtime_state.body_text}"
                )
                _record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=failure,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the deployed app before starting keyboard navigation to "
                        "the workspace switcher."
                    ),
                    observed=_snippet(runtime_state.body_text),
                )
                _capture_screenshot(page, FAILURE_SCREENSHOT_PATH, result)
                raise AssertionError(failure)

            topbar_sequence = page.collect_tab_sequence_from_search(
                tab_count=DESKTOP_TAB_COUNT,
            )
            result["desktop_topbar_focus_sequence"] = [
                asdict(step) for step in topbar_sequence
            ]
            topbar_summary = _focus_sequence_summary(topbar_sequence)
            if page.workspace_trigger_reached(topbar_sequence):
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=topbar_summary,
                )
            else:
                error = (
                    "Step 1 failed: keyboard Tab navigation from the visible top-bar "
                    "search field never reached the workspace switcher trigger.\n"
                    f"Observed focus sequence: {topbar_summary}"
                )
                _record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=error,
                )
                errors.append(error)

            opened_with_keyboard = False
            if page.workspace_trigger_reached(topbar_sequence):
                try:
                    page.press_enter_on_active_element_and_wait_for_surface()
                except AssertionError as error:
                    observed = str(error)
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=observed,
                    )
                    errors.append(
                        "Step 2 failed: pressing Enter on the focused workspace switcher "
                        f"trigger did not open the surface.\n{observed}"
                    )
                else:
                    opened_with_keyboard = True
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed="Pressing Enter on the focused trigger opened the visible workspace switcher dialog.",
                    )
            else:
                _record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "The keyboard Enter step was not reachable because Tab navigation "
                        "never focused the workspace switcher trigger. A pointer click was "
                        "used next only to collect diagnostic observations from the live dialog."
                    ),
                )

            if not opened_with_keyboard:
                page.open_surface_with_click()

            surface = page.observe_surface()
            SURFACE_PROBE_SCREENSHOT_PATH.unlink(missing_ok=True)
            page.screenshot(str(SURFACE_PROBE_SCREENSHOT_PATH))
            surface = _enrich_badge_contrast(
                surface=surface,
                screenshot_path=SURFACE_PROBE_SCREENSHOT_PATH,
            )
            surface = _enrich_icon_contrast(
                surface=surface,
                screenshot_path=SURFACE_PROBE_SCREENSHOT_PATH,
            )
            surface = _enrich_interactive_text_contrast(
                surface=surface,
                screenshot_path=SURFACE_PROBE_SCREENSHOT_PATH,
            )
            result["desktop_surface_observation"] = _surface_payload(surface)

            sheet_sequence = page.collect_tab_sequence(tab_count=SHEET_TAB_COUNT)
            result["desktop_sheet_focus_sequence"] = [
                asdict(step) for step in sheet_sequence
            ]
            try:
                sheet_summary = _assert_sheet_accessibility(
                    sequence=sheet_sequence,
                    surface=surface,
                )
            except AssertionError as error:
                observed = str(error)
                _record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=observed,
                )
                errors.append(observed)
            else:
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=sheet_summary,
                )

            try:
                contrast_summary = _assert_accessible_contrast(surface)
            except AssertionError as error:
                observed = str(error)
                _record_step(
                    result,
                    step=4,
                    status="failed",
                    action=REQUEST_STEPS[3],
                    observed=observed,
                )
                errors.append(observed)
            else:
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=contrast_summary,
                )

            _record_human_verification(
                result,
                check=(
                    "Viewed the live top bar as a keyboard user and watched where focus "
                    "actually moved while tabbing through the visible controls."
                ),
                observed=topbar_summary,
            )
            _record_human_verification(
                result,
                check=(
                    "Viewed the workspace switcher sheet as a user after opening it from "
                    "the real deployed UI."
                ),
                observed=(
                    f"heading={surface.heading_text!r}; "
                    f"interactive_labels={[item.label for item in surface.interactive_elements]!r}; "
                    f"semantics_labels={[node.label for node in surface.semantics_nodes]!r}; "
                    f"badge_labels={[badge.label for badge in surface.badges]!r}; "
                    f"interactive_text_labels={[text.label for text in surface.interactive_texts]!r}; "
                    f"icon_labels={[icon.label for icon in surface.interactive_icons]!r}"
                ),
            )
            _capture_screenshot(
                page,
                SUCCESS_SCREENSHOT_PATH if not errors else FAILURE_SCREENSHOT_PATH,
                result,
            )
            SURFACE_PROBE_SCREENSHOT_PATH.unlink(missing_ok=True)

        with create_live_tracker_app(
            config,
            runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                repository=config.repository,
                token=token,
                workspace_state=workspace_state,
            ),
        ) as tracker_page:
            tracker_page.session.set_viewport_size(width=760, height=960)
            page = LiveWorkspaceSwitcherPage(tracker_page)
            runtime_state = tracker_page.open()
            if runtime_state.kind != "ready":
                error = (
                    "Step 5 failed: the deployed mobile layout did not reach the "
                    "interactive shell before the condensed trigger focus-ring check.\n"
                    f"Observed runtime state: {runtime_state.kind}\n"
                    f"Observed body text:\n{runtime_state.body_text}"
                )
                _record_step(
                    result,
                    step=5,
                    status="failed",
                    action=REQUEST_STEPS[4],
                    observed=error,
                )
                errors.append(error)
            else:
                mobile_focus = page.observe_mobile_trigger_focus(
                    tab_count=MOBILE_TAB_COUNT,
                )
                result["mobile_trigger_focus_observation"] = asdict(mobile_focus)
                try:
                    mobile_summary = _assert_mobile_focus_ring(mobile_focus)
                except AssertionError as error:
                    observed = str(error)
                    _record_step(
                        result,
                        step=5,
                        status="failed",
                        action=REQUEST_STEPS[4],
                        observed=observed,
                    )
                    errors.append(observed)
                    if "screenshot" not in result:
                        _capture_screenshot(page, FAILURE_SCREENSHOT_PATH, result)
                else:
                    _record_step(
                        result,
                        step=5,
                        status="passed",
                        action=REQUEST_STEPS[4],
                        observed=mobile_summary,
                    )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the condensed mobile trigger state after attempting to "
                        "focus it like a keyboard user."
                    ),
                    observed=_mobile_focus_summary(mobile_focus),
                )

        if errors:
            raise AssertionError("\n\n".join(errors))
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-726 passed")


def _workspace_state() -> dict[str, object]:
    hosted_id = f"hosted:{HOSTED_TARGET.lower()}@{DEFAULT_BRANCH}"
    local_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": hosted_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": hosted_id,
                "displayName": "",
                "targetType": "hosted",
                "target": HOSTED_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-13T12:00:00.000Z",
            },
            {
                "id": local_id,
                "displayName": "",
                "targetType": "local",
                "target": LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-12T12:00:00.000Z",
            },
        ],
    }


def _assert_sheet_accessibility(
    *,
    sequence: tuple[FocusNavigationStep, ...],
    surface: WorkspaceSwitcherSurfaceObservation,
) -> str:
    if surface.heading_text != "Workspace switcher":
        raise AssertionError(
            "Step 3 failed: the visible dialog did not expose the expected "
            "`Workspace switcher` heading.\n"
            f"Observed heading: {surface.heading_text!r}\n"
            f"Observed body text:\n{surface.body_text}",
        )
    if not surface.semantics_nodes:
        raise AssertionError(
            "Step 3 failed: the workspace switcher probe did not expose the visible "
            "semantics tree for the sheet.\n"
            f"Observed interactive labels: {[item.label for item in surface.interactive_elements]!r}",
        )
    non_interactive_semantics = tuple(
        node
        for node in surface.semantics_nodes
        if node.role not in {"button", "textbox", "searchbox"}
        and node.label != "Workspace switcher"
    )
    if not non_interactive_semantics:
        raise AssertionError(
            "Step 3 failed: the workspace switcher semantics probe only exposed "
            "interactive controls, so AC6 coverage for non-interactive sheet content "
            "is still incomplete.\n"
            f"Observed semantics labels: {_semantics_summary(surface.semantics_nodes)}"
        )
    if surface.missing_interactive_labels or surface.missing_semantics_labels:
        raise AssertionError(
            "Step 3 failed: some visible workspace switcher elements were missing "
            "descriptive semantics labels.\n"
            f"Missing interactive labels: {list(surface.missing_interactive_labels)!r}\n"
            f"Missing semantics labels: {list(surface.missing_semantics_labels)!r}\n"
            f"Observed semantics labels: {_semantics_summary(surface.semantics_nodes)}",
        )
    labels = [step.after_label or "" for step in sequence]
    has_workspace_list_control = any(label in {"Open", "Delete", "Active"} for label in labels)
    has_add_workspace_control = any(
        label in {"Hosted", "Local", "Repository", "Branch", "Save and switch"}
        for label in labels
    )
    has_remove_control = any(label == "Delete" for label in labels)
    if not has_workspace_list_control or not has_add_workspace_control or not has_remove_control:
        raise AssertionError(
            "Step 3 failed: tabbing through the workspace switcher dialog did not reach "
            "the expected list, add-workspace, and remove controls.\n"
            f"Observed focus sequence: {_focus_sequence_summary(sequence)}\n"
            f"Observed interactive labels: {[item.label for item in surface.interactive_elements]!r}",
        )
    return (
        f"focus_sequence={_focus_sequence_summary(sequence)}; "
        f"interactive_labels={[item.label for item in surface.interactive_elements]!r}; "
        f"semantics_labels={_semantics_summary(surface.semantics_nodes)}"
    )


def _assert_accessible_contrast(
    surface: WorkspaceSwitcherSurfaceObservation,
) -> str:
    badges = surface.badges
    state_badges = tuple(
        badge
        for badge in badges
        if badge.label in {
            "Needs sign-in",
            "Unavailable",
            "Read-only",
            "Connected",
            "Attachments limited",
            "Local Git",
            "Saved hosted workspace",
        }
    )
    if not state_badges:
        raise AssertionError(
            "Step 4 failed: the workspace switcher dialog did not expose any visible "
            "state or type badges to evaluate for contrast."
        )
    if not surface.interactive_icons:
        raise AssertionError(
            "Step 4 failed: the workspace switcher probe did not expose any visible "
            "interactive icons for contrast inspection.\n"
            f"Observed icons: {_icon_summary(surface.interactive_icons)}"
        )
    if not surface.interactive_texts:
        raise AssertionError(
            "Step 4 failed: the workspace switcher probe did not expose any visible "
            "interactive text controls for contrast inspection.\n"
            f"Observed text controls: {_interactive_text_summary(surface.interactive_texts)}"
        )
    low_contrast = [
        badge
        for badge in state_badges
        if badge.contrast_ratio is None or badge.contrast_ratio < MIN_TEXT_CONTRAST
    ]
    low_text_contrast = [
        text_control
        for text_control in surface.interactive_texts
        if text_control.contrast_ratio is None
        or text_control.contrast_ratio < MIN_TEXT_CONTRAST
    ]
    low_icon_contrast = [
        icon
        for icon in surface.interactive_icons
        if icon.contrast_ratio is None or icon.contrast_ratio < MIN_GRAPHIC_CONTRAST
    ]
    if low_contrast:
        raise AssertionError(
            "Step 4 failed: one or more visible workspace badges did not meet the "
            f"{MIN_TEXT_CONTRAST}:1 text contrast requirement.\n"
            f"Observed badges: {_badge_summary(state_badges)}"
        )
    if low_text_contrast:
        raise AssertionError(
            "Step 4 failed: one or more visible text-bearing interactive controls did "
            f"not meet the {MIN_TEXT_CONTRAST}:1 text contrast requirement.\n"
            f"Observed text controls: {_interactive_text_summary(surface.interactive_texts)}"
        )
    if low_icon_contrast:
        raise AssertionError(
            "Step 4 failed: one or more visible interactive icons did not meet the "
            f"{MIN_GRAPHIC_CONTRAST}:1 non-text contrast requirement.\n"
            f"Observed icons: {_icon_summary(surface.interactive_icons)}"
        )
    return (
        f"badges={_badge_summary(state_badges)}; "
        f"text_controls={_interactive_text_summary(surface.interactive_texts)}; "
        f"icons={_icon_summary(surface.interactive_icons)}"
    )


def _enrich_badge_contrast(
    *,
    surface: WorkspaceSwitcherSurfaceObservation,
    screenshot_path: Path,
) -> WorkspaceSwitcherSurfaceObservation:
    image = RgbImage.open(screenshot_path)
    observed_badges = tuple(
        _observe_badge(image=image, badge=badge) for badge in surface.badges
    )
    return replace(surface, badges=observed_badges)


def _enrich_icon_contrast(
    *,
    surface: WorkspaceSwitcherSurfaceObservation,
    screenshot_path: Path,
) -> WorkspaceSwitcherSurfaceObservation:
    image = RgbImage.open(screenshot_path)
    observed_icons = tuple(
        _observe_icon(image=image, icon=icon) for icon in surface.interactive_icons
    )
    return replace(surface, interactive_icons=observed_icons)


def _enrich_interactive_text_contrast(
    *,
    surface: WorkspaceSwitcherSurfaceObservation,
    screenshot_path: Path,
) -> WorkspaceSwitcherSurfaceObservation:
    image = RgbImage.open(screenshot_path)
    observed_text_controls = tuple(
        _observe_interactive_text(image=image, text_control=text_control)
        for text_control in surface.interactive_texts
    )
    return replace(surface, interactive_texts=observed_text_controls)


def _observe_badge(
    *,
    image: RgbImage,
    badge: WorkspaceSwitcherBadgeObservation,
) -> WorkspaceSwitcherBadgeObservation:
    box = _box(
        image=image,
        left=badge.x,
        top=badge.y,
        width=badge.width,
        height=badge.height,
    )
    if box is None:
        return badge
    crop = image.crop(box)
    background = _dominant_color(crop)
    foreground = _sample_foreground(crop, background=background)
    return replace(
        badge,
        foreground_color=(rgb_to_hex(foreground).lower() if foreground is not None else None),
        background_color=rgb_to_hex(background).lower(),
        contrast_ratio=(
            round(contrast_ratio(foreground, background), 2)
            if foreground is not None
            else None
        ),
    )


def _observe_icon(
    *,
    image: RgbImage,
    icon: WorkspaceSwitcherIconObservation,
) -> WorkspaceSwitcherIconObservation:
    box = _box(
        image=image,
        left=icon.x,
        top=icon.y,
        width=icon.width,
        height=icon.height,
    )
    if box is None:
        return icon
    crop = image.crop(box)
    background = _dominant_color(crop)
    foreground = _sample_foreground(crop, background=background)
    return replace(
        icon,
        foreground_color=(rgb_to_hex(foreground).lower() if foreground is not None else None),
        background_color=rgb_to_hex(background).lower(),
        contrast_ratio=(
            round(contrast_ratio(foreground, background), 2)
            if foreground is not None
            else None
        ),
    )


def _observe_interactive_text(
    *,
    image: RgbImage,
    text_control: WorkspaceSwitcherInteractiveTextObservation,
) -> WorkspaceSwitcherInteractiveTextObservation:
    box = _box(
        image=image,
        left=text_control.x,
        top=text_control.y,
        width=text_control.width,
        height=text_control.height,
    )
    if box is None:
        return text_control
    crop = image.crop(box)
    background = _dominant_color(crop)
    foreground = _sample_foreground(crop, background=background)
    return replace(
        text_control,
        foreground_color=(rgb_to_hex(foreground).lower() if foreground is not None else None),
        background_color=rgb_to_hex(background).lower(),
        contrast_ratio=(
            round(contrast_ratio(foreground, background), 2)
            if foreground is not None
            else None
        ),
    )


def _box(
    *,
    image: RgbImage,
    left: float,
    top: float,
    width: float,
    height: float,
) -> tuple[int, int, int, int] | None:
    if width <= 0 or height <= 0:
        return None
    box = (
        max(int(math.floor(left)), 0),
        max(int(math.floor(top)), 0),
        min(int(math.ceil(left + width)), image.width),
        min(int(math.ceil(top + height)), image.height),
    )
    if box[0] >= box[2] or box[1] >= box[3]:
        return None
    return box


def _dominant_color(image: RgbImage) -> RgbColor:
    counts = Counter(image.getdata())
    color, _ = counts.most_common(1)[0]
    return color


def _sample_foreground(
    image: RgbImage,
    *,
    background: RgbColor,
) -> RgbColor | None:
    counts = Counter(image.getdata())
    samples = [
        (color, count)
        for color, count in counts.items()
        if color_distance(color, background) > 20
    ]
    if not samples:
        return None
    strongest_distance = max(color_distance(color, background) for color, _ in samples)
    strongest_samples = [
        (color, count)
        for color, count in samples
        if strongest_distance - color_distance(color, background) <= 8
    ]
    total = sum(count for _, count in strongest_samples)
    return (
        round(sum(color[0] * count for color, count in strongest_samples) / total),
        round(sum(color[1] * count for color, count in strongest_samples) / total),
        round(sum(color[2] * count for color, count in strongest_samples) / total),
    )


def _assert_mobile_focus_ring(
    observation: MobileTriggerFocusObservation,
) -> str:
    if observation.active_label_after_focus is None or not observation.active_label_after_focus.startswith(
        "Workspace switcher:"
    ):
        raise AssertionError(
            "Step 5 failed: keyboard Tab navigation in the condensed mobile layout "
            "never moved focus onto the workspace switcher trigger.\n"
            f"{_mobile_focus_summary(observation)}",
        )
    ring_visible = (
        "none" not in observation.after_outline.lower()
        or "rgba(0, 0, 0, 0)" not in observation.after_outline_color.lower()
        or observation.after_box_shadow.lower() != "none"
    )
    if not ring_visible:
        raise AssertionError(
            "Step 5 failed: the condensed mobile workspace switcher trigger did not "
            "show a visible focus ring after focus landed on it.\n"
            f"{_mobile_focus_summary(observation)}",
        )
    return _mobile_focus_summary(observation)


def _focus_sequence_summary(sequence: tuple[FocusNavigationStep, ...]) -> str:
    return " -> ".join(
        f"{step.step}:{step.after_label or '<none>'}"
        for step in sequence
    )


def _badge_summary(badges: tuple[WorkspaceSwitcherBadgeObservation, ...]) -> str:
    return str(
        [
            {
                "label": badge.label,
                "foreground": badge.foreground_color,
                "background": badge.background_color,
                "contrast": badge.contrast_ratio,
            }
            for badge in badges
        ]
    )


def _icon_summary(icons: tuple[WorkspaceSwitcherIconObservation, ...]) -> str:
    return str(
        [
            {
                "label": icon.label,
                "foreground": icon.foreground_color,
                "background": icon.background_color,
                "contrast": icon.contrast_ratio,
            }
            for icon in icons
        ]
    )


def _interactive_text_summary(
    texts: tuple[WorkspaceSwitcherInteractiveTextObservation, ...],
) -> str:
    return str(
        [
            {
                "label": text.label,
                "visible_text": text.visible_text,
                "foreground": text.foreground_color,
                "background": text.background_color,
                "contrast": text.contrast_ratio,
            }
            for text in texts
        ]
    )


def _semantics_summary(
    semantics_nodes: tuple[WorkspaceSwitcherSemanticsObservation, ...],
) -> str:
    return str(
        [
            {
                "label": node.label,
                "role": node.role,
                "tag": node.tag_name,
                "visible_text": node.visible_text,
            }
            for node in semantics_nodes
        ]
    )


def _mobile_focus_summary(observation: MobileTriggerFocusObservation) -> str:
    return (
        f"focus_sequence={_focus_sequence_summary(observation.focus_sequence)}; "
        f"trigger_text={observation.trigger_text!r}; "
        f"active_after_focus={observation.active_label_after_focus!r}; "
        f"active_role_after_focus={observation.active_role_after_focus!r}; "
        f"active_tag_after_focus={observation.active_tag_name_after_focus!r}; "
        f"before_outline={observation.before_outline!r}; "
        f"after_outline={observation.after_outline!r}; "
        f"after_outline_color={observation.after_outline_color!r}; "
        f"after_box_shadow={observation.after_box_shadow!r}"
    )


def _surface_payload(surface: WorkspaceSwitcherSurfaceObservation) -> dict[str, object]:
    return {
        "body_text": surface.body_text,
        "dialog_visible": surface.dialog_visible,
        "heading_text": surface.heading_text,
        "interactive_elements": [asdict(item) for item in surface.interactive_elements],
        "semantics_nodes": [asdict(item) for item in surface.semantics_nodes],
        "missing_interactive_labels": list(surface.missing_interactive_labels),
        "missing_semantics_labels": list(surface.missing_semantics_labels),
        "badges": [asdict(item) for item in surface.badges],
        "interactive_icons": [asdict(item) for item in surface.interactive_icons],
        "interactive_texts": [asdict(item) for item in surface.interactive_texts],
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
        }
    )


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


def _capture_screenshot(
    page: LiveWorkspaceSwitcherPage,
    path: Path,
    result: dict[str, object],
) -> None:
    path.unlink(missing_ok=True)
    try:
        page.screenshot(str(path))
    except Exception as error:
        result["screenshot_capture_error"] = _format_error(error)
        return
    if path.exists():
        result["screenshot"] = str(path)


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def _snippet(value: object, *, limit: int = 280) -> str:
    text = str(value).replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit - 3]}..."


def _write_pass_outputs(result: dict[str, object]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: unknown failure"))
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "h4. What was automated",
        (
            "* Opened the deployed TrackState web app in Chromium with preloaded hosted "
            "and local saved workspaces."
        ),
        (
            "* Checked keyboard focus movement toward the top-bar workspace switcher, "
            "then inspected the live switcher sheet, badge contrast, and condensed "
            "mobile trigger focus state."
        ),
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failure_summary(result)}"
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}."
        ),
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Exact error",
                "{code}",
                str(result.get("error", "")),
                "{code}",
            ]
        )
    if result.get("screenshot"):
        lines.extend(
            [
                "",
                f"*Screenshot:* {{{{{result['screenshot']}}}}}",
            ]
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Opened the deployed TrackState web app in Chromium with preloaded hosted and local saved workspaces.",
        "- Checked keyboard navigation to the workspace switcher trigger, the live switcher surface, visible badge contrast, and condensed mobile trigger focus behavior.",
        "",
        "## Result",
        (
            "- The observed behavior matched the expected result."
            if passed
            else f"- The observed behavior did not match the expected result. {_failure_summary(result)}"
        ),
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    if result.get("screenshot"):
        lines.extend(["", f"**Screenshot:** `{result['screenshot']}`"])
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    return _pr_body(result, passed=passed)


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return []
    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        status = "PASSED" if step.get("status") == "passed" else "FAILED"
        action = str(step.get("action", ""))
        observed = str(step.get("observed", ""))
        if jira:
            lines.append(
                f"* Step {step.get('step')}: *{status}* — {action} Observed: {observed}"
            )
        else:
            lines.append(
                f"- Step {step.get('step')}: **{status}** — {action} Observed: {observed}"
            )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    checks = result.get("human_verification", [])
    if not isinstance(checks, list):
        return []
    lines: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        if jira:
            lines.append(
                f"* {check.get('check')} Observed: {check.get('observed')}"
            )
        else:
            lines.append(
                f"- {check.get('check')} Observed: {check.get('observed')}"
            )
    return lines


def _failure_summary(result: dict[str, object]) -> str:
    failed_steps = [
        step
        for step in result.get("steps", [])
        if isinstance(step, dict) and step.get("status") == "failed"
    ]
    if not failed_steps:
        return str(result.get("error", "Unknown failure"))
    first = failed_steps[0]
    return f"First failed step: {first.get('step')} — {first.get('observed')}"


def _bug_description(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    annotated_steps: list[str] = []
    for index, request_step in enumerate(REQUEST_STEPS, start=1):
        matching = next(
            (
                step
                for step in steps
                if isinstance(step, dict) and step.get("step") == index
            ),
            None,
        )
        if isinstance(matching, dict):
            icon = "✅" if matching.get("status") == "passed" else "❌"
            annotated_steps.append(
                f"{index}. {icon} {request_step}\n   Observed: {matching.get('observed')}"
            )
        else:
            annotated_steps.append(f"{index}. ❌ {request_step}\n   Observed: Not reached.")
    return "\n".join(
        [
            f"# {TICKET_KEY} — {TEST_CASE_TITLE}",
            "",
            "## Steps to reproduce",
            *annotated_steps,
            "",
            "## Exact error message",
            "```",
            str(result.get("error", "")),
            "",
            str(result.get("traceback", "")),
            "```",
            "",
            "## Actual vs Expected",
            f"- **Expected:** {EXPECTED_RESULT}",
            (
                "- **Actual:** Keyboard focus did not reliably reach the workspace "
                "switcher trigger in the live top bar, and the condensed mobile "
                "trigger did not expose a visible focus state during the run."
            ),
            "",
            "## Environment",
            f"- URL: {result.get('app_url', '')}",
            f"- Repository: {result.get('repository', '')} @ {result.get('repository_ref', '')}",
            f"- Browser: {result.get('browser', '')}",
            f"- OS: {result.get('os', '')}",
            "",
            "## Logs and artifacts",
            f"- Screenshot: {result.get('screenshot', '<none>')}",
            "- Top-bar focus sequence:",
            f"  {result.get('desktop_topbar_focus_sequence', [])}",
            "- Switcher sheet focus sequence:",
            f"  {result.get('desktop_sheet_focus_sequence', [])}",
            "- Mobile focus observation:",
            f"  {result.get('mobile_trigger_focus_observation', {})}",
        ]
    ) + "\n"


if __name__ == "__main__":
    main()
