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
      const createdIssuePath = 'DEMO/DEMO-2/main.md';

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-94 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        await tester.runAsync(fixture.makeDirtyMainFileChange);
        final dirtyStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          dirtyStatus,
          equals(['M ${LocalTrackStateFixture.issuePath}']),
          reason:
              'TS-94 requires exactly one manual filesystem edit before opening '
              'Create issue, but `git status --short` returned '
              '${dirtyStatus.join(' | ')}.',
        );
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

        expect(
          await screen.isTextFieldVisible('Summary'),
          isTrue,
          reason:
              'After the dirty-repository guidance is shown, the Create issue '
              'form should remain open so the blocked create attempt is visible '
              'to the user.',
        );

        final latestHead = await tester.runAsync(fixture.headRevision) ?? '';
        final finalStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final createdIssueExists = await tester.runAsync(
          () => fixture!.repositoryPathExists(createdIssuePath),
        );

        expect(
          latestHead,
          initialHead,
          reason:
              'A blocked dirty-repository create attempt must not add a new git '
              'commit.',
        );
        expect(
          finalStatus,
          equals(dirtyStatus),
          reason:
              'A blocked dirty-repository create attempt must not change the '
              'worktree beyond the original manual edit. Observed status: '
              '${finalStatus.join(' | ')}.',
        );
        expect(
          createdIssueExists,
          isFalse,
          reason:
              'A blocked dirty-repository create attempt must not create the '
              'new issue file at $createdIssuePath.',
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
