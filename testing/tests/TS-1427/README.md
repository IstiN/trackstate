# TS-1427 — CI Validation Failure Diagnostic for Rate-Limit Exhaustion

Unit test of the diagnostic surfaced by `testing.frameworks.python.gh_cli_rate_limit.run_with_rate_limit_retry` when GitHub API rate-limit exhaustion persists through all retries.

The CI harness must not silently fail; it must return a clear error that:

- Identifies the failure as GitHub API rate-limit exhaustion.
- Preserves the HTTP status and any `Retry-After` guidance from GitHub.
- Allows a human reader to distinguish rate-limit exhaustion from other API errors.
