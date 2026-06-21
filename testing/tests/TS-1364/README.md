# TS-1364 — Install Script Custom Path

Functional test of `scripts/install/install.sh`, `scripts/install/install.ps1`, and `scripts/install/install.cmd` custom install directory support.

A local mock GitHub Release server provides a valid archive. The test verifies:

- Passing `--install-dir ~/custom/trackstate-bin` to `install.sh` installs the binary to the custom directory and does not create `~/.trackstate/bin`.
- Passing `-InstallDir <custom-path>` to `install.ps1` installs `trackstate.exe` to the custom directory and does not create `%LOCALAPPDATA%\trackstate\bin`.
- All three install scripts document or support the custom-path flag.
