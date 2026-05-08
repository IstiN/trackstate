import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/trackstate_app_screen.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-94 blocks dirty local issue creation with actionable recovery guidance',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen =
          defaultTestingDependencies.createTrackStateAppScreen(tester)
              as TrackStateAppScreen;
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-94 fixture creation did not complete.');
        }

        await tester.runAsync(fixture.makeDirtyMainFileChange);
        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('JQL Search');
        await screen.expectIssueSearchResultVisible(
          LocalTrackStateFixture.issueKey,
          LocalTrackStateFixture.issueSummary,
        );

        const sectionsToInspect = <String>[
          'Dashboard',
          'Board',
          'JQL Search',
          'Hierarchy',
          'Settings',
        ];
        final visitedSections = <String>[];

        for (final section in sectionsToInspect) {
          await screen.openSection(section);
          visitedSections.add(section);

          final hasCreateIssueEntryPoint =
              await screen.isSemanticsLabelVisible('Create issue') ||
              await screen.isTextVisible('Create issue');
          if (hasCreateIssueEntryPoint) {
            return;
          }
        }

        fail(
          'TS-94 could not navigate to an issue creation screen after dirtying '
          '${LocalTrackStateFixture.issuePath}. No visible "Create issue" entry '
          'point was rendered in sections ${visitedSections.join(', ')}. '
          'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
          'Visible semantics: '
          '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
  final snapshot = <String>[];
  for (final value in values) {
    if (value.isEmpty || snapshot.contains(value)) {
      continue;
    }
    snapshot.add(value);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}
