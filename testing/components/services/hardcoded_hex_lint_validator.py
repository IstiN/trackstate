from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from testing.core.config.hardcoded_hex_lint_config import HardcodedHexLintConfig
from testing.core.interfaces.flutter_analyze_probe import FlutterAnalyzeProbe
from testing.core.models.hardcoded_hex_lint_validation_result import (
    HardcodedHexLintValidationResult,
)


class HardcodedHexLintValidator:
    def __init__(self, repository_root: Path, probe: FlutterAnalyzeProbe) -> None:
        self._repository_root = repository_root
        self._probe = probe

    def validate(
        self,
        *,
        config: HardcodedHexLintConfig,
    ) -> HardcodedHexLintValidationResult:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts115-"))

        try:
            self._copy_repository(temp_repository_root)

            flutter_version = self._probe.flutter_version()
            pub_get = self._probe.pub_get(temp_repository_root)

            probe_path = temp_repository_root / config.probe_relative_path
            probe_path.parent.mkdir(parents=True, exist_ok=True)

            probe_path.write_text(
                self._probe_source(config.tokenized_color_expression),
                encoding="utf-8",
            )
            tokenized_analyze = self._probe.analyze(
                temp_repository_root,
                config.probe_relative_path,
            )

            probe_path.write_text(
                self._probe_source(config.hardcoded_color_expression),
                encoding="utf-8",
            )
            hardcoded_analyze = self._probe.analyze(
                temp_repository_root,
                config.probe_relative_path,
            )

            return HardcodedHexLintValidationResult(
                flutter_version=flutter_version,
                pub_get=pub_get,
                tokenized_analyze=tokenized_analyze,
                hardcoded_analyze=hardcoded_analyze,
                temp_repository_root=temp_repository_root,
                probe_relative_path=config.probe_relative_path,
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
    def _probe_source(color_expression: str) -> str:
        return f"""import 'package:flutter/material.dart';

class Ts115LintProbe extends StatelessWidget {{
  const Ts115LintProbe({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return ColoredBox(
      color: {color_expression},
      child: const SizedBox(width: 32, height: 32),
    );
  }}
}}
"""
