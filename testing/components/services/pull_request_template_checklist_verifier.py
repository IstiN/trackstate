from __future__ import annotations

from testing.core.config.pull_request_template_checklist_config import (
    PullRequestTemplateChecklistConfig,
)
from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.core.models.pull_request_template_checklist_result import (
    PullRequestTemplateCandidateObservation,
    PullRequestTemplateChecklistVerificationResult,
)


class PullRequestTemplateChecklistVerifier:
    def __init__(self, probe: ProjectCliProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: PullRequestTemplateChecklistConfig,
    ) -> PullRequestTemplateChecklistVerificationResult:
        repository_info = self._probe.repository_metadata(config.repository)
        default_branch = self._default_branch(
            repository_info=repository_info,
            expected_default_branch=config.expected_default_branch,
        )
        community_profile = self._probe.community_profile(config.repository)
        tree_fetch = self._probe.list_tree(config.repository, default_branch)
        candidate_observations = tuple(
            PullRequestTemplateCandidateObservation(
                path=path,
                contents_fetch=self._probe.get_contents(
                    config.repository,
                    default_branch,
                    path,
                ),
                raw_fetch=self._probe.get_raw_file(
                    config.repository,
                    default_branch,
                    path,
                ),
            )
            for path in config.candidate_template_paths
        )
        return PullRequestTemplateChecklistVerificationResult(
            target_repository=config.repository,
            required_checklist_item=config.required_checklist_item,
            repository_info=repository_info,
            community_profile=community_profile,
            tree_fetch=tree_fetch,
            candidate_observations=candidate_observations,
        )

    @staticmethod
    def _default_branch(
        *,
        repository_info,
        expected_default_branch: str | None,
    ) -> str:
        if isinstance(repository_info.json_payload, dict):
            default_branch = repository_info.json_payload.get("default_branch")
            if isinstance(default_branch, str) and default_branch:
                return default_branch
        if expected_default_branch:
            return expected_default_branch
        return "main"
