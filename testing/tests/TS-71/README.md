# TS-71

## Install dependencies

```bash
/tmp/flutter/bin/flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-71/broker_login_flow_test.dart -r expanded --dart-define=TRACKSTATE_GITHUB_AUTH_PROXY_URL=https://broker.example/login?provider=github-app
```

## Required configuration

This test exercises the hosted Flutter UI with a ticket-specific mocked GitHub repository and a recorded broker launcher. It requires the `TRACKSTATE_GITHUB_AUTH_PROXY_URL` dart define so the GitHub App broker button is visible, but it does not require any live external credentials.

## Expected passing output

```text
00:00 +1: All tests passed!
```
