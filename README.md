# TrackState.AI

Git-native, Jira-compatible project tracker built as a Flutter application. The current app ships a polished mockable MVP surface for the repository-backed tracker model: dashboard, kanban board, JQL search/list, issue detail, hierarchy tree, project settings, light/dark themes, responsive mobile layout, custom painted icons, localization, accessibility semantics, and golden coverage.

## Run locally

```bash
flutter pub get
flutter run -d chrome
```

## Validate

```bash
flutter analyze
flutter test
flutter build web --release --base-href /trackstate/
```

Golden baselines are stored in `test/goldens/` and are exercised by `flutter test`.

## CLI foundation

The repository now exposes a TrackState CLI entrypoint for target resolution, JQL search, attachment flows, and a narrow Jira compatibility fallback:

```bash
dart run trackstate --help
dart run trackstate session --target local
dart run trackstate session --target hosted --provider github --repository owner/name
dart run trackstate attachment upload --target local --issue TRACK-1 --file ./design.png
dart run trackstate attachment download --target hosted --provider github --repository owner/name --attachment-id TRACK/TRACK-1/attachments/design.png --out ./downloads/design.png
dart run trackstate jira_execute_request --target local --method GET --request-path /rest/api/2/search --query jql=project=TRACK
```

`session` defaults to JSON output and returns a versioned TrackState envelope with target/provider metadata plus command data. Hosted authentication uses this precedence:

1. `--token`
2. `TRACKSTATE_TOKEN`
3. `gh auth token`

`trackstate attachment upload` and `trackstate attachment download` are the primary public attachment commands. Jira migration aliases `jira_attach_file_to_ticket` and `jira_download_attachment` are also supported.

`jira_execute_request` returns raw Jira-compatible JSON on success for a documented allowlist of safe read paths (`/rest/api/2|3/search`, `/rest/api/2|3/issue/{key}`, and `/rest/api/2|3/issue/{key}/comment`). Unsupported or unsafe request shapes fail explicitly in the standard error envelope.

## GitHub artifacts

`.github/workflows/unit-tests.yml` runs Flutter required checks on pull requests. `.github/workflows/flutter-ci.yml` builds the GitHub Pages web app, uploads the `trackstate-web` artifact, and deploys Pages from `main`.

## Fork-and-run setup repository

End users should not fork this full source repository. They should fork `IstiN/trackstate-setup`, enable **Settings > Pages > Source: GitHub Actions**, then run **Actions > Install / Update TrackState** in their fork.

That setup workflow checks out a selected `IstiN/trackstate` ref (`main`, tag, or commit SHA), builds the Flutter web app with the fork repository as runtime context, and deploys it to the fork's GitHub Pages site. Runtime project data is read from the target repository through the GitHub API.

Maintainers should mark `IstiN/trackstate-setup` as a GitHub template repository in repository settings.

### Hosted `github-releases` attachment note

For hosted browser sessions, direct upload to GitHub Release assets is not a browser-safe path. `IstiN/trackstate-setup` now includes `process-attachment-inbox.yml` to handle this server-side:

1. Commit file to `<PROJECT>/.trackstate/upload-inbox/<ISSUE-KEY>/<file>`.
2. Push to `main`.
3. Workflow uploads the file to the issue release, updates `<issue-root>/attachments.json`, and removes the inbox file.

This preserves release-backed storage without relying on direct browser upload to `uploads.github.com`.
