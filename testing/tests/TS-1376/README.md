# TS-1376 — Windows PowerShell Install Script (install.ps1) — detect conflicting trackstate.exe on PATH

Focused regression test for bug TS-1375.

A local mock GitHub Release server provides a valid Windows archive. The patched
installer runs under PowerShell (pwsh) in an isolated temporary environment and
is redirected to the mock server. The test verifies:

- When a pre-existing `trackstate.exe` exists on PATH in a directory outside the
  managed install location, the installer detects the conflict.
- The installer prints a clear warning that names the conflicting binary path.
- The installer exits with a non-zero exit code.
- The managed install directory (`%LOCALAPPDATA%\trackstate\bin`) is not created
  or modified.
- The user PATH store is not modified.
