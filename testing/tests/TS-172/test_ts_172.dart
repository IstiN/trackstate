import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts136_legacy_deleted_index_fixture.dart';
import '../../fixtures/repositories/ts172_index_directory_integrity_fixture.dart';

void main() {
  test(
    'TS-172 deletes TRACK-777 without disturbing unrelated files in the index directory',
    () async {
      final fixture = await Ts172IndexDirectoryIntegrityFixture.create();
      addTearDown(fixture.dispose);

      final beforeDeletion = await fixture.observeBeforeDeletionState();

      expect(
        beforeDeletion.integrityFileExists,
        isTrue,
        reason:
            'TS-172 requires an unrelated tracked file at ${beforeDeletion.integrityCheckPath} before deleteIssue() runs.',
      );
      expect(
        beforeDeletion.integrityFileContent,
        Ts172IndexDirectoryIntegrityFixture.integrityCheckContent,
        reason:
            'TS-172 must start with a known integrity sentinel payload so post-delete comparison is meaningful.',
      );
      expect(
        beforeDeletion.indexDirectoryEntries,
        containsAll(['deleted.json', 'integrity_check.txt']),
        reason:
            'The fixture should expose the pre-delete index directory contents a repository user would inspect.',
      );

      final afterDeletion = await fixture.deleteIssueViaRepositoryService();
      final integrityDescription = _describeIntegrityMutation(
        beforeDeletion: beforeDeletion,
        afterDeletion: afterDeletion,
      );

      expect(
        afterDeletion.baseObservation.deletedIssueFileExists,
        isFalse,
        reason: 'Deleting TRACK-777 should remove its active main.md artifact.',
      );
      expect(
        afterDeletion.baseObservation.tombstoneFileExists,
        isTrue,
        reason:
            'Deleting TRACK-777 should create ${afterDeletion.baseObservation.tombstonePath}.',
      );
      expect(
        afterDeletion.baseObservation.tombstoneIndexExists,
        isTrue,
        reason:
            'Deleting TRACK-777 should create ${afterDeletion.baseObservation.tombstoneIndexPath}.',
      );
      expect(
        afterDeletion.baseObservation.tombstoneIndexJson,
        contains(
          allOf(
            containsPair('key', Ts136LegacyDeletedIndexFixture.deletedIssueKey),
            containsPair('path', Ts136LegacyDeletedIndexFixture.tombstonePath),
          ),
        ),
      );
      expect(
        afterDeletion.integrityFileExists,
        isTrue,
        reason:
            'Deleting TRACK-777 must not remove ${afterDeletion.integrityCheckPath}. $integrityDescription',
      );
      expect(
        afterDeletion.integrityFileContent,
        beforeDeletion.integrityFileContent,
        reason:
            'Deleting TRACK-777 must leave ${afterDeletion.integrityCheckPath} unchanged. $integrityDescription',
      );
      expect(
        afterDeletion.indexDirectoryEntries,
        containsAll([
          'deleted.json',
          'integrity_check.txt',
          'issues.json',
          'tombstones.json',
        ]),
        reason:
            'A repository user inspecting .trackstate/index after delete should still see the unrelated file alongside the surgically updated tombstone artifacts. $integrityDescription',
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
}

String _describeIntegrityMutation({
  required Ts172IndexDirectoryIntegrityObservation beforeDeletion,
  required Ts172IndexDirectoryIntegrityObservation afterDeletion,
}) {
  final beforeContent = beforeDeletion.integrityFileContent?.replaceAll(
    '\n',
    r'\n',
  );
  final afterContent = afterDeletion.integrityFileContent?.replaceAll(
    '\n',
    r'\n',
  );
  return 'beforeExists=${beforeDeletion.integrityFileExists}, '
      'afterExists=${afterDeletion.integrityFileExists}, '
      'beforeContent=$beforeContent, '
      'afterContent=$afterContent, '
      'afterEntries=${afterDeletion.indexDirectoryEntries.join(', ')}';
}
