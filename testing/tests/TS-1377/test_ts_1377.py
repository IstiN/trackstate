from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from testing.components.services.install_script_test_runtime import (
    MockGitHubReleaseServer,
    MockReleaseAssets,
    path_entry_count,
    patch_install_ps1,
    run_install_ps1,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install" / "install.ps1"


class WindowsPowerShellInstallScriptForceOverrideTest(unittest.TestCase):
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

    def test_install_ps1_force_allows_override_of_conflict(self) -> None:
        """Regression test for TS-1375: the -Force switch bypasses the PATH
        conflict check and allows the managed install to proceed.
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
                flags=["-Force"],
                path_prefix=str(conflict_dir),
            )
            output = (result.stdout or "") + "\n" + (result.stderr or "")

            self.assertEqual(
                result.returncode,
                0,
                f"Expected -Force to allow installation to continue despite a PATH conflict.\n{output}",
            )
            self.assertTrue(
                (install_dir / "trackstate.exe").exists(),
                "The managed binary should be installed when -Force is used.",
            )
            self.assertEqual(
                path_entry_count(path_store, install_dir),
                1,
                "The installer should append the managed install directory to the user PATH exactly once.",
            )


if __name__ == "__main__":
    unittest.main()
