# TS-555 test automation

Verifies that a local `trackstate attachment upload --issue TS-789 --file log.txt --target local`
run creates a missing draft GitHub Release when the expected remote tag already
exists but no release is attached to that tag.

The automation:
1. creates a disposable local TrackState repository configured for
   `github-releases` attachment storage with the `ts-` tag prefix
2. ensures the remote tag `ts-TS-789` exists before the upload while no GitHub
   Release exists for that tag
3. runs the exact ticket command with a real `log.txt` payload from the seeded
   local repository
4. verifies the caller-visible CLI success payload and the local
   `attachments.json` entry for the uploaded file
5. polls the live GitHub API until the release container becomes visible on the
   existing tag, then confirms the tag SHA stayed unchanged and the uploaded
   asset is attached to that draft release
6. cleans up the created release and any temporary tag created during setup

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
uses the repo-local Python modules together with the repository's TrackState CLI
implementation and the GitHub API.

## Run this test

```bash
python testing/tests/TS-555/test_ts_555.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with permission to manage releases in the live
  setup repository
- Network access to GitHub so the test can create, inspect, and clean up the
  draft release fixture

## Expected pass / fail behavior

- **Pass:** the command succeeds, `attachments.json` contains a
  `github-releases` entry for `TS/TS-789/attachments/log.txt`, and GitHub shows
  exactly one draft release on `ts-TS-789` with the `log.txt` asset while the
  tag SHA remains unchanged.
- **Fail:** the command fails, writes the wrong local attachment state, creates
  no release, creates multiple releases, uses the wrong tag, or mutates the
  pre-existing tag SHA.
