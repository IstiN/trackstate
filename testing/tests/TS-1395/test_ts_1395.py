from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
README_PATH = REPO_ROOT / "README.md"
INSTALL_SH_PATH = REPO_ROOT / "scripts" / "install" / "install.sh"
INSTALL_PS1_PATH = REPO_ROOT / "scripts" / "install" / "install.ps1"
INSTALL_CMD_PATH = REPO_ROOT / "scripts" / "install" / "install.cmd"


class DocumentationSynchronizationTest(unittest.TestCase):
    def test_readme_contains_install_commands_for_all_platforms(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "curl -fsSL https://github.com/IstiN/trackstate/releases/latest/download/install.sh | bash",
            readme,
            "README should contain the Linux/macOS one-line install command.",
        )
        self.assertIn(
            "https://github.com/IstiN/trackstate/releases/download/v1.2.3/install.sh",
            readme,
            "README should contain a pinned-version install.sh example.",
        )
        self.assertIn(
            "irm https://github.com/IstiN/trackstate/releases/latest/download/install.ps1 -OutFile install.ps1",
            readme,
            "README should contain the PowerShell install command.",
        )
        self.assertIn(
            ".\\install.ps1",
            readme,
            "README should contain the PowerShell execution step.",
        )
        self.assertIn(
            "curl -fsSL https://github.com/IstiN/trackstate/releases/latest/download/install.cmd -o install.cmd",
            readme,
            "README should contain the Command Prompt install command.",
        )
        self.assertIn(
            "install.cmd",
            readme,
            "README should contain the Command Prompt execution step.",
        )

    def test_readme_contains_assistant_install_surface(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")

        for expected in [
            "Assistant install surface",
            "trackstate assistant github",
            "trackstate assistant claude",
            "trackstate-github.skill",
            "trackstate-claude.skill",
        ]:
            self.assertIn(
                expected,
                readme,
                f"README should mention the assistant install surface: '{expected}'.",
            )

    def test_readme_links_to_setup_repository(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "IstiN/trackstate-setup",
            readme,
            "README should reference the fork-and-run setup repository.",
        )
        self.assertIn(
            "Fork-and-run setup repository",
            readme,
            "README should have a setup repository section.",
        )

    def test_readme_install_snippets_match_script_comments(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        install_sh = INSTALL_SH_PATH.read_text(encoding="utf-8")
        install_ps1 = INSTALL_PS1_PATH.read_text(encoding="utf-8")
        install_cmd = INSTALL_CMD_PATH.read_text(encoding="utf-8")

        sh_comment_match = re.search(
            r"# Usage:.*?(curl -fsSL https://github.com/__REPO_PLACEHOLDER__/releases/latest/download/install\.sh \| bash)",
            install_sh,
            re.DOTALL,
        )
        self.assertTrue(
            sh_comment_match,
            "install.sh usage comment should document the curl | bash command.",
        )

        ps1_comment_match = re.search(
            r"irm https://github\.com/__REPO_PLACEHOLDER__/releases/latest/download/install\.ps1 -OutFile install\.ps1",
            install_ps1,
        )
        self.assertTrue(
            ps1_comment_match,
            "install.ps1 usage comment should document the irm download command.",
        )

        cmd_comment_match = re.search(
            r"curl -fsSL https://github\.com/IstiN/trackstate/releases/latest/download/install\.cmd -o install\.cmd",
            install_cmd,
        )
        self.assertTrue(
            cmd_comment_match,
            "install.cmd usage comment should document the curl download command.",
        )

        # README uses the real repo placeholder value; scripts use __REPO_PLACEHOLDER__.
        # The important part is that README mirrors the documented commands.
        self.assertIn(
            "trackstate --help",
            readme,
            "README should mention trackstate --help as a validation step.",
        )


if __name__ == "__main__":
    unittest.main()
