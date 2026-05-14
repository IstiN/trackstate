# TS-708 test automation

Validates that the live `IstiN/trackstate` Apple release publishes the MVP
unsigned Apple Silicon artifacts expected by the ticket: a zipped `.app`, a
standalone CLI archive, and a `.sha256` manifest.

The automation:
1. selects the latest stable published version-tag release in `IstiN/trackstate`
2. captures the user-visible release summary with `gh release view`
3. verifies the release exposes exactly one app archive, one CLI archive, and
   one checksum manifest, with no `.dmg` or `.pkg` assets
4. downloads the archive assets, extracts the embedded binaries, and runs
   `file` on each executable
5. verifies the checksum manifest contains the downloaded archive filenames and
   SHA256 hashes

## Run this test

```bash
mkdir -p outputs && python testing/tests/TS-708/test_ts_708.py
```

## Required environment / config

- Python 3.12+
- `gh` CLI available on `PATH`
- `file` utility available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` recommended for GitHub API access

## Expected pass / fail behavior

- **Pass:** the selected release contains exactly three assets (app archive, CLI
  archive, checksum manifest), the extracted binaries both report
  `Mach-O 64-bit executable arm64`, the checksum manifest matches the downloaded
  archive bytes, and no `.dmg` or `.pkg` assets are present.
- **Fail:** any required asset is missing, extra/forbidden installer assets are
  published, the archives do not contain the expected binaries, the `file`
  output reports the wrong architecture, or the checksum manifest does not match
  the downloaded assets.
