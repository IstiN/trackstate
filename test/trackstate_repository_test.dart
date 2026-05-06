import 'dart:io';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  test(
    'demo repository exposes richer issue schema and repository index data',
    () async {
      const repository = DemoTrackStateRepository();

      final snapshot = await repository.loadSnapshot();
      final issue = snapshot.issues.firstWhere(
        (entry) => entry.key == 'TRACK-12',
      );

      expect(snapshot.project.key, 'TRACK');
      expect(snapshot.project.statusLabel('in-progress'), 'In Progress');
      expect(snapshot.project.fieldLabel('storyPoints'), 'Story Points');
      expect(
        snapshot.repositoryIndex.pathForKey('TRACK-12'),
        'TRACK/TRACK-1/TRACK-12/main.md',
      );
      expect(issue.issueTypeId, 'story');
      expect(issue.statusId, 'in-progress');
      expect(issue.priorityId, 'high');
      expect(issue.fixVersionIds, ['mvp']);
      expect(issue.watchers, ['ana', 'denis']);
      expect(issue.customFields['storyPoints'], 8);
      expect(issue.links.single.targetKey, 'TRACK-41');
      expect(issue.attachments.single.mediaType, 'image/svg+xml');
    },
  );

  test('JQL search filters out done issues and sorts by priority', () async {
    const repository = DemoTrackStateRepository();

    final results = await repository.searchIssues(
      'project = TRACK AND status != Done ORDER BY priority DESC',
    );

    expect(results, isNotEmpty);
    expect(results.any((issue) => issue.status == IssueStatus.done), isFalse);
    expect(results.first.priority, IssuePriority.highest);
  });

  test('JQL search supports epic relationship lookup', () async {
    const repository = DemoTrackStateRepository();

    final results = await repository.searchIssues(
      'project = TRACK AND issueType = Story AND epic = TRACK-34',
    );

    expect(results.map((issue) => issue.key), contains('TRACK-41'));
    expect(results.every((issue) => issue.epicKey == 'TRACK-34'), isTrue);
  });

  test(
    'setup repository loads indexes, comments, links, attachments, tombstones, and localized labels',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
            'defaultLocale': 'en',
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'todo', 'name': 'To Do'},
            {'id': 'in-progress', 'name': 'In Progress'},
            {'id': 'done', 'name': 'Done'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'epic', 'name': 'Epic'},
            {'id': 'story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
            {
              'id': 'storyPoints',
              'name': 'Story Points',
              'type': 'number',
              'required': false,
            },
          ]),
          'DEMO/config/priorities.json': jsonEncode([
            {'id': 'high', 'name': 'High'},
          ]),
          'DEMO/config/versions.json': jsonEncode([
            {'id': 'mvp', 'name': 'MVP'},
          ]),
          'DEMO/config/components.json': jsonEncode([
            {'id': 'tracker-core', 'name': 'Tracker Core'},
          ]),
          'DEMO/config/resolutions.json': jsonEncode([
            {'id': 'done', 'name': 'Done'},
          ]),
          'DEMO/config/i18n/en.json': jsonEncode({
            'issueTypes': {'epic': 'Epic', 'story': 'Story'},
            'statuses': {
              'todo': 'To Do',
              'in-progress': 'In Progress',
              'done': 'Done',
            },
            'fields': {'storyPoints': 'Story Points'},
            'priorities': {'high': 'High'},
            'versions': {'mvp': 'MVP'},
            'components': {'tracker-core': 'Tracker Core'},
            'resolutions': {'done': 'Done'},
          }),
          'DEMO/.trackstate/index/issues.json': jsonEncode([
            {
              'key': 'DEMO-1',
              'path': 'DEMO/DEMO-1/main.md',
              'parent': null,
              'epic': null,
              'children': ['DEMO-2'],
              'archived': false,
            },
            {
              'key': 'DEMO-2',
              'path': 'DEMO/DEMO-1/DEMO-2/main.md',
              'parent': null,
              'epic': 'DEMO-1',
              'children': [],
              'archived': false,
            },
          ]),
          'DEMO/.trackstate/index/deleted.json': jsonEncode([
            {
              'key': 'DEMO-99',
              'project': 'DEMO',
              'formerPath': 'DEMO/DEMO-99/main.md',
              'deletedAt': '2026-05-05T00:30:00Z',
              'summary': 'Retired issue',
              'issueType': 'story',
              'parent': null,
              'epic': 'DEMO-1',
            },
          ]),
          'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: epic
