# TS-659

Validates that the TrackState CLI rejects a self-referencing issue link instead
of creating relationship metadata that points an issue back to itself.

The automation:
1. creates `TS-1` in a disposable Local Git-backed TrackState repository
2. runs `trackstate ticket link --key TS-1 --target-key TS-1 --type "relates to"`
   through a repository-local compiled CLI binary
3. captures the terminal-visible JSON response for the attempted self-link
4. verifies the command fails with a validation error
5. verifies no `TS/TS-1/links.json` metadata is persisted after the rejection

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-659 -p 'test_*.py' -v
```

## Required configuration

This test creates its own temporary local Git repository fixture and compiles a
temporary CLI binary from the current checkout, so no external service
credentials are required.

## Expected result

The CLI should reject the self-link attempt, surface a validation error in the
visible JSON response, and leave the issue without any persisted link metadata.
