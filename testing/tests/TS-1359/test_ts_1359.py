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


class WindowsPowerShellInstallScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        if not shutil.which("pwsh"):
            self.skipTest(
                "PowerShell (pwsh) is required for the Windows installer functional test."
            )

    def test_install_ps1_contains_user_local_path_setup(self) -> None:
        content = INSTALL_SCRIPT.read_text(encoding="utf-8")

        self.assertIn(
            "$env:LOCALAPPDATA",
            content,
            "The PowerShell installer must reference %LOCALAPPDATA%.",
        )
        self.assertIn(
            '"trackstate\\bin"',
            content,
            "The PowerShell installer must target the trackstate\\bin directory under LocalAppData.",
        )
        self.assertIn(
            '[Environment]::GetEnvironmentVariable("Path", "User")',
            content,
            "The PowerShell installer must read and update the user-level PATH variable.",
        )
        self.assertIn(
            "trackstate.exe",
            content,
            "The PowerShell installer must extract and copy trackstate.exe.",
        )
        self.assertNotIn(
            "Start-Process",
            content,
            "The PowerShell installer must not use Start-Process, which would suggest UAC elevation.",
        )
        self.assertNotIn(
            "runAs",
            content,
            "The PowerShell installer must not request administrator (runAs) privileges.",
        )

    def test_install_ps1_installs_binary_and_updates_path(self) -> None:
        assets = MockReleaseAssets.build(
            tag="v1.2.3",
            platform="windows-x64",
            binary_name="trackstate.exe",
        )

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            local_app_data, install_dir, path_store, result = run_patched_install_ps1(
                INSTALL_SCRIPT, tmpdir, assets, version="v1.2.3"
            )
            output = (result.stdout or "") + "\n" + (result.stderr or "")

            self.assertEqual(
                result.returncode,
                0,
                f"The installer should succeed on a clean system.\n{output}",
            )
            self.assertTrue(
                (install_dir / "trackstate.exe").exists(),
                "trackstate.exe must be installed under %LOCALAPPDATA%\\trackstate\\bin.",
            )
            self.assertEqual(
                path_entry_count(path_store, install_dir),
                1,
                "The installer should append the install directory to the user PATH exactly once.",
            )

    def test_install_ps1_path_idempotency(self) -> None:
        assets = MockReleaseAssets.build(
            tag="v1.2.3",
            platform="windows-x64",
            binary_name="trackstate.exe",
        )

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)

            first = run_patched_install_ps1(INSTALL_SCRIPT, tmpdir, assets, version="v1.2.3")
            first_output = (first[3].stdout or "") + "\n" + (first[3].stderr or "")
            self.assertEqual(
                first[3].returncode,
                0,
                f"First install failed unexpectedly.\n{first_output}",
            )
            self.assertEqual(
                path_entry_count(first[2], first[1]),
                1,
                "First install should add exactly one PATH entry.",
            )

            # Re-run the installer in an environment where the install dir is already on PATH.
            second = run_patched_install_ps1(
                INSTALL_SCRIPT,
                tmpdir,
                assets,
                version="v1.2.3",
                path_prefix=str(first[1]),
            )
            second_output = (second[3].stdout or "") + "\n" + (second[3].stderr or "")
            self.assertEqual(
                second[3].returncode,
                0,
                f"Second install failed unexpectedly.\n{second_output}",
            )
            self.assertEqual(
                path_entry_count(second[2], second[1]),
                1,
                "Re-running the installer must not create duplicate PATH entries.",
            )

    def test_install_ps1_detects_conflicting_binary_on_path(self) -> None:
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

    def test_install_ps1_force_allows_override_of_conflict(self) -> None:
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
                f"Expected -Force to allow installation to continue.\n{output}",
            )
            self.assertTrue(
                (install_dir / "trackstate.exe").exists(),
                "The managed binary should be installed when -Force is used.",
            )


if __name__ == "__main__":
    unittest.main()
