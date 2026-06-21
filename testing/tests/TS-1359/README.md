# TS-1359 — Windows PowerShell Install Script (install.ps1)

Functional test of `scripts/install/install.ps1`.

A local mock GitHub Release server provides a valid Windows archive. The patched
installer runs under PowerShell (pwsh) in an isolated temporary environment and
is redirected to the mock server. The test verifies:

- The script targets `%LOCALAPPDATA%\trackstate\bin` for the installed binary.
- The script updates the user-level (`User`) `Path` environment variable.
- The script extracts and copies `trackstate.exe`.
- The script does not request UAC elevation (`Start-Process`, `runAs`).
- Running the installer succeeds and places `trackstate.exe` in the mocked
  `%LOCALAPPDATA%\trackstate\bin`.
- The install directory is appended to the user PATH exactly once.
- Re-running the installer when the install directory is already on PATH does
  not create duplicate PATH entries.
- A pre-existing `trackstate.exe` elsewhere on PATH is detected and blocks the
  install (currently missing in production).
- Passing `-Force` allows the managed install to override a conflict (currently
  missing in production).
