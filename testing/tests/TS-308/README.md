# TS-308

Validates that posting a new Local Git issue comment writes the next sequential
markdown side-car file with the expected frontmatter and unmodified Jira-markup
body text.

The automation:
1. creates a disposable Local Git repository where `PROJECT-1` already has
   `comments/0001.md`
2. launches the real `TrackStateApp` in Local Git mode
3. opens `PROJECT-1` from the production-visible search flow
4. enters Jira-markup text into the production comment composer and posts it
5. verifies the new comment is visible in the issue detail UI exactly as a user
   would experience it
6. inspects `PROJECT/PROJECT-1/comments/0002.md` and verifies the sequential
   filename, frontmatter, and verbatim body persistence

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-308/test_ts_308.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: posting a comment to PROJECT-1 shows the new Jira-markup text in the UI,
creates PROJECT/PROJECT-1/comments/0002.md, and saves matching author/created/
updated frontmatter with the body preserved exactly.

Fail: the comment composer is missing, posting surfaces an error, the new comment
is not visible in issue detail, the saved filename is not 0002.md, or the saved
frontmatter/body differs from what the user authored.
```
