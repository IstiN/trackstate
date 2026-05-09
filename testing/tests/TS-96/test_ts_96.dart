import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../fixtures/repositories/ts96_unmapped_frontmatter_repository_fixture.dart';

void main() {
  test(
    'TS-96 preserves arbitrary non-core frontmatter keys in customFields',
    () async {
      final fixture = await Ts96UnmappedFrontmatterRepositoryFixture.create();
      addTearDown(fixture.dispose);

      final resolution = await fixture.resolveIssueByKey();
      final issue = resolution.issue;
      final observedState = _describeObservedIssue(
        issue: issue,
        project: resolution.project,
      );

      expect(
        issue.customFields.containsKey(
          Ts96UnmappedFrontmatterRepositoryFixture.unmappedFieldKey,
        ),
        isTrue,
        reason:
            'The parsed issue should preserve arbitrary non-core frontmatter '
            'keys inside customFields. $observedState',
      );
      expect(
        issue.customFields[
            Ts96UnmappedFrontmatterRepositoryFixture.unmappedFieldKey],
        Ts96UnmappedFrontmatterRepositoryFixture.unmappedFieldValue,
        reason:
            'The parsed issue should map the unmapped_field frontmatter entry '
            'to "some_data" inside customFields. $observedState',
      );
      expect(
        issue.status,
        IssueStatus.done,
        reason:
            'The repository service should still map frontmatter status: done '
            'to IssueStatus.done. $observedState',
      );
      expect(
        issue.statusId,
        'done',
        reason:
            'The parsed issue should keep the stable machine status id "done" '
            'while preserving arbitrary custom metadata. $observedState',
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
            '"high" while preserving arbitrary custom metadata. '
            '$observedState',
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
        contains(
          '${Ts96UnmappedFrontmatterRepositoryFixture.unmappedFieldKey}: '
          '${Ts96UnmappedFrontmatterRepositoryFixture.unmappedFieldValue}',
        ),
        reason:
            'The fixture should exercise the arbitrary frontmatter key syntax '
            'from TS-96. $observedState',
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
