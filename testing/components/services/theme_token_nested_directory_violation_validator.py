from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from testing.core.config.theme_token_nested_directory_violation_config import (
    ThemeTokenNestedDirectoryViolationConfig,
)
from testing.core.interfaces.flutter_analyze_probe import FlutterAnalyzeProbe
from testing.core.models.theme_token_nested_directory_violation_result import (
    ThemeTokenNestedDirectoryViolationResult,
)


class ThemeTokenNestedDirectoryViolationValidator:
    def __init__(self, repository_root: Path, probe: FlutterAnalyzeProbe) -> None:
        self._repository_root = repository_root
        self._probe = probe

    def validate(
        self,
        *,
        config: ThemeTokenNestedDirectoryViolationConfig,
    ) -> ThemeTokenNestedDirectoryViolationResult:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts157-"))

        try:
            self._copy_repository(temp_repository_root)

            flutter_version = self._probe.flutter_version()
            pub_get = self._probe.pub_get(temp_repository_root)
            baseline_check = self._probe.theme_token_check(
                temp_repository_root,
                config.target_path,
            )

            probe_path = temp_repository_root / config.probe_relative_path
            probe_path.parent.mkdir(parents=True, exist_ok=True)
            probe_path.write_text(
                self._probe_source(config.violation_literal),
                encoding="utf-8",
            )

            nested_check = self._probe.theme_token_check(
                temp_repository_root,
                config.target_path,
            )

            return ThemeTokenNestedDirectoryViolationResult(
                flutter_version=flutter_version,
                pub_get=pub_get,
                baseline_check=baseline_check,
                nested_check=nested_check,
                temp_repository_root=temp_repository_root,
                probe_relative_path=config.probe_relative_path,
                target_path=config.target_path,
            )
        finally:
            if not config.keep_temp_project and temp_repository_root.exists():
                shutil.rmtree(temp_repository_root)

    def _copy_repository(self, destination: Path) -> None:
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

    @staticmethod
    def _probe_source(violation_literal: str) -> str:
        return f"""import 'package:flutter/material.dart';

class Ts157NestedViolation extends StatelessWidget {{
  const Ts157NestedViolation({{super.key}});

  @override
  Widget build(BuildContext context) {{
    final c = {violation_literal};
    return ColoredBox(
      color: c,
      child: const SizedBox(width: 32, height: 32),
    );
  }}
}}
"""
