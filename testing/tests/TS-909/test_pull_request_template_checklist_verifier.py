from __future__ import annotations

import json
import unittest

from testing.components.pages.github_pull_request_compose_page import (
    GitHubPullRequestComposePage,
)
from testing.components.services.pull_request_template_checklist_verifier import (
    PullRequestTemplateChecklistVerifier,
)
from testing.core.config.pull_request_template_checklist_config import (
    PullRequestTemplateChecklistConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.interfaces.web_app_session import WaitMatch, WebAppTimeoutError
from testing.tests.support.github_pull_request_compose_page_factory import (
    GitHubPullRequestComposePageContext,
    GitHubPullRequestComposeRuntimeUnavailableError,
)


class _FakeProbe:
    def repository_metadata(self, repository: str) -> CliCommandResult:
        del repository
        return CliCommandResult(
            command=("gh", "api", "repos/octocat/example"),
            exit_code=0,
            stdout=json.dumps({"default_branch": "main"}),
            stderr="",
            json_payload={"default_branch": "main"},
        )

    def community_profile(self, repository: str) -> CliCommandResult:
        del repository
        return CliCommandResult(
            command=("gh", "api", "repos/octocat/example/community/profile"),
            exit_code=0,
            stdout=json.dumps({"files": {"pull_request_template": None}}),
            stderr="",
            json_payload={"files": {"pull_request_template": None}},
        )

    def list_tree(self, repository: str, ref: str) -> CliCommandResult:
        del repository, ref
        payload = {
            "tree": [
                {"path": ".github/PULL_REQUEST_TEMPLATE/ui-layout.md"},
                {"path": "README.md"},
            ]
        }
        return CliCommandResult(
            command=("gh", "api", "repos/octocat/example/git/trees/main?recursive=1"),
            exit_code=0,
            stdout=json.dumps(payload),
            stderr="",
            json_payload=payload,
        )

    def pull_request_templates(self, repository: str) -> CliCommandResult:
        del repository
        payload = {
            "data": {
                "repository": {
                    "pullRequestTemplates": [
                        {
                            "filename": ".github/PULL_REQUEST_TEMPLATE/ui-layout.md",
                            "body": "## Accessibility checklist\n- Manual verification: DOM order matches visual hierarchy for keyboard-accessible elements.",
                        }
                    ]
                }
            }
        }
        return CliCommandResult(
            command=("gh", "api", "graphql"),
            exit_code=0,
            stdout=json.dumps(payload),
            stderr="",
            json_payload=payload,
        )

    def get_contents(self, repository: str, ref: str, path: str) -> CliCommandResult:
        del repository, ref
        if path != ".github/PULL_REQUEST_TEMPLATE/ui-layout.md":
            return CliCommandResult(command=("gh", "api"), exit_code=1, stdout="", stderr="404")
        payload = {
            "type": "file",
            "content": "",
            "encoding": "base64",
        }
        return CliCommandResult(
            command=("gh", "api", path),
            exit_code=0,
            stdout=json.dumps(payload),
            stderr="",
            json_payload=payload,
        )

    def get_raw_file(self, repository: str, ref: str, path: str) -> CliCommandResult:
        del repository, ref
        if path != ".github/PULL_REQUEST_TEMPLATE/ui-layout.md":
            return CliCommandResult(command=("GET", path), exit_code=1, stdout="", stderr="404")
        return CliCommandResult(
            command=("GET", path),
            exit_code=0,
            stdout="## Accessibility checklist\n- Manual verification: DOM order matches visual hierarchy for keyboard-accessible elements.",
            stderr="",
        )


class _FakeComposeSession:
    def __init__(
        self,
        *,
        evaluate_payload: object | None = None,
        read_values: dict[str, str] | None = None,
        body_text: str = "Open a pull request",
    ) -> None:
        self._evaluate_payload = evaluate_payload
        self._read_values = read_values or {}
        self._body_text = body_text

    def goto(self, url: str, *, wait_until: str = "domcontentloaded", timeout_ms: int = 120_000) -> None:
        del url, wait_until, timeout_ms

    def wait_for_any_text(
        self,
        texts,
        *,
        timeout_ms: int = 90_000,
    ) -> WaitMatch:
        del timeout_ms
        return WaitMatch(matched_text=str(texts[0]), body_text=self._body_text)

    def evaluate(self, expression: str, *, arg: object | None = None) -> object:
        del expression, arg
        if isinstance(self._evaluate_payload, Exception):
            raise self._evaluate_payload
        return self._evaluate_payload

    def read_value(
        self,
        selector: str,
        *,
        has_text: str | None = None,
        index: int = 0,
        timeout_ms: int = 30_000,
    ) -> str:
        del has_text, index, timeout_ms
        if selector not in self._read_values:
            raise WebAppTimeoutError(f'missing selector "{selector}"')
        return self._read_values[selector]

    def body_text(self) -> str:
        return self._body_text

    def screenshot(self, path: str, *, full_page: bool = True) -> None:
        del path, full_page


class PullRequestTemplateChecklistVerifierTest(unittest.TestCase):
    def setUp(self) -> None:
        self.verifier = PullRequestTemplateChecklistVerifier(_FakeProbe())
        self.config = PullRequestTemplateChecklistConfig(
            repository="octocat/example",
            expected_default_branch="main",
            required_checklist_item=(
                "Manual verification: DOM order matches visual hierarchy for "
                "keyboard-accessible elements."
            ),
            accessibility_section_markers=("Accessibility checklist",),
            candidate_template_paths=(".github/PULL_REQUEST_TEMPLATE.md",),
        )

    def test_validate_fetches_discovered_template_paths(self) -> None:
        result = self.verifier.validate(config=self.config)

        self.assertEqual(
            tuple(observation.path for observation in result.candidate_observations),
            (
                ".github/PULL_REQUEST_TEMPLATE.md",
                ".github/PULL_REQUEST_TEMPLATE/ui-layout.md",
            ),
        )
        self.assertEqual(
            result.selected_candidate.path,
            ".github/PULL_REQUEST_TEMPLATE/ui-layout.md",
        )

    def test_validate_exposes_github_recognized_templates(self) -> None:
        result = self.verifier.validate(config=self.config)

        self.assertEqual(len(result.recognized_templates), 1)
        self.assertEqual(
            result.selected_recognized_template.filename,
            ".github/PULL_REQUEST_TEMPLATE/ui-layout.md",
        )

    def test_compose_page_reads_description_value_from_dom_evaluation(self) -> None:
        expected_value = (
            "## Accessibility checklist\n"
            "- Manual verification: DOM order matches visual hierarchy for "
            "keyboard-accessible elements."
        )
        page = GitHubPullRequestComposePage(
            _FakeComposeSession(
                evaluate_payload={
                    "selector": 'textarea[name="pull_request[body]"]',
                    "value": expected_value,
                }
            )
        )

        observation = page.open_compose_surface(
            repository="octocat/example",
            base_branch="main",
            head_branch="feature-branch",
            expected_texts=("Open a pull request",),
        )

        self.assertEqual(
            observation.description_selector,
            'textarea[name="pull_request[body]"]',
        )
        self.assertEqual(observation.description_value, expected_value)

    def test_compose_page_falls_back_to_read_value_when_dom_evaluation_is_unavailable(
        self,
    ) -> None:
        expected_value = (
            "## Accessibility checklist\n"
            "- Manual verification: DOM order matches visual hierarchy for "
            "keyboard-accessible elements."
        )
        page = GitHubPullRequestComposePage(
            _FakeComposeSession(
                evaluate_payload=NotImplementedError(),
                read_values={'textarea[name*="body"]': expected_value},
            )
        )

        observation = page.open_compose_surface(
            repository="octocat/example",
            base_branch="main",
            head_branch="feature-branch",
            expected_texts=("Open a pull request",),
        )

        self.assertEqual(observation.description_selector, 'textarea[name*="body"]')
        self.assertEqual(observation.description_value, expected_value)

    def test_compose_page_factory_requires_playwright_runtime(self) -> None:
        def missing_runtime():
            raise GitHubPullRequestComposeRuntimeUnavailableError("playwright required")

        context = GitHubPullRequestComposePageContext(runtime_factory=missing_runtime)

        with self.assertRaisesRegex(
            GitHubPullRequestComposeRuntimeUnavailableError,
            "playwright required",
        ):
            with context:
                self.fail("context manager should not yield without a browser runtime")


if __name__ == "__main__":
    unittest.main()
