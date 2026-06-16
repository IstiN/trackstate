from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_repository_access_banner_page import (  # noqa: E402
    LiveRepositoryAccessBannerPage,
    RepositoryAccessBannerExpectation,
    RepositoryAccessBannerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedRepositoryMetadata,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.read_only_connect_hosted_session_runtime import (  # noqa: E402
    ReadOnlyConnectHostedSessionObservation,
    ReadOnlyConnectHostedSessionRuntime,
)

TICKET_KEY = "TS-370"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts370_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts370_failure.png"

DISCONNECTED = RepositoryAccessBannerExpectation(
    mode_label="Needs sign-in",
    title="GitHub write access is not connected",
    message=(
        "Create, edit, comment, and status changes stay read-only until you connect "
        "GitHub with a fine-grained token that has repository Contents write access. "
        "PAT is the default browser path."
    ),
    action_label="Connect GitHub",
)
READ_ONLY = RepositoryAccessBannerExpectation(
    mode_label="Read-only",
    title="This repository session is read-only",
    message=(
        "This account can read the repository but cannot push Git-backed changes. "
        "Reconnect with a token or account that has repository Contents write access, "
        "or switch to a repository where you have that access."
    ),
    action_label="Reconnect for write access",
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    if not service.token:
        raise RuntimeError(
            "TS-370 requires GH_TOKEN or GITHUB_TOKEN to exercise the hosted PAT flow.",
        )

    metadata = service.fetch_demo_metadata()
    _assert_preconditions(metadata)
    issue = service.fetch_issue_fixture("DEMO/DEMO-1")
    observation = ReadOnlyConnectHostedSessionObservation(repository=service.repository)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "browser": "chromium",
        "os": platform.platform(),
        "steps": [],
        "human_verification": [],
        "disconnected_observations": [],
        "read_only_observations": [],
    }
    failures: list[str] = []

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: ReadOnlyConnectHostedSessionRuntime(
                repository=service.repository,
                token=service.token or "",
                observation=observation,
            ),
        ) as tracker_page:
            page = LiveRepositoryAccessBannerPage(tracker_page)
            try:
                runtime = page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    failures.append(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell in an interactive state.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                disconnected_observations = page.observe_banner_across_issue_flows(
                    expectation=DISCONNECTED,
                    issue_key=issue.key,
                    issue_summary=issue.summary,
                )
                result["disconnected_observations"] = [
                    _observation_payload(item) for item in disconnected_observations
                ]
                disconnected_failures = _validate_observations(
                    step=2,
                    expectation=DISCONNECTED,
                    observations=disconnected_observations,
                )
                failures.extend(disconnected_failures)
                _record_step(
                    result,
                    step=2,
                    status="passed" if not disconnected_failures else "failed",
                    action=(
                        "Launch the deployed app unauthenticated and verify the disconnected "
                        "repository-access banner across Dashboard, Board, JQL Search, "
                        "Hierarchy, and issue detail."
                    ),
                    observed=_observation_summary(disconnected_observations),
                )

                dialog = page.open_connect_dialog_from_banner(
                    title=DISCONNECTED.title,
                    action_label=DISCONNECTED.action_label,
                )
                result["connect_dialog"] = {
                    "body_text": dialog.body_text,
                    "token_field_count": dialog.token_field_count,
                    "connect_token_button_count": dialog.connect_token_button_count,
                }
                dialog_failed = (
                    dialog.token_field_count != 1 or dialog.connect_token_button_count < 1
                )
                if dialog_failed:
                    failures.append(
                        "Step 3 failed: clicking the disconnected repository-access banner "
                        "did not expose the expected PAT dialog with a Fine-grained token "
                        "field and Connect token action.\n"
                        f"Observed body text:\n{dialog.body_text}",
                    )
                _record_step(
                    result,
                    step=3,
                    status="failed" if dialog_failed else "passed",
                    action=(
                        'Click the disconnected banner CTA and verify the visible "Connect '
                        'GitHub" dialog exposes the Fine-grained token field and the '
                        '"Connect token" submit action.'
                    ),
                    observed=(
                        f"token_field_count={dialog.token_field_count}; "
                        f"connect_token_button_count={dialog.connect_token_button_count}"
                    ),
                )

                connect_result = page.connect_with_read_only_token(
                    token=service.token,
                    read_only_title=READ_ONLY.title,
                )
                result["read_only_transition"] = {
                    "dialog_text": connect_result.dialog_text,
                    "body_text": connect_result.body_text,
                }
                if not observation.was_exercised:
                    failures.append(
                        "Step 4 failed: the hosted runtime never intercepted the repository "
                        "permission response, so the read-only state was not proven to come "
                        "from a read-only RepositoryAccessDescriptor.\n"
                        f"Observed permission intercepts: {observation.intercepted_urls}",
                    )
                _record_step(
                    result,
                    step=4,
                    status="passed" if observation.was_exercised else "failed",
                    action=(
                        "Authenticate with a PAT while forcing the hosted repository "
                        "permission response to read-only and wait for the live banner to "
                        "switch modes."
                    ),
                    observed=(
                        f"permission_intercepts={len(observation.intercepted_urls)}; "
                        f"read_only_title_visible={READ_ONLY.title in connect_result.body_text}"
                    ),
                )

                read_only_observations = page.observe_banner_across_issue_flows(
                    expectation=READ_ONLY,
                    issue_key=issue.key,
                    issue_summary=issue.summary,
                )
                result["read_only_observations"] = [
                    _observation_payload(item) for item in read_only_observations
                ]
                read_only_failures = _validate_observations(
                    step=5,
                    expectation=READ_ONLY,
                    observations=read_only_observations,
                )
                failures.extend(read_only_failures)
                _record_step(
                    result,
                    step=5,
                    status="passed" if not read_only_failures else "failed",
                    action=(
                        "Verify the read-only repository-access banner stays visible across "
                        "Dashboard, Board, JQL Search, Hierarchy, and issue detail."
                    ),
                    observed=_observation_summary(read_only_observations),
                )

                settings_body = page.click_recovery_action(
                    title=READ_ONLY.title,
                    action_label=READ_ONLY.action_label,
                )
                result["recovery_body_text"] = settings_body
                recovery_failed = (
                    ("Project Settings" not in settings_body or "Repository access" not in settings_body)
                    and "Manage GitHub access" not in settings_body
                )
                if recovery_failed:
                    failures.append(
                        "Step 6 failed: clicking the read-only recovery CTA did not route "
                        "to the canonical recovery surface.\n"
                        f"Observed body text:\n{settings_body}",
                    )
                _record_step(
                    result,
                    step=6,
                    status="failed" if recovery_failed else "passed",
                    action=(
                        "Click the read-only recovery CTA and verify the user is routed to "
                        "the canonical settings/auth recovery surface."
                    ),
                    observed=(
                        f'project_settings_visible={"Project Settings" in settings_body}; '
                        f'repository_access_visible={"Repository access" in settings_body}; '
                        f'manage_github_access_visible={"Manage GitHub access" in settings_body}'
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the deployed shell like a user and confirmed the disconnected "
                        "banner text, CTA label, and mode label remained visible while "
                        "switching sections and opening a real issue detail."
                    ),
                    observed=_observation_summary(disconnected_observations),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the post-auth read-only shell and confirmed the recovery CTA "
                        "visibly switched to Reconnect for write access and opened the "
                        "canonical settings/auth recovery surface."
                    ),
                    observed=(
                        _observation_summary(read_only_observations)
                        + " | "
                        + (
                            f'project_settings_visible={"Project Settings" in settings_body}; '
                            f'repository_access_visible={"Repository access" in settings_body}; '
                            f'manage_github_access_visible={"Manage GitHub access" in settings_body}'
                        )
                    ),
                )

                if failures:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    raise AssertionError("\n".join(failures))

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                return
            except Exception:
                if "screenshot" not in result:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["permission_patch_observation"] = {
            "intercepted_urls": list(observation.intercepted_urls),
            "observed_permissions": list(observation.observed_permissions),
        }
        _write_failure_outputs(result)
        raise


