## Summary
- Resolved the `origin/main` sync conflict in `lib/data/providers/local/local_git_trackstate_provider.dart` by merging the new GitHub identity resolver contract with the TS-539 local GitHub Releases delegation work.
- Preserved the TS-539 fix so local attachment uploads now forward optional GitHub credentials, delegate release-backed attachment writes through the repository's GitHub remote, and keep the original attachment name in metadata while storing the sanitized remote asset filename separately.
- Fixed the post-merge runtime regression by ensuring local release downloads can still use the shared hosted GitHub client for read-only release asset fetches, even when the local session has no token.
- Cleaned up `LocalTrackStateRepository` so the shared HTTP client is still threaded into hosted GitHub providers without tripping the analyzer.

## Root cause
The sync failure came from concurrent edits to `local_git_trackstate_provider.dart`: `origin/main` added the repository GitHub identity resolver path while TS-539 added local GitHub Releases delegation. The original conflict resolution also exposed a constructor cleanup issue in `LocalTrackStateRepository` and a merged runtime expectation that local release downloads must continue to use the shared GitHub client.

## Validation
- `flutter analyze`
- `flutter test`
- `python testing/tests/TS-534/test_ts_534.py`