status: in-progress
priority: high
summary: Root epic
assignee: demo-admin
reporter: demo-admin
labels:
  - root
components:
  - tracker-core
fixVersions:
  - mvp
watchers:
  - demo-admin
archived: false
parent: null
epic: null
updated: 2026-05-05T00:00:00Z
---

# Description

Root epic.
''',
          'DEMO/DEMO-1/DEMO-2/main.md': '''
---
key: DEMO-2
project: DEMO
issueType: story
status: in-progress
priority: high
summary: Indexed markdown issue
assignee: demo-user
reporter: demo-admin
labels:
  - setup
components:
  - tracker-core
fixVersions:
  - mvp
watchers:
  - demo-admin
resolution: done
archived: false
customFields:
  storyPoints: 5
  releaseTrain:
    - web
    - mobile
parent: null
epic: DEMO-1
updated: 2026-05-05T00:05:00Z
---

# Description

Loaded from setup data.
''',
          'DEMO/DEMO-1/DEMO-2/comments/0001.md': '''
---
author: demo-admin
created: 2026-05-05T00:10:00Z
---

This comment demonstrates markdown-backed collaboration history.
''',
          'DEMO/DEMO-1/DEMO-2/links.json': jsonEncode([
            {'type': 'blocks', 'target': 'DEMO-1', 'direction': 'outward'},
          ]),
          'DEMO/DEMO-1/DEMO-2/attachments/preview.svg': '<svg />',
        },
      );

      final snapshot = await repository.loadSnapshot();
      final issue = snapshot.issues.firstWhere(
        (entry) => entry.key == 'DEMO-2',
      );

      expect(snapshot.project.key, 'DEMO');
      expect(snapshot.project.defaultLocale, 'en');
      expect(snapshot.project.statusLabel('in-progress'), 'In Progress');
      expect(snapshot.project.fieldLabel('storyPoints'), 'Story Points');
      expect(snapshot.project.versionLabel('mvp'), 'MVP');
      expect(snapshot.project.componentLabel('tracker-core'), 'Tracker Core');
      expect(snapshot.project.resolutionLabel('done'), 'Done');
      expect(
        snapshot.repositoryIndex.pathForKey('DEMO-2'),
        'DEMO/DEMO-1/DEMO-2/main.md',
      );
      expect(snapshot.repositoryIndex.deleted.single.key, 'DEMO-99');
      expect(issue.issueTypeId, 'story');
      expect(issue.statusId, 'in-progress');
      expect(issue.priorityId, 'high');
      expect(issue.fixVersionIds, ['mvp']);
      expect(issue.watchers, ['demo-admin']);
      expect(issue.customFields['storyPoints'], 5);
      expect(issue.customFields['releaseTrain'], ['web', 'mobile']);
      expect(issue.comments.single.id, '0001');
      expect(issue.comments.single.author, 'demo-admin');
      expect(issue.links.single.type, 'blocks');
      expect(issue.links.single.targetKey, 'DEMO-1');
      expect(issue.attachments.single.name, 'preview.svg');
      expect(issue.attachments.single.mediaType, 'image/svg+xml');
      expect(issue.epicPath, 'DEMO/DEMO-1/main.md');
      expect(issue.resolutionId, 'done');
    },
  );

  test(
    'checked-in setup template includes repository index artifacts and richer fixtures',
    () async {
      final files = _fixtureFilesFromDisk('trackstate-setup/DEMO');

      expect(
        files.keys,
        containsAll([
          'DEMO/.trackstate/index/issues.json',
          'DEMO/.trackstate/index/deleted.json',
          'DEMO/config/resolutions.json',
          'DEMO/DEMO-1/DEMO-2/links.json',
          'DEMO/DEMO-1/DEMO-2/attachments/board-preview.svg',
        ]),
      );

      final repository = _mockSetupRepository(files: files);
      final snapshot = await repository.loadSnapshot();
      final boardIssue = snapshot.issues.firstWhere((entry) => entry.key == 'DEMO-2');
      final doneIssue = snapshot.issues.firstWhere((entry) => entry.key == 'DEMO-4');

      expect(snapshot.project.fieldLabel('storyPoints'), 'Story Points');
      expect(snapshot.project.resolutionLabel('done'), 'Done');
      expect(
        snapshot.repositoryIndex.pathForKey('DEMO-2'),
        'DEMO/DEMO-1/DEMO-2/main.md',
      );
      expect(snapshot.repositoryIndex.deleted.single.key, 'DEMO-99');
      expect(boardIssue.issueTypeId, 'story');
      expect(boardIssue.statusId, 'in-review');
      expect(boardIssue.priorityId, 'high');
      expect(boardIssue.fixVersionIds, ['mvp']);
      expect(boardIssue.watchers, ['demo-admin', 'demo-user']);
      expect(boardIssue.customFields['storyPoints'], 5);
      expect(boardIssue.customFields['releaseTrain'], ['web', 'mobile']);
      expect(boardIssue.links.single.targetKey, 'DEMO-4');
      expect(boardIssue.attachments.single.name, 'board-preview.svg');
      expect(doneIssue.statusId, 'done');
      expect(doneIssue.resolutionId, 'done');
    },
  );

  test(
    'setup repository keeps compatibility with legacy display labels',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'queued', 'name': 'To Do'},
            {'id': 'building', 'name': 'In Progress'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'feature-story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
          ]),
          'DEMO/config/priorities.json': jsonEncode([
            {'id': 'p1', 'name': 'High'},
          ]),
          'DEMO/config/versions.json': jsonEncode([]),
          'DEMO/config/components.json': jsonEncode([]),
          'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: Story
status: In Progress
priority: High
summary: Legacy markdown issue
assignee: user
reporter: admin
parent: null
epic: null
---

# Description

Loaded from older demo data.
''',
        },
      );

      final snapshot = await repository.loadSnapshot();
      final issue = snapshot.issues.single;

      expect(issue.issueType, IssueType.story);
      expect(issue.issueTypeId, 'feature-story');
      expect(issue.status, IssueStatus.inProgress);
      expect(issue.statusId, 'building');
      expect(issue.priority, IssuePriority.high);
      expect(issue.priorityId, 'p1');
      expect(issue.storagePath, 'DEMO/DEMO-1/main.md');
    },
  );

  test(
    'setup repository preserves stored config ids while reading semantic enums',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'queued', 'name': 'To Do'},
            {'id': 'building', 'name': 'In Progress'},
            {'id': 'accepted', 'name': 'Done'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'feature-story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
          ]),
          'DEMO/config/priorities.json': jsonEncode([
            {'id': 'p1', 'name': 'High'},
          ]),
          'DEMO/config/versions.json': jsonEncode([]),
          'DEMO/config/components.json': jsonEncode([]),
          'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: feature-story
