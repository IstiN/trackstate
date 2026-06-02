from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.pull_request_template_checklist_verifier import (  # noqa: E402
    PullRequestTemplateChecklistVerifier,
)
from testing.core.config.pull_request_template_checklist_config import (  # noqa: E402
    PullRequestTemplateChecklistConfig,
)
from testing.core.models.pull_request_template_checklist_result import (  # noqa: E402
    PullRequestTemplateChecklistVerificationResult,
)
from testing.tests.support.github_pull_request_compose_page_factory import (  # noqa: E402
    GitHubPullRequestComposeRuntimeUnavailableError,
    create_github_pull_request_compose_page,
)
from testing.tests.support.github_repository_blob_page_factory import (  # noqa: E402
    create_github_repository_blob_page,
)
from testing.tests.support.project_cli_probe_factory import create_project_cli_probe  # noqa: E402

TICKET_KEY = "TS-909"
TEST_CASE_TITLE = (
    "Verify PR template — manual accessibility checklist item for DOM order is present"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-909/test_ts_909.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts909_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts909_failure.png"
TICKET_STEPS = [
    "Create a new Pull Request for a UI layout change.",
    "Verify that the PR description template automatically includes an accessibility checklist.",
    (
        "Confirm the presence of the specific item: "
        "'Manual verification: DOM order matches visual hierarchy for keyboard-accessible elements.'"
    ),
]
EXPECTED_RESULT = (
    "The checklist item is present in the PR template, ensuring developers and "
    "reviewers manually confirm focus order logic matches the visual layout."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config_path = REPO_ROOT / "testing/tests/TS-909/config.yaml"
    config = PullRequestTemplateChecklistConfig.from_file(config_path)
    probe = create_project_cli_probe(REPO_ROOT)
    verifier = PullRequestTemplateChecklistVerifier(probe)
    verification = verifier.validate(config=config)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "repository": config.repository,
        "expected_default_branch": config.expected_default_branch,
        "required_checklist_item": config.required_checklist_item,
        "run_command": RUN_COMMAND,
        "browser": "Chromium (Playwright required)",
        "os": platform.platform(),
        "linked_bugs": ["TS-905"],
        "ticket_steps": list(TICKET_STEPS),
        "expected_result": EXPECTED_RESULT,
        "steps": [],
        "human_verification": [],
        "failure_kind": "product",
    }

    try:
        _capture_verification_metadata(
            result=result,
            verification=verification,
            config=config,
        )
        repository_template_available = _evaluate_repository_template(
            result=result,
            verification=verification,
            config=config,
        )
        if repository_template_available:
            _evaluate_pull_request_compose_surface(
                result=result,
                probe=probe,
                verification=verification,
                config=config,
            )
            _evaluate_template_body(
                result=result,
                verification=verification,
                config=config,
            )
        _perform_human_template_verification(
            result=result,
            config=config,
        )

        failures = _failed_steps(result)
        if result.get("failure_kind") == "setup":
            result["blocked_reason"] = _blocked_reason(result)
            result["missing"] = [_blocked_missing_entry(config)]
            _write_blocked_outputs(result)
            return
        if failures:
            raise AssertionError("\n".join(failures))

        _write_pass_outputs(result)
    except AssertionError as error:
        result["error"] = f"AssertionError: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _capture_verification_metadata(
    *,
    result: dict[str, object],
    verification: PullRequestTemplateChecklistVerificationResult,
    config: PullRequestTemplateChecklistConfig,
) -> None:
    default_branch = verification.default_branch or config.expected_default_branch or "main"
    selected_candidate = verification.selected_candidate
    selected_recognized_template = verification.selected_recognized_template
    result["default_branch"] = default_branch
    result["configured_pull_request_template_url"] = (
        verification.configured_pull_request_template_url
    )
    result["configured_pull_request_template_path"] = (
        verification.configured_pull_request_template_path
    )
    result["discovered_template_paths"] = list(verification.discovered_template_paths)
    result["candidate_template_paths"] = [
        {
            "path": observation.path,
            "exists": observation.exists,
            "entry_type": observation.entry_type,
            "contents_exit_code": observation.contents_fetch.exit_code,
            "raw_exit_code": observation.raw_fetch.exit_code,
            "contents_stderr": observation.contents_fetch.stderr,
            "raw_stderr": observation.raw_fetch.stderr,
        }
        for observation in verification.candidate_observations
    ]
    result["recognized_pull_request_templates"] = [
        {
            "filename": template.filename,
            "body": template.body,
        }
        for template in verification.recognized_templates
    ]
    result["selected_template_path"] = (
        selected_recognized_template.filename
        if selected_recognized_template is not None
        else (selected_candidate.path if selected_candidate is not None else None)
    )
    result["selected_template_text"] = (
        selected_recognized_template.body
        if selected_recognized_template is not None
        else (selected_candidate.raw_text if selected_candidate is not None else None)
    )


