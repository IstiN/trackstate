from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

from testing.components.services.github_accessibility_log_validation_step_presence_probe import (
    GitHubAccessibilityLogValidationStepPresenceProbeService,
)
from testing.core.config.accessibility_log_validation_exit_code_config import (
    AccessibilityLogValidationExitCodeConfig,
)
from testing.core.models.accessibility_log_validation_exit_code_result import (
    AccessibilityLogValidationExitCodeObservation,
)
from testing.core.models.cli_command_result import CliCommandResult


class AccessibilityLogValidationExitCodeProbeService:
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = repository_root

    def validate(
        self,
        config: AccessibilityLogValidationExitCodeConfig,
    ) -> AccessibilityLogValidationExitCodeObservation:
        workflow_path = self._repository_root / config.workflow_relative_path
        workflow_source = workflow_path.read_text(encoding="utf-8")
        original_workflow_contains_step = (
            f"- name: {config.log_validation_step_name}" in workflow_source
        )

        control_run = self._run_command(
            config.requested_command,
            cwd=self._repository_root,
        )

        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts968-"))
        try:
            self._copy_runtime_files(config, temp_repository_root=temp_repository_root)
            temp_workflow_path = temp_repository_root / config.workflow_relative_path
            mutated_source = (
                GitHubAccessibilityLogValidationStepPresenceProbeService._remove_log_validation_step(
                    temp_workflow_path.read_text(encoding="utf-8")
                )
            )
            temp_workflow_path.write_text(mutated_source, encoding="utf-8")
            mutated_workflow_contains_step = (
                f"- name: {config.log_validation_step_name}" in mutated_source
            )

            mutated_run = self._run_command(
                config.requested_command,
                cwd=temp_repository_root,
            )
        finally:
            shutil.rmtree(temp_repository_root, ignore_errors=True)

        return AccessibilityLogValidationExitCodeObservation(
            requested_command=config.requested_command,
            workflow_relative_path=config.workflow_relative_path,
            node_test_relative_path=config.node_test_relative_path,
            validator_relative_path=config.validator_relative_path,
            log_validation_step_name=config.log_validation_step_name,
            original_workflow_contains_log_validation_step=(
                original_workflow_contains_step
            ),
            mutated_workflow_contains_log_validation_step=(
                mutated_workflow_contains_step
            ),
            control_run=control_run,
            mutated_run=mutated_run,
        )

    def _copy_runtime_files(
        self,
        config: AccessibilityLogValidationExitCodeConfig,
        *,
        temp_repository_root: Path,
    ) -> None:
        for relative_path in (
            config.node_test_relative_path,
            config.validator_relative_path,
            config.workflow_relative_path,
        ):
            source_path = self._repository_root / relative_path
            target_path = temp_repository_root / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)

    @staticmethod
    def _run_command(
        command: tuple[str, ...],
        *,
        cwd: Path,
    ) -> CliCommandResult:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return CliCommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
