# TS-71

## Install dependencies

```bash
/tmp/flutter/bin/flutter pub get
```

## Run this test

Browser-backed execution is required so the callback URL fragment is visible to
`Uri.base`. Run the scenario through a wrapper file under `test/` (or your
existing browser test harness) that calls
`testing/tests/TS-71/broker_login_flow_test.dart`, then execute that wrapper on
Chrome:

```bash
/tmp/flutter/bin/flutter test --platform chrome test/<temporary-wrapper>.dart -r expanded --dart-define=TRACKSTATE_GITHUB_AUTH_PROXY_URL=https://broker.example/login?provider=github-app
```

## Required configuration

This test exercises the hosted Flutter UI with a ticket-specific mocked GitHub
repository and a recorded broker launcher. It requires the
`TRACKSTATE_GITHUB_AUTH_PROXY_URL` dart define so the GitHub App broker button
is visible, and it must run in a browser-backed harness so the test can drive
the callback URL fragment that the app reads on return. It does not require any
live external credentials.

## Expected passing output

```text
00:00 +1: All tests passed!
```
