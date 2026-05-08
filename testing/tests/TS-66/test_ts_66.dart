import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts66_deleted_issue_fixture.dart';

void main() {
  test(
    'TS-66 requires a real repository-service delete path before tombstone assertions can run',
    () async {
      final fixture = await Ts66DeletedIssueFixture.create();
      addTearDown(fixture.dispose);

      final beforeDeletion = await fixture.observeBeforeDeletionState();

      expect(
        beforeDeletion.deletedIssueFileExists,
        isTrue,
        reason:
            'TRACK-123 must exist as a real issue before TS-66 attempts the delete workflow.',
      );
      expect(
        beforeDeletion.deletedIndexExists,
        isFalse,
        reason:
            'The repository should not contain ${beforeDeletion.deletedIndexPath} before the delete workflow runs.',
      );
      expect(
        beforeDeletion.snapshot.repositoryIndex.deleted,
        isEmpty,
        reason:
            'No deleted-key metadata should exist before the repository-service delete step.',
      );
      expect(
        beforeDeletion.snapshot.repositoryIndex.pathForKey('TRACK-123'),
        Ts66DeletedIssueFixture.deletedIssuePath,
        reason:
            'TRACK-123 should still resolve to its active repository file before deletion.',
      );
      expect(
        beforeDeletion.deletedIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        ['TRACK-123'],
        reason:
            'TRACK-123 should be discoverable through standard search before deletion.',
      );
      expect(
        beforeDeletion.activeIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        ['TRACK-122'],
        reason:
            'TRACK-122 should remain searchable while TS-66 verifies the pre-delete state.',
      );

      await fixture.deleteIssueViaRepositoryService();
    },
  );
}
