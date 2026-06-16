# TS-1360 — Install Script Integrity

Functional test of `scripts/install/install.sh` checksum verification.

A local mock GitHub Release server returns a corrupted SHA256 checksum file for the requested
archive. The test verifies that the installer:

- Detects the checksum mismatch.
- Exits with a non-zero status.
- Prints a clear error message mentioning the checksum mismatch.
- Does not install a binary.
