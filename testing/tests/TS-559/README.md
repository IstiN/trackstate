# TS-559 test automation

This test verifies that uploading the first local attachment for `TS-999`
creates a new machine-managed draft GitHub Release container when no release
already exists for that issue.

## Run this test

```bash
python testing/tests/TS-559/test_ts_559.py
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

1. `trackstate attachment upload --issue TS-999 --file setup.log --target local`
   succeeds from the disposable local repository
2. local `attachments.json` persists the release-backed metadata for `setup.log`
3. `gh release view ts559-assets-TS-999` shows a draft release titled
   `Attachments for TS-999` containing the uploaded `setup.log` asset