def _assert_preconditions(metadata: LiveHostedRepositoryMetadata) -> None:
    if metadata.project_key != "DEMO":
        raise AssertionError(
            "Precondition failed: TS-370 expected the seeded DEMO hosted project.\n"
            f"Observed project key: {metadata.project_key}",
        )


def _validate_observations(
    *,
    step: int,
    expectation: RepositoryAccessBannerExpectation,
    observations: list[RepositoryAccessBannerObservation],
) -> list[str]:
    failures: list[str] = []
    for observation in observations:
        if observation.navigation_error:
            failures.append(
                f"Step {step} failed: could not reach {observation.location} while "
                f"verifying the {expectation.mode_label} repository-access banner.\n"
                f"Navigation error: {observation.navigation_error}\n"
                f"Observed body text:\n{observation.body_text}",
            )
            continue
        if not observation.topbar_label_visible:
            failures.append(
                f"Step {step} failed: {observation.location} did not expose the expected "
                f'"{expectation.mode_label}" repository-access mode label.\n'
                f"Observed body text:\n{observation.body_text}",
            )
        if observation.banner_text is None:
            failures.append(
                f"Step {step} failed: {observation.location} did not show the "
                f'"{expectation.title}" repository-access banner with the expected '
                "message and recovery action in the same visible surface.\n"
                f"Observed body text:\n{observation.body_text}",
            )
            continue
        if observation.action_button_count < 1:
            failures.append(
                f"Step {step} failed: {observation.location} showed the "
                f'"{expectation.title}" banner text but did not expose a visible '
                f'"{expectation.action_label}" action inside that banner.\n'
                f"Observed banner text:\n{observation.banner_text}",
            )
    return failures


def _observation_payload(
    observation: RepositoryAccessBannerObservation,
) -> dict[str, object]:
    return {
        "location": observation.location,
        "topbar_label_visible": observation.topbar_label_visible,
        "banner_text": observation.banner_text,
        "action_button_count": observation.action_button_count,
        "navigation_error": observation.navigation_error,
        "body_text": observation.body_text,
    }