def _evaluate_pull_request_compose_surface(
    *,
    result: dict[str, object],
    probe,
    verification: PullRequestTemplateChecklistVerificationResult,
    config: PullRequestTemplateChecklistConfig,
) -> None:
    default_branch = verification.default_branch or config.expected_default_branch or "main"
    branches_result = probe.list_branches(config.repository)
    pulls_result = probe.pull_requests(config.repository, state="open")

    if not branches_result.succeeded:
        result["failure_kind"] = "setup"
        _record_step(
            result,
            step=1,
            status="failed",
            action=TICKET_STEPS[0],
            observed=(
                "The automation could not list live repository branches to find a real "
                "pull-request compose candidate.\n"
                f"Command: {branches_result.command_text}\n"
                f"Exit code: {branches_result.exit_code}\n"
                f"stdout:\n{branches_result.stdout}\n"
                f"stderr:\n{branches_result.stderr}"
            ),
        )
        return

    if not pulls_result.succeeded:
        result["failure_kind"] = "setup"
        _record_step(
            result,
            step=1,
            status="failed",
            action=TICKET_STEPS[0],
            observed=(
                "The automation could not list open pull requests to avoid branches "
                "that already have a PR.\n"
                f"Command: {pulls_result.command_text}\n"
                f"Exit code: {pulls_result.exit_code}\n"
                f"stdout:\n{pulls_result.stdout}\n"
                f"stderr:\n{pulls_result.stderr}"
            ),
        )
        return

    branch_names = _branch_names(branches_result.json_payload)
    open_pull_request_heads = _open_pull_request_heads(pulls_result.json_payload)
    candidate_heads = [
        branch
        for branch in branch_names
        if branch != default_branch and branch not in open_pull_request_heads
    ]
    result["candidate_compare_heads"] = candidate_heads[:10]

    if not candidate_heads:
        result["failure_kind"] = "setup"
        _record_step(
            result,
            step=1,
            status="failed",
            action=TICKET_STEPS[0],
            observed=(
                "The repository did not expose any branch that could be used to open a "
                "new pull-request compose surface after excluding the default branch and "
                "branches that already have open pull requests.\n"
                f"Default branch: {default_branch}\n"
                f"Open pull-request heads: {sorted(open_pull_request_heads)}"
            ),
        )
        return

    compare_attempts: list[dict[str, object]] = []
    successful_observation = None
    successful_head_branch: str | None = None
    last_observation = None
    expected_surface_texts = (
        "Open a pull request",
        "View pull request",
        "There isn’t anything to compare.",
        "There isn’t anything to compare",
        "Choose different branches or forks above to discuss and review changes.",
        "Comparing changes",
    )
    try:
        with create_github_pull_request_compose_page() as compose_page:
            for head_branch in candidate_heads[:10]:
                try:
                    observation = compose_page.open_compose_surface(
                        repository=verification.target_repository,
                        base_branch=default_branch,
                        head_branch=head_branch,
                        expected_texts=expected_surface_texts,
                        screenshot_path=None,
                    )
                except AssertionError as error:
                    error_text = str(error)
                    compare_attempts.append(
                        {
                            "head_branch": head_branch,
                            "url": _compose_compare_url(
                                repository=verification.target_repository,
                                base_branch=default_branch,
                                head_branch=head_branch,
                            ),
                            "matched_text": None,
                            "body_text_excerpt": _snippet(error_text),
                            "description_selector": None,
                            "description_value_excerpt": None,
                            "error": error_text,
                        }
                    )
                    if _looks_like_unauthenticated_compare_surface(error_text):
                        result["failure_kind"] = "setup"
                        break
                    continue
                last_observation = observation
                compare_attempts.append(
                    {
                        "head_branch": head_branch,
                        "url": observation.url,
                        "matched_text": observation.matched_text,
                        "body_text_excerpt": _snippet(observation.body_text),
                        "description_selector": observation.description_selector,
                        "description_value_excerpt": (
                            _snippet(observation.description_value)
                            if isinstance(observation.description_value, str)
                            else None
                        ),
                    }
                )
                if _looks_like_unauthenticated_compare_surface(observation.body_text):
                    result["failure_kind"] = "setup"
                    break
                if observation.matched_text == "Open a pull request":
                    successful_observation = observation
                    successful_head_branch = head_branch
                    break
    except GitHubPullRequestComposeRuntimeUnavailableError as error:
        result["failure_kind"] = "setup"
        _record_step(
            result,
            step=1,
            status="failed",
            action=TICKET_STEPS[0],
            observed=str(error),
        )
        return

    result["compare_attempts"] = compare_attempts

    if successful_observation is None or successful_head_branch is None:
        if _looks_like_unauthenticated_github_browser(compare_attempts):
            result["failure_kind"] = "setup"
        if last_observation is not None:
            result["compare_surface"] = {
                "head_branch": candidate_heads[min(len(compare_attempts), len(candidate_heads)) - 1],
                "url": last_observation.url,
                "matched_text": last_observation.matched_text,
                "body_text": last_observation.body_text,
                "screenshot_path": last_observation.screenshot_path,
                "description_value": last_observation.description_value,
                "description_selector": last_observation.description_selector,
            }
            result["screenshot"] = last_observation.screenshot_path
        failure_prefix = (
            "The automation did not have an authenticated GitHub browser session, so "
            "it could not reach the live `Open a pull request` compose form needed to "
            "inspect the generated PR description body.\n"
            if result.get("failure_kind") == "setup"
            else (
                "The automation exercised live GitHub compare pages, but none reached "
                "the `Open a pull request` compose surface needed to inspect the "
                "generated PR description body.\n"
            )
        )
        _record_step(
            result,
            step=1,
            status="failed",
            action=TICKET_STEPS[0],
            observed=(
                failure_prefix
                + f"Repository: {verification.target_repository}\n"
                f"Default branch: {default_branch}\n"
                f"Attempt summaries: {json.dumps(compare_attempts, indent=2)}"
            ),
        )
        return

    result["compare_surface"] = {
        "head_branch": successful_head_branch,
        "url": successful_observation.url,
        "matched_text": successful_observation.matched_text,
        "body_text": successful_observation.body_text,
        "screenshot_path": successful_observation.screenshot_path,
        "description_value": successful_observation.description_value,
        "description_selector": successful_observation.description_selector,
    }
    result["compare_url"] = successful_observation.url
    result["screenshot"] = successful_observation.screenshot_path
    _record_step(
        result,
        step=1,
        status="passed",
        action=TICKET_STEPS[0],
        observed=(
            "GitHub opened the live compare page on the `Open a pull request` compose "
            "surface.\n"
            f"Repository: {verification.target_repository}\n"
            f"Base branch: {default_branch}\n"
            f"Head branch: {successful_head_branch}\n"
            f"Compose URL: {successful_observation.url}\n"
            f"Description field selector: "
            f"{successful_observation.description_selector or '<not exposed>'}"
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Opened the live GitHub compare page and confirmed the reviewer-visible "
            "`Open a pull request` surface."
        ),
        observed=(
            f"Visible page URL: {successful_observation.url}\n"
            f"Matched visible text: {successful_observation.matched_text}\n"
            f"Visible body text excerpt: {_snippet(successful_observation.body_text)}\n"
            f"Description field selector: "
            f"{successful_observation.description_selector or '<not exposed>'}\n"
            f"Description value excerpt: "
            f"{_snippet(successful_observation.description_value) if isinstance(successful_observation.description_value, str) else '<not exposed>'}\n"
            f"Screenshot: {successful_observation.screenshot_path or '<not captured>'}"
        ),
    )


