from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from testing.components.services.install_script_test_runtime import (
    MockReleaseAssets,
    path_entry_count,
    run_patched_install_ps1,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install" / "install.ps1"


class WindowsPowerShellInstallScriptForceOverrideTest(unittest.TestCase):
    def setUp(self) -> None:
        if not shutil.which("pwsh"):
            self.skipTest(
                "PowerShell (pwsh) is required for the Windows installer functional test."
            )

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

            local_app_data, install_dir, path_store, result = run_patched_install_ps1(
                INSTALL_SCRIPT,
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
