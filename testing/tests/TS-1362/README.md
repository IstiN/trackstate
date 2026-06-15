# TS-1362 — Compiled CLI Regression

Functional regression test for the compiled TrackState CLI binary.

The test compiles `bin/trackstate.dart` to a standalone executable and verifies that:

- The compilation succeeds with no `dart:ui` platform-availability errors.
- The compiled binary produces JSON output identical to the Dart VM entrypoint for the same command.
- Environment-token authentication precedence is preserved (`TRACKSTATE_TOKEN` > `gh` config).
