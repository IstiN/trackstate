# TS-381

Validates the local `trackstate attachment upload` success path for a disposable
repository and confirms the returned JSON envelope exposes the attachment
metadata required by the ticket.

The automation:
1. seeds a disposable local TrackState repository containing issue `TS-22`
2. writes a local `sample.pdf` fixture file
3. executes `trackstate attachment upload --issue TS-22 --file sample.pdf --name "Spec Document" --target local`
4. inspects the visible JSON output for `ok: true`, the issue key, and
   attachment metadata fields `id`, `name`, `mediaType`, `sizeBytes`,
   `createdAt`, and `revisionOrOid`
5. verifies the uploaded file is physically stored under the issue
   `attachments/` directory with matching bytes

## Install dependencies

No extra Python packages are required beyond the standard library. Ensure these
tools are available before running the test:

1. `python3`
2. `git`
3. Dart SDK on `PATH` or `TRACKSTATE_DART_BIN`

## Run this test

```bash
python3 testing/tests/TS-381/test_ts_381.py
```

## Expected result

```text
Pass: the command returns a success envelope with issue `TS-22`, preserves the
requested attachment name `Spec Document`, reports `mediaType` as
`application/pdf`, and stores the file under the issue attachments directory.

Fail: the command exits non-zero, omits the required JSON fields, returns
metadata that does not match the ticket contract, or does not store the
uploaded file under the issue attachments directory.
```
