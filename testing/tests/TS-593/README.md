# TS-593 test automation

Verifies that a local `github-releases` attachment upload fails with an explicit
GitHub API release-creation error when the active local branch used as
`target_commitish` has not been pushed to the remote repository.

The automation:
1. creates a disposable local TrackState repository configured with
   `attachmentStorage.mode = github-releases`
2. points the local Git `origin` at the live setup repository
3. checks out a new local branch `feature-unpushed` that does not exist on the
   remote
4. runs the exact ticket command
   `trackstate attachment upload --issue TS-101 --file report.pdf --target local`
5. verifies the caller-visible CLI failure surfaces the GitHub API
   `target_commitish` validation (`422` / `Validation Failed`) rather than a
   generic provider failure
6. verifies no local attachment file, manifest entry, remote release, or remote
   tag is created

## Run this test

```bash
python testing/tests/TS-593/test_ts_593.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected pass / fail behavior

- **Pass:** the command fails with visible `422` / `target_commitish`
  release-creation guidance, no local attachment file is written under
  `TS/TS-101/attachments/report.pdf`, and no remote release/tag is created for
  `ts593-unpushed-TS-101`.
- **Fail:** the command succeeds, returns only a generic provider failure, omits
  the GitHub API branch-resolution error, writes local attachment state, or
  creates remote release/tag artifacts.
