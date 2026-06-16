from __future__ import annotations

import platform
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install" / "install.ps1"


class WindowsPowerShellInstallScriptTest(unittest.TestCase):
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

    def test_install_ps1_parses_in_powershell(self) -> None:
        if platform.system() != "Windows":
            self.skipTest(
                "Functional validation of the Windows PowerShell installer requires a Windows host."
            )

        result = subprocess.run(
            ["pwsh", "-Command", f"Get-Command {INSTALL_SCRIPT}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"PowerShell was unable to load or parse install.ps1.\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
