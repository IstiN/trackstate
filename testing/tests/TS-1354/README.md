# TS-1354 test automation

Verifies that the Windows and macOS desktop builds exclude GitHub App OAuth as
an authentication method and only expose Personal Access Token authentication.

## What is tested

1. Desktop release build jobs (`build-linux`, `build-windows`, `build-macos`)
   do not pass GitHub App OAuth dart-defines.
2. The web build step still passes those defines, confirming the scope split.
3. A Flutter widget test launches the hosted repository access dialog under
   desktop build conditions (empty `TRACKSTATE_GITHUB_APP_CLIENT_ID` and
   `TRACKSTATE_GITHUB_AUTH_PROXY_URL` dart-defines) and verifies at runtime that
   the `Continue with GitHub App` control is not rendered.
4. The runtime dialog contains a PAT/token input field and a token-connect
   submit button with accessible labels.
5. All relevant auth controls have non-empty visible labels in the localization
   file.

## Run this test

```bash
python -m unittest testing.tests.TS-1354.test_ts_1354
```

The Python runner executes the static guards and then runs:

```bash
flutter test testing/tests/TS-1354/test_ts_1354_runtime.dart \
  --dart-define=TRACKSTATE_GITHUB_APP_CLIENT_ID= \
  --dart-define=TRACKSTATE_GITHUB_AUTH_PROXY_URL= \
  --reporter expanded
```
