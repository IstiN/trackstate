import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts135_archived_issue_fixture.dart';

void main() {
  test('TS-166 keeps an archived issue archived after the repository restarts', () async {
    final fixture = await Ts135ArchivedIssueFixture.create();
    addTearDown(fixture.dispose);

    final beforeArchival = await fixture.observeBeforeArchivalState();

    expect(
      beforeArchival.issueFileExists,
      isTrue,
      reason:
          'TRACK-555 must exist as a real repository issue before the restart persistence workflow begins.',
    );
    expect(
      beforeArchival.issue.isArchived,
      isFalse,
      reason:
          'TS-166 requires TRACK-555 to start active before archiveIssue is invoked.',
    );
    expect(
      beforeArchival.indexEntry?.isArchived,
      isFalse,
      reason:
          'The active repository index must not already mark TRACK-555 as archived before the workflow runs.',
    );
    expect(
      beforeArchival.mainMarkdown,
      isNot(contains('archived: true')),
      reason:
          'The issue frontmatter must start without archived: true so TS-166 can verify persistence after the archive operation.',
    );

    final afterArchive = await fixture.archiveIssueAndObserveAfterRestart();

    expect(
      afterArchive.archivedIssue.isArchived,
      isTrue,
      reason:
          'The archiveIssue result should immediately report TRACK-555 as archived in the current repository session.',
    );
    expect(
      afterArchive.currentSessionIssue.isArchived,
      isTrue,
      reason:
          'Reloading the snapshot in the same repository session should keep TRACK-555 archived before restart.',
    );
    expect(
      afterArchive.currentSessionIndexEntry?.isArchived,
      isTrue,
      reason:
          'The current repository session should re-index TRACK-555 as archived immediately after archiving.',
    );
    expect(
      afterArchive.currentSessionMainMarkdown,
      contains('archived: true'),
      reason:
          'Archiving TRACK-555 must persist archived: true to the issue frontmatter before the repository is restarted.',
    );
    expect(
      afterArchive.currentSessionSearchResults
          .map((issue) => issue.key)
          .toList(),
      [Ts135ArchivedIssueFixture.archivedIssueKey],
      reason:
          'Integrated clients should still find TRACK-555 in standard search results immediately after archiving.',
    );
    expect(
      afterArchive.currentSessionSearchResults.single.isArchived,
      isTrue,
      reason:
          'Integrated clients should observe TRACK-555 as archived in standard search results before restart.',
    );

    final restartedObservation = afterArchive.restartedObservation;

    expect(
      restartedObservation.issue.key,
      Ts135ArchivedIssueFixture.archivedIssueKey,
      reason:
          'The fresh repository instance should retrieve TRACK-555 from the same data directory after restart.',
    );
    expect(
      restartedObservation.issue.isArchived,
      isTrue,
      reason:
          'After the repository restarts, TRACK-555 must still resolve as archived.',
    );
    expect(
      restartedObservation.indexEntry?.isArchived,
      isTrue,
      reason:
          'After restart, the repository index must still expose TRACK-555 as archived.',
    );
    expect(
      restartedObservation.mainMarkdown,
      contains('archived: true'),
      reason:
          'After restart, the persisted issue frontmatter must still contain archived: true.',
    );
    expect(
      restartedObservation.standardSearchResults
          .map((issue) => issue.key)
          .toList(),
      [Ts135ArchivedIssueFixture.archivedIssueKey],
      reason:
          'After restart, standard repository search should still return TRACK-555 from the same data directory.',
    );
    expect(
      restartedObservation.standardSearchResults.single.isArchived,
      isTrue,
      reason:
          'After restart, integrated clients should still observe TRACK-555 as archived in standard search results.',
    );
  });
}
