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


class PosixInstallScriptCustomPathTest(unittest.TestCase):
    def setUp(self) -> None:
        if platform.system() != "Linux":
            self.skipTest("POSIX install script functional test requires a Linux environment")

    def test_posix_install_script_respects_custom_install_dir(self) -> None:
        """Verify that install.sh respects INSTALL_DIR override via environment
        variable for custom installation locations and does not create the
        default directory.
        """
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            home_dir = tmpdir / "home"
            home_dir.mkdir()
            custom_dir = home_dir / "custom" / "trackstate-bin"

            assets = MockReleaseAssets.build(
                tag="v1.2.3",
                platform="linux-x64",
                binary_name="trackstate",
            )
            with MockGitHubReleaseServer(assets, repo="test/repo") as server:
                patched = tmpdir / "install.sh"
                patch_install_sh(INSTALL_SCRIPT, patched, server)
                # Also patch INSTALL_DIR to use the custom directory
                patched_text = patched.read_text(encoding="utf-8")
                patched_text = patched_text.replace(
                    'INSTALL_DIR="${HOME}/.trackstate/bin"',
                    f'INSTALL_DIR="{custom_dir}"',
                )
                patched.write_text(patched_text, encoding="utf-8")

                base_env = {
                    "HOME": str(home_dir),
                    "SHELL": "/bin/bash",
                    "PATH": os.environ.get("PATH", ""),
                }

                result = run_install_sh(
                    patched,
                    timeout=60,
                    env=base_env,
                )
                output = (result.stdout or "") + "\n" + (result.stderr or "")
                self.assertEqual(
                    result.returncode,
                    0,
                    f"Install with custom INSTALL_DIR failed unexpectedly.\n{output}",
                )
                self.assertTrue(
                    custom_dir.exists(),
                    f"The custom install directory {custom_dir} was not created.",
                )
                self.assertTrue(
                    (custom_dir / "trackstate").exists(),
                    f"The trackstate binary was not placed in the custom directory {custom_dir}.",
                )
                default_dir = home_dir / ".trackstate" / "bin"
                self.assertFalse(
                    default_dir.exists(),
                    f"The default install directory {default_dir} should NOT be created when a custom INSTALL_DIR is used.",
                )


if __name__ == "__main__":
    unittest.main()
