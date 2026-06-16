# TS-1361 — Install Script Path Idempotency and Conflict Management

Functional test of `scripts/install/install.sh` PATH handling and conflict detection.

A local mock GitHub Release server provides a valid archive. The test verifies:

- Running the installer twice leaves exactly one `~/.trackstate/bin` PATH entry in the shell profile.
- When an existing `trackstate` binary is present on PATH (simulating `/usr/local/bin`),
  the installer warns the user and exits non-zero.
- Passing `--force` allows the managed version to be installed.