def _observation_summary(
    observations: list[RepositoryAccessBannerObservation],
) -> str:
    fragments: list[str] = []
    for observation in observations:
        if observation.navigation_error:
            fragments.append(
                f"{observation.location}=navigation_error({observation.navigation_error})",
            )
            continue
        fragments.append(
            f"{observation.location}=mode:{observation.topbar_label_visible},"
            f"banner:{observation.banner_text is not None},"
            f"action_count:{observation.action_button_count}",
        )
    return "; ".join(fragments)


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
        "* Opened the deployed hosted TrackState app in an unauthenticated browser session.",
        "* Verified the disconnected repository-access banner stayed visible across Dashboard, Board, JQL Search, Hierarchy, and a real issue detail view.",
        "* Clicked the disconnected banner CTA, completed the visible PAT dialog, and patched the live repository permission response to read-only.",
        "* Verified the banner switched to the read-only mode and stayed visible across the same issue flows.",
        "* Clicked the read-only recovery CTA and verified the canonical recovery surface opened.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the deployed banner reflected the repository access mode and kept a functional recovery link across the covered issue flows."
            if passed
            else "* Did not match the expected result."
        ),
        f"* Environment: URL {{{{{result['app_url']}}}}}, repository *{result['repository']}*, browser *chromium*, OS *{result['os']}*.",
        f"* Screenshot: {{{{{screenshot_path}}}}}",
        "",
        "*Real user-style verification*",
    ]
    for item in result.get("human_verification", []):
        if isinstance(item, dict):
            lines.append(f"* {item.get('check')} Observed: {item.get('observed')}")
    if not passed:
        lines.extend(
            [
                "",
                "*Failure details*",
                f"* Error: {{code}}{result.get('error', 'unknown error')}{{code}}",
                "* Traceback:",
                "{code}",
                str(result.get("traceback", "")),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation coverage",
        "- Opened the deployed hosted TrackState app in an unauthenticated browser session.",
        "- Verified the disconnected repository-access banner stayed visible across Dashboard, Board, JQL Search, Hierarchy, and a real issue detail view.",
        "- Clicked the disconnected banner CTA, completed the visible PAT dialog, and patched the live repository permission response to read-only.",
        "- Verified the banner switched to the read-only mode and stayed visible across the same issue flows.",
        "- Clicked the read-only recovery CTA and verified the canonical recovery surface opened.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: the deployed banner reflected the repository access mode and kept a functional recovery link across the covered issue flows."
            if passed
            else "- Did not match the expected result."
        ),
        f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}`, browser `chromium`, OS `{result['os']}`.",
        f"- Screenshot: `{screenshot_path}`",
        "",
        "### Real user-style verification",
    ]
    for item in result.get("human_verification", []):
        if isinstance(item, dict):
            lines.append(f"- {item.get('check')} Observed: {item.get('observed')}")
    if not passed:
        lines.extend(
            [
                "",
                "### Failure details",
                f"- Error: `{result.get('error', 'unknown error')}`",
                "",
                "```text",
                str(result.get("traceback", "")),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        f"# {TICKET_KEY} {'passed' if passed else 'failed'}",
        "",
        (
            "Verified the deployed hosted repository-access banner reflected the "
            "disconnected and read-only modes across Dashboard, Board, JQL Search, "
            "Hierarchy, and issue detail, and that the read-only recovery CTA opened "
            "the canonical settings/auth recovery surface."
            if passed
            else "The deployed hosted repository-access banner scenario did not match the expected result."
        ),
        "",
        f"- URL: `{result['app_url']}`",
        f"- Repository: `{result['repository']}`",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
    ]
    if not passed:
        lines.extend(
            [
                "",
                f"- Error: `{result.get('error', 'unknown error')}`",
            ],
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    steps_lines = []
    for item in result.get("steps", []):
        if not isinstance(item, dict):
            continue
        emoji = "✅" if item.get("status") == "passed" else "❌"
        steps_lines.append(
            f"# {item.get('action')} {emoji}\nObserved: {item.get('observed')}",
        )

    return "\n".join(
        [
            f"h3. Bug: {TICKET_KEY} global repository-access banner did not stay consistent across the live hosted recovery flow",
            "",
            "h4. Environment",
            f"* URL: {result.get('app_url')}",
            f"* Repository: {result.get('repository')}",
            "* Browser: chromium",
            f"* OS: {result.get('os')}",
            "",
            "h4. Steps to Reproduce",
            *steps_lines,
            "",
            "h4. Expected Result",
            "The banner remains visible across the covered issue flows, reflects the current repository access mode, and its recovery CTA opens the canonical recovery surface.",
            "",
            "h4. Actual Result",
            str(result.get("error", "Unknown failure")),
            "",
            "h4. Logs / Error Output",
            "{code}",
            str(result.get("traceback", "")),
            "{code}",
            "",
            "h4. Notes",
            f"* Screenshot: {result.get('screenshot', FAILURE_SCREENSHOT_PATH)}",
        ],
    ) + "\n"


if __name__ == "__main__":
    main()
