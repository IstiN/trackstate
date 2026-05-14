# macOS release runner contract

TrackState Apple release jobs run from the source repository (`IstiN/trackstate`) and publish downloadable macOS artifacts from GitHub Releases. They do **not** replace the existing Ubuntu-based CI path and they do **not** move release ownership into `trackstate-setup`.

## Ownership and scope

- **Operational owner:** TrackState maintainer team
- **Registration scope:** organization runner restricted to TrackState repositories
- **Workflow label contract:** `[self-hosted, macOS, trackstate-release, ARM64]`
- **Release scope only:** macOS desktop and macOS CLI release jobs
- **Out of scope:** generic shared runners, iOS builds, signing, notarization, `.dmg`, and `.pkg` packaging

## Required toolchain

| Tool | Required version | Why |
| --- | --- | --- |
| Flutter | `3.35.3` | Matches repository CI and release builds |
| Dart | `3.9.2` | Bundled with Flutter `3.35.3`; required for CLI compilation |
| Xcode | `16.x` or newer | Required for current Flutter macOS desktop builds on Apple Silicon |
| Bash | `3.2` or newer | Required by release and readiness scripts |
| Archive tools | `zip`, `ditto`, `tar`, `shasum` on `PATH` | Required to publish the `.app` zip, CLI archive, and checksum manifest |

The workflow installs the pinned Flutter SDK with `subosito/flutter-action@v2`; the runner itself must still provide Xcode, shell tooling, and archive tooling on `PATH`.

## Release artifacts

Each semantic tag release publishes exactly these Apple artifacts:

1. Zipped macOS desktop `.app` bundle
2. Standalone compiled macOS CLI `tar.gz` archive
3. SHA256 checksum file covering both published assets

## Readiness and failure mode

The release workflow fails in two explicit places:

1. **Ubuntu preflight:** queries the repository runner inventory and fails immediately when no online runner matches `[self-hosted, macOS, trackstate-release, ARM64]`
2. **macOS readiness script:** runs `tool/check_macos_release_runner.sh` on the selected runner and fails if the host is not Apple Silicon macOS or if any required toolchain version is missing or out of contract

This keeps the existing Ubuntu CI path unchanged while making Apple release infrastructure failures obvious for tagged releases.

## Manual verification

Run this on the registered macOS runner host after provisioning or upgrades:

```bash
./tool/check_macos_release_runner.sh
```

The command must succeed before `v*` release tags are built from GitHub Actions.
