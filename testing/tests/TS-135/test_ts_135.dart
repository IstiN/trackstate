import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts135_archived_issue_fixture.dart';

void main() {
  test(
    'TS-135 archives an issue through the repository service and updates repository metadata',
    () async {
      final fixture = await Ts135ArchivedIssueFixture.create();
      addTearDown(fixture.dispose);

      final beforeArchival = await fixture.observeBeforeArchivalState();

      expect(
        beforeArchival.issueFileExists,
        isTrue,
        reason:
            'TRACK-555 must exist as a real repository issue before the archive workflow runs.',
      );
      expect(
        beforeArchival.issue.isArchived,
        isFalse,
        reason:
            'TRACK-555 should start active before TS-135 invokes the repository archive operation.',
      );
      expect(
        beforeArchival.indexEntry?.isArchived,
        isFalse,
        reason:
            'The repository metadata must not mark TRACK-555 as archived before the workflow runs.',
      );
      expect(
        beforeArchival.mainMarkdown,
        isNot(contains('archived: true')),
        reason:
            'The issue frontmatter should not already contain an archived lifecycle flag before the archive workflow runs.',
      );
      expect(
        beforeArchival.standardSearchResults.map((issue) => issue.key).toList(),
        ['TRACK-555'],
        reason:
            'A standard repository search should find the active TRACK-555 issue before archiving.',
      );

      final afterArchival = await fixture.archiveIssueViaRepositoryService();

      expect(
        afterArchival.issue.isArchived,
        isTrue,
        reason:
            'Archiving TRACK-555 should update the resolved repository issue lifecycle state to archived.',
      );
      expect(
        afterArchival.indexEntry?.isArchived,
        isTrue,
        reason:
            'Archiving TRACK-555 should persist the archived lifecycle flag in repository metadata.',
      );
      expect(
        afterArchival.mainMarkdown,
        contains('archived: true'),
        reason:
            'Archiving TRACK-555 should write archived: true into the issue frontmatter metadata.',
      );
      expect(
        afterArchival.standardSearchResults.map((issue) => issue.key).toList(),
        ['TRACK-555'],
        reason:
            'A standard repository search should still surface TRACK-555 after archiving so integrated clients can observe its lifecycle state.',
      );
      expect(
        afterArchival.standardSearchResults.single.isArchived,
        isTrue,
        reason:
            'The issue returned from standard repository search should expose the archived lifecycle state to clients.',
      );
    },
  );
}
