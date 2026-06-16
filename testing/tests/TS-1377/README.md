# TS-1377 — Windows PowerShell Install Script (install.ps1) — -Force parameter overrides PATH conflict

Focused regression test for bug TS-1375.

A local mock GitHub Release server provides a valid Windows archive. The patched
installer runs under PowerShell (pwsh) in an isolated temporary environment and
is redirected to the mock server. The test verifies:

- When a pre-existing `trackstate.exe` exists on PATH in a directory outside the
  managed install location, passing `-Force` allows the installer to continue.
- The installer exits with code 0.
- `trackstate.exe` is extracted to `%LOCALAPPDATA%\trackstate\bin`.
- The managed install directory is appended to the user PATH exactly once.
