# TS-1370 test automation

Verifies that the unified SHA256 checksum file correctly validates the integrity
of all published desktop and CLI assets.

## What is tested

1. A release tag is selected from:
   - `TS1370_RELEASE_TAG` environment variable,
   - GitHub Actions CI metadata for a version-tag workflow run, or
   - the latest published GitHub release.
2. The release exposes all six expected platform archives:
   - Linux desktop and CLI
   - Windows desktop and CLI
   - macOS desktop and CLI
3. The release exposes a unified checksum file named
   `trackstate-${release_tag}.sha256`.
4. All archives and the checksum file are downloaded to the same directory.
5. `sha256sum -c` returns `OK` for every file listed in the checksum manifest.

## Run this test

```bash
mkdir -p outputs && python testing/tests/TS-1370/test_ts_1370.py
```

## Required environment

- `gh` CLI available on `PATH` (public repository access is sufficient).
- `sha256sum` utility available on `PATH`.
- Optional: `TS1370_RELEASE_TAG` to target a specific release tag.

## Expected pass / fail / blocked behavior

- **Pass:** all six archives and the checksum file are present, and
  `sha256sum -c` reports `OK` for every listed file.
- **Fail:** a downloaded archive fails the checksum verification, the manifest
  lists fewer files than expected, or filenames in the manifest do not match
  the published assets.
- **Blocked:** the selected release does not expose all required assets or the
  checksum file.
