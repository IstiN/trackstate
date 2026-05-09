# TS-224

Validates that Local Git can still save a new issue while `DEMO/config/fields.json`
is malformed and the app has fallen back to the core system fields.

The automation:
1. creates a clean Local Git repository fixture whose `DEMO/config/fields.json`
   contains invalid JSON
2. launches the real `TrackStateApp` in Local Git mode against that fixture
3. waits for the malformed-config path to emit a visible parse-error message
4. opens the production-visible `Create issue` flow and fills the fallback
   `Summary` and `Description` fields
5. submits the form and verifies the save completes without a visible error
6. confirms a real user can find and open the created issue in `JQL Search`
7. inspects the Local Git repository to verify `DEMO/DEMO-2/main.md` and the
   corresponding create commit were written correctly

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-224/test_ts_224.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: malformed fields.json still logs the parse error, the fallback Create issue
form saves successfully with Summary and Description, the created issue is
visible to the user, and Local Git persists a dedicated DEMO-2 commit with a
clean worktree.

Fail: the app leaves fallback mode unusable, save surfaces an error, the created
issue is not visible through search/detail UI, or the Local Git repository does
not persist the expected issue artifact and commit.
```
