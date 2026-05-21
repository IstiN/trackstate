from __future__ import annotations

import json
import unittest

from testing.components.services.pull_request_template_checklist_verifier import (
    PullRequestTemplateChecklistVerifier,
)
from testing.core.config.pull_request_template_checklist_config import (
    PullRequestTemplateChecklistConfig,
)
from testing.core.models.cli_command_result import CliCommandResult


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


if __name__ == "__main__":
    unittest.main()