status: building
priority: p1
summary: Canonical ids stay intact
assignee: user
reporter: admin
parent: null
epic: null
---

# Description

Machine ids should survive parsing.
''',
        },
      );

      final snapshot = await repository.loadSnapshot();
      final issue = snapshot.issues.single;

      expect(issue.issueType, IssueType.story);
      expect(issue.issueTypeId, 'feature-story');
      expect(issue.status, IssueStatus.inProgress);
      expect(issue.statusId, 'building');
      expect(issue.priority, IssuePriority.high);
      expect(issue.priorityId, 'p1');
    },
  );

  test('updating an issue status writes the repository canonical status id', () async {
    String? putBody;
    final repository = SetupTrackStateRepository(
      client: MockClient((request) async {
        final path = request.url.path;
        if (path == '/repos/owner/demo') {
          return http.Response('{"full_name":"owner/demo"}', 200);
        }
        if (path == '/user') {
          return http.Response('{"login":"demo-user","name":"Demo User"}', 200);
        }
        if (path == '/repos/owner/demo/contents/DEMO/DEMO-1/main.md' &&
            request.method == 'GET') {
          return _contentResponse('''
---
key: DEMO-1
project: DEMO
status: building
---
''');
        }
        if (path == '/repos/owner/demo/contents/DEMO/config/statuses.json' &&
            request.method == 'GET') {
          return _contentResponse(jsonEncode([
            {'id': 'queued', 'name': 'To Do'},
            {'id': 'building', 'name': 'In Progress'},
            {'id': 'accepted', 'name': 'Done'},
          ]));
        }
        if (path == '/repos/owner/demo/contents/DEMO/DEMO-1/main.md' &&
            request.method == 'PUT') {
          putBody = request.body;
          return http.Response('{"content":{"sha":"next"}}', 200);
        }
        return http.Response('', 404);
      }),
    );

    await repository.connect(
      const GitHubConnection(
        repository: 'owner/demo',
        branch: 'main',
        token: 'secret',
      ),
    );

    await repository.updateIssueStatus(
      const TrackStateIssue(
        key: 'DEMO-1',
        project: 'DEMO',
        issueType: IssueType.story,
        issueTypeId: 'story',
        status: IssueStatus.inProgress,
        statusId: 'building',
        priority: IssuePriority.high,
        priorityId: 'high',
        summary: 'Issue',
        description: 'Description',
        assignee: 'demo-user',
        reporter: 'demo-admin',
        labels: [],
        components: [],
        fixVersionIds: [],
        watchers: [],
        customFields: {},
        parentKey: null,
        epicKey: null,
        parentPath: null,
        epicPath: null,
        progress: 0.5,
        updatedLabel: 'now',
        acceptanceCriteria: [],
        comments: [],
        links: [],
        attachments: [],
        isArchived: false,
        storagePath: 'DEMO/DEMO-1/main.md',
      ),
      IssueStatus.done,
    );

    final body = jsonDecode(putBody!) as Map<String, Object?>;
    final content = utf8.decode(base64Decode(body['content']! as String));
    expect(content, contains('status: accepted'));
    expect(content, isNot(contains('status: done')));
  });
}

SetupTrackStateRepository _mockSetupRepository({
  required Map<String, String> files,
}) {
  return SetupTrackStateRepository(
    client: MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/git/trees/main')) {
        final tree = files.keys
            .map((filePath) => {'path': filePath, 'type': 'blob'})
            .toList(growable: false);
        return http.Response(jsonEncode({'tree': tree}), 200);
      }
      final contentsPrefix =
          '/repos/${SetupTrackStateRepository.repositoryName}/contents/';
      if (path.startsWith(contentsPrefix)) {
        final filePath = path.substring(contentsPrefix.length);
        final content = files[filePath];
        if (content != null) {
          return _contentResponse(content);
        }
      }
      return http.Response('', 404);
    }),
  );
}

http.Response _contentResponse(String content) {
  final encoded = base64Encode(utf8.encode(content));
  return http.Response('{"content":"$encoded","sha":"abc123"}', 200);
}

Map<String, String> _fixtureFilesFromDisk(String rootPath) {
  final root = Directory(rootPath);
  final normalizedRoot = root.path.replaceAll('\\', '/');
  final files = <String, String>{};

  for (final entity in root.listSync(recursive: true, followLinks: false)) {
    if (entity is! File) continue;
    final normalizedPath = entity.path.replaceAll('\\', '/');
    final relativePath = normalizedPath.substring(normalizedRoot.length + 1);
    files['DEMO/$relativePath'] = entity.readAsStringSync();
  }

  return files;
}
