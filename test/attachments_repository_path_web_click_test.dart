import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _restrictionTitle = 'Attachments stay download-only in the browser';
const String _restrictionMessage =
    'Attachment upload is unavailable in this browser session. Existing attachments remain available for download.';
const String _openSettingsLabel = 'Open settings';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'web repository-path Attachments notice click opens Project Settings > Attachments',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      SharedPreferences.setMockInitialValues(const <String, Object>{
        _hostedTokenKey: 'repository-path-token',
      });

      await tester.pumpWidget(
        TrackStateApp(
          repository: ProviderBackedTrackStateRepository(
            provider: const _RepositoryPathWebTestProvider(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('JQL Search').first);
      await tester.pumpAndSettle();

      final issueLink = find.bySemanticsLabel(
        RegExp('Open ${RegExp.escape(_issueKey)} ${RegExp.escape(_issueSummary)}'),
      );
      await tester.ensureVisible(issueLink.first);
      await tester.tap(issueLink.first);
      await tester.pumpAndSettle();

      final issueDetail = _issueDetailFinder(_issueKey);
      final attachmentsTab = find.descendant(
        of: issueDetail,
        matching: find.byWidgetPredicate((widget) {
          if (widget is! Semantics) {
            return false;
          }
          return widget.properties.label == 'Attachments' &&
              widget.properties.button == true;
        }, description: 'Attachments collaboration tab'),
      );
      await tester.ensureVisible(attachmentsTab.first);
      await tester.tap(attachmentsTab.first);
      await tester.pumpAndSettle();

      final action = _attachmentsRestrictionActionFinder(
        _issueKey,
        title: _restrictionTitle,
        message: _restrictionMessage,
        actionLabel: _openSettingsLabel,
      );
      expect(action, findsOneWidget);
      expect(action.hitTestable(), findsOneWidget);

      await tester.tap(action.hitTestable().first);
      await tester.pumpAndSettle();

      expect(find.text('Project Settings'), findsOneWidget);
      expect(find.widgetWithText(Tab, 'Attachments'), findsWidgets);
      expect(find.text('Attachment storage mode'), findsOneWidget);
    },
  );

  testWidgets(
    'web repository-path notice overrides a previously selected Statuses settings tab',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      SharedPreferences.setMockInitialValues(const <String, Object>{
        _hostedTokenKey: 'repository-path-token',
      });

      await tester.pumpWidget(
        TrackStateApp(
          repository: ProviderBackedTrackStateRepository(
            provider: const _RepositoryPathWebTestProvider(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Settings').first);
      await tester.pumpAndSettle();
      final statusesTab = find.widgetWithText(Tab, 'Statuses').first;
      await tester.ensureVisible(statusesTab);
      await tester.tap(statusesTab);
      await tester.pumpAndSettle();
      expect(find.text('Add status'), findsOneWidget);
      expect(find.text('Attachment storage mode'), findsNothing);

      await tester.tap(find.text('JQL Search').first);
      await tester.pumpAndSettle();

      final issueLink = find.bySemanticsLabel(
        RegExp('Open ${RegExp.escape(_issueKey)} ${RegExp.escape(_issueSummary)}'),
      );
      await tester.ensureVisible(issueLink.first);
      await tester.tap(issueLink.first);
      await tester.pumpAndSettle();

      final issueDetail = _issueDetailFinder(_issueKey);
      final attachmentsTab = find.descendant(
        of: issueDetail,
        matching: find.byWidgetPredicate((widget) {
          if (widget is! Semantics) {
            return false;
          }
          return widget.properties.label == 'Attachments' &&
              widget.properties.button == true;
        }, description: 'Attachments collaboration tab'),
      );
      await tester.ensureVisible(attachmentsTab.first);
      await tester.tap(attachmentsTab.first);
      await tester.pumpAndSettle();

      final action = _attachmentsRestrictionActionFinder(
        _issueKey,
        title: _restrictionTitle,
        message: _restrictionMessage,
        actionLabel: _openSettingsLabel,
      );
      expect(action.hitTestable(), findsOneWidget);

      await tester.tap(action.hitTestable().first);
      await tester.pumpAndSettle();

      expect(find.text('Project Settings'), findsOneWidget);
      expect(find.text('Attachment storage mode'), findsOneWidget);
      expect(find.text('Add status'), findsNothing);
    },
  );
}

Finder _issueDetailFinder(String issueKey) => find.byWidgetPredicate((widget) {
  if (widget is! Semantics) {
    return false;
  }
  return widget.properties.label == 'Issue detail $issueKey';
}, description: 'Semantics widget labeled Issue detail $issueKey');

Finder _attachmentsRestrictionActionFinder(
  String issueKey, {
  required String title,
  required String message,
  required String actionLabel,
}) {
  final callout = find.ancestor(
    of: find.descendant(
      of: _issueDetailFinder(issueKey),
      matching: find.text(title, findRichText: true),
    ),
    matching: find.byWidgetPredicate((widget) {
      if (widget is! Semantics) {
        return false;
      }
      final label = widget.properties.label ?? '';
      return label.contains(title) && label.contains(message);
    }, description: 'attachments restriction callout "$title"'),
  );
  final outlinedButton = find.descendant(
    of: callout,
    matching: find.widgetWithText(OutlinedButton, actionLabel),
  );
  if (outlinedButton.evaluate().isNotEmpty) {
    return outlinedButton.first;
  }
  return find.descendant(
    of: callout,
    matching: find.widgetWithText(FilledButton, actionLabel),
  );
}

class _RepositoryPathWebTestProvider implements TrackStateProviderAdapter {
  const _RepositoryPathWebTestProvider();

  static const String _revision = 'attachments-web-test-revision';

  static const RepositoryPermission _permission = RepositoryPermission(
    canRead: true,
    canWrite: true,
    isAdmin: false,
    canCreateBranch: true,
    canManageAttachments: true,
    attachmentUploadMode: AttachmentUploadMode.full,
    canCheckCollaborators: false,
  );

  static const Map<String, String> _files = {
    'project.json': '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config",
  "attachmentStorage": {
    "mode": "repository-path"
  }
}
''',
    'config/statuses.json': '''
[
  {"id": "todo", "name": "To Do", "category": "new"},
  {"id": "in-progress", "name": "In Progress", "category": "indeterminate"},
  {"id": "in-review", "name": "In Review", "category": "indeterminate"},
  {"id": "done", "name": "Done", "category": "done"}
]
''',
    'config/issue-types.json': '''
[
  {"id": "epic", "name": "Epic", "hierarchyLevel": 1, "icon": "epic"},
  {"id": "story", "name": "Story", "hierarchyLevel": 0, "icon": "story"},
  {"id": "task", "name": "Task", "hierarchyLevel": 0, "icon": "task"},
  {"id": "subtask", "name": "Sub-task", "hierarchyLevel": -1, "icon": "subtask"},
  {"id": "bug", "name": "Bug", "hierarchyLevel": 0, "icon": "bug"}
]
''',
    'config/fields.json': '''
[
  {"id": "summary", "name": "Summary", "type": "string", "required": true},
  {"id": "description", "name": "Description", "type": "markdown", "required": false},
  {"id": "acceptanceCriteria", "name": "Acceptance Criteria", "type": "markdown", "required": false},
  {"id": "priority", "name": "Priority", "type": "option", "required": false},
  {"id": "assignee", "name": "Assignee", "type": "user", "required": false},
  {"id": "labels", "name": "Labels", "type": "array", "required": false}
]
''',
    'config/priorities.json': '''
[
  {"id": "highest", "name": "Highest"},
  {"id": "high", "name": "High"},
  {"id": "medium", "name": "Medium"}
]
''',
    'config/workflows.json': '''
{
  "default": {
    "name": "Default Workflow",
    "statuses": ["todo", "in-progress", "in-review", "done"],
    "transitions": [
      {"id": "start", "name": "Start", "from": "todo", "to": "in-progress"},
      {"id": "review", "name": "Review", "from": "in-progress", "to": "in-review"},
      {"id": "finish", "name": "Finish", "from": "in-review", "to": "done"}
    ]
  }
}
''',
    '.trackstate/index/issues.json': '''
[
  {
    "key": "TRACK-12",
    "path": "TRACK-12/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "Implement Git sync service",
    "issueType": "story",
    "status": "in-progress",
    "priority": "high",
    "assignee": "Denis",
    "labels": ["sync"],
    "updated": "5 minutes ago",
    "children": [],
    "archived": false
  }
]
''',
    'TRACK-12/main.md': '''
---
key: TRACK-12
project: TRACK
issueType: Story
status: In Progress
priority: High
summary: Implement Git sync service
assignee: Denis
reporter: Ana
labels:
  - sync
components:
  - storage
updated: 5 minutes ago
---

# Description
Read and write tracker files through GitHub Contents API.
''',
    'TRACK-12/acceptance_criteria.md': '''
- Push issue updates as commits.
''',
  };

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(
        login: 'write-enabled-user',
        displayName: 'Write Enabled User',
      );

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async => RepositoryAttachment(path: path, bytes: Uint8List.fromList('<svg />'.codeUnits));

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _files[path];
    if (content == null) {
      throw TrackStateProviderException('Missing fixture for $path.');
    }
    return RepositoryTextFile(path: path, content: content, revision: _revision);
  }

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == dataRef);

  @override
  Future<RepositoryPermission> getPermission() async => _permission;

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async => [
    for (final path in _files.keys)
      RepositoryTreeEntry(path: path, type: 'blob'),
    const RepositoryTreeEntry(
      path: 'TRACK-12/attachments/sync-sequence.svg',
      type: 'blob',
    ),
  ];

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => throw const TrackStateProviderException(
    'This regression test should not create commits.',
  );

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<String> resolveWriteBranch() async => dataRef;

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async => throw const TrackStateProviderException(
    'This regression test should not upload attachments.',
  );

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async => throw const TrackStateProviderException(
    'This regression test should not write project files.',
  );
}
