# TS-736

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-736/test_ts_736.dart --reporter expanded
```

## Required environment

- Flutter SDK available on `PATH`
- `git` available on `PATH`
- No additional environment variables are required

## Expected passing output

The command exits with code `0` and reports the TS-736 widget test as passed,
producing:

- `outputs/test_automation_result.json` with `{"status":"passed","passed":1,"failed":0,"skipped":0,"summary":"1 passed, 0 failed"}`
- `outputs/jira_comment.md`
- `outputs/pr_body.md`
- `outputs/response.md`
- `outputs/review_replies.json`
