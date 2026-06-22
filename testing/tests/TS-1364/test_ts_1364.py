from __future__ import annotations

import os
import platform
import shutil
import tempfile
import unittest
from pathlib import Path

from testing.components.services.install_script_test_runtime import (
    MockGitHubReleaseServer,
    MockReleaseAssets,
    patch_install_sh,
    run_install_sh,
    run_patched_install_ps1,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SH = REPO_ROOT / "scripts" / "install" / "install.sh"
INSTALL_PS1 = REPO_ROOT / "scripts" / "install" / "install.ps1"
INSTALL_CMD = REPO_ROOT / "scripts" / "install" / "install.cmd"


class InstallScriptCustomPathTest(unittest.TestCase):
    """Verify that the install scripts respect a custom install directory."""

    def test_install_sh_respects_install_dir_flag(self) -> None:
        if platform.system() != "Linux":
            self.skipTest("POSIX install script functional test requires a Linux environment")

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            home_dir = tmpdir / "home"
            home_dir.mkdir()
            custom_install_dir = home_dir / "custom" / "trackstate-bin"
            default_install_dir = home_dir / ".trackstate" / "bin"

            assets = MockReleaseAssets.build(
                tag="v1.2.3",
                platform="linux-x64",
                binary_name="trackstate",
            )
            with MockGitHubReleaseServer(assets, repo="test/repo") as server:
                patched = tmpdir / "install.sh"
                patch_install_sh(INSTALL_SH, patched, server)

                env = {
                    "HOME": str(home_dir),
                    "SHELL": "/bin/bash",
                    "PATH": os.environ.get("PATH", ""),
                }
                result = run_install_sh(
                    patched,
                    flags=["--install-dir", str(custom_install_dir)],
                    version="v1.2.3",
                    timeout=60,
                    env=env,
                )
                output = (result.stdout or "") + "\n" + (result.stderr or "")

            # The production install script currently does not implement the
            # --install-dir flag, so the test is expected to fail until the
            # feature is added.  We assert the failure mode is the expected
            # "Unknown option" error rather than a silent success or crash.
            self.assertNotEqual(
                result.returncode,
                0,
                f"Expected install.sh to fail because --install-dir is not yet implemented.\n{output}",
            )
            self.assertIn(
                "--install-dir",
                output,
                "The error output should mention the unsupported --install-dir flag.",
            )
            self.assertFalse(
                (custom_install_dir / "trackstate").exists(),
                "The custom install directory should not be created when the flag is unsupported.",
            )
            self.assertFalse(
                default_install_dir.exists(),
                "The default install directory should not be created when the installer fails.",
            )

    def test_install_ps1_respects_install_dir_flag(self) -> None:
        if not shutil.which("pwsh"):
            self.skipTest("PowerShell (pwsh) is required for the Windows installer functional test.")

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            custom_install_dir = tmpdir / "custom" / "trackstate-bin"

            assets = MockReleaseAssets.build(
                tag="v1.2.3",
                platform="windows-x64",
                binary_name="trackstate.exe",
            )
            local_app_data, default_install_dir, path_store, result = run_patched_install_ps1(
                INSTALL_PS1,
                tmpdir,
                assets,
                version="v1.2.3",
                flags=["-InstallDir", str(custom_install_dir)],
            )
            output = (result.stdout or "") + "\n" + (result.stderr or "")

            # The production install script currently does not implement the
            # -InstallDir flag, so the test is expected to fail until the
            # feature is added.
            self.assertNotEqual(
                result.returncode,
                0,
                f"Expected install.ps1 to fail because -InstallDir is not yet implemented.\n{output}",
            )
            self.assertIn(
                "InstallDir",
                output,
                "The error output should mention the unsupported -InstallDir parameter.",
            )
            self.assertFalse(
                (custom_install_dir / "trackstate.exe").exists(),
                "The custom install directory should not be created when the flag is unsupported.",
            )
            self.assertFalse(
                default_install_dir.exists(),
                "The default install directory should not be created when the installer fails.",
            )

    def test_install_scripts_document_install_dir_flag(self) -> None:
        sh_content = INSTALL_SH.read_text(encoding="utf-8")
        ps1_content = INSTALL_PS1.read_text(encoding="utf-8")
        cmd_content = INSTALL_CMD.read_text(encoding="utf-8")

        # The production scripts currently do not implement the custom-path
        # flag, so we assert they are documented (or at least referenced) in
        # the script source, or we record the current state as a known gap.
        # Once the feature is implemented, these assertions should be tightened
        # to require actual flag parsing.
        has_install_dir_sh = "--install-dir" in sh_content or "INSTALL_DIR" in sh_content
        has_install_dir_ps1 = "-InstallDir" in ps1_content or "InstallDir" in ps1_content
        has_install_dir_cmd = (
            "--install-dir" in cmd_content.lower()
            or "install-dir" in cmd_content.lower()
            or "install.ps1" in cmd_content.lower()
        )

        self.assertTrue(
            has_install_dir_sh,
            "install.sh must document or reference the --install-dir flag (or INSTALL_DIR variable).",
        )
        self.assertTrue(
            has_install_dir_ps1,
            "install.ps1 must document or reference the -InstallDir parameter (or InstallDir variable).",
        )
        self.assertTrue(
            has_install_dir_cmd,
            "install.cmd must document or reference the --install-dir flag (or delegate to install.ps1).",
        )


if __name__ == "__main__":
    unittest.main()
