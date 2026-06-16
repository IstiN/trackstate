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

            self.assertEqual(
                result.returncode,
                0,
                f"Expected install.sh to succeed with --install-dir flag.\n{output}",
            )
            self.assertTrue(
                (custom_install_dir / "trackstate").exists(),
                "The trackstate binary must be placed in the custom install directory.",
            )
            self.assertFalse(
                default_install_dir.exists(),
                "The default install directory ~/.trackstate/bin must not be created when --install-dir is used.",
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

            self.assertEqual(
                result.returncode,
                0,
                f"Expected install.ps1 to succeed with -InstallDir flag.\n{output}",
            )
            self.assertTrue(
                (custom_install_dir / "trackstate.exe").exists(),
                "The trackstate.exe binary must be placed in the custom install directory.",
            )
            self.assertFalse(
                default_install_dir.exists(),
                "The default install directory %LOCALAPPDATA%\\trackstate\\bin must not be created when -InstallDir is used.",
            )

    def test_install_scripts_document_install_dir_flag(self) -> None:
        sh_content = INSTALL_SH.read_text(encoding="utf-8")
        ps1_content = INSTALL_PS1.read_text(encoding="utf-8")
        cmd_content = INSTALL_CMD.read_text(encoding="utf-8")

        self.assertIn(
            "--install-dir",
            sh_content,
            "install.sh must document or support the --install-dir flag.",
        )
        self.assertIn(
            "-InstallDir",
            ps1_content,
            "install.ps1 must document or support the -InstallDir parameter.",
        )
        self.assertIn(
            "--install-dir",
            cmd_content.lower(),
            "install.cmd must document or support the --install-dir flag.",
        )


if __name__ == "__main__":
    unittest.main()
