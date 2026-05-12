from __future__ import annotations

import json
import platform
import re
import sys
import traceback
import urllib.error
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_project_settings_page import (  # noqa: E402
    LiveProjectSettingsPage,
    RepositoryAccessCalloutObservation,
    RepositoryAccessSectionObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedRepositoryMetadata,
    LiveHostedRepositoryFile,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-495"
PROJECT_JSON_PATH = "DEMO/project.json"
RELEASE_TAG_PREFIX_BASE = "ts495-release-access-"
PRIMARY_TITLE = "Connected"
SECONDARY_TITLE = "GitHub Releases attachment storage"
LEGACY_WARNING_TITLE = "Some attachment uploads still require local Git"
SETTINGS_HINT = (
    "Settings is the canonical place to review repository access and reconnect safely."
)
SUCCESS_BORDER_HEX = "#3BBE60"
SUCCESS_BACKGROUND_HEX = "#E7F7EC"
EXPECTED_SUCCESS_BORDER_COLORS = {"rgb(59, 190, 96)", SUCCESS_BORDER_HEX.lower()}
EXPECTED_SUCCESS_BACKGROUND_COLORS = {
    "rgb(231, 247, 236)",
    "rgba(59, 190, 96, 0.12)",
    SUCCESS_BACKGROUND_HEX.lower(),
}

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts495_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts495_failure.png"

@dataclass(frozen=True)
class RepoMutation:
    path: str
    original_file: LiveHostedRepositoryFile


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-495 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    metadata = service.fetch_demo_metadata()
    _assert_preconditions(metadata)
    user = service.fetch_authenticated_user()
    mutation = RepoMutation(
        path=PROJECT_JSON_PATH,
        original_file=service.fetch_repo_file(PROJECT_JSON_PATH),
    )
    requested_release_tag_prefix = _build_release_tag_prefix()

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "project_key": metadata.project_key,
        "project_name": metadata.project_name,
        "project_json_path": PROJECT_JSON_PATH,
        "user_login": user.login,
        "requested_release_tag_prefix": requested_release_tag_prefix,
        "steps": [],
        "human_verification": [],
    }

    scenario_error: Exception | None = None
    cleanup_error: str | None = None
    try:
        fixture_setup = _seed_fixture(
            service,
            requested_release_tag_prefix=requested_release_tag_prefix,
        )
        result["fixture_setup"] = fixture_setup
        release_tag_prefix = str(fixture_setup["release_tag_prefix"])
        expected_primary_message = (
            f"Connected as {user.login} to {service.repository}. "
            f"New attachments use GitHub Releases tags derived as "
            f"{release_tag_prefix}<ISSUE_KEY>. "
            f"{SETTINGS_HINT}"
        )
        expected_secondary_message = (
            f"New attachments resolve to release tag {release_tag_prefix}<ISSUE_KEY>, "
            "and this hosted session can complete release-backed uploads in the browser."
        )
        result["release_tag_prefix"] = release_tag_prefix
        result["expected_primary_message"] = expected_primary_message
        result["expected_secondary_message"] = expected_secondary_message

        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            settings_page = LiveProjectSettingsPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted "
                        "tracker shell before the repository access success-state "
                        "scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the application in a hosted browser session.",
                    observed=(
                        f"runtime_state=ready; project={metadata.project_key}; "
                        f"repository={service.repository}"
                    ),
                )

                settings_page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                settings_page.dismiss_connection_banner()
                settings_body = settings_page.open_settings()
                result["settings_body"] = settings_body
                if "Project Settings" not in settings_body or PRIMARY_TITLE not in settings_body:
                    raise AssertionError(
                        "Step 2 failed: the hosted session did not navigate to the "
                        "Project Settings surface that contains the repository access "
                        "controls.\n"
                        f"Observed body text:\n{settings_body}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Navigate to Project Settings or an issue detail view.",
                    observed=(
                        "opened_view=Project Settings; "
                        f'project_settings_visible={"Project Settings" in settings_body}; '
                        f'connected_callout_visible={PRIMARY_TITLE in settings_body}'
                    ),
                )

                observation = settings_page.observe_repository_access_section(
                    primary_title=PRIMARY_TITLE,
                    secondary_title=SECONDARY_TITLE,
                )
                result["repository_access_observation"] = _section_payload(observation)
                _assert_primary_callout(
                    observation.primary_callout,
                    expected_message=expected_primary_message,
                )
                _assert_secondary_callout(
                    observation.secondary_callout,
                    expected_message=expected_secondary_message,
                )
                _assert_callout_order(observation)
                _assert_local_git_warning_absent(observation)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Inspect the repository access banner/callout area.",
                    observed=(
                        f'primary_title="{observation.primary_callout.title}"; '
                        f'secondary_title="{observation.secondary_callout.title}"; '
                        f"primary_top={observation.primary_callout.top:.1f}; "
                        f"secondary_top={observation.secondary_callout.top:.1f}"
                    ),
                )

                settings_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                secondary_styles = _assert_success_treatment(
                    observation.secondary_callout,
                    screenshot_path=str(SUCCESS_SCREENSHOT_PATH),
                    callout_name="secondary GitHub Releases callout",
                )
                result["secondary_callout_styles"] = secondary_styles
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Verify the styling and copy of the secondary attachment callout.",
                    observed=(
                        f'secondary_message="{observation.secondary_callout.message}"; '
                        f"secondary_border_color={secondary_styles['normalized_border_color']}; "
                        f"secondary_background_color={secondary_styles['normalized_background_color']}; "
                        f"secondary_border_width={secondary_styles['border_width']}; "
                        f'legacy_warning_present={LEGACY_WARNING_TITLE in observation.body_text}'
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the Repository access section showed a visible "
                        "`Connected` status band above the attachment-storage callout."
                    ),
                    observed=(
                        f'primary_rendered_text="{observation.primary_callout.rendered_text}"; '
                        f"primary_top={observation.primary_callout.top:.1f}; "
                        f"secondary_top={observation.secondary_callout.top:.1f}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the secondary callout used green success styling and "
                        "explicitly said hosted release-backed browser uploads are supported, "
                        "without showing the blanket local-Git warning."
                    ),
                    observed=(
                        f'title="{observation.secondary_callout.title}"; '
                        f'message="{observation.secondary_callout.message}"; '
                        f"border_color={secondary_styles['normalized_border_color']}; "
                        f"background_color={secondary_styles['normalized_background_color']}; "
                        f"border_width={secondary_styles['border_width']}; "
                        f"warning_count={observation.body_text.count(LEGACY_WARNING_TITLE)}"
                    ),
                )
            except Exception:
                settings_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        scenario_error = error
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
    finally:
        try:
            cleanup_result = _restore_fixture(service=service, mutation=mutation)
            result["cleanup"] = cleanup_result
        except Exception:
            cleanup_error = traceback.format_exc()
            result["cleanup_error"] = cleanup_error

    if scenario_error is not None:
        if cleanup_error is not None:
            result["error"] = (
                f"{result['error']}\n\nCleanup also failed:\n{cleanup_error}"
            )
        _write_failure_outputs(result)
        raise scenario_error

    if cleanup_error is not None:
        result["error"] = f"AssertionError: cleanup failed\n\n{cleanup_error}"
        _write_failure_outputs(result)
        raise AssertionError(result["error"])

    _write_pass_outputs(result)


