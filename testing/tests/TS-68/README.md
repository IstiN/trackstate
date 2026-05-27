# TS-68

## Install dependencies

```bash
/tmp/flutter/bin/flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test --reporter compact testing/tests/TS-68/issue_detail_accessibility_test.dart
```

## Required environment

- Flutter SDK 3.35.3 available at `/tmp/flutter/bin/flutter`
- No extra environment variables are required
- The test uses the built-in `DemoTrackStateRepository` issue snapshot for `TRACK-12`

## Expected passing output

The test passes when the expanded issue detail renders the rich issue metadata
for `TRACK-12`, exposes semantics labels for the status/component/comment
controls, keeps the semantics traversal logical from summary through comments,
and maintains WCAG AA contrast for the `In Progress` badge.
