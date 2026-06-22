from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def find_dart_bin() -> str:
    """Return the Dart binary to use for CLI probes.

    Resolution order:
    1. {{TRACKSTATE_DART_BIN}} environment variable.
    2. First {{dart}} executable on PATH.
    3. Fallback string {{dart}}.
    """
    return os.environ.get("TRACKSTATE_DART_BIN") or shutil.which("dart") or "dart"


def run_trackstate_cli(
    args: list[str],
    *,
    cwd: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the TrackState CLI via {{dart run trackstate}} and return the result.

    The runner pins execution to the repository-local CLI so tests are not
    affected by an unrelated {{trackstate}} binary on PATH.
    """
    dart_bin = find_dart_bin()
    command = [dart_bin, "run", "trackstate", *args]
    env = os.environ.copy()
    env.setdefault("CI", "true")
    env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        command,
        cwd=cwd or REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