def _assert_preconditions(metadata: LiveHostedRepositoryMetadata) -> None:
    if metadata.project_key != "DEMO":
        raise AssertionError(
            "Precondition failed: TS-495 expected the seeded DEMO hosted project.\n"
            f"Observed project key: {metadata.project_key}",
        )


def _build_release_tag_prefix() -> str:
    import uuid

    return f"{RELEASE_TAG_PREFIX_BASE}{uuid.uuid4().hex[:8]}-"


def _seed_fixture(
    service: LiveSetupRepositoryService,
    *,
    requested_release_tag_prefix: str,
) -> dict[str, object]:
    current_project_json = service.fetch_repo_text(PROJECT_JSON_PATH)
    current_mode = _project_attachment_mode(current_project_json)
    current_release_tag_prefix = _project_release_tag_prefix(current_project_json)
    if current_mode == "github-releases" and current_release_tag_prefix:
        return {
            "project_json": current_project_json,
            "attachment_storage_mode": current_mode,
            "release_tag_prefix": current_release_tag_prefix,
            "mutation_applied": False,
        }

    project_payload = json.loads(current_project_json)
    if not isinstance(project_payload, dict):
        raise AssertionError(
            f"Precondition failed: {PROJECT_JSON_PATH} did not deserialize to a JSON object.",
        )
    project_payload["attachmentStorage"] = {
        "mode": "github-releases",
        "githubReleases": {"tagPrefix": requested_release_tag_prefix},
    }
    _write_repo_text_with_retry(
        PROJECT_JSON_PATH,
        service=service,
        content=json.dumps(project_payload, indent=2) + "\n",
        message=f"{TICKET_KEY}: ensure github-releases attachment storage",
    )

    matched, observed_project_json = poll_until(
        probe=lambda: service.fetch_repo_text(PROJECT_JSON_PATH),
        is_satisfied=lambda text: _project_attachment_mode(text) == "github-releases"
        and _project_release_tag_prefix(text) == requested_release_tag_prefix,
        timeout_seconds=120,
        interval_seconds=4,
    )
    if not matched:
        raise AssertionError(
            "Precondition failed: the hosted repository did not expose the expected "
            "github-releases project configuration within the timeout.\n"
            f"Observed project.json:\n{observed_project_json}",
        )
    return {
        "project_json": observed_project_json,
        "attachment_storage_mode": _project_attachment_mode(observed_project_json),
        "release_tag_prefix": _project_release_tag_prefix(observed_project_json),
        "mutation_applied": True,
    }


