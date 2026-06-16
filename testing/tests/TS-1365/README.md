# TS-1365 — Install Script Resilience to GitHub API Rate Limits

Functional test of `scripts/install/install.sh` and `scripts/install/install.ps1` behavior when the GitHub API returns HTTP 403 during `latest` release resolution.

A local mock GitHub Release server is configured to return a `403 Rate Limit Exceeded` response for `/repos/$REPO/releases/latest`. The test verifies that the installer:

- Detects the API failure and exits with a non-zero status.
- Prints a clear error message identifying the GitHub API / rate-limit problem.
- Advises the user to provide a pinned version URL so the rate-limited resolution step can be bypassed.
- Does not install a binary.
