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

## GitHub artifacts

`.github/workflows/flutter-ci.yml` runs on pull requests and pushes to `main`. It installs Flutter, analyzes, runs unit/widget/golden tests, builds the GitHub Pages web app, uploads the `trackstate-web` artifact, and deploys Pages from `main`.

## Fork-and-run setup repository

End users should not fork this full source repository. They should fork `IstiN/trackstate-setup`, enable **Settings > Pages > Source: GitHub Actions**, then run **Actions > Install / Update TrackState** in their fork.

That setup workflow checks out a selected `IstiN/trackstate` ref (`main`, tag, or commit SHA), builds the Flutter web app with the fork repository as runtime context, copies the setup repository's demo/config data into the web artifact, and deploys it to the fork's GitHub Pages site.

Maintainers should mark `IstiN/trackstate-setup` as a GitHub template repository in repository settings.