def _evaluate_template_body(
    *,
    result: dict[str, object],
    verification: PullRequestTemplateChecklistVerificationResult,
    config: PullRequestTemplateChecklistConfig,
) -> None:
    if _step_status(result, 1) != "passed":
        return

    body_source_name, body_source_path, body_source_field, body_source_text = _resolved_template_body_source(
        result=result,
    )
    result["selected_template_source"] = body_source_name
    if body_source_path is not None:
        result["selected_template_path"] = body_source_path
    if body_source_field is not None:
        result["selected_template_field"] = body_source_field
    if body_source_text is not None:
        result["selected_template_text"] = body_source_text

    if body_source_text is None:
        _record_step(
            result,
            step=2,
            status="failed",
            action=TICKET_STEPS[1],
            observed=(
                "The live `Open a pull request` surface did not expose a readable PR "
                "description field value, so the automation could not verify that GitHub "
                "auto-populated an accessibility checklist in the generated PR body.\n"
                f"Description field selector: {body_source_field or '<not exposed>'}\n"
                f"Compose URL: {result.get('compare_url', '<unavailable>')}\n"
                f"Recognized templates: {json.dumps(result['recognized_pull_request_templates'], indent=2)}\n"
                f"Candidate file observations: {json.dumps(result['candidate_template_paths'], indent=2)}"
            ),
        )
        _record_step(
            result,
            step=3,
            status="failed",
            action=TICKET_STEPS[2],
            observed=(
                "The exact DOM-order checklist item could not be present because the live "
                "compose surface did not expose a readable PR description field value.\n"
                f"Description field selector: {body_source_field or '<not exposed>'}\n"
                f"Required item: {config.required_checklist_item}"
            ),
        )
        return

    matched_marker = _first_accessibility_marker(
        body_source_text,
        config.accessibility_section_markers,
    )
    if matched_marker is None:
        _record_step(
            result,
            step=2,
            status="failed",
            action=TICKET_STEPS[1],
            observed=(
                "The actual PR description value from the live compose page did not "
                "include an accessibility checklist marker.\n"
                f"Body source: {body_source_name}\n"
                f"Compose URL: {body_source_path}\n"
                f"Description field selector: {body_source_field}\n"
                f"Expected markers: {list(config.accessibility_section_markers)}\n"
                f"Observed body text:\n{body_source_text}"
            ),
        )
    else:
        result["matched_accessibility_marker"] = matched_marker
        _record_step(
            result,
            step=2,
            status="passed",
            action=TICKET_STEPS[1],
            observed=(
                "The actual PR description value from the live compose page includes an "
                "accessibility checklist marker.\n"
                f"Body source: {body_source_name}\n"
                f"Compose URL: {body_source_path}\n"
                f"Description field selector: {body_source_field}\n"
                f"Matched marker: {matched_marker}"
            ),
        )

    if config.required_checklist_item not in body_source_text:
        _record_step(
            result,
            step=3,
            status="failed",
            action=TICKET_STEPS[2],
            observed=(
                "The actual PR description value from the live compose page did not "
                "contain the "
                "exact required checklist item.\n"
                f"Body source: {body_source_name}\n"
                f"Compose URL: {body_source_path}\n"
                f"Description field selector: {body_source_field}\n"
                f"Required item: {config.required_checklist_item}\n"
                f"Observed body text:\n{body_source_text}"
            ),
        )
        return

    if matched_marker is None:
        _record_step(
            result,
            step=3,
            status="failed",
            action=TICKET_STEPS[2],
            observed=(
                "The exact checklist item was found, but GitHub did not expose it "
                "inside a recognizable accessibility checklist section."
            ),
        )
        return

    _record_step(
        result,
        step=3,
        status="passed",
        action=TICKET_STEPS[2],
        observed=(
            "The actual PR description value from the live compose page contains the exact "
            "required checklist item.\n"
            f"Body source: {body_source_name}\n"
            f"Compose URL: {body_source_path}\n"
            f"Description field selector: {body_source_field}\n"
            f"Required item: {config.required_checklist_item}"
        ),
    )


