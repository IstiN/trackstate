# TS-382 test automation

Verifies the CLI attachment download command writes the attachment bytes to the
requested local file path and returns a JSON success envelope with attachment
metadata and the resolved saved-file path, without exposing binary payload data
in stdout.

The automation:
1. seeds a disposable local TrackState repository with issue `TS-1` and PNG
   attachment `TS/TS-1/attachments/ATT-123.png`
2. executes `trackstate attachment download --attachment-id
   TS/TS-1/attachments/ATT-123.png --out ./downloads/downloaded_file.png
   --target local`
3. verifies the output file exists and its bytes exactly match the seeded
   attachment
4. verifies the JSON response contains the required success envelope,
   attachment metadata, and resolved `savedFile` path without requiring exact
   key order or a frozen object shape
5. verifies stdout does not expose attachment payload fields or base64 content

## Install dependencies

No Python packages are required beyond the standard library.

## Run this test

```bash
PYTHONPATH=. python testing/tests/TS-382/test_ts_382.py
```

## Required environment and config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- git CLI available on `PATH`
- No additional environment variables are required for the seeded local flow

## Expected result

```text
Pass: the command writes `./downloads/downloaded_file.png`, the file bytes match
the seeded PNG attachment, the JSON response includes the required metadata and
resolved saved-file path, and stdout does not leak attachment payload content.

Fail: the file is not created, the saved bytes differ, the required response
metadata is missing, or stdout/JSON expose attachment content or base64 data.
```
