import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts66_deleted_issue_fixture.dart';

void main() {
  test(
    'TS-66 keeps deleted issue metadata reserved in the deleted index and removes the issue from active search results',
    () async {
      final fixture = await Ts66DeletedIssueFixture.create();
      addTearDown(fixture.dispose);

      final observation = await fixture.observeDeletedIssueBehavior();
      final tombstone = observation.snapshot.repositoryIndex.deleted
          .singleWhere(
            (entry) => entry.key == Ts66DeletedIssueFixture.deletedIssueKey,
          );

      expect(
        observation.deletedIndexExists,
        isTrue,
        reason:
            'Deleted-key metadata should be persisted in ${observation.deletedIndexPath}.',
      );
      expect(
        observation.deletedIndexEntries,
        hasLength(1),
        reason:
            'The deleted index should contain exactly one reserved-key record in this fixture.',
      );
      expect(
        observation.deletedIndexEntries.single['key'],
        'TRACK-123',
        reason:
            'The persisted deleted index should keep the original issue key reserved.',
      );
      expect(
        observation.deletedIndexEntries.single['formerPath'],
        'TRACK/TRACK-123/main.md',
        reason:
            'The deleted index should preserve the original repository path so the deleted issue stays traceable.',
      );
      expect(
        observation.deletedIndexEntries.single['deletedAt'],
        '2026-05-06T12:00:00Z',
        reason:
            'The deleted index should include the recorded deletion timestamp.',
      );
      expect(
        observation.deletedIndexEntries.single['summary'],
        'Deleted story',
        reason:
            'The deleted index should preserve the deleted issue summary for human traceability.',
      );
      expect(
        observation.deletedIndexEntries.single['issueType'],
        'story',
        reason:
            'The deleted index should preserve the deleted issue type identifier.',
      );

      expect(
        tombstone.key,
        'TRACK-123',
        reason:
            'The repository snapshot should expose the reserved deleted key through repositoryIndex.deleted.',
      );
      expect(
        tombstone.project,
        'TRACK',
        reason:
            'The loaded deleted metadata should stay associated with the original project.',
      );
      expect(
        tombstone.formerPath,
        'TRACK/TRACK-123/main.md',
        reason:
            'The loaded deleted metadata should preserve the original repository path.',
      );
      expect(
        tombstone.deletedAt,
        '2026-05-06T12:00:00Z',
        reason:
            'The loaded deleted metadata should expose the recorded deletion timestamp.',
      );
      expect(
        tombstone.summary,
        'Deleted story',
        reason:
            'The loaded deleted metadata should preserve the deleted issue summary.',
      );
      expect(
        tombstone.issueTypeId,
        'story',
        reason:
            'The loaded deleted metadata should preserve the deleted issue type identifier.',
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
            'Human-style verification should still find the surviving issue so the test confirms only the deleted key disappeared from active search.',
      );
    },
  );
}