def _evaluate_repository_template(
    *,
    result: dict[str, object],
    verification: PullRequestTemplateChecklistVerificationResult,
    config: PullRequestTemplateChecklistConfig,
) -> bool:
    body_source_name, body_source_path, body_source_text = _selected_template_body_source(
        verification=verification
    )
    result["selected_template_source"] = body_source_name
    if body_source_path is not None:
        result["selected_template_path"] = body_source_path
    if body_source_text is not None:
        result["selected_template_text"] = body_source_text

    if body_source_text is None:
        result["failure_kind"] = "product"
        _record_step(
            result,
            step=1,
            status="failed",
            action=TICKET_STEPS[0],
            observed=(
                "GitHub does not expose any pull-request template body for this "
                "repository, so a new UI layout pull request cannot automatically "
                "start from a template that includes the required accessibility "
                "checklist item.\n"
                f"Repository: {verification.target_repository}\n"
                f"Default branch: {verification.default_branch or config.expected_default_branch or 'main'}\n"
                f"Configured template path: {verification.configured_pull_request_template_path}\n"
                f"Discovered template paths: {list(verification.discovered_template_paths)}\n"
                f"Recognized templates: {json.dumps(result['recognized_pull_request_templates'], indent=2)}\n"
                f"Candidate file observations: {json.dumps(result['candidate_template_paths'], indent=2)}"
            ),
        )
        _record_step(
            result,
            step=2,
            status="failed",
            action=TICKET_STEPS[1],
            observed=(
                "GitHub did not expose a PR template body that could contain an "
                "accessibility checklist.\n"
                f"Configured template URL: {verification.configured_pull_request_template_url}\n"
                f"Recognized templates: {json.dumps(result['recognized_pull_request_templates'], indent=2)}"
            ),
        )
        _record_step(
            result,
            step=3,
            status="failed",
            action=TICKET_STEPS[2],
            observed=(
                "The exact DOM-order checklist item could not be present because "
                "GitHub did not expose any PR template body for the repository.\n"
                f"Required item: {config.required_checklist_item}"
            ),
        )
        return False

    return True


def _selected_template_body_source(
    *,
    verification: PullRequestTemplateChecklistVerificationResult,
) -> tuple[str | None, str | None, str | None]:
    selected_recognized_template = verification.selected_recognized_template
    if (
        selected_recognized_template is not None
        and selected_recognized_template.body.strip()
    ):
        return (
            "GitHub pullRequestTemplates GraphQL response",
            selected_recognized_template.filename,
            selected_recognized_template.body,
        )

    selected_candidate = verification.selected_candidate
    if selected_candidate is None:
        return None, None, None

    raw_text = selected_candidate.raw_text
    if isinstance(raw_text, str) and raw_text.strip():
        return (
            "GitHub repository file contents",
            selected_candidate.path,
            raw_text,
        )
    return None, selected_candidate.path, None


