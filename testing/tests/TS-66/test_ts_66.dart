import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts66_deleted_issue_fixture.dart';

void main() {
  test(
    'TS-66 deleting an issue reserves its key in the tombstone index and removes it from active search results',
    () async {
      final fixture = await Ts66DeletedIssueFixture.create();
      addTearDown(fixture.dispose);

      final observation = await fixture.observeDeletedIssueBehavior();
      final tombstone = observation.snapshot.repositoryIndex.deleted
          .singleWhere((entry) => entry.key == 'TRACK-123');

      expect(
        observation.tombstoneArtifactExistsBeforeDeletion,
        isFalse,
        reason:
            'The fixture should start without a tombstone artifact so the test exercises the delete transition instead of loading a prewritten deleted state.',
      );
      expect(
        observation.tombstoneIndexExistsBeforeDeletion,
        isFalse,
        reason:
            'The fixture should start without a tombstone index so the delete operation is responsible for reserving the deleted key.',
      );
      expect(
        observation.deletedIssueSearchResultsBeforeDeletion
            .map((issue) => issue.key)
            .toList(),
        ['TRACK-123'],
        reason:
            'TRACK-123 should be discoverable through standard repository search before the delete operation runs.',
      );
      expect(
        observation.tombstoneArtifactExists,
        isTrue,
        reason:
            'Deleting TRACK-123 should persist a tombstone artifact in ${observation.tombstoneArtifactPath}.',
      );
      expect(
        observation.tombstoneArtifact['key'],
        'TRACK-123',
        reason:
            'The tombstone artifact should keep the original issue key reserved after deletion.',
      );
      expect(
        observation.tombstoneArtifact['formerPath'],
        'TRACK/TRACK-123/main.md',
        reason:
            'The tombstone artifact should preserve the original repository path so the deleted issue stays traceable.',
      );
      expect(
        observation.tombstoneArtifact['deletedAt'],
        '2026-05-06T12:00:00Z',
        reason:
            'The tombstone artifact should include deletion metadata that records when the issue was removed.',
      );
      expect(
        observation.tombstoneIndexExists,
        isTrue,
        reason:
            'Deleting TRACK-123 should reserve the key in ${observation.tombstoneIndexPath}.',
      );
      expect(
        observation.tombstoneIndexEntries,
        hasLength(1),
        reason:
            'The tombstone index should contain exactly one reserved-key record for the deleted issue in this fixture.',
      );
      expect(
        observation.tombstoneIndexEntries.single['key'],
        'TRACK-123',
        reason:
            'The tombstone index should keep the original issue key reserved after deletion.',
      );
      expect(
        observation.tombstoneIndexEntries.single['formerPath'],
        'TRACK/TRACK-123/main.md',
        reason:
            'The tombstone index should preserve the original repository path so the deleted issue stays traceable.',
      );
      expect(
        observation.tombstoneIndexEntries.single['deletedAt'],
        '2026-05-06T12:00:00Z',
        reason:
            'The tombstone index should include deletion metadata that records when the issue was removed.',
      );

      expect(
        tombstone.key,
        'TRACK-123',
        reason:
            'The repository service should expose the deleted key through the loaded tombstone index.',
      );
      expect(
        tombstone.project,
        'TRACK',
        reason:
            'The tombstone record should stay associated with the original project.',
      );
      expect(
        tombstone.formerPath,
        'TRACK/TRACK-123/main.md',
        reason:
            'The loaded tombstone metadata should keep the deleted issue path available to clients.',
      );
      expect(
        tombstone.deletedAt,
        '2026-05-06T12:00:00Z',
        reason:
            'The loaded tombstone metadata should expose the recorded deletion timestamp.',
      );
      expect(
        tombstone.summary,
        'Deleted story',
        reason:
            'The tombstone metadata should preserve the deleted issue summary for human traceability.',
      );
      expect(
        tombstone.issueTypeId,
        'story',
        reason:
            'The tombstone metadata should preserve the deleted issue type so downstream consumers can reason about the reserved key.',
      );

      expect(
        observation.snapshot.issues.map((issue) => issue.key),
        isNot(contains('TRACK-123')),
        reason:
            'A deleted issue must no longer appear in the active repository snapshot.',
      );
      expect(
        observation.snapshot.repositoryIndex.pathForKey('TRACK-123'),
        isNull,
        reason:
            'The active repository index should not resolve TRACK-123 after deletion removes it from current issue paths.',
      );
      expect(
        observation.deletedIssueSearchResults,
        isEmpty,
        reason:
            'A user searching for TRACK-123 through standard JQL should not see the deleted issue in active results.',
      );
      expect(
        observation.activeIssueSearchResults.map((issue) => issue.key).toList(),
        ['TRACK-122'],
        reason:
            'Human-style verification should still find the surviving issue so the test confirms only the deleted key disappeared from search.',
      );
    },
  );
}
