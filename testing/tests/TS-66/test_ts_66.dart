import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts66_deleted_issue_fixture.dart';

void main() {
  test(
    'TS-66 deleting an issue through the repository service reserves its key in the tombstone index and removes it from active search results',
    () async {
      final fixture = await Ts66DeletedIssueFixture.create();
      addTearDown(fixture.dispose);

      final beforeDeletion = await fixture.observeRepositoryState();

      expect(
        beforeDeletion.deletedIssueFileExists,
        isTrue,
        reason:
            'The fixture should start with TRACK-123 present as a real repository file before the repository-service delete runs.',
      );
      expect(
        beforeDeletion.tombstoneArtifactExists,
        isFalse,
        reason:
            'The fixture should start without a tombstone artifact so the test exercises the repository-service delete transition instead of loading a prewritten deleted state.',
      );
      expect(
        beforeDeletion.tombstoneIndexExists,
        isFalse,
        reason:
            'The fixture should start without a tombstone index so the delete operation is responsible for reserving the deleted key.',
      );
      expect(
        beforeDeletion.deletedIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        ['TRACK-123'],
        reason:
            'TRACK-123 should be discoverable through standard repository search before the delete operation runs.',
      );

      await fixture.deleteIssueViaRepositoryService();

      final afterDeletion = await fixture.observeRepositoryState();

      expect(
        afterDeletion.deletedIssueFileExists,
        isFalse,
        reason:
            'Deleting TRACK-123 should remove ${afterDeletion.deletedIssuePath} from the active repository state rather than only hiding it in derived indexes.',
      );
      expect(
        afterDeletion.tombstoneArtifactExists,
        isTrue,
        reason:
            'Deleting TRACK-123 should persist a tombstone artifact in ${afterDeletion.tombstoneArtifactPath}.',
      );
      expect(
        afterDeletion.tombstoneArtifact['key'],
        'TRACK-123',
        reason:
            'The tombstone artifact should keep the original issue key reserved after deletion.',
      );
      expect(
        afterDeletion.tombstoneArtifact['formerPath'],
        'TRACK/TRACK-123/main.md',
        reason:
            'The tombstone artifact should preserve the original repository path so the deleted issue stays traceable.',
      );
      expect(
        afterDeletion.tombstoneArtifact['deletedAt'],
        '2026-05-06T12:00:00Z',
        reason:
            'The tombstone artifact should include deletion metadata that records when the issue was removed.',
      );
      expect(
        afterDeletion.tombstoneIndexExists,
        isTrue,
        reason:
            'Deleting TRACK-123 should reserve the key in ${afterDeletion.tombstoneIndexPath}.',
      );
      expect(
        afterDeletion.tombstoneIndexEntries,
        hasLength(1),
        reason:
            'The tombstone index should contain exactly one reserved-key record for the deleted issue in this fixture.',
      );
      expect(
        afterDeletion.tombstoneIndexEntries.single['key'],
        'TRACK-123',
        reason:
            'The tombstone index should keep the original issue key reserved after deletion.',
      );
      expect(
        afterDeletion.tombstoneIndexEntries.single['formerPath'],
        'TRACK/TRACK-123/main.md',
        reason:
            'The tombstone index should preserve the original repository path so the deleted issue stays traceable.',
      );
      expect(
        afterDeletion.tombstoneIndexEntries.single['deletedAt'],
        '2026-05-06T12:00:00Z',
        reason:
            'The tombstone index should include deletion metadata that records when the issue was removed.',
      );

      expect(
        afterDeletion.snapshot.issues.map((issue) => issue.key),
        isNot(contains('TRACK-123')),
        reason:
            'A deleted issue must no longer appear in the active repository snapshot.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.pathForKey('TRACK-123'),
        isNull,
        reason:
            'The active repository index should not resolve TRACK-123 after its repository file is removed.',
      );
      expect(
        afterDeletion.deletedIssueSearchResults,
        isEmpty,
        reason:
            'A user searching for TRACK-123 through standard JQL should not see the deleted issue in active results.',
      );
      expect(
        afterDeletion.activeIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        ['TRACK-122'],
        reason:
            'Human-style verification should still find the surviving issue so the test confirms only the deleted key disappeared from search.',
      );
    },
  );
}
