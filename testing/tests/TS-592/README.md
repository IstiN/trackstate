# TS-592 test automation

Verifies that a local `trackstate attachment upload --target local` run fails
with a specific repository-identity validation outcome when the repository is
configured for `attachmentStorage.mode = github-releases` but its configured
Git remotes do not point to GitHub.

The automation:
1. creates a disposable local TrackState repository configured for
   `attachmentStorage.mode = github-releases`
2. seeds a non-GitHub `origin` remote
3. removes ambient GitHub credentials from the runtime environment
4. runs the exact ticket command against `TS-475` with a real `test.txt`
   payload
5. checks the caller-visible CLI failure output for explicit non-GitHub-remote
   repository-identity guidance
6. rejects generic `REPOSITORY_OPEN_FAILED` and provider-capability failure
   contracts for this scenario
7. verifies no local attachment metadata or file output is written after the
   failure

## Run this test

```bash
python testing/tests/TS-592/test_ts_592.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`

## Expected pass / fail behavior

- **Pass:** the CLI fails with explicit repository-identity guidance for the
  non-GitHub remote scenario, does not return `REPOSITORY_OPEN_FAILED`, does
  not surface the old provider-capability message, and does not write local
  attachment files.
- **Fail:** the command succeeds, still returns `REPOSITORY_OPEN_FAILED`,
  surfaces the old provider-capability failure, omits the non-GitHub-remote
  repository-identity guidance, or mutates the local repository.
