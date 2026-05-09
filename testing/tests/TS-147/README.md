# TS-147

Verifies that selecting the `Local Git` provider exposes empty, editable
`Repository Path` and `Write Branch` fields before any value is entered.

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-147/test_ts_147.dart -r expanded
```

## Expected result

```text
Pass: after selecting Local Git, Repository Path and Write Branch are visible,
empty, editable, and accept typed input.
```