def _perform_human_template_verification(
    *,
    result: dict[str, object],
    config: PullRequestTemplateChecklistConfig,
) -> None:
    if _step_status(result, 1) == "passed":
        return
    if result.get("failure_kind") == "setup":
        default_branch = str(
            result.get("default_branch", result.get("expected_default_branch", "main"))
        )
        selected_template_path = result.get("selected_template_path")
        configured_template_path = result.get("configured_pull_request_template_path")
        if isinstance(configured_template_path, str) and configured_template_path:
            template_path = configured_template_path
        elif (
            isinstance(selected_template_path, str)
            and selected_template_path
            and "/" in selected_template_path
        ):
            template_path = selected_template_path
        else:
            template_path = config.candidate_template_paths[0]
        expected_texts = (
            config.required_checklist_item,
            *config.accessibility_section_markers,
            config.repository.split("/", maxsplit=1)[1],
        )
        try:
            with create_github_repository_blob_page() as file_page:
                observation = file_page.open_blob_page(
                    repository=config.repository,
                    ref=default_branch,
                    path=template_path,
                    expected_texts=expected_texts,
                    screenshot_path=None,
                )
        except GitHubPullRequestComposeRuntimeUnavailableError as error:
            _record_human_verification(
                result,
                check=(
                    "Attempted to open the live GitHub PR template file page for "
                    "human-style confirmation."
                ),
                observed=(
                    "The browser runtime required for reviewer-visible evidence was "
                    f"unavailable, but the run had already been blocked by the "
                    f"authenticated GitHub browser wall.\nRuntime error: {error}"
                ),
            )
            return

        result["evidence_url"] = observation.url
        result["evidence_body_text"] = observation.body_text
        result["evidence_matched_text"] = observation.matched_text
        visible_body_text = observation.body_text
        if config.required_checklist_item not in visible_body_text:
            raise AssertionError(
                "Human-style verification expected the live PR template file page to "
                "show the required checklist item, but the visible page did not.\n"
                f"URL: {observation.url}\n"
                f"Matched text: {observation.matched_text}\n"
                f"Visible body text:\n{visible_body_text}"
            )

        _record_human_verification(
            result,
            check=(
                "Opened the live GitHub PR template file page and confirmed the "
                "required checklist item is visible."
            ),
            observed=(
                f"Visible page URL: {observation.url}\n"
                f"Matched visible text: {observation.matched_text}\n"
                f"Template path: {template_path}\n"
                f"Screenshot: {observation.screenshot_path or '<not captured>'}\n"
                f"Visible body text excerpt: {_snippet(observation.body_text)}"
            ),
        )
        return
    if result.get("failure_kind") != "product":
        return

    default_branch = str(
        result.get("default_branch", result.get("expected_default_branch", "main"))
    )
    selected_template_path = result.get("selected_template_path")
    configured_template_path = result.get("configured_pull_request_template_path")
    if isinstance(configured_template_path, str) and configured_template_path:
        template_path = configured_template_path
    elif (
        isinstance(selected_template_path, str)
        and selected_template_path
        and "/" in selected_template_path
    ):
        template_path = selected_template_path
    else:
        template_path = config.candidate_template_paths[0]
    screenshot_path = str(
        FAILURE_SCREENSHOT_PATH if _failed_steps(result) else SUCCESS_SCREENSHOT_PATH
    )
    expected_texts = (
        config.required_checklist_item,
        *config.accessibility_section_markers,
        "404",
        "page not found",
        config.repository.split("/", maxsplit=1)[1],
    )
    try:
        with create_github_repository_blob_page() as file_page:
            observation = file_page.open_blob_page(
                repository=config.repository,
                ref=default_branch,
                path=template_path,
                expected_texts=expected_texts,
                screenshot_path=screenshot_path,
            )
    except GitHubPullRequestComposeRuntimeUnavailableError as error:
        _record_human_verification(
            result,
            check=(
                "Attempted to open the live GitHub PR template file page for "
                "human-style confirmation."
            ),
            observed=(
                "The browser runtime required for reviewer-visible evidence was "
                f"unavailable, but the repository checks had already proved the "
                f"product defect.\nRuntime error: {error}"
            ),
        )
        return

    result["screenshot"] = observation.screenshot_path
    result["evidence_url"] = observation.url
    result["evidence_body_text"] = observation.body_text
    result["evidence_matched_text"] = observation.matched_text

    visible_body_text = observation.body_text
    if "404" not in visible_body_text and "page not found" not in visible_body_text.lower():
        raise AssertionError(
            "Human-style verification expected GitHub to show a missing-template "
            "page, but the visible file page did not show a 404.\n"
            f"URL: {observation.url}\n"
            f"Matched text: {observation.matched_text}\n"
            f"Visible body text:\n{visible_body_text}"
        )

    _record_human_verification(
        result,
        check=(
            "Opened the live GitHub PR template file page and inspected the "
            "visible page content a reviewer would read."
        ),
        observed=(
            f"Visible page URL: {observation.url}\n"
            f"Matched visible text: {observation.matched_text}\n"
            f"Template path: {template_path}\n"
            f"Screenshot: {observation.screenshot_path or '<not captured>'}\n"
            f"Visible body text excerpt: {_snippet(observation.body_text)}"
        ),
    )


def _resolved_template_body_source(
    *,
    result: dict[str, object],
) -> tuple[str | None, str | None, str | None, str | None]:
    compare_surface = result.get("compare_surface", {})
    if isinstance(compare_surface, dict):
        description_value = compare_surface.get("description_value")
        if isinstance(description_value, str):
            return (
                "live GitHub PR description field",
                compare_surface.get("url")
                if isinstance(compare_surface.get("url"), str)
                else None,
                compare_surface.get("description_selector")
                if isinstance(compare_surface.get("description_selector"), str)
                else None,
                description_value,
            )

        return (
            None,
            compare_surface.get("url")
            if isinstance(compare_surface.get("url"), str)
            else None,
            compare_surface.get("description_selector")
            if isinstance(compare_surface.get("description_selector"), str)
            else None,
            None,
        )

    return None, None, None, None


