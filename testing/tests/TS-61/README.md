# TS-61

## Install dependencies

```bash
/tmp/flutter/bin/flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-61/attachment_missing_gitattributes_test.dart -r expanded
```

## Required configuration

This test uses a ticket-specific fixture in `testing/fixtures/attachments/` to exercise the real GitHub provider upload logic with stubbed GitHub API responses. No external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```
