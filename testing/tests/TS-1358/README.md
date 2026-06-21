# TS-1358 — POSIX Install Script (install.sh)

Functional test of `scripts/install/install.sh` on Linux.

A local mock GitHub Release server is used so the test does not depend on the live
`IstiN/trackstate` releases endpoint. The test executes the script directly with `bash`
rather than the `curl | sh` pipeline described in the Test Case step, so the mock server
endpoints can be injected and the execution can be observed locally. The test verifies:

- Latest release resolution via the mock API.
- Correct platform archive selection (`linux-x64`).
- SHA256 checksum verification before extraction.
- Local installation to `~/.trackstate/bin` with the executable bit preserved.
- A single PATH entry appended to the shell profile.
- No `sudo` prompt or invocation.
