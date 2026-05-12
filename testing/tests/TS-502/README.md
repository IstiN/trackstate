# TS-502

Verifies that a `github-releases` attachment upload auto-repairs a missing
GitHub release when the release tag already exists.

The automation:
1. seeds a cached `TS-200` issue in `github-releases` mode with the canonical
   release tag prefix
2. runs the production `ProviderBackedTrackStateRepository` attachment upload
   flow through layered testing abstractions backed by a scripted GitHub HTTP
   framework
3. verifies the flow observes a `404` for the release-by-tag lookup, creates a
   replacement draft release for the same tag, uploads the attachment asset to
   that release, and persists `attachments.json`
4. confirms the refreshed issue attachment metadata and cached snapshot both
   expose the uploaded release-backed attachment immediately

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-502/test_ts_502.dart -r expanded
```

## Required environment / config

No external credentials are required. The test uses a mocked GitHub client and
the production repository upload flow inside the Flutter test harness.
