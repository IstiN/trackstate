# TS-663

Validates that the TrackState CLI rejects a self-referencing issue link even
when the target key uses different casing from the source key.

The automation:
1. creates `TS-1` in a disposable Local Git-backed TrackState repository
2. runs `trackstate ticket link --key TS-1 --target-key ts-1 --type "relates to"`
   through a repository-local compiled CLI binary
3. captures the terminal-visible JSON response for the mixed-case self-link
   attempt
4. verifies the command fails with validation exit code `2`
5. verifies no `TS/TS-1/links.json` metadata is persisted after the rejection

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-663 -p 'test_*.py' -v
```

## Required configuration

This test creates its own temporary local Git repository fixture and compiles a
temporary CLI binary from the current checkout, so no external service
credentials are required.

## Expected result

The CLI should treat `TS-1` and `ts-1` as the same issue for self-link
validation, reject the mutation with exit code `2`, surface the validation
error in the visible JSON response, and leave the issue without any persisted
link metadata.
