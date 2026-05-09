# TS-107

Validates that Local Git mode does not surface fake fallback identity metadata
when the repository has no configured Git author.

The automation:
1. creates a temporary Local Git repository fixture
2. removes both local `user.name` and `user.email`
3. launches the real `TrackStateApp` in Local Git mode
4. verifies the top-bar session/profile area stays in a guest or login-only
   state instead of rendering fallback placeholders like `Local User` or
   `local-user`
5. opens the Local Git runtime dialog to confirm the runtime remains usable

## Install dependencies

```bash
flutter pub get
```

## Run this test

Run with an isolated git config so no global `user.name` / `user.email`
overrides the ticket precondition:

```bash
tmp_home="$(mktemp -d)"
HOME="$tmp_home" XDG_CONFIG_HOME="$tmp_home/.config" \
  flutter test testing/tests/TS-107/test_ts_107.dart --reporter expanded
rm -rf "$tmp_home"
```

If Flutter is not already on `PATH`, replace `flutter` with your local Flutter
binary.

## Expected result

```text
Pass: Local Git mode shows an unauthenticated/login-only profile surface (for
example guest initials) and does not render fallback identity placeholders or
error text when no Git author is configured.
```
