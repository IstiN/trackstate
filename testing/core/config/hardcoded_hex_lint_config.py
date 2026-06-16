from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HardcodedHexLintConfig:
    flutter_version: str
    probe_relative_path: Path
    tokenized_color_expression: str
    hardcoded_color_expression: str
    required_diagnostic_fragments: tuple[str, ...]
    keep_temp_project: bool

    @classmethod
    def from_env(cls) -> "HardcodedHexLintConfig":
        return cls(
            flutter_version=os.environ.get("TS115_FLUTTER_VERSION", "3.35.3"),
            probe_relative_path=Path(
                os.environ.get("TS115_PROBE_PATH", "lib/ts115_lint_probe.dart"),
            ),
            tokenized_color_expression=os.environ.get(
                "TS115_TOKENIZED_COLOR_EXPRESSION",
                "Theme.of(context).colorScheme.primary",
            ),
            hardcoded_color_expression=os.environ.get(
                "TS115_HARDCODED_COLOR_EXPRESSION",
                "Color(0xFFFAF8F4)",
            ),
            required_diagnostic_fragments=(
                "theme",
                "token",
                "hardcoded",
                "hex",
            ),
            keep_temp_project=os.environ.get("TS115_KEEP_TEMP_PROJECT") == "1",
        )
