from __future__ import annotations

import os
import platform
import tempfile
import unittest
from pathlib import Path

from testing.components.services.install_script_test_runtime import (
    MockGitHubReleaseServer,
    MockReleaseAssets,
    detect_profile,
    install_dir_on_path_env,
    patch_install_sh,
    path_entry_count,
    run_install_sh,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install" / "install.sh"


class PosixInstallScriptLatestAndLocalInstallTest(unittest.TestCase):
    def setUp(self) -> None:
        if platform.system() != "Linux":
            self.skipTest("POSIX install script functional test requires a Linux environment")

    def test_posix_install_script_resolves_latest_and_installs_locally(self) -> None:
        assets = MockReleaseAssets.build(
            tag="v1.2.3",
            platform="linux-x64",
            binary_name="trackstate",
        )

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            home_dir = tmpdir / "home"
            home_dir.mkdir()
            install_dir = home_dir / ".trackstate" / "bin"

            with MockGitHubReleaseServer(assets, repo="test/repo") as server:
                patched = tmpdir / "install.sh"
                patch_install_sh(INSTALL_SCRIPT, patched, server)

                env = {
                    "HOME": str(home_dir),
                    "SHELL": "/bin/bash",
                    "PATH": os.environ.get("PATH", ""),
                }
                result = run_install_sh(patched, timeout=60, env=env)
                combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

            self.assertEqual(
                result.returncode,
                0,
                f"Install script exited non-zero.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn(
                "v1.2.3",
                combined_output,
                "Expected the resolved release tag to appear in the install log.",
            )
            self.assertIn(
                str(install_dir),
                combined_output,
                "Expected the install directory to appear in the install log.",
            )
            self.assertNotIn(
                "sudo",
                combined_output.lower(),
                "The installer should not prompt for or invoke sudo.",
            )
            self.assertNotIn(
                "ERROR:",
                combined_output,
                "No error output should be produced for a valid install.",
            )

            installed_binary = install_dir / "trackstate"
            self.assertTrue(
                installed_binary.exists(),
                f"The installed binary was not created at {installed_binary}",
            )
            self.assertTrue(
                os.access(installed_binary, os.X_OK),
                "The installed binary is not executable.",
            )

            profile = detect_profile(home_dir, shell_name="bash")
            self.assertTrue(
                profile.exists(),
                "The shell profile was not updated with a PATH entry.",
            )
            self.assertEqual(
                path_entry_count(profile, install_dir),
                1,
                "The shell profile should contain exactly one PATH addition for the install directory.",
            )
            self.assertTrue(
                install_dir_on_path_env(
                    os.environ.get("PATH", ""),
                    install_dir,
                )
                or path_entry_count(profile, install_dir) >= 1,
                "The install directory must be added to the user PATH (profile or environment).",
            )


if __name__ == "__main__":
    unittest.main()
