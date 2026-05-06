## Issues/Notes

- `instruction.md` was not present at the repository root, so implementation followed the ticket inputs available under `input/TS-8/`.
- `trackstate-setup` was updated intentionally as part of the demo/template data surface.

## Approach

- Expanded the core issue/domain model to carry canonical ids and richer repository-backed metadata: fix versions, watchers, custom fields, links, attachments, archived state, and repository index relationships.
- Reworked the setup repository loader to read generated `.trackstate/index/*.json` artifacts, parse richer frontmatter/comment/link/attachment conventions, preserve tombstones for deleted issues, and load localized labels from config i18n files while keeping stored values machine-stable.
- Kept backward compatibility for older markdown that still stores Jira-style display labels by normalizing them during read.
- Switched status persistence to write canonical status ids back into issue frontmatter.

## Files Modified

- `lib/domain/models/trackstate_models.dart` — expanded project, issue, index, comment, attachment, link, and tombstone models plus config label helpers.
- `lib/data/repositories/trackstate_repository.dart` — added richer config/index loading, frontmatter parsing, comments/links/attachments support, deleted tombstone parsing, canonical id persistence, and updated demo snapshot data.
- `test/trackstate_repository_test.dart` — replaced repository tests with coverage for indexes, localized config labels, richer issue schema, legacy compatibility, and canonical status writes.
- `.gitignore` — ignored generated/local-only `input/` and `cacheBasicJiraClient/` directories so automation does not stage them.
- `trackstate-setup/DEMO/**/*.md` — converted demo issue frontmatter to canonical ids and added richer metadata fields.
- `trackstate-setup/DEMO/config/{fields.json,i18n/en.json,resolutions.json}` — expanded fixture config for custom fields, resolution metadata, and localized labels.
- `trackstate-setup/DEMO/DEMO-1/DEMO-2/{links.json,attachments/board-preview.svg}` — added reviewable non-hierarchy links and attachment fixture data.
- `trackstate-setup/DEMO/.trackstate/index/{issues.json,deleted.json}` — added generated key/path and tombstone index fixtures.
- `pubspec.lock` — refreshed after dependency resolution with the local Flutter SDK.

## Test Coverage

- Added repository tests for:
  - richer demo snapshot fields and repository index access,
  - setup-repository loading of comments, links, attachments, localized config labels, and deleted tombstones,
  - compatibility parsing for legacy display-label frontmatter,
  - canonical status id writes during issue updates.

## Verification

- `flutter analyze`
- `flutter test`
- `flutter build web`
