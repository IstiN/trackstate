from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

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
    PullRequestTemplateCandidateObservation,
    PullRequestTemplateChecklistVerificationResult,
)
from testing.tests.support.github_repository_file_page_factory import (  # noqa: E402
    create_github_repository_file_page,
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
    verifier = PullRequestTemplateChecklistVerifier(
        create_project_cli_probe(REPO_ROOT),
    )
    verification = verifier.validate(config=config)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "repository": config.repository,
        "expected_default_branch": config.expected_default_branch,
        "required_checklist_item": config.required_checklist_item,
        "run_command": RUN_COMMAND,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "linked_bugs": ["TS-905"],
        "ticket_steps": list(TICKET_STEPS),
        "expected_result": EXPECTED_RESULT,
        "steps": [],
        "human_verification": [],
    }

    try:
        _evaluate_repository_state(
            result=result,
            verification=verification,
            config=config,
        )
        _evaluate_human_visible_state(
            result=result,
            verification=verification,
            config=config,
        )

        failures = _failed_steps(result)
        if failures:
            failure_message = "\n".join(failures)
            raise AssertionError(failure_message)

        _write_pass_outputs(result)
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _evaluate_repository_state(
    *,
    result: dict[str, object],
    verification: PullRequestTemplateChecklistVerificationResult,
    config: PullRequestTemplateChecklistConfig,
) -> None:
    repository_info = verification.repository_info
    community_profile = verification.community_profile
    default_branch = verification.default_branch or config.expected_default_branch or "main"
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

    if not repository_info.succeeded:
        _record_step(
            result,
            step=1,
            status="failed",
            action=TICKET_STEPS[0],
            observed=(
                "The automation could not read the live repository metadata needed to "
                "verify the PR template source.\n"
                f"Command: {repository_info.command_text}\n"
                f"Exit code: {repository_info.exit_code}\n"
                f"stdout:\n{repository_info.stdout}\n"
                f"stderr:\n{repository_info.stderr}"
            ),
        )
        return

    repository_default_branch = verification.default_branch
    if config.expected_default_branch is not None and (
        repository_default_branch != config.expected_default_branch
    ):
        _record_step(
            result,
            step=1,
            status="failed",
            action=TICKET_STEPS[0],
            observed=(
                "GitHub reported an unexpected default branch, so the PR template "
                "source could be resolving from the wrong branch.\n"
                f"Expected default branch: {config.expected_default_branch}\n"
                f"Observed default branch: {repository_default_branch}"
            ),
        )
    else:
        if not community_profile.succeeded:
            _record_step(
                result,
                step=1,
                status="failed",
                action=TICKET_STEPS[0],
                observed=(
                    "The live repository metadata loaded, but GitHub community profile "
                    "data did not. The automation could not confirm whether GitHub "
                    "recognizes any PR template for new pull requests.\n"
                    f"Command: {community_profile.command_text}\n"
                    f"Exit code: {community_profile.exit_code}\n"
                    f"stdout:\n{community_profile.stdout}\n"
                    f"stderr:\n{community_profile.stderr}"
                ),
            )
        elif verification.configured_pull_request_template_url is None and not (
            verification.existing_candidates or verification.discovered_template_paths
        ):
            _record_step(
                result,
                step=1,
                status="failed",
                action=TICKET_STEPS[0],
                observed=(
                    "GitHub does not expose a PR template for this repository. The "
                    "community profile returned `pull_request_template: null`, and the "
                    "default-branch tree did not contain any conventional PR template "
                    "file paths.\n"
                    f"Repository: {verification.target_repository}\n"
                    f"Default branch: {default_branch}\n"
                    f"Checked candidate paths: {', '.join(config.candidate_template_paths)}\n"
                    f"Discovered template-like paths: {list(verification.discovered_template_paths)}"
                ),
            )
        else:
            template_path = (
                verification.configured_pull_request_template_path
                or (
                    verification.selected_candidate.path
                    if verification.selected_candidate is not None
                    else None
                )
            )
            _record_step(
                result,
                step=1,
                status="passed",
                action=TICKET_STEPS[0],
                observed=(
                    "GitHub exposed a PR template source for the repository.\n"
                    f"Repository: {verification.target_repository}\n"
                    f"Default branch: {default_branch}\n"
                    f"Configured template path: {template_path}\n"
                    f"Configured template URL: {verification.configured_pull_request_template_url}"
                ),
            )

    selected_candidate = verification.selected_candidate
    result["selected_template_path"] = (
        selected_candidate.path if selected_candidate is not None else None
    )
    result["selected_template_text"] = (
        selected_candidate.raw_text if selected_candidate is not None else None
    )

    accessibility_check_passed = False
    if selected_candidate is None or selected_candidate.raw_text is None:
        _record_step(
            result,
            step=2,
            status="failed",
            action=TICKET_STEPS[1],
            observed=(
                "No live PR template file could be read from the repository, so the "
                "automation could not find an accessibility checklist in the PR body "
                "template.\n"
                f"Configured template URL: {verification.configured_pull_request_template_url}\n"
                f"Candidate file observations: {json.dumps(result['candidate_template_paths'], indent=2)}"
            ),
        )
    else:
        matched_marker = _first_accessibility_marker(
            selected_candidate.raw_text,
            config.accessibility_section_markers,
        )
        if matched_marker is None:
            _record_step(
                result,
                step=2,
                status="failed",
                action=TICKET_STEPS[1],
                observed=(
                    "The live PR template file exists, but its visible text did not "
                    "include an accessibility checklist marker.\n"
                    f"Template path: {selected_candidate.path}\n"
                    f"Expected markers: {list(config.accessibility_section_markers)}\n"
                    f"Observed template text:\n{selected_candidate.raw_text}"
                ),
            )
        else:
            accessibility_check_passed = True
            result["matched_accessibility_marker"] = matched_marker
            _record_step(
                result,
                step=2,
                status="passed",
                action=TICKET_STEPS[1],
                observed=(
                    "The live PR template text includes an accessibility checklist "
                    "marker.\n"
                    f"Template path: {selected_candidate.path}\n"
                    f"Matched marker: {matched_marker}"
                ),
            )

    if selected_candidate is None or selected_candidate.raw_text is None:
        _record_step(
            result,
            step=3,
            status="failed",
            action=TICKET_STEPS[2],
            observed=(
                "The exact DOM-order checklist item could not be present because no "
                "live PR template file was available to inspect.\n"
                f"Required item: {config.required_checklist_item}"
            ),
        )
        return

    if config.required_checklist_item not in selected_candidate.raw_text:
        _record_step(
            result,
            step=3,
            status="failed",
            action=TICKET_STEPS[2],
            observed=(
                "The live PR template file did not contain the exact required checklist "
                "item.\n"
                f"Template path: {selected_candidate.path}\n"
                f"Required item: {config.required_checklist_item}\n"
                f"Observed template text:\n{selected_candidate.raw_text}"
            ),
        )
        return

    if not accessibility_check_passed:
        _record_step(
            result,
            step=3,
            status="failed",
            action=TICKET_STEPS[2],
            observed=(
                "The exact checklist item was found, but the broader accessibility "
                "checklist marker was still missing, so the PR body would not present "
                "the item inside an explicit accessibility checklist section."
            ),
        )
        return

    _record_step(
        result,
        step=3,
        status="passed",
        action=TICKET_STEPS[2],
        observed=(
            "The live PR template file contains the exact required checklist item.\n"
            f"Template path: {selected_candidate.path}\n"
            f"Required item: {config.required_checklist_item}"
        ),
    )


