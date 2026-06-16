import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../fixtures/repositories/ts128_null_or_empty_frontmatter_repository_fixture.dart';

void main() {
  test(
    'TS-128 preserves empty and null arbitrary frontmatter keys in customFields',
    () async {
      final fixture =
          await Ts128NullOrEmptyFrontmatterRepositoryFixture.create();
      addTearDown(fixture.dispose);

      final resolution = await fixture.resolveIssueByKey();
      final issue = resolution.issue;
      final observedState = _describeObservedIssue(
        issue: issue,
        project: resolution.project,
      );

      expect(
        issue.customFields,
        equals(<String, Object?>{
          Ts128NullOrEmptyFrontmatterRepositoryFixture.emptyCustomFieldKey:
              null,
          Ts128NullOrEmptyFrontmatterRepositoryFixture.nullCustomFieldKey: null,
        }),
        reason:
            'Arbitrary frontmatter keys with empty and explicit null values '
            'should be preserved in customFields without leaking core keys. '
            '$observedState',
      );
      expect(
        issue.status,
        IssueStatus.todo,
        reason:
            'The repository service should still resolve frontmatter '
            'status: open into the semantic todo/open issue state. '
            '$observedState',
      );
      expect(
        issue.statusId,
        'open',
        reason:
            'The parsed issue should keep the stable machine status id '
            '"open" while preserving null custom metadata. $observedState',
      );
      expect(
        issue.priority,
        IssuePriority.medium,
        reason:
            'The repository service should still resolve frontmatter '
            'priority: medium while preserving null custom metadata. '
            '$observedState',
      );
      expect(
        issue.priorityId,
        'medium',
        reason:
            'The parsed issue should keep the stable machine priority id '
            '"medium" while preserving null custom metadata. $observedState',
      );
      expect(
        resolution.project.statusLabel(issue.statusId),
        'Open',
        reason:
            'An integrated client resolving the stored status id should still '
            'present the user-facing label "Open". $observedState',
      );
      expect(
        resolution.project.priorityLabel(issue.priorityId),
        'Medium',
        reason:
            'An integrated client resolving the stored priority id should '
            'still present the user-facing label "Medium". $observedState',
      );
      expect(
        issue.rawMarkdown,
        contains(
          '${Ts128NullOrEmptyFrontmatterRepositoryFixture.emptyCustomFieldKey}:',
        ),
        reason:
            'The fixture should exercise an empty arbitrary frontmatter key '
            'value. $observedState',
      );
      expect(
        issue.rawMarkdown,
        contains(
          '${Ts128NullOrEmptyFrontmatterRepositoryFixture.nullCustomFieldKey}: null',
        ),
        reason:
            'The fixture should exercise an explicit null arbitrary '
            'frontmatter value. $observedState',
      );
    },
  );

  testWidgets(
    'TS-128 keeps the real issue-detail flow usable with null custom metadata',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      Ts128NullOrEmptyFrontmatterRepositoryFixture? fixture;

      try {
        fixture = await tester.runAsync(
          Ts128NullOrEmptyFrontmatterRepositoryFixture.create,
        );
        if (fixture == null) {
          throw StateError('TS-128 fixture creation did not complete.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Launching the app against the null/empty custom metadata '
              'fixture should not surface a framework exception.',
        );

        await screen.openSection('JQL Search');
        await screen.expectIssueSearchResultVisible(
          Ts128NullOrEmptyFrontmatterRepositoryFixture.issueKey,
          Ts128NullOrEmptyFrontmatterRepositoryFixture.issueSummary,
        );
        await screen.openIssue(
          Ts128NullOrEmptyFrontmatterRepositoryFixture.issueKey,
          Ts128NullOrEmptyFrontmatterRepositoryFixture.issueSummary,
        );
        await screen.expectIssueDetailText(
          Ts128NullOrEmptyFrontmatterRepositoryFixture.issueKey,
          Ts128NullOrEmptyFrontmatterRepositoryFixture.issueSummary,
        );
        await screen.expectIssueDetailText(
          Ts128NullOrEmptyFrontmatterRepositoryFixture.issueKey,
          Ts128NullOrEmptyFrontmatterRepositoryFixture.issueDescription,
        );
        await screen.expectIssueDetailText(
          Ts128NullOrEmptyFrontmatterRepositoryFixture.issueKey,
          'To Do',
        );
        await screen.expectIssueDetailText(
          Ts128NullOrEmptyFrontmatterRepositoryFixture.issueKey,
          'Medium',
        );
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Opening the issue through the real issue-detail flow should not '
              'surface framework exceptions or crash-visible errors when '
              'customFields contains null values.',
        );
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

String _describeObservedIssue({
  required TrackStateIssue issue,
  required ProjectConfig project,
}) {
  final normalizedMarkdown = issue.rawMarkdown.replaceAll('\n', r'\n');
  return 'Observed customFields=${issue.customFields}, '
      'status=${issue.status.name}, statusId=${issue.statusId}, '
      'statusLabel=${project.statusLabel(issue.statusId)}, '
      'priority=${issue.priority.name}, priorityId=${issue.priorityId}, '
      'priorityLabel=${project.priorityLabel(issue.priorityId)}, '
      'rawMarkdown=$normalizedMarkdown';
}
