from __future__ import annotations

import os
from pathlib import Path

from testing.core.interfaces.dart_probe_runtime import DartProbeRuntime
from testing.core.interfaces.ts501_release_lifecycle_probe import (
    Ts501ReleaseLifecycleProbe,
    Ts501ReleaseLifecycleProbeRequest,
    Ts501ReleaseLifecycleProbeResult,
)

_ENVIRONMENT_KEYS = (
    "TS501_REPOSITORY",
    "TS501_REF",
    "TS501_TOKEN",
    "TS501_ISSUE_KEY",
    "TS501_ATTACHMENT_NAME",
    "TS501_ATTACHMENT_TEXT",
    "TS501_RELEASE_TAG_PREFIX",
)


class Ts501ReleaseLifecycleProbeService(Ts501ReleaseLifecycleProbe):
    def __init__(
        self,
        repository_root: Path,
        *,
        runtime: DartProbeRuntime,
        probe_root: Path | None = None,
        entrypoint: Path | None = None,
    ) -> None:
        resolved_probe_root = probe_root or Path("testing/tests/TS-501/dart_probe")
        self._probe_root = (
            resolved_probe_root
            if resolved_probe_root.is_absolute()
            else repository_root / resolved_probe_root
        )
        self._entrypoint = entrypoint or Path("bin/ts501_release_lifecycle_probe.dart")
        self._runtime = runtime

    def execute(
        self,
        *,
        request: Ts501ReleaseLifecycleProbeRequest,
    ) -> Ts501ReleaseLifecycleProbeResult:
        original_values = {key: os.environ.get(key) for key in _ENVIRONMENT_KEYS}
        os.environ["TS501_REPOSITORY"] = request.repository
        os.environ["TS501_REF"] = request.ref
        os.environ["TS501_TOKEN"] = request.token
        os.environ["TS501_ISSUE_KEY"] = request.issue_key
        os.environ["TS501_ATTACHMENT_NAME"] = request.attachment_name
        os.environ["TS501_ATTACHMENT_TEXT"] = request.attachment_text
        os.environ["TS501_RELEASE_TAG_PREFIX"] = request.release_tag_prefix
        try:
            execution = self._runtime.execute(
                probe_root=self._probe_root,
                entrypoint=self._entrypoint,
            )
        finally:
            for key, value in original_values.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        return Ts501ReleaseLifecycleProbeResult(
            succeeded=execution.succeeded,
            analyze_output=execution.analyze_output,
            run_output=execution.run_output,
            session_payload=execution.session_payload,
        )
