from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from testing.components.pages.github_pull_request_compose_page import (
    GitHubPullRequestComposePage,
)
from testing.components.pages.github_repository_blob_page import (
    GitHubRepositoryBlobPage,
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


def _load_ts_909_module():
    module_path = Path(__file__).with_name("test_ts_909.py")
    spec = importlib.util.spec_from_file_location("ts_909_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


class _FakeBlobSession:
    def __init__(
        self,
        *,
        body_text: str = "trackstate",
        matched_text: str = "trackstate",
    ) -> None:
        self._body_text = body_text
        self._matched_text = matched_text

    def goto(
        self,
        url: str,
        *,
        wait_until: str = "domcontentloaded",
        timeout_ms: int = 120_000,
    ) -> None:
        del url, wait_until, timeout_ms

    def wait_for_any_text(
        self,
        texts,
        *,
        timeout_ms: int = 90_000,
    ) -> WaitMatch:
        del texts, timeout_ms
        return WaitMatch(matched_text=self._matched_text, body_text=self._body_text)

    def body_text(self) -> str:
        return self._body_text

    def screenshot(self, path: str, *, full_page: bool = True) -> None:
        del path, full_page


class _ComposeProbe:
    def __init__(
        self,
        *,
        branches_result: CliCommandResult,
        pulls_result: CliCommandResult,
    ) -> None:
        self._branches_result = branches_result
        self._pulls_result = pulls_result

    def list_branches(self, repository: str) -> CliCommandResult:
        del repository
        return self._branches_result

    def pull_requests(self, repository: str, *, state: str) -> CliCommandResult:
        del repository, state
        return self._pulls_result


class _ComposePageStub:
    def __init__(self, outcome) -> None:
        self._outcome = outcome

    def open_compose_surface(self, **kwargs):
        del kwargs
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


class _ComposePageContextStub:
    def __init__(self, compose_page) -> None:
        self._compose_page = compose_page

    def __enter__(self):
        return self._compose_page

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        return None


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

    def test_compose_page_skips_description_lookup_until_compose_surface_is_reached(
        self,
    ) -> None:
        page = GitHubPullRequestComposePage(
            _FakeComposeSession(
                body_text="Comparing changes",
            )
        )

        observation = page.open_compose_surface(
            repository="octocat/example",
            base_branch="main",
            head_branch="feature-branch",
            expected_texts=("Comparing changes",),
        )

        self.assertEqual(observation.matched_text, "Comparing changes")
        self.assertIsNone(observation.description_selector)
        self.assertIsNone(observation.description_value)

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

    def test_blob_page_reads_visible_body_text(self) -> None:
        page = GitHubRepositoryBlobPage(
            _FakeBlobSession(
                body_text=(
                    "Accessibility checklist\n"
                    "Manual verification: DOM order matches visual hierarchy for "
                    "keyboard-accessible elements."
                ),
                matched_text="Accessibility checklist",
            )
        )

        observation = page.open_blob_page(
            repository="octocat/example",
            ref="main",
            path=".github/PULL_REQUEST_TEMPLATE.md",
            expected_texts=("Accessibility checklist",),
        )

        self.assertIn(".github/PULL_REQUEST_TEMPLATE.md", observation.url)
        self.assertEqual(observation.matched_text, "Accessibility checklist")


class Ts909ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_909_module()
        cls.config = PullRequestTemplateChecklistConfig(
            repository="octocat/example",
            expected_default_branch="main",
            required_checklist_item=(
                "Manual verification: DOM order matches visual hierarchy for "
                "keyboard-accessible elements."
            ),
            accessibility_section_markers=("Accessibility checklist",),
            candidate_template_paths=(".github/PULL_REQUEST_TEMPLATE.md",),
        )
        cls.verification = SimpleNamespace(
            default_branch="main",
            target_repository="octocat/example",
            recognized_templates=(),
            candidate_observations=(),
        )

    def _result(self) -> dict[str, object]:
        return {
            "steps": [],
            "human_verification": [],
            "failure_kind": "product",
            "recognized_pull_request_templates": [],
            "candidate_template_paths": [],
        }

    def test_pre_browser_branch_lookup_failure_is_setup_limited(self) -> None:
        result = self._result()
        probe = _ComposeProbe(
            branches_result=CliCommandResult(
                command=("gh", "api", "branches"),
                exit_code=1,
                stdout="",
                stderr="authentication failed",
            ),
            pulls_result=CliCommandResult(
                command=("gh", "pr", "list"),
                exit_code=0,
                stdout="[]",
                stderr="",
                json_payload=[],
            ),
        )

        self.module._evaluate_pull_request_compose_surface(  # type: ignore[attr-defined]
            result=result,
            probe=probe,
            verification=self.verification,
            config=self.config,
        )

        self.assertEqual(result["failure_kind"], "setup")
        self.assertEqual(result["steps"][0]["status"], "failed")

    def test_exhausted_branch_candidates_are_setup_limited(self) -> None:
        result = self._result()
        probe = _ComposeProbe(
            branches_result=CliCommandResult(
                command=("gh", "api", "branches"),
                exit_code=0,
                stdout='[{"name":"main"}]',
                stderr="",
                json_payload=[{"name": "main"}],
            ),
            pulls_result=CliCommandResult(
                command=("gh", "pr", "list"),
                exit_code=0,
                stdout="[]",
                stderr="",
                json_payload=[],
            ),
        )

        self.module._evaluate_pull_request_compose_surface(  # type: ignore[attr-defined]
            result=result,
            probe=probe,
            verification=self.verification,
            config=self.config,
        )

        self.assertEqual(result["failure_kind"], "setup")
        self.assertEqual(result["steps"][0]["status"], "failed")

    def test_login_page_markers_are_treated_as_setup_limited(self) -> None:
        result = self._result()
        probe = _ComposeProbe(
            branches_result=CliCommandResult(
                command=("gh", "api", "branches"),
                exit_code=0,
                stdout='[{"name":"main"},{"name":"feature-branch"}]',
                stderr="",
                json_payload=[{"name": "main"}, {"name": "feature-branch"}],
            ),
            pulls_result=CliCommandResult(
                command=("gh", "pr", "list"),
                exit_code=0,
                stdout="[]",
                stderr="",
                json_payload=[],
            ),
        )
        login_error = AssertionError(
            "Could not open the GitHub pull-request compose surface.\n"
            "URL: https://github.com/login\n"
            "Visible body text:\n"
            "Sign in\nUsername or email address"
        )

        with patch.object(
            self.module,
            "create_github_pull_request_compose_page",
            return_value=_ComposePageContextStub(_ComposePageStub(login_error)),
        ):
            self.module._evaluate_pull_request_compose_surface(  # type: ignore[attr-defined]
                result=result,
                probe=probe,
                verification=self.verification,
                config=self.config,
            )

        self.assertEqual(result["failure_kind"], "setup")
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn("authenticated GitHub browser session", result["steps"][0]["observed"])

    def test_template_body_checks_stop_when_step_one_failed(self) -> None:
        result = self._result()
        result["steps"] = [
            {
                "step": 1,
                "status": "failed",
                "action": "Create a new Pull Request for a UI layout change.",
                "observed": "Playwright runtime unavailable.",
            }
        ]
        result["failure_kind"] = "setup"

        self.module._evaluate_template_body(  # type: ignore[attr-defined]
            result=result,
            verification=self.verification,
            config=self.config,
        )

        self.assertEqual(len(result["steps"]), 1)

    def test_repository_template_check_marks_missing_template_as_product_failure(self) -> None:
        result = self._result()
        verification = SimpleNamespace(
            target_repository="octocat/example",
            default_branch="main",
            configured_pull_request_template_path=None,
            configured_pull_request_template_url=None,
            discovered_template_paths=(),
            selected_recognized_template=None,
            selected_candidate=None,
        )

        self.module._evaluate_repository_template(  # type: ignore[attr-defined]
            result=result,
            verification=verification,
            config=self.config,
        )

        self.assertEqual(result["failure_kind"], "product")
        self.assertEqual(result["steps"][0]["status"], "failed")
        self.assertIn(
            "does not expose any pull-request template body",
            result["steps"][0]["observed"],
        )

    def test_repository_template_check_passes_when_item_is_present(self) -> None:
        result = self._result()
        verification = SimpleNamespace(
            target_repository="octocat/example",
            default_branch="main",
            selected_recognized_template=SimpleNamespace(
                filename=".github/PULL_REQUEST_TEMPLATE.md",
                body=(
                    "## Accessibility checklist\n"
                    "- Manual verification: DOM order matches visual hierarchy for "
                    "keyboard-accessible elements."
                ),
            ),
            selected_candidate=None,
        )

        self.module._evaluate_repository_template(  # type: ignore[attr-defined]
            result=result,
            verification=verification,
            config=self.config,
        )

        self.assertEqual(
            [step["status"] for step in result["steps"]],
            ["passed", "passed", "passed"],
        )


if __name__ == "__main__":
    unittest.main()
