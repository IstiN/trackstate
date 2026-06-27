# TS-1363 — Windows Command Prompt Install Script

Tests that `install.cmd` delegates correctly to `install.ps1`, handles the `--force` flag,
and produces appropriate error output when the download fails.

## Test approach

Because `install.cmd` is a Windows batch script, the test runs it under `pwsh` (PowerShell Core)
using `cmd /c` when available, or validates the script structure statically when a Windows
runtime is not available.

The test patches the `__REPO_PLACEHOLDER__` in the script to point to a mock GitHub release
server so the download step can be exercised without live network access.