def _restore_fixture(
    *,
    service: LiveSetupRepositoryService,
    mutation: RepoMutation,
) -> dict[str, object]:
    current_text = service.fetch_repo_text(mutation.path)
    if current_text != mutation.original_file.content:
        _write_repo_text_with_retry(
            mutation.path,
            service=service,
            content=mutation.original_file.content,
            message=f"{TICKET_KEY}: restore original fixture",
        )
        restored_text = service.fetch_repo_text(mutation.path)
        return {
            "status": "restored",
            "restored_path": mutation.path,
            "restored_attachment_storage_mode": _project_attachment_mode(restored_text),
            "restored_release_tag_prefix": _project_release_tag_prefix(restored_text),
        }
    return {
        "status": "unchanged",
        "restored_path": mutation.path,
        "restored_attachment_storage_mode": _project_attachment_mode(current_text),
        "restored_release_tag_prefix": _project_release_tag_prefix(current_text),
    }


def _project_attachment_mode(project_json_text: str) -> str:
    payload = json.loads(project_json_text)
    if not isinstance(payload, dict):
        return ""
    attachment_storage = payload.get("attachmentStorage")
    if not isinstance(attachment_storage, dict):
        return ""
    return str(attachment_storage.get("mode", "")).strip()


def _project_release_tag_prefix(project_json_text: str) -> str:
    payload = json.loads(project_json_text)
    if not isinstance(payload, dict):
        return ""
    attachment_storage = payload.get("attachmentStorage")
    if not isinstance(attachment_storage, dict):
        return ""
    release_config = attachment_storage.get("githubReleases")
    if not isinstance(release_config, dict):
        return ""
    return str(release_config.get("tagPrefix", "")).strip()


def _write_repo_text_with_retry(
    path: str,
    *,
    service: LiveSetupRepositoryService,
    content: str,
    message: str,
    max_attempts: int = 4,
) -> None:
    for attempt in range(max_attempts):
        try:
            service.write_repo_text(path, content=content, message=message)
            return
        except urllib.error.HTTPError as error:
            if error.code != 409 or attempt == max_attempts - 1:
                raise
            if service.fetch_repo_text(path) == content:
                return


