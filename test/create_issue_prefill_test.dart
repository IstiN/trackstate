import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/core_enums.dart';
import 'package:trackstate/domain/models/extensions.dart';
import 'package:trackstate/domain/models/issue.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app_types.dart';

TrackStateIssue _makeIssue({
  required String key,
  required String summary,
  required IssueType issueType,
  String? epicKey,
}) {
  return TrackStateIssue(
    key: key,
    project: 'PROJ',
    issueType: issueType,
    issueTypeId: issueType.id,
    status: IssueStatus.todo,
    statusId: 'todo',
    priority: IssuePriority.medium,
    priorityId: 'medium',
    summary: summary,
    description: '',
    assignee: '',
    reporter: '',
    labels: const [],
    components: const [],
    fixVersionIds: const [],
    watchers: const [],
    customFields: const {},
    parentKey: null,
    epicKey: epicKey,
    parentPath: null,
    epicPath: null,
    progress: 0,
    updatedLabel: '',
    acceptanceCriteria: const [],
    comments: const [],
    links: const [],
    attachments: const [],
    isArchived: false,
  );
}

void main() {
  group('CreateIssuePrefill', () {
    test('forChild sets epicKey when parent is epic', () {
      final epic = _makeIssue(
        key: 'PROJ-1',
        summary: 'Epic issue',
        issueType: IssueType.epic,
      );
      final prefill = CreateIssuePrefill.forChild(
        originSection: TrackerSection.board,
        issue: epic,
      );
      expect(prefill.originSection, TrackerSection.board);
      expect(prefill.issueTypeId, IssueType.story.id);
      expect(prefill.epicKey, 'PROJ-1');
      expect(prefill.parentKey, isNull);
    });

    test('forChild sets parentKey and epicKey when parent is story', () {
      final story = _makeIssue(
        key: 'PROJ-2',
        summary: 'Story issue',
        issueType: IssueType.story,
        epicKey: 'PROJ-1',
      );
      final prefill = CreateIssuePrefill.forChild(
        originSection: TrackerSection.dashboard,
        issue: story,
      );
      expect(prefill.originSection, TrackerSection.dashboard);
      expect(prefill.issueTypeId, IssueType.subtask.id);
      expect(prefill.parentKey, 'PROJ-2');
      expect(prefill.epicKey, 'PROJ-1');
    });

    test('forChild sets parentKey when parent has no epic', () {
      final task = _makeIssue(
        key: 'PROJ-3',
        summary: 'Task issue',
        issueType: IssueType.task,
      );
      final prefill = CreateIssuePrefill.forChild(
        originSection: TrackerSection.hierarchy,
        issue: task,
      );
      expect(prefill.originSection, TrackerSection.hierarchy);
      expect(prefill.issueTypeId, IssueType.subtask.id);
      expect(prefill.parentKey, 'PROJ-3');
      expect(prefill.epicKey, isNull);
    });
  });
}
