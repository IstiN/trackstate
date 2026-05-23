from __future__ import annotations

import io
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

from testing.core.config.semantic_label_context_lint_config import (
    SemanticLabelContextLintConfig,
)
from testing.core.interfaces.flutter_analyze_probe import FlutterAnalyzeProbe
from testing.core.models.semantic_label_context_lint_validation_result import (
    SemanticLabelContextLintValidationResult,
)


class SemanticLabelContextLintValidator:
    def __init__(self, repository_root: Path, probe: FlutterAnalyzeProbe) -> None:
        self._repository_root = repository_root
        self._probe = probe

    def validate(
        self,
        *,
        config: SemanticLabelContextLintConfig,
    ) -> SemanticLabelContextLintValidationResult:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts907-"))

        try:
            self._prepare_repository(
                destination=temp_repository_root,
                source_git_ref=config.source_git_ref,
            )

            flutter_version = self._probe.flutter_version()
            pub_get = self._probe.pub_get(temp_repository_root)

            target_path = temp_repository_root / config.target_relative_path
            localization_path = temp_repository_root / config.localization_relative_path
            baseline_source = target_path.read_text(encoding="utf-8")
            localization_source = localization_path.read_text(encoding="utf-8")
            baseline_analyze = self._probe.analyze(
                temp_repository_root,
                config.target_relative_path,
            )

            mutated_source = baseline_source.replace(
                config.required_source_snippet,
                config.replacement_source_snippet,
                1,
            )
            target_path.write_text(mutated_source, encoding="utf-8")
            mutated_analyze = self._probe.analyze(
                temp_repository_root,
                config.target_relative_path,
            )

            return SemanticLabelContextLintValidationResult(
                flutter_version=flutter_version,
                pub_get=pub_get,
                baseline_analyze=baseline_analyze,
                mutated_analyze=mutated_analyze,
                temp_repository_root=temp_repository_root,
                target_relative_path=config.target_relative_path,
                localization_relative_path=config.localization_relative_path,
                baseline_source=baseline_source,
                mutated_source=mutated_source,
                localization_source=localization_source,
            )
        finally:
            if not config.keep_temp_project and temp_repository_root.exists():
                shutil.rmtree(temp_repository_root)

    def _prepare_repository(self, *, destination: Path, source_git_ref: str) -> None:
        if source_git_ref:
            self._export_git_ref(source_git_ref, destination)
            return
        self._copy_worktree(destination)

    def _copy_worktree(self, destination: Path) -> None:
        shutil.copytree(
            self._repository_root,
            destination,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                ".git",
                ".dart_tool",
                "build",
                "outputs",
            ),
        )

    def _export_git_ref(self, source_git_ref: str, destination: Path) -> None:
        remote_name, remote_branch = _split_remote_ref(source_git_ref)
        if remote_name is not None and remote_branch is not None:
            fetch_result = subprocess.run(
                ["git", "fetch", "--no-tags", remote_name, remote_branch, "--quiet"],
                cwd=self._repository_root,
                text=True,
                capture_output=True,
                check=False,
            )
            if fetch_result.returncode != 0:
                raise RuntimeError(
                    "TS-907 could not refresh the configured source git ref.\n"
                    f"Ref: {source_git_ref}\n"
                    f"stdout:\n{fetch_result.stdout}\n"
                    f"stderr:\n{fetch_result.stderr}"
                )

        archive_result = subprocess.run(
            ["git", "archive", "--format=tar", source_git_ref],
            cwd=self._repository_root,
            capture_output=True,
            check=False,
        )
        if archive_result.returncode != 0:
            raise RuntimeError(
                "TS-907 could not export the configured source git ref.\n"
                f"Ref: {source_git_ref}\n"
                f"stdout:\n{archive_result.stdout.decode('utf-8', errors='replace')}\n"
                f"stderr:\n{archive_result.stderr.decode('utf-8', errors='replace')}"
            )

        with tarfile.open(fileobj=io.BytesIO(archive_result.stdout), mode="r:") as archive:
            archive.extractall(destination)


def _split_remote_ref(source_git_ref: str) -> tuple[str | None, str | None]:
    if "/" not in source_git_ref:
        return None, None
    remote_name, remote_branch = source_git_ref.split("/", 1)
    if not remote_name or not remote_branch:
        return None, None
    return remote_name, remote_branch