def _assert_primary_callout(
    observation: RepositoryAccessCalloutObservation,
    *,
    expected_message: str,
) -> None:
    if observation.title != PRIMARY_TITLE:
        raise AssertionError(
            "Step 3 failed: the top Repository access band did not show the overall "
            "connected status.\n"
            f"Observed title: {observation.title}\n"
            f"Observed rendered text: {observation.rendered_text}",
        )
    if observation.message != expected_message:
        raise AssertionError(
            "Step 3 failed: the top Repository access band did not show the expected "
            "GitHub Releases connected copy.\n"
            f"Expected message: {expected_message}\n"
            f"Observed message: {observation.message}",
        )


def _assert_secondary_callout(
    observation: RepositoryAccessCalloutObservation,
    *,
    expected_message: str,
) -> None:
    if observation.title != SECONDARY_TITLE:
        raise AssertionError(
            "Step 4 failed: the secondary attachment callout did not show the GitHub "
            "Releases storage title.\n"
            f"Observed title: {observation.title}\n"
            f"Observed rendered text: {observation.rendered_text}",
        )
    if observation.message != expected_message:
        raise AssertionError(
            "Step 4 failed: the secondary attachment callout did not use the expected "
            "browser-supported GitHub Releases copy.\n"
            f"Expected message: {expected_message}\n"
            f"Observed message: {observation.message}",
        )


def _assert_callout_order(observation: RepositoryAccessSectionObservation) -> None:
    if observation.primary_callout.top >= observation.secondary_callout.top:
        raise AssertionError(
            "Step 3 failed: the overall repository access band was not rendered above "
            "the secondary attachment-storage callout.\n"
            f"Primary top: {observation.primary_callout.top}\n"
            f"Secondary top: {observation.secondary_callout.top}",
        )


def _assert_local_git_warning_absent(
    observation: RepositoryAccessSectionObservation,
) -> None:
    if LEGACY_WARNING_TITLE in observation.section_text or LEGACY_WARNING_TITLE in observation.body_text:
        raise AssertionError(
            "Step 4 failed: the blanket local-Git warning was still visible in the "
            "hosted Repository access surface.\n"
            f"Observed section text:\n{observation.section_text}",
        )


def _assert_success_treatment(
    observation: RepositoryAccessCalloutObservation,
    *,
    screenshot_path: str,
    callout_name: str,
) -> dict[str, object]:
    normalized_border_color = _normalize_css_color(observation.border_color)
    normalized_background_color = _normalize_css_color(observation.background_color)
    border_width = _parse_css_pixels(observation.border_width)
    if (
        normalized_border_color not in EXPECTED_SUCCESS_BORDER_COLORS
        or normalized_background_color not in EXPECTED_SUCCESS_BACKGROUND_COLORS
        or border_width <= 0
    ):
        raise AssertionError(
            f"Step 4 failed: the {callout_name} did not use the TrackState success "
            "treatment exposed by the rendered DOM styles.\n"
            f"Expected border colors: {sorted(EXPECTED_SUCCESS_BORDER_COLORS)}\n"
            f"Expected background colors: {sorted(EXPECTED_SUCCESS_BACKGROUND_COLORS)}\n"
            f"Observed border color: {observation.border_color!r}\n"
            f"Observed background color: {observation.background_color!r}\n"
            f"Observed border width: {observation.border_width!r}\n"
            f"Observed rendered text: {observation.rendered_text}\n"
            f"Screenshot: {screenshot_path}",
        )
    return {
        "border_color": observation.border_color,
        "background_color": observation.background_color,
        "border_width": observation.border_width,
        "normalized_border_color": normalized_border_color,
        "normalized_background_color": normalized_background_color,
    }


def _section_payload(
    observation: RepositoryAccessSectionObservation,
) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "section_text": observation.section_text,
        "primary_callout": _callout_payload(observation.primary_callout),
        "secondary_callout": _callout_payload(observation.secondary_callout),
    }


