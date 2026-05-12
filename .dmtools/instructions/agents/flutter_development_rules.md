# TrackState Flutter Development Rules

These rules are TrackState-specific and are injected from `.dmtools/config.js`.
The shared `agents/` submodule must remain project-independent.

## Stack

| Area | Rule |
|------|------|
| App | Flutter / Dart |
| CLI | `bin/trackstate.dart`, executed as `dart run trackstate` |
| Tests | `flutter test`; automation lives under `testing/` |
| Project config | `.dmtools/config.js` |

## Development and rework rules

1. Read the current architecture before changing code: inspect `lib/`, `pubspec.yaml`, `lib/main.dart`, and existing state-management patterns.
2. Do not introduce new packages by hand-editing `pubspec.yaml`; use ecosystem tooling and only add packages required by the ticket.
3. Add stable semantic keys to user-facing or automation-targeted widgets, preferably `ValueKey` with kebab-case names.
4. Add semantic labels to `IconButton`, `GestureDetector`, and custom interactive widgets.
5. Use theme tokens (`Theme.of(context).colorScheme`, text theme, spacing conventions) instead of hardcoded colors/sizes.
6. Keep user-visible strings localized. Do not add raw strings directly in `Text()` widgets when localization is available.
7. For CLI changes, validate `--path` before operations and keep structured JSON responses stable.
8. Development/rework agents must not modify top-level `testing/` unless the ticket explicitly requires test-harness changes or the implementation contract changed. If touched, explain why in `outputs/response.md`.
9. Run `flutter analyze` and `flutter test` before finishing; fix failures caused by the change.
10. Preserve null safety. Avoid `dynamic`, unnecessary casts, and `!` unless the value is provably non-null.

## Bug-fix rules

- If the ticket returned to development, read prior Jira comments and previous PR diffs before changing code.
- For CLI bugs, test both the happy path and the exact error path from the ticket.
- Check recent changes to affected files before fixing to avoid repeating an incomplete prior approach.

## Output expectations

`outputs/response.md` must state:
- issues/notes and assumptions
- implementation approach
- files modified
- test coverage
- `flutter analyze` / `flutter test` outcome
