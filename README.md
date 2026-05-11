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

The repository now exposes a TrackState CLI entrypoint for target resolution and session loading:

```bash
dart run trackstate --help
dart run trackstate session --target local
dart run trackstate session --target hosted --provider github --repository owner/name
```

`session` defaults to JSON output and returns a versioned TrackState envelope with target/provider metadata plus command data. Hosted authentication uses this precedence:

1. `--token`
2. `TRACKSTATE_TOKEN`
3. `gh auth token`

## GitHub artifacts

`.github/workflows/unit-tests.yml` runs Flutter required checks on pull requests. `.github/workflows/flutter-ci.yml` builds the GitHub Pages web app, uploads the `trackstate-web` artifact, and deploys Pages from `main`.

## Fork-and-run setup repository

End users should not fork this full source repository. They should fork `IstiN/trackstate-setup`, enable **Settings > Pages > Source: GitHub Actions**, then run **Actions > Install / Update TrackState** in their fork.

That setup workflow checks out a selected `IstiN/trackstate` ref (`main`, tag, or commit SHA), builds the Flutter web app with the fork repository as runtime context, and deploys it to the fork's GitHub Pages site. Runtime project data is read from the target repository through the GitHub API.

Maintainers should mark `IstiN/trackstate-setup` as a GitHub template repository in repository settings.
