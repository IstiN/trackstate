# TS-1357 — Install Script Asset Availability

Static validation that the `release-on-main.yml` workflow attaches the three install scripts
(`install.sh`, `install.ps1`, `install.cmd`) as standalone GitHub Release assets.

The test verifies the `Prepare install script assets` step and the `gh release upload` invocation
include all three script files.
