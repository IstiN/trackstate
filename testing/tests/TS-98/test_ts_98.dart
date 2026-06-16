import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../fixtures/repositories/ts98_malformed_custom_fields_fixture.dart';

void main() {
  test(
    'TS-98 resolves malformed customFields frontmatter without throwing and defaults to an empty map',
    () async {
      final fixture = await Ts98MalformedCustomFieldsFixture.create();
      addTearDown(fixture.dispose);

      final resolution = await fixture.resolveIssueByKey();
      final issue = resolution.issue;
      final observedState = _describeObservedIssue(
        issue: issue,
        project: resolution.project,
      );

      expect(
        issue.customFields,
        isEmpty,
        reason:
            'Malformed primitive customFields values should be ignored instead '
            'of crashing resolution or leaking an invalid scalar into the '
            'canonical issue model. $observedState',
      );
      expect(
        issue.status,
        IssueStatus.todo,
        reason:
            'The malformed customFields entry should not prevent the issue from '
            'resolving its canonical status. $observedState',
      );
      expect(
        issue.statusId,
        'todo',
        reason:
            'The stored status ID should remain the stable machine ID even when '
            'customFields is malformed. $observedState',
      );
      expect(
        issue.priority,
        IssuePriority.low,
        reason:
            'The malformed customFields entry should not prevent the issue from '
            'resolving its canonical priority. $observedState',
      );
      expect(
        issue.priorityId,
        'low',
        reason:
            'The stored priority ID should remain the stable machine ID even '
            'when customFields is malformed. $observedState',
      );
      expect(
        resolution.project.statusLabel(issue.statusId),
        'To Do',
        reason:
            'Integrated clients should still be able to present the resolved '
            'status label after repository resolution succeeds. $observedState',
      );
      expect(
        resolution.project.priorityLabel(issue.priorityId),
        'Low',
        reason:
            'Integrated clients should still be able to present the resolved '
            'priority label after repository resolution succeeds. $observedState',
      );
      expect(
        issue.rawMarkdown,
        contains(
          'customFields: "${Ts98MalformedCustomFieldsFixture.invalidCustomFieldsValue}"',
        ),
        reason:
            'The fixture should exercise the malformed primitive customFields '
            'frontmatter syntax from TS-98. $observedState',
      );
    },
  );

  testWidgets(
    'TS-98 keeps the real issue-detail flow usable when customFields is malformed',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      Ts98MalformedCustomFieldsFixture? fixture;

      try {
        fixture = await tester.runAsync(
          Ts98MalformedCustomFieldsFixture.create,
        );
        if (fixture == null) {
          throw StateError('TS-98 fixture creation did not complete.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Launching the app against the malformed customFields fixture '
              'should not surface a framework exception.',
        );

        await screen.openSection('JQL Search');
        await screen.openIssue(
          Ts98MalformedCustomFieldsFixture.issueKey,
          Ts98MalformedCustomFieldsFixture.issueSummary,
        );
        await screen.expectIssueDetailText(
          Ts98MalformedCustomFieldsFixture.issueKey,
          Ts98MalformedCustomFieldsFixture.issueSummary,
        );
        await screen.expectIssueDetailText(
          Ts98MalformedCustomFieldsFixture.issueKey,
          Ts98MalformedCustomFieldsFixture.issueDescription,
        );
        await screen.expectIssueDetailText(
          Ts98MalformedCustomFieldsFixture.issueKey,
          'To Do',
        );
        await screen.expectIssueDetailText(
          Ts98MalformedCustomFieldsFixture.issueKey,
          'Low',
        );
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Opening the malformed issue through the real issue-detail flow '
              'should not surface framework exceptions or crash-visible errors.',
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
