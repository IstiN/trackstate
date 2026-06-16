from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

from testing.core.config.unsupported_provider_cli_config import (
    UnsupportedProviderCliConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.unsupported_provider_cli_result import (
    UnsupportedProviderCliObservation,
)


class PythonUnsupportedProviderCliFramework:
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def unsupported_provider(
        self,
        *,
        config: UnsupportedProviderCliConfig,
    ) -> UnsupportedProviderCliObservation:
        preferred_binary = shutil.which(config.requested_command[0])
        if preferred_binary:
            executed_command = (preferred_binary, *config.requested_command[1:])
            return UnsupportedProviderCliObservation(
                requested_command=config.requested_command,
                executed_command=executed_command,
                fallback_reason=None,
                result=self._run(executed_command),
            )

        return UnsupportedProviderCliObservation(
            requested_command=config.requested_command,
            executed_command=config.fallback_command,
            fallback_reason=(
                f'"{config.requested_command[0]}" was not available on PATH, so the '
                "test used the package executable via `dart run trackstate`."
            ),
            result=self._run(config.fallback_command),
        )

    def _run(self, command: tuple[str, ...]) -> CliCommandResult:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            command,
            cwd=self._repository_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return CliCommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            json_payload=self._parse_json(completed.stdout),
        )

    def _parse_json(self, stdout: str) -> object | None:
        payload = stdout.strip()
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None
