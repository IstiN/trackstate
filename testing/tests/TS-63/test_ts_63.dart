import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../fixtures/repositories/ts63_custom_fields_repository_fixture.dart';

void main() {
  test(
    'TS-63 loads inline custom fields and canonical core ids through the repository service',
    () async {
      final fixture = await Ts63CustomFieldsRepositoryFixture.create();
      addTearDown(fixture.dispose);

      final resolution = await fixture.resolveIssueByKey();
      final issue = resolution.issue;
      final observedState = _describeObservedIssue(
        issue: issue,
        project: resolution.project,
      );

      expect(
        issue.customFields.containsKey('field_101'),
        isTrue,
        reason:
            'The parsed issue should preserve the inline customFields entry '
            'under key "field_101". $observedState',
      );
      expect(
        issue.customFields['field_101'],
        'value',
        reason:
            'The parsed issue should map field_101 to "value" inside the '
            'customFields map. $observedState',
      );
      expect(
        issue.status,
        IssueStatus.done,
        reason:
            'The repository service should map frontmatter status: done to '
            'IssueStatus.done. $observedState',
      );
      expect(
        issue.statusId,
        'done',
        reason:
            'The parsed issue should keep the stable machine status id '
            '"done" instead of a display label. $observedState',
      );
      expect(
        issue.priority,
        IssuePriority.high,
        reason:
            'The repository service should map frontmatter priority: high to '
            'IssuePriority.high. $observedState',
      );
      expect(
        issue.priorityId,
        'high',
        reason:
            'The parsed issue should keep the stable machine priority id '
            '"high" instead of a display label. $observedState',
      );
      expect(
        resolution.project.statusLabel(issue.statusId),
        'Done',
        reason:
            'A client resolving the stored status id should still present the '
            'user-facing label "Done". $observedState',
      );
      expect(
        resolution.project.priorityLabel(issue.priorityId),
        'High',
        reason:
            'A client resolving the stored priority id should still present '
            'the user-facing label "High". $observedState',
      );
      expect(
        issue.rawMarkdown,
        contains('customFields: { "field_101": "value" }'),
        reason:
            'The fixture should exercise the exact inline customFields '
            'frontmatter syntax from TS-63. $observedState',
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