def _evaluate_human_visible_state(
    *,
    result: dict[str, object],
    verification: PullRequestTemplateChecklistVerificationResult,
    config: PullRequestTemplateChecklistConfig,
) -> None:
    default_branch = verification.default_branch or config.expected_default_branch or "main"
    selected_candidate = verification.selected_candidate
    template_path = (
        selected_candidate.path
        if selected_candidate is not None
        else config.candidate_template_paths[0]
    )
    screenshot_path = (
        SUCCESS_SCREENSHOT_PATH
        if selected_candidate is not None and selected_candidate.raw_text is not None
        else FAILURE_SCREENSHOT_PATH
    )

    expected_texts = [config.required_checklist_item]
    if selected_candidate is None or selected_candidate.raw_text is None:
        expected_texts.extend(["Page not found", "404", "Uh oh!"])
    else:
        expected_texts.extend(config.accessibility_section_markers)

    with create_github_repository_file_page() as file_page:
        observation = file_page.open_file(
            repository=verification.target_repository,
            branch=default_branch,
            file_path=template_path,
            expected_texts=tuple(expected_texts),
            screenshot_path=str(screenshot_path),
        )

    result["browser_observation"] = {
        "url": observation.url,
        "matched_text": observation.matched_text,
        "body_text": observation.body_text,
        "screenshot_path": observation.screenshot_path,
    }
    result["screenshot"] = observation.screenshot_path

    if config.required_checklist_item in observation.body_text:
        _record_human_verification(
            result,
            check=(
                "Opened the live GitHub PR template file page in Chromium and checked "
                "the visible checklist text a reviewer would read."
            ),
            observed=(
                f"Visible page URL: {observation.url}\n"
                f"Matched visible text: {observation.matched_text}\n"
                f"Screenshot: {observation.screenshot_path}"
            ),
        )
        return

    _record_human_verification(
        result,
        check=(
            "Opened the live GitHub PR template file page in Chromium and checked the "
            "visible page content a reviewer would read."
        ),
        observed=(
            f"Visible page URL: {observation.url}\n"
            f"Matched visible text: {observation.matched_text}\n"
            f"Screenshot: {observation.screenshot_path}\n"
            f"Visible body text excerpt: {_snippet(observation.body_text)}"
        ),
    )
    _record_step(
        result,
        step=4,
        status="failed",
        action=(
            "Open the live GitHub PR template file page and verify the checklist item "
            "is visibly present for a human reviewer."
        ),
        observed=(
            "The browser did not visibly show the required checklist item on the live "
            "GitHub page.\n"
            f"URL: {observation.url}\n"
            f"Matched text: {observation.matched_text}\n"
            f"Screenshot: {observation.screenshot_path}\n"
            f"Visible body text:\n{observation.body_text}"
        ),
    )


