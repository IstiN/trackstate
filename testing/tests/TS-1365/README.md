# TS-1365 — Install Script Resilience — handling of GitHub API rate limits during latest resolution

Functional test of `scripts/install/install.sh` error handling when the GitHub API
rate-limits the `latest` release resolution request.

A local mock GitHub Release server returns HTTP 403 for the `/releases/latest`
endpoint. The test verifies:

- The installer exits with a non-zero status code.
- The error output mentions the GitHub API or rate limit.
- The error output suggests providing a pinned version to bypass the rate-limited
  resolution step.
