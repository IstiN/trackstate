import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../fixtures/repositories/ts136_legacy_deleted_index_fixture.dart';

void main() {
  test(
    'TS-173 deletes an issue successfully when the legacy deleted index file is absent',
    () async {
      final fixture = await Ts136LegacyDeletedIndexFixture.create(
        seedLegacyDeletedIndex: false,
        tempDirectoryPrefix: 'trackstate-ts-173-',
      );
      addTearDown(fixture.dispose);

      final beforeDeletion = await fixture.observeBeforeDeletionState();

      expect(
        beforeDeletion.legacyDeletedIndexExists,
        isFalse,
        reason:
            'Step 1 failed: ${beforeDeletion.legacyDeletedIndexPath} must be absent before TS-173 runs the delete workflow.',
      );
      expect(
        beforeDeletion.legacyDeletedIndexContent,
        isNull,
        reason:
            'Step 1 failed: TS-173 requires no legacy deleted.json payload before deletion begins.',
      );
      expect(
        beforeDeletion.deletedIssueFileExists,
        isTrue,
        reason:
            'Step 2 failed: TRACK-777 must exist as a real issue before the repository service deletes it.',
      );
      expect(
        beforeDeletion.tombstoneFileExists,
        isFalse,
        reason:
            'Step 2 failed: ${beforeDeletion.tombstonePath} must not exist before the delete operation runs.',
      );
      expect(
        beforeDeletion.tombstoneIndexExists,
        isFalse,
        reason:
            'Step 2 failed: ${beforeDeletion.tombstoneIndexPath} must not exist before the delete operation runs.',
      );
      expect(
        beforeDeletion.deletedIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts136LegacyDeletedIndexFixture.deletedIssueKey],
        reason:
            'Human-style verification failed before deletion: TRACK-777 should be visible in active search results.',
      );
      expect(
        beforeDeletion.survivingIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts136LegacyDeletedIndexFixture.survivingIssueKey],
        reason:
            'Human-style verification failed before deletion: TRACK-776 should remain visible alongside the delete target.',
      );

      final afterDeletion = await fixture.deleteIssueViaRepositoryService();

      expect(
        afterDeletion.deletedIssueFileExists,
        isFalse,
        reason:
            'Step 2 failed: deleting TRACK-777 should remove its active main.md artifact.',
      );
      expect(
        afterDeletion.tombstoneFileExists,
        isTrue,
        reason:
            'Step 3 failed: deleting TRACK-777 should create ${afterDeletion.tombstonePath}.',
      );
      expect(
        afterDeletion.tombstoneJson,
        isNotNull,
        reason:
            'Step 3 failed: the tombstone artifact should contain deletion metadata.',
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
            'Step 4 failed: deleting TRACK-777 should create ${afterDeletion.tombstoneIndexPath}.',
      );
      expect(
        afterDeletion.tombstoneIndexJson,
        contains(
          allOf(
            containsPair('key', Ts136LegacyDeletedIndexFixture.deletedIssueKey),
            containsPair('path', Ts136LegacyDeletedIndexFixture.tombstonePath),
          ),
        ),
        reason:
            'Step 4 failed: the tombstone index must register TRACK-777 in ${afterDeletion.tombstoneIndexPath}.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.deleted.map(
          (entry) => entry.key,
        ),
        contains(Ts136LegacyDeletedIndexFixture.deletedIssueKey),
        reason:
            'Expected result mismatch: the active repository index should reserve TRACK-777 as deleted after the tombstone write.',
      );
      expect(
        afterDeletion.legacyDeletedIndexExists,
        isFalse,
        reason:
            'Expected result mismatch: deleting TRACK-777 must not create ${afterDeletion.legacyDeletedIndexPath} when it was absent before the workflow.',
      );
      expect(
        afterDeletion.legacyDeletedIndexContent,
        isNull,
        reason:
            'Expected result mismatch: deleting TRACK-777 must not synthesize legacy deleted.json content.',
      );
      expect(
        afterDeletion.deletedIssueSearchResults,
        isEmpty,
        reason:
            'Human-style verification failed after deletion: TRACK-777 should disappear from active search results once deleted.',
      );
      expect(
        afterDeletion.survivingIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts136LegacyDeletedIndexFixture.survivingIssueKey],
        reason:
            'Human-style verification failed after deletion: TRACK-776 should remain visible after TRACK-777 is deleted.',
      );
    },
  );

  testWidgets(
    'TS-173 keeps the JQL Search experience usable when delete runs without a legacy deleted index file',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      Ts136LegacyDeletedIndexFixture? fixture;

      try {
        fixture = await tester.runAsync(
          () => Ts136LegacyDeletedIndexFixture.create(
            seedLegacyDeletedIndex: false,
            tempDirectoryPrefix: 'trackstate-ts-173-',
          ),
        );
        if (fixture == null) {
          throw StateError('TS-173 fixture creation did not complete.');
        }

        await tester.runAsync(fixture.deleteIssueViaRepositoryService);
        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Launching the app after deleting TRACK-777 without deleted.json should not surface a framework exception.',
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
              'The real JQL Search flow should stay usable and show only the surviving issue after the delete runs without deleted.json.',
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