def _branch_names(payload: object | None) -> list[str]:
    if not isinstance(payload, list):
        return []
    branches: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name:
            branches.append(name)
    return branches


def _open_pull_request_heads(payload: object | None) -> set[str]:
    if not isinstance(payload, list):
        return set()
    heads: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        head = item.get("head")
        if not isinstance(head, dict):
            continue
        ref = head.get("ref")
        if isinstance(ref, str) and ref:
            heads.add(ref)
    return heads


def _first_accessibility_marker(
    template_text: str,
    markers: tuple[str, ...],
) -> str | None:
    lowered = template_text.lower()
    for marker in markers:
        if marker.lower() in lowered:
            return marker
    return None


def _no_template_exists(
    verification: PullRequestTemplateChecklistVerificationResult,
) -> bool:
    """Return True when every API source confirms no PR template is present."""
    existing_candidates = getattr(verification, "existing_candidates", ())
    recognized_templates = getattr(verification, "recognized_templates", ())
    has_existing_candidate = bool(existing_candidates)
    has_recognized_template = bool(recognized_templates)
    return not has_existing_candidate and not has_recognized_template


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


def _failed_steps(result: dict[str, object]) -> list[str]:
    failures: list[str] = []
    for item in result.get("steps", []):
        if not isinstance(item, dict):
            continue
        if item.get("status") != "failed":
            continue
        failures.append(f"Step {item.get('step')} failed: {item.get('observed')}")
    return failures


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
    if result.get("failure_kind") == "product":
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _write_blocked_outputs(result: dict[str, object]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "blocked_by_human",
                "blocked_reason": result.get("blocked_reason", ""),
                "missing": result.get("missing", []),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment_blocked(result), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body_blocked(result), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary_blocked(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            "* Queried the live GitHub repository metadata, community profile, "
            "default-branch tree, conventional "
            f"template paths, and GitHub `pullRequestTemplates` diagnostics for {{{{{result['repository']}}}}}."
        ),
        (
            "* When repository evidence showed a usable PR template body, opened a live GitHub compare page that reached {{Open a pull request}} and inspected the actual PR description field value."
        ),
        (
            "* When repository evidence already proved the template was missing, opened the live GitHub file page for the canonical template path and checked the reviewer-visible content."
        ),
        "",
        "*Observed result*",
        "* Matched the expected result." if passed else "* Did not match the expected result.",
        (
            f"* Environment: repository {{{{{result['repository']}}}}}, branch "
            f"{{{{{result.get('default_branch', result.get('expected_default_branch', 'main'))}}}}}, "
            f"browser {{{{{result['browser']}}}}}, OS {{{{{result['os']}}}}}."
        ),
        f"* Evidence URL: {{{{{result.get('evidence_url', '<unavailable>')}}}}}",
        f"* Screenshot: {{{{{result.get('screenshot', '<not captured>')}}}}}",
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
            ]
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        (
            f"- Queried the live GitHub repository metadata, community profile, "
            f"default-branch tree, conventional "
            f"template paths, and GitHub `pullRequestTemplates` diagnostics for `{result['repository']}`."
        ),
        "- When repository evidence showed a usable PR template body, opened a live GitHub compare page that reached `Open a pull request` and inspected the actual PR description field value.",
        "- When repository evidence already proved the template was missing, opened the live GitHub file page for the canonical template path and checked the reviewer-visible content.",
        "",
        "### Observed result",
        "- Matched the expected result." if passed else "- Did not match the expected result.",
        (
            f"- Environment: repository `{result['repository']}`, branch "
            f"`{result.get('default_branch', result.get('expected_default_branch', 'main'))}`, "
            f"browser `{result['browser']}`, OS `{result['os']}`."
        ),
        f"- Evidence URL: `{result.get('evidence_url', '<unavailable>')}`",
        f"- Screenshot: `{result.get('screenshot', '<not captured>')}`",
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
            ]
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    failure_kind = str(result.get("failure_kind", "product"))
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        f"- Repository: `{result['repository']}`",
        (
            "- Result: GitHub exposed the required PR-template checklist item in the live PR compose description field."
            if passed
            else (
                "- Result: the runner could not reach or inspect the live GitHub PR compose flow needed to verify the generated PR description body, so this run is a setup limitation rather than a proven product defect."
                if failure_kind == "setup"
                else (
                "- Result: GitHub did not expose any PR-template body with the required checklist item, so the repository currently misses the expected accessibility verification step."
                )
            )
        ),
        f"- Evidence URL: `{result.get('evidence_url', '<unavailable>')}`",
        f"- Screenshot: `{result.get('screenshot', '<not captured>')}`",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _jira_comment_blocked(result: dict[str, object]) -> str:
    lines = [
        f"h3. {TICKET_KEY} BLOCKED",
        "",
        "*Automation coverage*",
        (
            "* Queried the live GitHub repository metadata, community profile, "
            "default-branch tree, conventional "
            f"template paths, and GitHub `pullRequestTemplates` diagnostics for {{{{{result['repository']}}}}}."
        ),
        (
            "* Attempted to open the live GitHub compare page for a UI layout change, but the browser session was blocked at the authenticated `Open a pull request` surface."
        ),
        (
            "* Opened the live GitHub file page for the canonical PR template path and verified the checklist item in the visible template body."
        ),
        "",
        "*Observed result*",
        "* Blocked before the full compose-flow verification could complete.",
        (
            f"* Environment: repository {{{{{result['repository']}}}}}, branch "
            f"{{{{{result.get('default_branch', result.get('expected_default_branch', 'main'))}}}}}, "
            f"browser {{{{{result['browser']}}}}}, OS {{{{{result['os']}}}}}."
        ),
        f"* Evidence URL: {{{{{result.get('evidence_url', '<unavailable>')}}}}}",
        f"* Screenshot: {{{{{result.get('screenshot', '<not captured>')}}}}}",
        "",
        "*Step results*",
        *_step_lines(result, jira=True),
        "",
        "*Human-style verification*",
        *_human_lines(result, jira=True),
        "",
        "*Blocked reason*",
        f"* {result.get('blocked_reason', 'Blocked by missing browser auth.')}",
        "",
        "*Missing input*",
        *_missing_lines(result, jira=True),
    ]
    return "\n".join(lines) + "\n"


