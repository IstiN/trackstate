from __future__ import annotations

from testing.core.config.template_workflow_file_config import TemplateWorkflowFileConfig
from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.core.models.template_workflow_file_verification_result import (
    TemplateWorkflowFileVerificationResult,
)


class TemplateWorkflowFileVerifier:
    def __init__(self, probe: ProjectCliProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TemplateWorkflowFileConfig,
    ) -> TemplateWorkflowFileVerificationResult:
        repository_info = self._probe.repository_metadata(config.repository)
        default_branch = self._repository_default_branch(repository_info)
        directory_fetch = self._probe.get_contents(
            config.repository,
            default_branch,
            config.workflow_directory_path,
        )
        tree_fetch = self._probe.list_tree(config.repository, default_branch)
        workflow_contents_fetch = self._probe.get_contents(
            config.repository,
            default_branch,
            config.workflow_path,
        )
        return TemplateWorkflowFileVerificationResult(
            target_repository=config.repository,
            workflow_path=config.workflow_path,
            workflow_directory_path=config.workflow_directory_path,
            workflow_filename=config.workflow_filename,
            repository_info=repository_info,
            directory_fetch=directory_fetch,
            tree_fetch=tree_fetch,
            workflow_contents_fetch=workflow_contents_fetch,
        )

    def _repository_default_branch(self, repository_info: object) -> str:
        if hasattr(repository_info, "json_payload") and isinstance(
            repository_info.json_payload,
            dict,
        ):
            default_branch = repository_info.json_payload.get("default_branch")
            if isinstance(default_branch, str) and default_branch:
                return default_branch
        return "main"
