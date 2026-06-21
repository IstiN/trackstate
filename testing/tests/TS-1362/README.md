# TS-1362 — Compiled CLI Regression

Functional regression test for the compiled TrackState CLI binary.

The test compiles `bin/trackstate.dart` to a standalone executable and verifies that:

- The compilation succeeds with no `dart:ui` platform-availability errors.
- The compiled binary produces JSON output identical to the Dart VM entrypoint for the same command.
- Local-target authSource neutrality is preserved: the compiled binary reports `authSource: "none"` even when hosted tokens (`TRACKSTATE_TOKEN`, `GITHUB_TOKEN`, `GH_TOKEN`) are present in the environment.

## Command under test

The test case references `trackstate session --target local --path . --output json`.
This exercises the same parity surface as `trackstate get-ticket TRACK-1` (both read
repository state and emit JSON), but uses a self-contained local target that does not
require a pre-existing ticket.
