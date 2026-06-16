import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../fixtures/repositories/ts97_empty_custom_fields_repository_fixture.dart';

void main() {
  test(
    'TS-97 resolves an issue without custom fields into an empty canonical map',
    () async {
      final fixture = await Ts97EmptyCustomFieldsRepositoryFixture.create();
      addTearDown(fixture.dispose);

      final resolution = await fixture.resolveIssueByKey();
      final issue = resolution.issue;
      final observedState = _describeObservedIssue(
        issue: issue,
        project: resolution.project,
      );

      expect(
        issue.customFields,
        equals(<String, Object?>{}),
        reason:
            'The canonical model should initialize customFields as an empty '
            'map when frontmatter omits custom fields entirely. $observedState',
      );
      expect(
        issue.status,
        IssueStatus.todo,
        reason:
            'The repository service should map frontmatter status: open into '
            'the semantic todo/open issue state. $observedState',
      );
      expect(
        issue.statusId,
        'open',
        reason:
            'The parsed issue should keep the stable machine status id '
            '"open". $observedState',
      );
      expect(
        issue.priority,
        IssuePriority.medium,
        reason:
            'The repository service should map frontmatter priority: medium '
            'to IssuePriority.medium. $observedState',
      );
      expect(
        issue.priorityId,
        'medium',
        reason:
            'The parsed issue should keep the stable machine priority id '
            '"medium". $observedState',
      );
      expect(
        resolution.project.statusLabel(issue.statusId),
        'Open',
        reason:
            'A client resolving the stored status id should still present the '
            'user-facing label "Open". $observedState',
      );
      expect(
        resolution.project.priorityLabel(issue.priorityId),
        'Medium',
        reason:
            'A client resolving the stored priority id should still present '
            'the user-facing label "Medium". $observedState',
      );
      expect(
        issue.rawMarkdown,
        isNot(contains('customFields:')),
        reason:
            'The fixture should exercise the no-custom-fields frontmatter '
            'shape from TS-97 without hidden customFields input. $observedState',
      );
    },
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
