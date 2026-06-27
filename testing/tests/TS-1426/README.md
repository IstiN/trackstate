# TS-1426 — GitHub API Rate-Limit Resilience in CI Harness

Unit test of `testing.frameworks.python.gh_cli_rate_limit.run_with_rate_limit_retry`.

The CI harness wraps `gh` API calls with a retry loop that detects GitHub rate-limit responses and backs off before retrying. This test verifies the retry mechanism:

- Retries on rate-limit errors and eventually succeeds when the API recovers.
- Gives up after the configured maximum number of retries.
- Does not retry non-rate-limit errors.
- Respects the `Retry-After` header when GitHub provides one.