def _first_accessibility_marker(
    template_text: str,
    markers: tuple[str, ...],
) -> str | None:
    lowered = template_text.lower()
    for marker in markers:
        if marker.lower() in lowered:
            return marker
    return None


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
        failures.append(
            f"Step {item.get('step')} failed: {item.get('observed')}"
        )
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
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            "* Queried the live GitHub repository metadata, community profile, "
            "default-branch tree, and conventional pull-request-template paths for "
            f"{{{{{result['repository']}}}}}."
        ),
        (
            "* Verified whether the live PR template exposes an accessibility "
            "checklist and the exact item {{Manual verification: DOM order matches "
            "visual hierarchy for keyboard-accessible elements.}}"
        ),
        (
            "* Opened the live GitHub file page in Chromium to confirm what a human "
            "reviewer would visibly read."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: repository {{{{{result['repository']}}}}}, branch "
            f"{{{{{result.get('default_branch', result.get('expected_default_branch', 'main'))}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}."
        ),
        f"* Screenshot: {{{{{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}}}}}",
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
            f"default-branch tree, and conventional PR template paths for `{result['repository']}`."
        ),
        (
            "- Verified whether the live PR template exposes an accessibility "
            "checklist and the exact item `Manual verification: DOM order matches "
            "visual hierarchy for keyboard-accessible elements.`"
        ),
        "- Opened the live GitHub file page in Chromium to confirm the visible reviewer experience.",
        "",
        "### Observed result",
        (
            "- Matched the expected result."
            if passed
            else "- Did not match the expected result."
        ),
        (
            f"- Environment: repository `{result['repository']}`, branch "
            f"`{result.get('default_branch', result.get('expected_default_branch', 'main'))}`, "
            f"browser `Chromium (Playwright)`, OS `{result['os']}`."
        ),
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
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
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        f"- Repository: `{result['repository']}`",
        (
            f"- Result: expected PR-template checklist item was present."
            if passed
            else (
                "- Result: expected PR-template checklist item was not present in the "
                "live GitHub implementation."
            )
        ),
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
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


def _bug_description(result: dict[str, object]) -> str:
    browser_observation = result.get("browser_observation", {})
    if not isinstance(browser_observation, dict):
        browser_observation = {}
    lines = [
        f"# Bug report — {TICKET_KEY}",
        "",
        f"## Summary",
        (
            "The live `IstiN/trackstate` repository does not expose a PR template that "
            "contains the required manual accessibility checklist item for DOM order."
        ),
        "",
        "## Exact steps to reproduce",
        (
            "1. Create a new Pull Request for a UI layout change. "
            + _step_outcome(result, 1)
        ),
        (
            "2. Verify that the PR description template automatically includes an "
            "accessibility checklist. "
            + _step_outcome(result, 2)
        ),
        (
            "3. Confirm the presence of the specific item "
            "`Manual verification: DOM order matches visual hierarchy for "
            "keyboard-accessible elements.` "
            + _step_outcome(result, 3)
        ),
        "",
        "## Actual result",
        (
            "GitHub community profile returned `pull_request_template: null`, the "
            "default branch tree did not contain any conventional PR template file, "
            "and the browser opened the conventional PR template URL as a missing file "
            "page instead of a visible template containing the required checklist item."
        ),
        "",
        "## Expected result",
        EXPECTED_RESULT,
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
        "- Browser: `Chromium (Playwright)`",
        f"- OS: `{result['os']}`",
        f"- Run command: `{RUN_COMMAND}`",
        "",
        "## Screenshots / logs",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
        (
            f"- Browser URL: `{browser_observation.get('url', '<unavailable>')}`"
        ),
        (
            f"- Browser matched text: `{browser_observation.get('matched_text', '<unavailable>')}`"
        ),
        "- Candidate path observations:",
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


def _snippet(text: str, *, limit: int = 400) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


if __name__ == "__main__":
    main()
