from __future__ import annotations

from pathlib import Path
from typing import Protocol

from testing.core.models.cli_command_result import CliCommandResult


class FlutterAnalyzeProbe(Protocol):
    def flutter_version(self) -> CliCommandResult: ...

    def pub_get(self, project_root: Path) -> CliCommandResult: ...

    def analyze(self, project_root: Path, target: Path) -> CliCommandResult: ...

    def theme_token_check(self, project_root: Path, target: Path) -> CliCommandResult: ...
