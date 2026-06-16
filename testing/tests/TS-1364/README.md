# TS-1364 — Install Script Custom Path — directory override via INSTALL_DIR

Functional test of `scripts/install/install.sh` custom installation path handling.

A local mock GitHub Release server provides a valid archive. The test verifies:

- Overriding `INSTALL_DIR` via a patched script redirects the installation to the
  specified directory.
- The `trackstate` binary is placed inside the custom directory.
- The default `~/.trackstate/bin` directory is NOT created.
