# TS-310

Validates the Repository API attachment metadata contract for one standard
attachment and one Git LFS-tracked attachment.

The automation:
1. seeds a real Local Git TrackState repository with a standard SVG attachment
   and an LFS pointer-backed PNG attachment
2. loads the issue through the production `TrackStateRepository`
3. verifies each attachment exposes the required business fields
4. confirms the standard file reports its Git blob SHA while the LFS-tracked
   file reports its LFS OID and declared file size

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-310/test_ts_310.dart --reporter expanded
```

## Expected result

```text
Pass: the Repository API returns attachment metadata entries with the required
business fields, the standard attachment uses its Git blob SHA for
revisionOrOid, and the LFS-tracked attachment uses its LFS OID with the
declared binary size.

Fail: attachment fields are missing, sizeBytes falls back to pointer-file bytes,
or revisionOrOid reports the wrong identifier for either attachment type.
```
