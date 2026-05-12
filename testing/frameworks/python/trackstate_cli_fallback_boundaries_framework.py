from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

from testing.core.config.trackstate_cli_fallback_boundaries_config import (
    TrackStateCliFallbackBoundariesConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_fallback_boundaries_result import (
    TrackStateCliFallbackBoundariesValidationResult,
    TrackStateCliFallbackBoundaryObservation,
)


class PythonTrackStateCliFallbackBoundariesFramework:
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def observe_rejections(
        self,
        *,
        config: TrackStateCliFallbackBoundariesConfig,
    ) -> TrackStateCliFallbackBoundariesValidationResult:
        observations: list[TrackStateCliFallbackBoundaryObservation] = []
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")

        for scenario in config.scenarios:
            with tempfile.TemporaryDirectory(
                prefix=f"trackstate-ts-385-{scenario.name}-"
            ) as temp_dir:
                local_target_path = Path(temp_dir)
                executed_command = (
                    dart_bin,
                    "run",
                    "trackstate",
                    "jira_execute_request",
                    "--target",
                    "local",
                    "--path",
                    str(local_target_path),
                    "--method",
                    scenario.method,
                    "--request-path",
                    scenario.request_path,
                )
                observations.append(
                    TrackStateCliFallbackBoundaryObservation(
                        name=scenario.name,
                        ticket_command=scenario.ticket_command,
                        local_target_path=str(local_target_path),
                        process_cwd=str(self._repository_root),
                        executed_command=executed_command,
                        result=self._run(executed_command, cwd=self._repository_root),
                    )
                )

        return TrackStateCliFallbackBoundariesValidationResult(
            observations=tuple(observations)
        )

    def _run(self, command: tuple[str, ...], *, cwd: Path) -> CliCommandResult:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            command,
            cwd=cwd,
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

    @staticmethod
    def _parse_json(stdout: str) -> object | None:
        payload = stdout.strip()
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None
