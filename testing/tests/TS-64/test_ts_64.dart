import 'package:flutter_test/flutter_test.dart';

import '../../components/screens/trackstate_app_screen.dart';
import '../../fixtures/repositories/ts64_moved_issue_fixture.dart';

void main() {
  testWidgets(
    'TS-64 resolves a moved issue by key from the regenerated repository index',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = TrackStateAppScreen(tester);
      Ts64MovedIssueFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts64MovedIssueFixture.create);
        if (fixture == null) {
          throw StateError('TS-64 fixture creation did not complete.');
        }

        final resolution = await tester.runAsync(
          () => fixture!.service.resolveIssueByKey(
            Ts64MovedIssueFixture.movedIssueKey,
          ),
        );
        if (resolution == null) {
          throw StateError('TS-64 key-resolution probe did not complete.');
        }
        final legacyIssueExists = await tester.runAsync(fixture.legacyIssueExists);

        expect(
          legacyIssueExists,
          isFalse,
          reason:
              'The legacy PROJECT-1 path should stay absent so the test proves the lookup depends on the regenerated index entry.',
        );
        expect(
          resolution.indexPath,
          Ts64MovedIssueFixture.movedIssuePath,
          reason:
              'Resolving PROJECT-1 should use the updated path written to .trackstate/index/issues.json after the move.',
        );
        expect(
          resolution.storagePath,
          Ts64MovedIssueFixture.movedIssuePath,
          reason:
              'The loaded issue should come from the moved filesystem location instead of the former PROJECT/PROJECT-1 directory.',
        );
        expect(
          resolution.parentKey,
          Ts64MovedIssueFixture.parentIssueKey,
          reason:
              'The resolved issue should retain the parent relationship recorded by the regenerated hierarchy/index metadata.',
        );
        expect(
          resolution.parentPath,
          Ts64MovedIssueFixture.parentIssuePath,
          reason:
              'Hierarchy normalization should translate the parent metadata to the new parent path rather than preserving the stale parentPath from issues.json.',
        );
        expect(
          resolution.searchResultKeys,
          [Ts64MovedIssueFixture.movedIssueKey],
          reason:
              'Searching by the moved issue key should still return exactly that issue for user-facing lookup flows.',
        );
        expect(
          resolution.acceptanceCriteria,
          contains(Ts64MovedIssueFixture.movedIssueCriterion),
          reason:
              'The moved issue detail should preserve its acceptance criteria after loading through the updated index path.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        await screen.openSection('Search');
        await screen.openIssue(
          Ts64MovedIssueFixture.movedIssueKey,
          Ts64MovedIssueFixture.movedIssueSummary,
        );
        await screen.expectIssueDetailText(
          Ts64MovedIssueFixture.movedIssueKey,
          Ts64MovedIssueFixture.movedIssueSummary,
        );
        await screen.expectIssueDetailText(
          Ts64MovedIssueFixture.movedIssueKey,
          'Loads from the regenerated repository index.',
        );
        await screen.expectIssueDetailText(
          Ts64MovedIssueFixture.movedIssueKey,
          Ts64MovedIssueFixture.movedIssueCriterion,
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
  );
}
