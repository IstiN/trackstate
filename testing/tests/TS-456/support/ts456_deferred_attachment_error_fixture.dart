import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../../frameworks/flutter/issue_detail_accessibility_widget_framework.dart';

class Ts456DeferredAttachmentErrorFixture {
  Ts456DeferredAttachmentErrorFixture._({
    required this.repository,
    required _Ts456DeferredAttachmentErrorProvider provider,
  }) : _provider = provider;

  static const issueKey = 'TRACK-12';
  static const issueSummary = 'Attachment hydration should stay accessible';
  static const deferredErrorMessage =
      'deferred-attachment-read: Unable to load the seeded attachment metadata.';
  static const deferredErrorIconSemanticLabel = 'Attachments error';

  final ProviderBackedTrackStateRepository repository;
  final _Ts456DeferredAttachmentErrorProvider _provider;

  int get attachmentReadAttempts => _provider.attachmentReadAttempts;

  static Future<Ts456DeferredAttachmentErrorFixture> create() async {
    final provider = _Ts456DeferredAttachmentErrorProvider();
    final repository = ProviderBackedTrackStateRepository(provider: provider);
    await repository.connect(
      const RepositoryConnection(
        repository: 'trackstate/trackstate',
        branch: 'main',
        token: 'ts-456-test-token',
      ),
    );
    return Ts456DeferredAttachmentErrorFixture._(
      repository: repository,
      provider: provider,
    );
  }
}

Future<IssueDetailAccessibilityScreenHandle>
launchTs456DeferredAttachmentErrorScreen(
  WidgetTester tester, {
  required Ts456DeferredAttachmentErrorFixture fixture,
}) {
  return launchIssueDetailAccessibilityWidgetScreen(
    tester,
    repository: fixture.repository,
  );
}

class _Ts456DeferredAttachmentErrorProvider
    implements TrackStateProviderAdapter {
  static const _revision = 'ts-456-revision';
  static const _failingAttachmentPath =
      'TRACK-12/attachments/deferred-accessibility-log.txt';

  static const Map<String, String> _files = {
    'project.json': '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config"
}
''',
    'config/statuses.json': '''
[
  {"id": "todo", "name": "To Do", "category": "new"},
  {"id": "in-progress", "name": "In Progress", "category": "indeterminate"},
  {"id": "done", "name": "Done", "category": "done"}
]
''',
    'config/issue-types.json': '''
[
  {"id": "story", "name": "Story", "hierarchyLevel": 0, "icon": "story"}
]
''',
    'config/fields.json': '''
[
  {"id": "summary", "name": "Summary", "type": "string", "required": true},
  {"id": "description", "name": "Description", "type": "markdown", "required": false},
  {"id": "priority", "name": "Priority", "type": "option", "required": false},
  {"id": "labels", "name": "Labels", "type": "array", "required": false}
]
''',
    'config/priorities.json': '''
[
  {"id": "high", "name": "High"},
  {"id": "medium", "name": "Medium"}
]
''',
    'config/workflows.json': '''
{
  "default": {
    "name": "Default Workflow",
    "statuses": ["todo", "in-progress", "done"],
    "transitions": [
      {"id": "start", "name": "Start", "from": "todo", "to": "in-progress"},
      {"id": "finish", "name": "Finish", "from": "in-progress", "to": "done"}
    ]
  }
}
''',
    '.trackstate/index/issues.json': '''
[
  {
    "key": "TRACK-11",
    "path": "TRACK-11/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "Bootstrap filler issue",
    "issueType": "story",
    "status": "todo",
    "priority": "medium",
    "assignee": "qa-user",
    "labels": ["bootstrap"],
    "updated": "2026-05-11T09:00:00Z",
    "children": [],
    "archived": false
  },
  {
    "key": "TRACK-12",
    "path": "TRACK-12/main.md",
    "parent": null,
    "epic": null,
    "parentPath": null,
    "epicPath": null,
    "summary": "Attachment hydration should stay accessible",
    "issueType": "story",
    "status": "in-progress",
    "priority": "high",
    "assignee": "qa-user",
    "labels": ["attachments", "accessibility"],
    "updated": "2026-05-12T05:00:00Z",
    "children": [],
    "archived": false
  }
]
''',
    'TRACK-11/main.md': '''
---
key: TRACK-11
project: TRACK
issueType: Story
status: To Do
priority: Medium
summary: Bootstrap filler issue
assignee: qa-user
reporter: qa-user
updated: 2026-05-11T09:00:00Z
---

# Description

Keeps the issue list realistic for TS-456.
''',
    'TRACK-12/main.md': '''
---
key: TRACK-12
project: TRACK
issueType: Story
status: In Progress
priority: High
summary: Attachment hydration should stay accessible
assignee: qa-user
reporter: qa-user
labels:
  - attachments
  - accessibility
updated: 2026-05-12T05:00:00Z
---

# Description

Deferred attachment loading should surface an accessible error treatment.
''',
    'TRACK-12/acceptance_criteria.md': '''
- Deferred attachment failures expose a visible Retry action.
- Keyboard and screen-reader users can reach the Retry action.
''',
  };

  int attachmentReadAttempts = 0;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'ts-456-user', displayName: 'TS-456 User');

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == dataRef);

  @override
  Future<RepositoryPermission> getPermission() async =>
      const RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: true,
        canCheckCollaborators: false,
      );

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async => [
    for (final path in [..._files.keys, _failingAttachmentPath])
      RepositoryTreeEntry(path: path, type: 'blob'),
  ];

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    if (path == _failingAttachmentPath) {
      attachmentReadAttempts += 1;
      throw const TrackStateProviderException(
        Ts456DeferredAttachmentErrorFixture.deferredErrorMessage,
      );
    }
    return RepositoryAttachment(
      path: path,
      bytes: Uint8List.fromList(const <int>[]),
      revision: _revision,
      declaredSizeBytes: 0,
    );
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = _files[path];
    if (content == null) {
      throw TrackStateProviderException('Missing TS-456 fixture for $path.');
    }
    return RepositoryTextFile(
      path: path,
      content: content,
      revision: _revision,
    );
  }

  @override
  Future<String> resolveWriteBranch() async => dataRef;

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-456 should not create commits while verifying attachment error accessibility.',
    );
  }

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-456 should not write text files while verifying attachment error accessibility.',
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw const TrackStateProviderException(
      'TS-456 should not write attachments while verifying attachment error accessibility.',
    );
  }
}
