import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts66_deleted_issue_fixture.dart';

void main() {
  test(
    'TS-66 loads deleted-key metadata from the shipped deleted index and hides the deleted issue from active search results',
    () async {
      final fixture = await Ts66DeletedIssueFixture.create();
      addTearDown(fixture.dispose);

      final beforeDeletion = await fixture.observeBeforeDeletionState();

      expect(
        beforeDeletion.deletedIssueFileExists,
        isTrue,
        reason:
            'The pre-delete repository revision should still contain TRACK-123 as a real issue file.',
      );
      expect(
        beforeDeletion.deletedIndexExists,
        isFalse,
        reason:
            'The pre-delete revision should not contain ${Ts66DeletedIssueFixture.deletedIndexPath} before the delete commit lands.',
      );
      expect(
        beforeDeletion.snapshot.repositoryIndex.deleted,
        isEmpty,
        reason:
            'The loaded repository index should not expose deleted-key metadata before the delete revision.',
      );
      expect(
        beforeDeletion.snapshot.repositoryIndex.pathForKey('TRACK-123'),
        Ts66DeletedIssueFixture.deletedIssuePath,
        reason:
            'The pre-delete repository index should still resolve TRACK-123 to its active repository file.',
      );
      expect(
        beforeDeletion.deletedIssueSearchResults
            .map((issue) => issue.key)
            .toList(),
        ['TRACK-123'],
        reason:
            'TRACK-123 should be discoverable through standard repository search in the active revision before deletion.',
      );

      final afterDeletion = await fixture.observeAfterDeletionState();

      expect(
        afterDeletion.deletedIssueFileExists,
        isFalse,
        reason:
            'The deleted revision should remove ${afterDeletion.deletedIssuePath} from the active repository tree.',
      );
      expect(
        afterDeletion.deletedIndexExists,
        isTrue,
        reason:
            'The shipped delete flow on main should persist deleted-key metadata in ${afterDeletion.deletedIndexPath}.',
      );
      expect(
        afterDeletion.deletedIndexEntries,
        hasLength(1),
        reason:
            'The deleted index should contain exactly one reserved-key record for the deleted issue in this fixture.',
      );
      expect(
        afterDeletion.deletedIndexEntries.single['key'],
        'TRACK-123',
        reason:
            'The deleted index should keep the original issue key reserved after deletion.',
      );
      expect(
        afterDeletion.deletedIndexEntries.single['formerPath'],
        'TRACK/TRACK-123/main.md',
        reason:
            'The deleted index should preserve the original repository path so the deleted issue stays traceable.',
      );
      expect(
        afterDeletion.deletedIndexEntries.single['deletedAt'],
        '2026-05-06T12:00:00Z',
        reason:
            'The deleted index should include deletion metadata that records when the issue was removed.',
      );
      expect(
        afterDeletion.deletedIndexEntries.single['summary'],
        'Deleted story',
        reason:
            'The deleted index should preserve the deleted issue summary for user-facing history and traceability.',
      );
      expect(
        afterDeletion.deletedIndexEntries.single['issueType'],
        'story',
        reason:
            'The deleted index should preserve the deleted issue type identifier from the shipped main-branch schema.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.deleted,
        hasLength(1),
        reason:
            'Loading the deleted revision should hydrate one deleted-key tombstone model from ${afterDeletion.deletedIndexPath}.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.deleted.single.key,
        'TRACK-123',
        reason:
            'The loaded deleted-key model should keep the original issue key reserved after deletion.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.deleted.single.formerPath,
        'TRACK/TRACK-123/main.md',
        reason:
            'The loaded deleted-key model should preserve the original repository path so the deleted issue stays traceable.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.deleted.single.deletedAt,
        '2026-05-06T12:00:00Z',
        reason:
            'The loaded deleted-key model should include deletion metadata that records when the issue was removed.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.deleted.single.summary,
        'Deleted story',
        reason:
            'The loaded deleted-key model should preserve the deleted issue summary from deleted.json.',
      );
      expect(
        afterDeletion.snapshot.repositoryIndex.deleted.single.issueTypeId,
        'story',
        reason:
            'The loaded deleted-key model should preserve the deleted issue type identifier from deleted.json.',
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
            'The active repository index should not resolve TRACK-123 after the deleted revision removes its repository file.',
      );
      expect(
        afterDeletion.deletedIssueSearchResults,
        isEmpty,
        reason:
            'A user searching for TRACK-123 through standard JQL should not see the deleted issue in active results once it is represented only in deleted.json.',
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
