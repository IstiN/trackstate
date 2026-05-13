# TS-554 test automation

This test verifies the local `github-releases` attachment-upload flow when the
target tag and draft release do not already exist in the hosted repository. It
cleans any pre-existing `ts-att-TS-456` release slot, runs the exact ticket
command from a disposable local TrackState repository, then confirms both the
local manifest and the hosted draft release converge to the expected state.

## Run this test

```bash
python testing/tests/TS-554/test_ts_554.py
```

## Required configuration

1. `python`
2. `git`
3. `gh`
4. `GH_TOKEN` or `GITHUB_TOKEN` with permission to inspect, create, upload to,
   and delete draft releases and tags in the configured setup repository
5. Network access to `api.github.com`, `uploads.github.com`, and `github.com`

## Expected passing behavior

The test passes only when:

1. `trackstate attachment upload --issue TS-456 --file image.png --target local`
   succeeds from the disposable local repository
2. local `attachments.json` persists the release-backed metadata for `image.png`
3. `gh release view ts-att-TS-456` shows a draft release titled
   `Attachments for TS-456` containing the uploaded `image.png` asset
