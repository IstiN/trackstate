import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts66_deleted_issue_fixture.dart';

void main() {
  test('TS-66 deletes an issue, writes a tombstone artifact, and reserves the key', () async {
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
      beforeDeletion.tombstoneFileExists,
      isFalse,
      reason:
          'The repository should not contain ${beforeDeletion.tombstonePath} before the delete workflow runs.',
    );
    expect(
      beforeDeletion.tombstoneIndexExists,
      isFalse,
      reason:
          'The repository should not contain ${beforeDeletion.tombstoneIndexPath} before the delete workflow runs.',
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

    final afterDeletion = await fixture.deleteIssueViaRepositoryService();

    expect(
      afterDeletion.deletedIssueFileExists,
      isFalse,
      reason: 'Deleting TRACK-123 should remove its active main.md artifact.',
    );
    expect(
      afterDeletion.tombstoneFileExists,
      isTrue,
      reason:
          'Deleting TRACK-123 should create ${afterDeletion.tombstonePath}.',
    );
    expect(
      afterDeletion.tombstoneJson,
      isNotNull,
      reason: 'The tombstone artifact should contain deletion metadata.',
    );
    expect(afterDeletion.tombstoneJson?['key'], 'TRACK-123');
    expect(
      afterDeletion.tombstoneJson?['formerPath'],
      Ts66DeletedIssueFixture.deletedIssuePath,
    );
    expect(afterDeletion.tombstoneJson?['project'], 'TRACK');
    expect(afterDeletion.tombstoneJson?['deletedAt'], isNotEmpty);

    expect(
      afterDeletion.tombstoneIndexExists,
      isTrue,
      reason:
          'Deleting TRACK-123 should create ${afterDeletion.tombstoneIndexPath}.',
    );
    expect(
      afterDeletion.tombstoneIndexJson,
      contains(
        allOf(
          containsPair('key', 'TRACK-123'),
          containsPair('path', Ts66DeletedIssueFixture.tombstonePath),
        ),
      ),
    );
    expect(
      afterDeletion.snapshot.repositoryIndex.deleted.map((entry) => entry.key),
      contains('TRACK-123'),
    );
    expect(
      afterDeletion.snapshot.repositoryIndex.pathForKey('TRACK-123'),
      isNull,
      reason: 'Deleted issues should no longer resolve from the active index.',
    );
    expect(
      afterDeletion.deletedIssueSearchResults,
      isEmpty,
      reason: 'Deleted issues must disappear from active search results.',
    );
    expect(
      afterDeletion.activeIssueSearchResults.map((issue) => issue.key).toList(),
      ['TRACK-122'],
      reason: 'Deleting TRACK-123 must not affect other active issues.',
    );
  });
}
