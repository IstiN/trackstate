import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../fixtures/repositories/ts136_legacy_deleted_index_fixture.dart';

void main() {
  test(
    'TS-136 deletes TRACK-777 through tombstone artifacts without mutating the legacy deleted index',
    () async {
      final fixture = await Ts136LegacyDeletedIndexFixture.create();
      addTearDown(fixture.dispose);

      final beforeDeletion = await fixture.observeBeforeDeletionState();

      expect(
        beforeDeletion.deletedIssueFileExists,
        isTrue,
        reason:
            'TRACK-777 must exist as a real issue before the delete workflow runs.',
      );
      expect(
        beforeDeletion.tombstoneFileExists,
        isFalse,
        reason:
            'The repository should not contain ${beforeDeletion.tombstonePath} before deletion.',
      );
      expect(
        beforeDeletion.tombstoneIndexExists,
        isFalse,
        reason:
            'The repository should not contain ${beforeDeletion.tombstoneIndexPath} before deletion.',
      );
      expect(
        beforeDeletion.legacyDeletedIndexExists,
        isTrue,
        reason:
            'TS-136 requires an existing legacy deleted index at ${beforeDeletion.legacyDeletedIndexPath}.',
      );
      expect(
        beforeDeletion.legacyDeletedIndexContent,
        Ts136LegacyDeletedIndexFixture.legacyDeletedIndexContent,
        reason:
            'TS-136 must begin with a known deleted.json payload so the post-delete comparison is meaningful.',
      );
      expect(
        beforeDeletion.deletedIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts136LegacyDeletedIndexFixture.deletedIssueKey],
        reason: 'TRACK-777 should be searchable before it is deleted.',
      );
      expect(
        beforeDeletion.survivingIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts136LegacyDeletedIndexFixture.survivingIssueKey],
        reason: 'TRACK-776 should remain searchable before deletion.',
      );

      final afterDeletion = await fixture.deleteIssueViaRepositoryService();
      final legacyIndexDescription = _describeLegacyIndexMutation(
        beforeDeletion: beforeDeletion,
        afterDeletion: afterDeletion,
      );

      expect(
        afterDeletion.deletedIssueFileExists,
        isFalse,
        reason: 'Deleting TRACK-777 should remove its active main.md artifact.',
      );
      expect(
        afterDeletion.tombstoneFileExists,
        isTrue,
        reason:
            'Deleting TRACK-777 should create ${afterDeletion.tombstonePath}.',
      );
      expect(
        afterDeletion.tombstoneJson,
        isNotNull,
        reason: 'The tombstone artifact should contain deletion metadata.',
      );
      expect(afterDeletion.tombstoneJson?['key'], 'TRACK-777');
      expect(
        afterDeletion.tombstoneJson?['formerPath'],
        Ts136LegacyDeletedIndexFixture.deletedIssuePath,
      );
      expect(afterDeletion.tombstoneJson?['project'], 'TRACK');
      expect(afterDeletion.tombstoneJson?['deletedAt'], isNotEmpty);
      expect(
        afterDeletion.tombstoneIndexExists,
        isTrue,
        reason:
            'Deleting TRACK-777 should create ${afterDeletion.tombstoneIndexPath}.',
      );
      expect(
        afterDeletion.tombstoneIndexJson,
        contains(
          allOf(
            containsPair('key', Ts136LegacyDeletedIndexFixture.deletedIssueKey),
            containsPair('path', Ts136LegacyDeletedIndexFixture.tombstonePath),
          ),
        ),
      );
      expect(
        afterDeletion.legacyDeletedIndexExists,
        isTrue,
        reason:
            'Deleting TRACK-777 must leave ${afterDeletion.legacyDeletedIndexPath} untouched. $legacyIndexDescription',
      );
      expect(
        afterDeletion.legacyDeletedIndexContent,
        beforeDeletion.legacyDeletedIndexContent,
        reason:
            'Deleting TRACK-777 must not rewrite ${afterDeletion.legacyDeletedIndexPath}. $legacyIndexDescription',
      );
      expect(
        afterDeletion.deletedIssueSearchResults,
        isEmpty,
        reason: 'Deleted issues must disappear from active search results.',
      );
      expect(
        afterDeletion.survivingIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts136LegacyDeletedIndexFixture.survivingIssueKey],
        reason: 'Deleting TRACK-777 must not affect other active issues.',
      );
    },
  );

  testWidgets(
    'TS-136 keeps the JQL Search experience consistent after the delete writes tombstones',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      Ts136LegacyDeletedIndexFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts136LegacyDeletedIndexFixture.create);
        if (fixture == null) {
          throw StateError('TS-136 fixture creation did not complete.');
        }

        await tester.runAsync(fixture.deleteIssueViaRepositoryService);
        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Launching the app against the deleted-issue fixture should not surface a framework exception.',
        );

        await screen.openSection('JQL Search');
        await screen.searchIssues('project = TRACK');
        screen.expectIssueSearchResultAbsent(
          Ts136LegacyDeletedIndexFixture.deletedIssueKey,
          'Delete target issue',
        );
        await screen.expectIssueSearchResultVisible(
          Ts136LegacyDeletedIndexFixture.survivingIssueKey,
          'Surviving issue',
        );
        expect(
          tester.takeException(),
          isNull,
          reason:
              'The real JQL Search flow should keep the deleted issue hidden and the surviving issue visible without framework exceptions.',
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

String _describeLegacyIndexMutation({
  required Ts136LegacyDeletedIndexObservation beforeDeletion,
  required Ts136LegacyDeletedIndexObservation afterDeletion,
}) {
  final beforeContent = beforeDeletion.legacyDeletedIndexContent?.replaceAll(
    '\n',
    r'\n',
  );
  final afterContent = afterDeletion.legacyDeletedIndexContent?.replaceAll(
    '\n',
    r'\n',
  );
  return 'beforeExists=${beforeDeletion.legacyDeletedIndexExists}, '
      'afterExists=${afterDeletion.legacyDeletedIndexExists}, '
      'beforeContent=$beforeContent, '
      'afterContent=$afterContent';
}
