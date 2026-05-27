from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from testing.core.interfaces.dart_probe_runtime import DartProbeRuntime
from testing.frameworks.python.dart_probe_runtime import PythonDartProbeRuntime


@dataclass(frozen=True)
class Ts1001DelayedAuthSessionProbeResult:
    succeeded: bool
    analyze_output: str
    run_output: str | None
    observation_payload: dict[str, object] | None


class Ts1001DelayedAuthSessionProbe:
    def __init__(
        self,
        repository_root: Path,
        runtime: DartProbeRuntime,
    ) -> None:
        self._probe_root = repository_root / "testing" / "tests" / "TS-1001" / "dart_probe"
        self._entrypoint = Path("bin/ts1001_delayed_auth_session_probe.dart")
        self._runtime = runtime

    def inspect(
        self,
        *,
        repository: str,
        branch: str,
        token: str,
        auth_delay_seconds: int,
        timeout_assertion_seconds: int,
    ) -> Ts1001DelayedAuthSessionProbeResult:
        execution = self._runtime.execute(
            probe_root=self._probe_root,
            entrypoint=self._entrypoint,
            extra_env={
                "TS1001_REPOSITORY": repository,
                "TS1001_BRANCH": branch,
                "TS1001_GITHUB_TOKEN": token,
                "TS1001_AUTH_DELAY_SECONDS": str(auth_delay_seconds),
                "TS1001_TIMEOUT_ASSERTION_SECONDS": str(timeout_assertion_seconds),
            },
        )
        return Ts1001DelayedAuthSessionProbeResult(
            succeeded=execution.succeeded,
            analyze_output=execution.analyze_output,
            run_output=execution.run_output,
            observation_payload=execution.session_payload,
        )


def create_ts1001_delayed_auth_session_probe(
    repository_root: Path,
) -> Ts1001DelayedAuthSessionProbe:
    return Ts1001DelayedAuthSessionProbe(
        repository_root=repository_root,
        runtime=PythonDartProbeRuntime(repository_root),
    )
