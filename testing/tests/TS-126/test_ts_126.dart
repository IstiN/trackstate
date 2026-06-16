import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../fixtures/repositories/ts126_merged_custom_fields_repository_fixture.dart';

void main() {
  test(
    'TS-126 merges explicit customFields entries with arbitrary top-level frontmatter keys',
    () async {
      final fixture = await Ts126MergedCustomFieldsRepositoryFixture.create();
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
          Ts126MergedCustomFieldsRepositoryFixture.explicitCustomFieldKey:
              Ts126MergedCustomFieldsRepositoryFixture.explicitCustomFieldValue,
          Ts126MergedCustomFieldsRepositoryFixture.arbitraryCustomFieldKey:
              Ts126MergedCustomFieldsRepositoryFixture
                  .arbitraryCustomFieldValue,
        }),
        reason:
            'The parsed issue should merge the explicit customFields object and '
            'the arbitrary top-level key into one canonical customFields map. '
            '$observedState',
      );
      expect(
        issue.status,
        IssueStatus.todo,
        reason:
            'The repository service should still map frontmatter status: open '
            'to the semantic todo/open state. $observedState',
      );
      expect(
        issue.statusId,
        'open',
        reason:
            'The parsed issue should keep the stable machine status id "open" '
            'while merging custom field sources. $observedState',
      );
      expect(
        issue.priority,
        IssuePriority.high,
        reason:
            'The repository service should still map frontmatter priority: '
            'high to IssuePriority.high. $observedState',
      );
      expect(
        issue.priorityId,
        'high',
        reason:
            'The parsed issue should keep the stable machine priority id '
            '"high" while merging custom field sources. $observedState',
      );
      expect(
        resolution.project.statusLabel(issue.statusId),
        'Open',
        reason:
            'Integrated clients should still resolve the stored status id to '
            'the user-facing label "Open". $observedState',
      );
      expect(
        resolution.project.priorityLabel(issue.priorityId),
        'High',
        reason:
            'Integrated clients should still resolve the stored priority id to '
            'the user-facing label "High". $observedState',
      );
      expect(
        issue.rawMarkdown,
        contains(
          'customFields:\n'
          '  ${Ts126MergedCustomFieldsRepositoryFixture.explicitCustomFieldKey}: '
          '"${Ts126MergedCustomFieldsRepositoryFixture.explicitCustomFieldValue}"',
        ),
        reason:
            'The fixture should exercise the explicit customFields object shape '
            'from TS-126. $observedState',
      );
      expect(
        issue.rawMarkdown,
        contains(
          '${Ts126MergedCustomFieldsRepositoryFixture.arbitraryCustomFieldKey}: '
          '"${Ts126MergedCustomFieldsRepositoryFixture.arbitraryCustomFieldValue}"',
        ),
        reason:
            'The fixture should exercise the arbitrary top-level key syntax '
            'from TS-126. $observedState',
      );
    },
  );

  testWidgets(
    'TS-126 keeps the real issue-detail flow usable after customFields merge explicit and arbitrary keys',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      Ts126MergedCustomFieldsRepositoryFixture? fixture;

      try {
        fixture = await tester.runAsync(
          Ts126MergedCustomFieldsRepositoryFixture.create,
        );
        if (fixture == null) {
          throw StateError('TS-126 fixture creation did not complete.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Launching the app against the merged-custom-fields fixture '
              'should not surface a framework exception.',
        );

        await screen.openSection('JQL Search');
        await screen.openIssue(
          Ts126MergedCustomFieldsRepositoryFixture.issueKey,
          Ts126MergedCustomFieldsRepositoryFixture.issueSummary,
        );
        await screen.expectIssueDetailText(
          Ts126MergedCustomFieldsRepositoryFixture.issueKey,
          Ts126MergedCustomFieldsRepositoryFixture.issueSummary,
        );
        await screen.expectIssueDetailText(
          Ts126MergedCustomFieldsRepositoryFixture.issueKey,
          Ts126MergedCustomFieldsRepositoryFixture.issueDescription,
        );
        await screen.expectIssueDetailText(
          Ts126MergedCustomFieldsRepositoryFixture.issueKey,
          'To Do',
        );
        await screen.expectIssueDetailText(
          Ts126MergedCustomFieldsRepositoryFixture.issueKey,
          'High',
        );
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Opening the merged-custom-fields issue through the real issue '
              'detail flow should not surface framework exceptions or '
              'crash-visible errors.',
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
