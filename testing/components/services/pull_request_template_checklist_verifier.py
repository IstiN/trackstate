from __future__ import annotations

import re

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
        pull_request_templates_fetch = self._probe.pull_request_templates(
            config.repository
        )
        candidate_paths = self._candidate_paths(
            configured_paths=config.candidate_template_paths,
            tree_fetch=tree_fetch,
        )
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
            for path in candidate_paths
        )
        return PullRequestTemplateChecklistVerificationResult(
            target_repository=config.repository,
            required_checklist_item=config.required_checklist_item,
            repository_info=repository_info,
            community_profile=community_profile,
            tree_fetch=tree_fetch,
            pull_request_templates_fetch=pull_request_templates_fetch,
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

    @staticmethod
    def _candidate_paths(
        *,
        configured_paths: tuple[str, ...],
        tree_fetch,
    ) -> tuple[str, ...]:
        merged_paths = list(configured_paths)
        seen_paths = set(configured_paths)
        for path in PullRequestTemplateChecklistVerifier._discovered_template_paths(
            tree_fetch
        ):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            merged_paths.append(path)
        return tuple(merged_paths)

    @staticmethod
    def _discovered_template_paths(tree_fetch) -> tuple[str, ...]:
        payload = tree_fetch.json_payload
        if not isinstance(payload, dict):
            return ()
        tree = payload.get("tree")
        if not isinstance(tree, list):
            return ()
        pattern = re.compile(
            r"(?i)(^|/)(pull_request_template(\.md)?|pull_request_template/[^/]+\.md)$"
        )
        paths: list[str] = []
        for item in tree:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            if isinstance(path, str) and path and pattern.search(path):
                paths.append(path)
        return tuple(paths)
