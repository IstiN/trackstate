# TS-1359 — Windows PowerShell Install Script (install.ps1)

Static validation of `scripts/install/install.ps1`.

The test verifies that the script:

- Targets `%LOCALAPPDATA%\trackstate\bin` for the installed binary.
- Updates the user-level (`User`) `Path` environment variable.
- Extracts and copies `trackstate.exe`.
- Does not request UAC elevation (`Start-Process`, `runAs`).

Functional execution requires a Windows host; the runtime portion is skipped on non-Windows platforms.
