import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts135_archived_issue_fixture.dart';

void main() {
  test(
    'TS-152 archives an already archived issue without changing its archived lifecycle state',
    () async {
      final fixture = await Ts135ArchivedIssueFixture.create(
        initiallyArchived: true,
      );
      addTearDown(fixture.dispose);

      final beforeRedundantArchive = await fixture.observeCurrentState();

      expect(
        beforeRedundantArchive.issueFileExists,
        isTrue,
        reason:
            'TRACK-555 must exist as a real repository issue before the redundant archive workflow runs.',
      );
      expect(
        beforeRedundantArchive.issue.isArchived,
        isTrue,
        reason:
            'TS-152 requires TRACK-555 to start archived before archiveIssue is invoked again.',
      );
      expect(
        beforeRedundantArchive.indexEntry?.isArchived,
        isTrue,
        reason:
            'The repository metadata must already expose TRACK-555 as archived before the redundant archive request.',
      );
      expect(
        beforeRedundantArchive.mainMarkdown,
        contains('archived: true'),
        reason:
            'The issue frontmatter must already contain archived: true before the redundant archive request.',
      );
      expect(
        _archivedFlagCount(beforeRedundantArchive.mainMarkdown),
        1,
        reason:
            'TRACK-555 should begin with exactly one archived frontmatter flag so TS-152 can detect duplicate writes.',
      );
      expect(
        beforeRedundantArchive.standardSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts135ArchivedIssueFixture.archivedIssueKey],
        reason:
            'A standard repository search should already surface TRACK-555 while it is archived.',
      );
      expect(
        beforeRedundantArchive.standardSearchResults.single.isArchived,
        isTrue,
        reason:
            'Integrated clients must already observe TRACK-555 as archived before the redundant archive request.',
      );

      Object? archiveError;
      StackTrace? archiveStackTrace;
      Ts135ArchivedIssueObservation? afterRedundantArchive;

      try {
        afterRedundantArchive = await fixture
            .archiveIssueViaRepositoryService();
      } catch (error, stackTrace) {
        archiveError = error;
        archiveStackTrace = stackTrace;
      }

      expect(
        archiveError,
        isNull,
        reason:
            'Calling archiveIssue for an already archived TRACK-555 should be idempotent and must not throw. '
            'Observed error: $archiveError\n$archiveStackTrace',
      );

      final afterArchive = afterRedundantArchive;
      expect(
        afterArchive,
        isNotNull,
        reason:
            'The repository should still return a refreshed archived observation after a redundant archive request.',
      );

      expect(
        afterArchive!.issue.isArchived,
        isTrue,
        reason:
            'A redundant archive request must keep the resolved repository issue lifecycle state archived.',
      );
      expect(
        afterArchive.indexEntry?.isArchived,
        isTrue,
        reason:
            'A redundant archive request must keep repository metadata marked archived for TRACK-555.',
      );
      expect(
        afterArchive.mainMarkdown,
        contains('archived: true'),
        reason:
            'A redundant archive request must keep archived: true in the issue frontmatter.',
      );
      expect(
        _archivedFlagCount(afterArchive.mainMarkdown),
        1,
        reason:
            'A redundant archive request must not duplicate the archived frontmatter line.\nObserved main.md:\n${afterArchive.mainMarkdown}',
      );
      expect(
        afterArchive.standardSearchResults.map((issue) => issue.key).toList(),
        [Ts135ArchivedIssueFixture.archivedIssueKey],
        reason:
            'A standard repository search should still surface TRACK-555 after the redundant archive request.',
      );
      expect(
        afterArchive.standardSearchResults.single.isArchived,
        isTrue,
        reason:
            'The issue returned from standard repository search must remain archived after the redundant archive request.',
      );
    },
  );
}

int _archivedFlagCount(String markdown) => RegExp(
  r'^archived:\s*true\s*$',
  multiLine: true,
).allMatches(markdown).length;
