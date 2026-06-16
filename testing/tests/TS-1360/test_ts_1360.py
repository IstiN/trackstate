from __future__ import annotations

import os
import platform
import tempfile
import unittest
from pathlib import Path

from testing.components.services.install_script_test_runtime import (
    MockGitHubReleaseServer,
    MockReleaseAssets,
    patch_install_sh,
    run_install_sh,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install" / "install.sh"


class PosixInstallScriptIntegrityTest(unittest.TestCase):
    def setUp(self) -> None:
        if platform.system() != "Linux":
            self.skipTest("POSIX install script functional test requires a Linux environment")

    def test_posix_install_script_fails_on_checksum_mismatch(self) -> None:
        good_assets = MockReleaseAssets.build(
            tag="v1.2.3",
            platform="linux-x64",
            binary_name="trackstate",
        )
        corrupt_assets = good_assets.with_corrupt_checksum()

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            home_dir = tmpdir / "home"
            home_dir.mkdir()

            with MockGitHubReleaseServer(corrupt_assets, repo="test/repo") as server:
                patched = tmpdir / "install.sh"
                patch_install_sh(INSTALL_SCRIPT, patched, server)

                env = {
                    "HOME": str(home_dir),
                    "SHELL": "/bin/bash",
                    "PATH": os.environ.get("PATH", ""),
                }
                result = run_install_sh(patched, version="v1.2.3", timeout=60, env=env)
                combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

            self.assertNotEqual(
                result.returncode,
                0,
                "Expected the installer to exit with a non-zero status on checksum mismatch.",
            )
            self.assertIn(
                "checksum",
                combined_output.lower(),
                "Expected the error output to mention the checksum failure.",
            )
            self.assertIn(
                "mismatch",
                combined_output.lower(),
                "Expected the error output to mention a checksum mismatch.",
            )

            installed_binary = home_dir / ".trackstate" / "bin" / "trackstate"
            self.assertFalse(
                installed_binary.exists(),
                "The binary must not be installed when the checksum verification fails.",
            )


if __name__ == "__main__":
    unittest.main()
