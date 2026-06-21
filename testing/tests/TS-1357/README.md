# TS-1357 — Install Script Asset Availability

Static validation that the `release-on-main.yml` workflow attaches the three install scripts
(`install.sh`, `install.ps1`, `install.cmd`) as standalone GitHub Release assets.

The test verifies:

* the source install scripts exist under `scripts/install/`;
* the `Prepare install script assets` step copies the scripts into `build/install/`;
* the `gh release upload` invocation includes the literal standalone filenames
  `install.sh`, `install.ps1`, and `install.cmd`.