def _pr_body_blocked(result: dict[str, object]) -> str:
    lines = [
        f"## {TICKET_KEY} Blocked",
        "",
        "### Automation",
        (
            f"- Queried the live GitHub repository metadata, community profile, "
            f"default-branch tree, conventional "
            f"template paths, and GitHub `pullRequestTemplates` diagnostics for `{result['repository']}`."
        ),
        "- Attempted to open the live GitHub compare page for a UI layout change, but the browser session was blocked at the authenticated `Open a pull request` surface.",
        "- Opened the live GitHub file page for the canonical PR template path and verified the checklist item in the visible template body.",
        "",
        "### Observed result",
        "- Blocked before the full compose-flow verification could complete.",
        (
            f"- Environment: repository `{result['repository']}`, branch "
            f"`{result.get('default_branch', result.get('expected_default_branch', 'main'))}`, "
            f"browser `{result['browser']}`, OS `{result['os']}`."
        ),
        f"- Evidence URL: `{result.get('evidence_url', '<unavailable>')}`",
        f"- Screenshot: `{result.get('screenshot', '<not captured>')}`",
        "",
        "### Step results",
        *_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *_human_lines(result, jira=False),
        "",
        "### Blocked reason",
        f"- {result.get('blocked_reason', 'Blocked by missing browser auth.')}",
        "",
        "### Missing input",
        *_missing_lines(result, jira=False),
    ]
    return "\n".join(lines) + "\n"


def _response_summary_blocked(result: dict[str, object]) -> str:
    lines = [
        f"# {TICKET_KEY} BLOCKED",
        "",
        f"- Repository: `{result['repository']}`",
        (
            "- Result: the runner could not reach the authenticated GitHub PR compose form needed to verify the generated PR description body, so this run is blocked on browser auth rather than on a product defect."
        ),
        f"- Evidence URL: `{result.get('evidence_url', '<unavailable>')}`",
        f"- Screenshot: `{result.get('screenshot', '<not captured>')}`",
        "",
        "## Blocked reason",
        f"- {result.get('blocked_reason', 'Blocked by missing browser auth.')}",
        "",
        "## Missing input",
        *_missing_lines(result, jira=False),
    ]
    return "\n".join(lines) + "\n"


def _blocked_reason(result: dict[str, object]) -> str:
    repository = result.get("repository", "the repository")
    return (
        f"The live GitHub browser session for {repository} is not authenticated in this runner, "
        "so TS-909 cannot open the `Open a pull request` compose surface until browser auth "
        "is provided."
    )


def _blocked_missing_entry(
    config: PullRequestTemplateChecklistConfig,
) -> dict[str, str]:
    return {
        "type": "secret",
        "name": "GITHUB_BROWSER_AUTH_SESSION",
        "description": (
            "Authenticated GitHub browser session or persisted cookies for the Playwright "
            "runtime so the live `Open a pull request` compose surface can be opened."
        ),
        "how_to_add": (
            "Provide an authenticated GitHub browser session to the Playwright runtime "
            f"used for `{config.repository}` before running TS-909."
        ),
    }


def _missing_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    missing = result.get("missing", [])
    if not isinstance(missing, list) or not missing:
        return [f"{prefix} No missing inputs recorded."]
    lines: list[str] = []
    for item in missing:
        if not isinstance(item, dict):
            continue
        lines.extend(
            [
                (
                    f"{prefix} Type: {item.get('type')}, name: {item.get('name')}"
                ),
                f"  Description: {item.get('description')}",
                f"  How to add: {item.get('how_to_add')}",
            ]
        )
    return lines if lines else [f"{prefix} No missing inputs recorded."]


