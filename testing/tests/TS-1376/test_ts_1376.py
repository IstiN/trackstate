from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from testing.components.services.install_script_test_runtime import (
    MockGitHubReleaseServer,
    MockReleaseAssets,
    patch_install_ps1,
    run_install_ps1,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install" / "install.ps1"


class WindowsPowerShellInstallScriptConflictDetectionTest(unittest.TestCase):
    def setUp(self) -> None:
        if not shutil.which("pwsh"):
            self.skipTest(
                "PowerShell (pwsh) is required for the Windows installer functional test."
            )

    def _run_patched_install(
        self,
        tmpdir: Path,
        assets: MockReleaseAssets,
        version: str | None = None,
        flags: list[str] | None = None,
        path_prefix: str | None = None,
    ) -> tuple[Path, Path, Path, "subprocess.CompletedProcess[str]"]:
        local_app_data = tmpdir / "localappdata"
        local_app_data.mkdir(exist_ok=True)
        install_dir = local_app_data / "trackstate" / "bin"
        path_store = tmpdir / "user_path.txt"
        temp_dir = tmpdir / "temp"
        temp_dir.mkdir(exist_ok=True)

        with MockGitHubReleaseServer(assets, repo="test/repo") as server:
            patched = tmpdir / "install.ps1"
            patch_install_ps1(INSTALL_SCRIPT, patched, server, local_app_data, path_store)

            base_path = os.environ.get("PATH", "")
            env_path = base_path if path_prefix is None else f"{path_prefix}{os.pathsep}{base_path}"
            env = {
                "LOCALAPPDATA": str(local_app_data),
                "TEMP": str(temp_dir),
                "PATH": env_path,
            }
            result = run_install_ps1(patched, version=version, flags=flags, timeout=60, env=env)

        return local_app_data, install_dir, path_store, result

    def test_install_ps1_detects_conflicting_binary_on_path(self) -> None:
        """Regression test for TS-1375: installer warns and fails when a conflicting
        trackstate.exe already exists on the user's PATH.
        """
        assets = MockReleaseAssets.build(
            tag="v1.2.3",
            platform="windows-x64",
            binary_name="trackstate.exe",
        )

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            conflict_dir = tmpdir / "preexisting-bin"
            conflict_dir.mkdir()
            (conflict_dir / "trackstate.exe").write_text("@echo off\necho conflict\n")

            local_app_data, install_dir, path_store, result = self._run_patched_install(
                tmpdir,
                assets,
                version="v1.2.3",
                path_prefix=str(conflict_dir),
            )
            output = (result.stdout or "") + "\n" + (result.stderr or "")

            self.assertNotEqual(
                result.returncode,
                0,
                "Expected the installer to fail when a conflicting trackstate.exe is already on PATH.\n"
                f"Observed output:\n{output}",
            )
            output_lower = output.lower()
            self.assertIn(
                "trackstate",
                output_lower,
                "The error message should warn the user about the existing trackstate binary.",
            )
            self.assertTrue(
                any(
                    marker in output_lower
                    for marker in ("conflict", "already", "exists", "existing")
                ),
                "The error message should indicate a conflict with an existing binary.",
            )
            self.assertIn(
                str(conflict_dir / "trackstate.exe").lower(),
                output_lower,
                "The error message should identify the conflicting binary path.",
            )
            self.assertFalse(
                (install_dir / "trackstate.exe").exists(),
                "The managed install directory must not be modified when a conflict is detected.",
            )
            self.assertFalse(
                path_store.exists(),
                "The user PATH store must not be modified when a conflict is detected.",
            )


if __name__ == "__main__":
    unittest.main()
