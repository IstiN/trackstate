import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-94 blocks dirty local issue creation with actionable recovery guidance',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
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

        final createIssueSection = await screen.openCreateIssueFlow();
        await _attemptDirtyIssueCreation(
          screen,
          createIssueSection: createIssueSection,
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

Future<void> _attemptDirtyIssueCreation(
  TrackStateAppComponent screen, {
  required String createIssueSection,
}) async {
  await screen.expectCreateIssueFormVisible(
    createIssueSection: createIssueSection,
  );
  await screen.populateCreateIssueForm(
    summary: 'TS-94 dirty create candidate',
    description: 'Dirty local creation should surface recovery guidance.',
  );
  await screen.submitCreateIssue(createIssueSection: createIssueSection);

  await screen.expectMessageBannerContains('commit');
  await screen.expectMessageBannerContains('stash');
  await screen.expectMessageBannerContains('clean');
}
