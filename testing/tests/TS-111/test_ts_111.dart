import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-111 shows a functional dismiss control on the dirty-save failure banner',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-111 fixture creation did not complete.');
        }

        await tester.runAsync(fixture.makeDirtyMainFileChange);
        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('Search');
        await screen.openIssue(
          LocalTrackStateFixture.issueKey,
          LocalTrackStateFixture.issueSummary,
        );
        await screen.expectIssueDetailText(
          LocalTrackStateFixture.issueKey,
          LocalTrackStateFixture.originalDescription,
        );
        await screen.tapIssueDetailAction(
          LocalTrackStateFixture.issueKey,
          label: 'Edit',
        );
        await screen.expectIssueDescriptionEditorVisible(
          LocalTrackStateFixture.issueKey,
          label: 'Description',
        );
        await screen.enterIssueDescription(
          LocalTrackStateFixture.issueKey,
          label: 'Description',
          text: LocalTrackStateFixture.updatedDescription,
        );
        await screen.tapIssueDetailAction(
          LocalTrackStateFixture.issueKey,
          label: 'Save',
        );

        await screen.expectMessageBannerContains('Save failed:');
        await screen.expectMessageBannerContains('commit');
        await screen.expectMessageBannerContains('stash');
        await screen.expectMessageBannerContains('clean');

        final dismissed = await screen.dismissMessageBannerContaining(
          'Save failed:',
        );
        final visibleTexts = _formatSnapshot(screen.visibleTextsSnapshot());
        final visibleSemantics = _formatSnapshot(
          screen.visibleSemanticsLabelsSnapshot(),
        );

        expect(
          dismissed,
          isTrue,
          reason:
              'Expected the visible "Save failed:" banner to expose a working '
              'close or dismiss control and disappear after tapping it. '
              'Visible texts: $visibleTexts. '
              'Visible semantics: $visibleSemantics.',
        );

        expect(
          await screen.isTextVisible('Save failed:'),
          isFalse,
          reason:
              'Expected the failed-save banner to be removed from the UI after '
              'the user dismissed it. Visible texts: $visibleTexts.',
        );

        await screen.openSection('Search');
        await screen.expectIssueSearchResultVisible(
          LocalTrackStateFixture.issueKey,
          LocalTrackStateFixture.issueSummary,
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
    timeout: const Timeout(Duration(seconds: 30)),
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