def _callout_payload(
    observation: RepositoryAccessCalloutObservation,
) -> dict[str, object]:
    return {
        "title": observation.title,
        "message": observation.message,
        "rendered_text": observation.rendered_text,
        "semantic_label": observation.semantic_label,
        "border_color": observation.border_color,
        "background_color": observation.background_color,
        "border_width": observation.border_width,
        "top": observation.top,
        "left": observation.left,
        "width": observation.width,
        "height": observation.height,
    }


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


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


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
            },
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
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            f"* Ensured {{{{{PROJECT_JSON_PATH}}}}} used `attachmentStorage.mode = "
            f"github-releases` and observed release tag prefix "
            f"{{{{{result.get('release_tag_prefix', '')}}}}}."
        ),
        "* Opened the deployed hosted TrackState app in a browser-authenticated GitHub session and navigated to Project Settings / Repository access.",
        "* Verified the top repository access band stayed connected and the secondary GitHub Releases callout rendered the supported browser-upload copy.",
        "* Verified the visible callout styling remained success/green and the blanket local-Git warning was removed.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result: Repository access showed a connected top band, the secondary GitHub Releases callout used green success styling with browser-supported upload copy, and the blanket local-Git warning was absent."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}."
        ),
        f"* Screenshot: {{{{{screenshot_path}}}}}",
        "",
        "*Step results*",
        *_step_lines(result, jira=True),
        "",
        "*Human-style verification*",
        *_human_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact error*",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        (
            f"- Ensured `{PROJECT_JSON_PATH}` used "
            "`attachmentStorage.mode = github-releases` and observed release tag "
            f"prefix `{result.get('release_tag_prefix', '')}`."
        ),
        "- Opened the deployed hosted TrackState app in a browser-authenticated GitHub session and navigated to `Project Settings` / `Repository access`.",
        "- Verified the top repository access band stayed connected and the secondary `GitHub Releases attachment storage` callout rendered the supported browser-upload copy.",
        "- Verified the visible callout styling remained success/green and the blanket local-Git warning was removed.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: Repository access showed a connected top band, the secondary GitHub Releases callout used green success styling with browser-supported upload copy, and the blanket local-Git warning was absent."
            if passed
            else "- Did not match the expected result."
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{platform.system()}`."
        ),
        f"- Screenshot: `{screenshot_path}`",
        "",
        "### Step results",
        *_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "### Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            "Ran the deployed hosted Repository access success-state scenario for "
            "GitHub Releases storage and checked the visible settings callouts, copy, "
            "and success styling."
        ),
        "",
        "## Observed",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        f"- Cleanup: `{result.get('cleanup')}`",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    observation = result.get("repository_access_observation", {})
    return "\n".join(
        [
            "# TS-495 - Hosted Repository access does not show the GitHub Releases success state",
            "",
            "## Steps to reproduce",
            "1. Open the application in a hosted browser session.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Navigate to `Project Settings` or an issue detail view.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Inspect the repository access banner/callout area.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "4. Verify the styling and copy of the secondary attachment callout.",
            f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            (
                "- Expected: the top Repository access band shows the overall connected "
                "status, and the secondary `GitHub Releases attachment storage` callout "
                "uses green success styling with copy that explicitly states hosted "
                "release-backed browser uploads are supported."
            ),
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the hosted Repository access surface did not show the expected GitHub Releases success state."
                )
            ),
            "",
            "## Environment",
            f"- URL: `{result['app_url']}`",
            f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
            f"- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.platform()}`",
            f"- Project config: `{PROJECT_JSON_PATH}` with release tag prefix `{result.get('release_tag_prefix', '')}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
            f"- Repository access observation: `{observation}`",
            f"- Settings body text: `{result.get('settings_body', '')}`",
        ],
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        status = str(step.get("status", "failed")).upper() if jira else step.get("status", "failed")
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — {status}: {step['observed']}"
        )
    if not lines:
        lines.append("# No step details were recorded." if jira else "1. No step details were recorded.")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(f"{prefix} {check.get('check')}: {check.get('observed')}")
    if not lines:
        lines.append(
            "# No human-style verification data was recorded."
            if jira
            else "1. No human-style verification data was recorded."
        )
    return lines


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("observed", "No observation recorded."))
    previous_step = step_number - 1
    if previous_step >= 1 and _step_status(result, previous_step) != "passed":
        return (
            f"Not reached because Step {previous_step} failed: "
            f"{_step_observation(result, previous_step)}"
        )
    return str(result.get("error", "No observation recorded."))


if __name__ == "__main__":
    main()
