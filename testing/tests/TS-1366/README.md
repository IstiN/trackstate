# TS-1366 test automation

Verifies that the published Linux x64 CLI archive is atomic and contains only
the compiled `trackstate` executable with the executable bit preserved.

## What is tested

1. A release tag is selected from:
   - `TS1366_RELEASE_TAG` environment variable,
   - GitHub Actions CI metadata for a version-tag workflow run, or
   - the latest published GitHub release.
2. The release exposes a Linux x64 CLI archive matching
   `trackstate-cli-linux-x64-*.tar.gz`.
3. The archive contains exactly one member: a regular file named `trackstate`.
4. No directories, metadata files (for example AppleDouble `._*` files), or
   extra files are present.
5. After extraction, the binary has read and execute permissions (the
   executable bit is preserved).
6. As a real-user verification, the extracted binary is run with `--help`
   when the host OS can execute the Linux x64 ELF binary.

## Run this test

```bash
mkdir -p outputs && python testing/tests/TS-1366/test_ts_1366.py
```

## Required environment

- `gh` CLI available on `PATH` (public repository access is sufficient).
- `tar` utility available on `PATH`.
- Optional: `file` utility for human-style binary type verification.
- Optional: `TS1366_RELEASE_TAG` to target a specific release tag.

## Expected pass / fail / blocked behavior

- **Pass:** the selected release exposes a Linux x64 CLI archive that contains
  exactly one regular file named `trackstate`, with read/execute permissions
  preserved, and the binary runs after extraction.
- **Fail:** the archive contains extra files or directories, the member is not
  a regular file named `trackstate`, or the executable bit is missing.
- **Blocked:** no published release exposes a matching Linux x64 CLI archive.
