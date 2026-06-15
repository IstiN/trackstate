# TS-1354 test automation

Verifies that the Windows and macOS desktop builds exclude GitHub App OAuth as
an authentication method and only expose Personal Access Token authentication.

## What is tested

1. Desktop release build jobs (`build-linux`, `build-windows`, `build-macos`)
   do not pass GitHub App OAuth dart-defines.
2. The web build step still passes those defines, confirming the scope split.
3. The hosted repository access dialog conditionally renders the
   `Continue with GitHub App` button based on runtime availability.
4. The dialog contains a PAT/token input field and a token-connect submit button.
5. All relevant auth controls have non-empty visible labels in the localization file.

## Run this test

```bash
python -m unittest testing.tests.TS-1354.test_ts_1354
```