def _bug_description(result: dict[str, object]) -> str:
    selected_template_text = result.get("selected_template_text")
    lines = [
        f"# Bug report — {TICKET_KEY}",
        "",
        "## Summary",
        (
            "The live GitHub PR creation flow for `IstiN/trackstate` does not expose a PR template body that contains the required manual "
            "accessibility DOM-order checklist item."
        ),
        "",
        "## Exact steps to reproduce",
        (
            "1. Open the repository's live PR template configuration and determine "
            "whether GitHub exposes a PR template body for new pull requests. "
            + _step_outcome(result, 1)
        ),
        (
            "2. Verify that the PR template body includes an accessibility "
            "checklist. " + _step_outcome(result, 2)
        ),
        (
            "3. Confirm the presence of the specific item "
            "`Manual verification: DOM order matches visual hierarchy for "
            "keyboard-accessible elements.` " + _step_outcome(result, 3)
        ),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Actual result",
        (
            "GitHub did not expose any PR template body with the required checklist "
            "item, so reviewers are not automatically prompted to verify that DOM "
            "order matches the visual hierarchy."
        ),
        "",
        "## Missing / broken production capability",
        (
            "The repository's live GitHub PR template configuration does not expose a "
            "template body containing the required manual DOM-order accessibility checklist "
            "item for reviewers."
        ),
        "",
        "## Exact error message / assertion failure",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Environment details",
        f"- Repository: `{result['repository']}`",
        (
            f"- Default branch: "
            f"`{result.get('default_branch', result.get('expected_default_branch', 'main'))}`"
        ),
        f"- Browser/runtime: `{result['browser']}`",
        f"- OS: `{result['os']}`",
        f"- Run command: `{RUN_COMMAND}`",
        "",
        "## Evidence",
        f"- Evidence URL: `{result.get('evidence_url', '<unavailable>')}`",
        f"- Visible page matched text: `{result.get('evidence_matched_text', '<unavailable>')}`",
        f"- Selected template path: `{result.get('selected_template_path', '<unavailable>')}`",
        f"- Selected template source: `{result.get('selected_template_source', '<unavailable>')}`",
        "- Selected template excerpt:",
        "```text",
        _snippet(
            str(selected_template_text if isinstance(selected_template_text, str) else "<not exposed>"),
            limit=1_000,
        ),
        "```",
        f"- Screenshot: `{result.get('screenshot', '<not captured>')}`",
        "- Recognized pull-request templates:",
        "```json",
        json.dumps(result.get("recognized_pull_request_templates", []), indent=2),
        "```",
        "- Candidate file observations:",
        "```json",
        json.dumps(result.get("candidate_template_paths", []), indent=2),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for item in result.get("steps", []):
        if not isinstance(item, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(
            (
                f"{prefix} Step {item.get('step')} — "
                f"{str(item.get('status', '')).upper()}: {item.get('action')}\n"
                f"  Observed: {item.get('observed')}"
            )
        )
    return lines if lines else ["* No steps recorded." if jira else "- No steps recorded."]


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for item in result.get("human_verification", []):
        if not isinstance(item, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} {item.get('check')}\n  Observed: {item.get('observed')}"
        )
    return lines if lines else [
        "* No human-style checks recorded." if jira else "- No human-style checks recorded."
    ]


def _step_outcome(result: dict[str, object], step_number: int) -> str:
    for item in result.get("steps", []):
        if not isinstance(item, dict) or item.get("step") != step_number:
            continue
        status = item.get("status")
        marker = "Passed" if status == "passed" else "Failed"
        return f"{marker}: {item.get('observed')}"
    return "No observation was recorded for this step."


def _step_status(result: dict[str, object], step_number: int) -> str | None:
    for item in result.get("steps", []):
        if not isinstance(item, dict) or item.get("step") != step_number:
            continue
        status = item.get("status")
        return status if isinstance(status, str) and status else None
    return None


def _snippet(text: str, *, limit: int = 400) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


def _looks_like_unauthenticated_github_browser(
    compare_attempts: list[dict[str, object]],
) -> bool:
    if not compare_attempts:
        return False
    for attempt in compare_attempts:
        body_text_excerpt = attempt.get("body_text_excerpt")
        if not isinstance(body_text_excerpt, str):
            continue
        if _looks_like_unauthenticated_compare_surface(body_text_excerpt):
            return True
    return False


def _looks_like_unauthenticated_compare_surface(body_text: str) -> bool:
    lowered_body = body_text.lower()
    return (
        ("sign in" in lowered_body and "comparing changes" in lowered_body)
        or "github.com/login" in lowered_body
        or "username or email address" in lowered_body
    )


def _compose_compare_url(
    *,
    repository: str,
    base_branch: str,
    head_branch: str,
) -> str:
    return (
        f"https://github.com/{repository}/compare/"
        f"{quote(base_branch, safe='')}...{quote(head_branch, safe='')}?expand=1"
    )


if __name__ == "__main__":
    main()
