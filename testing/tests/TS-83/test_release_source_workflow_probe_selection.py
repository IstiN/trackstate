from __future__ import annotations

import json
import unittest

from testing.components.services.release_source_workflow_validator import (
    ReleaseSourceWorkflowValidator,
)
from testing.core.config.release_source_workflow_config import (
    ReleaseSourceWorkflowConfig,
)
from testing.core.interfaces.github_api_client import GitHubApiClientError


class _FakeGitHubApiClient:
    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses

    def request_text(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        field_args=None,
        stdin_json=None,
    ) -> str:
        del method, field_args, stdin_json
        response = self._responses[endpoint]
        if isinstance(response, Exception):
            raise response
        return json.dumps(response)


def _releases_endpoint() -> str:
    return "/repos/IstiN/trackstate-setup/releases?per_page=100"


def _tags_endpoint() -> str:
    return "/repos/IstiN/trackstate-setup/tags?per_page=100"


def _contents_endpoint(workflow_path: str, ref: str) -> str:
    return f"/repos/IstiN/trackstate-setup/contents/{workflow_path}?ref={ref}"


def _commit_endpoint(sha: str) -> str:
    return f"/repos/IstiN/trackstate-setup/commits/{sha}"


class ReleaseSourceWorkflowSelectionTest(unittest.TestCase):
    def test_selects_newer_tag_when_it_is_more_recent_than_latest_release(self) -> None:
        config = ReleaseSourceWorkflowConfig(
            repository="IstiN/trackstate-setup",
            default_branch="main",
            workflow_path=".github/workflows/install-update-trackstate.yml",
        )
        workflow_path = ".github/workflows/install-update-trackstate.yml"
        probe = ReleaseSourceWorkflowValidator(
            config,
            github_api_client=_FakeGitHubApiClient(
                {
                    _releases_endpoint(): [
                        {
                            "tag_name": "v1.0.0",
                            "html_url": "https://github.com/IstiN/trackstate-setup/releases/tag/v1.0.0",
                            "published_at": "2026-05-01T00:00:00Z",
                        }
                    ],
                    _tags_endpoint(): [
                        {
                            "name": "v1.1.0",
                            "commit": {"sha": "tag-sha"},
                        }
                    ],
                    _commit_endpoint("tag-sha"): {
                        "commit": {
                            "committer": {"date": "2026-05-02T00:00:00Z"},
                        }
                    },
                    _contents_endpoint(workflow_path, "main"): {"type": "file"},
                    _contents_endpoint(workflow_path, "v1.1.0"): {"type": "file"},
                }
            ),
        )

        observation = probe.validate()

        self.assertIsNotNone(observation.selected_ref)
        assert observation.selected_ref is not None
        self.assertEqual(observation.selected_ref.kind, "tag")
        self.assertEqual(observation.selected_ref.name, "v1.1.0")
        self.assertTrue(observation.selected_ref_has_workflow)

    def test_treats_missing_workflow_on_selected_reference_as_false(self) -> None:
        config = ReleaseSourceWorkflowConfig(
            repository="IstiN/trackstate-setup",
            default_branch="main",
            workflow_path=".github/workflows/install-update-trackstate.yml",
        )
        workflow_path = ".github/workflows/install-update-trackstate.yml"
        probe = ReleaseSourceWorkflowValidator(
            config,
            github_api_client=_FakeGitHubApiClient(
                {
                    _releases_endpoint(): [],
                    _tags_endpoint(): [
                        {
                            "name": "v1.1.0",
                            "commit": {"sha": "tag-sha"},
                        }
                    ],
                    _commit_endpoint("tag-sha"): {
                        "commit": {
                            "committer": {"date": "2026-05-02T00:00:00Z"},
                        }
                    },
                    _contents_endpoint(workflow_path, "main"): {"type": "file"},
                    _contents_endpoint(workflow_path, "v1.1.0"): GitHubApiClientError(
                        "gh api failed: Not Found (HTTP 404)", status_code=404
                    ),
                }
            ),
        )

        observation = probe.validate()

        self.assertIsNotNone(observation.selected_ref)
        self.assertFalse(observation.selected_ref_has_workflow)

    def test_skips_draft_and_prerelease_releases(self) -> None:
        config = ReleaseSourceWorkflowConfig(
            repository="IstiN/trackstate-setup",
            default_branch="main",
            workflow_path=".github/workflows/install-update-trackstate.yml",
        )
        workflow_path = ".github/workflows/install-update-trackstate.yml"
        probe = ReleaseSourceWorkflowValidator(
            config,
            github_api_client=_FakeGitHubApiClient(
                {
                    _releases_endpoint(): [
                        {
                            "tag_name": "v2.0.0-draft",
                            "html_url": "https://github.com/IstiN/trackstate-setup/releases/tag/v2.0.0-draft",
                            "published_at": "2026-05-03T00:00:00Z",
                            "draft": True,
                        },
                        {
                            "tag_name": "v2.0.0-rc1",
                            "html_url": "https://github.com/IstiN/trackstate-setup/releases/tag/v2.0.0-rc1",
                            "published_at": "2026-05-03T00:00:00Z",
                            "prerelease": True,
                        },
                        {
                            "tag_name": "v1.0.0",
                            "html_url": "https://github.com/IstiN/trackstate-setup/releases/tag/v1.0.0",
                            "published_at": "2026-05-01T00:00:00Z",
                        },
                    ],
                    _tags_endpoint(): [],
                    _contents_endpoint(workflow_path, "main"): {"type": "file"},
                    _contents_endpoint(workflow_path, "v1.0.0"): {"type": "file"},
                }
            ),
        )

        observation = probe.validate()

        self.assertIsNotNone(observation.selected_ref)
        assert observation.selected_ref is not None
        self.assertEqual(observation.selected_ref.kind, "release")
        self.assertEqual(observation.selected_ref.name, "v1.0.0")
        self.assertTrue(observation.selected_ref_has_workflow)

    def test_finds_stable_release_behind_drafts_with_larger_page(self) -> None:
        config = ReleaseSourceWorkflowConfig(
            repository="IstiN/trackstate-setup",
            default_branch="main",
            workflow_path=".github/workflows/install-update-trackstate.yml",
        )
        workflow_path = ".github/workflows/install-update-trackstate.yml"
        probe = ReleaseSourceWorkflowValidator(
            config,
            github_api_client=_FakeGitHubApiClient(
                {
                    _releases_endpoint(): [
                        {
                            "tag_name": "v2.0.0-draft",
                            "html_url": "https://github.com/IstiN/trackstate-setup/releases/tag/v2.0.0-draft",
                            "published_at": "2026-05-03T00:00:00Z",
                            "draft": True,
                        },
                        {
                            "tag_name": "v2.0.0-rc1",
                            "html_url": "https://github.com/IstiN/trackstate-setup/releases/tag/v2.0.0-rc1",
                            "published_at": "2026-05-03T00:00:00Z",
                            "prerelease": True,
                        },
                        {
                            "tag_name": "v1.0.0",
                            "html_url": "https://github.com/IstiN/trackstate-setup/releases/tag/v1.0.0",
                            "published_at": "2026-05-01T00:00:00Z",
                        },
                    ],
                    _tags_endpoint(): [],
                    _contents_endpoint(workflow_path, "main"): {"type": "file"},
                    _contents_endpoint(workflow_path, "v1.0.0"): {"type": "file"},
                }
            ),
        )

        observation = probe.validate()

        self.assertIsNotNone(observation.selected_ref)
        assert observation.selected_ref is not None
        self.assertEqual(observation.selected_ref.kind, "release")
        self.assertEqual(observation.selected_ref.name, "v1.0.0")
        self.assertTrue(observation.selected_ref_has_workflow)


if __name__ == "__main__":
    unittest.main()
