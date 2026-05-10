import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
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
    'demo repository creates the first issue under the project root path when no issue paths exist yet',
    () async {
      const repository = DemoTrackStateRepository(
        snapshot: TrackerSnapshot(
          project: ProjectConfig(
            key: 'DEMO',
            name: 'Demo Project',
            repository: 'demo/repository',
            branch: 'main',
            defaultLocale: 'en',
            issueTypeDefinitions: [
              TrackStateConfigEntry(id: 'story', name: 'Story'),
            ],
            statusDefinitions: [
              TrackStateConfigEntry(id: 'todo', name: 'To Do'),
            ],
            fieldDefinitions: [
              TrackStateFieldDefinition(
                id: 'summary',
                name: 'Summary',
                type: 'string',
                required: true,
              ),
            ],
            priorityDefinitions: [
              TrackStateConfigEntry(id: 'medium', name: 'Medium'),
            ],
          ),
          issues: [],
        ),
      );

      final created = await repository.createIssue(
        summary: 'First demo issue',
        description: 'Created in an empty project snapshot.',
      );

      expect(created.key, 'DEMO-1');
      expect(created.storagePath, 'DEMO/DEMO-1/main.md');
    },
  );

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
          'DEMO/.trackstate/index/tombstones.json': jsonEncode([
            {
              'key': 'DEMO-99',
              'path': 'DEMO/.trackstate/tombstones/DEMO-99.json',
            },
          ]),
          'DEMO/.trackstate/tombstones/DEMO-99.json': jsonEncode({
            'key': 'DEMO-99',
            'project': 'DEMO',
            'formerPath': 'DEMO/DEMO-99/main.md',
            'deletedAt': '2026-05-05T00:30:00Z',
            'summary': 'Retired issue',
            'issueType': 'story',
            'parent': null,
            'epic': 'DEMO-1',
          }),
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
          'DEMO/config/resolutions.json',
          'DEMO/DEMO-1/DEMO-2/links.json',
          'DEMO/DEMO-1/DEMO-2/attachments/board-preview.svg',
        ]),
      );
      expect(
        files.containsKey('DEMO/.trackstate/index/tombstones.json') ||
            files.containsKey('DEMO/.trackstate/index/deleted.json'),
        isTrue,
        reason:
            'The checked-in setup template must include either the current '
            'tombstone index or the legacy deleted index.',
      );
      if (files.containsKey('DEMO/.trackstate/index/tombstones.json')) {
        expect(
          files.keys,
          contains('DEMO/.trackstate/tombstones/DEMO-99.json'),
        );
      }

      final repository = _mockSetupRepository(files: files);
      final snapshot = await repository.loadSnapshot();
      final boardIssue = snapshot.issues.firstWhere(
        (entry) => entry.key == 'DEMO-2',
      );
      final doneIssue = snapshot.issues.firstWhere(
        (entry) => entry.key == 'DEMO-4',
      );
      final epicIssue = snapshot.issues.firstWhere(
        (entry) => entry.key == 'DEMO-1',
      );

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
      expect(epicIssue.customFields['created'], '2026-05-05T00:00:00Z');
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

  test(
    'setup repository preserves inline customFields while resolving canonical ids',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'todo', 'name': 'To Do'},
            {'id': 'done', 'name': 'Done'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
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
              'id': 'field_101',
              'name': 'Custom Field 101',
              'type': 'string',
              'required': false,
            },
            {
              'id': 'priority',
              'name': 'Priority',
              'type': 'option',
              'required': false,
            },
          ]),
          'DEMO/config/priorities.json': jsonEncode([
            {'id': 'high', 'name': 'High'},
          ]),
          'DEMO/config/versions.json': jsonEncode([]),
          'DEMO/config/components.json': jsonEncode([]),
          'DEMO/DEMO-63/main.md': '''
---
key: DEMO-63
project: DEMO
issueType: story
status: done
priority: high
summary: Inline custom fields issue
assignee: qa-user
reporter: qa-admin
customFields: { "field_101": "value" }
updated: 2026-05-07T00:00:00Z
---

# Description

Created from inline frontmatter custom fields.
''',
        },
      );

      final snapshot = await repository.loadSnapshot();
      final issue = snapshot.issues.single;

      expect(issue.customFields['field_101'], 'value');
      expect(issue.status, IssueStatus.done);
      expect(issue.statusId, 'done');
      expect(issue.priority, IssuePriority.high);
      expect(issue.priorityId, 'high');
    },
  );

  test(
    'setup repository writes the repository canonical status id through the provider adapter',
    () async {
      Map<String, Object?>? savedBody;
      final repository = SetupTrackStateRepository(
        client: MockClient((request) async {
          final path = request.url.path;
          if (path.endsWith('/git/trees/main')) {
            return http.Response('''
{
  "tree": [
    {"path": "DEMO/project.json", "type": "blob"},
    {"path": "DEMO/config/statuses.json", "type": "blob"},
    {"path": "DEMO/config/issue-types.json", "type": "blob"},
    {"path": "DEMO/config/fields.json", "type": "blob"},
    {"path": "DEMO/config/priorities.json", "type": "blob"},
    {"path": "DEMO/config/versions.json", "type": "blob"},
    {"path": "DEMO/config/components.json", "type": "blob"},
    {"path": "DEMO/DEMO-1/main.md", "type": "blob"}
  ]
}
''', 200);
          }
          if (path == '/repos/${SetupTrackStateRepository.repositoryName}') {
            return http.Response('''
{"full_name":"${SetupTrackStateRepository.repositoryName}","permissions":{"pull":true,"push":true,"admin":false}}
''', 200);
          }
          if (path == '/user') {
            return http.Response(
              '{"login":"demo-user","name":"Demo User"}',
              200,
            );
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/project.json') {
            return _contentResponse('{"key":"DEMO","name":"Demo Project"}');
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/config/statuses.json') {
            return _contentResponse(
              jsonEncode([
                {'id': 'queued', 'name': 'To Do'},
                {'id': 'building', 'name': 'In Progress'},
                {'id': 'accepted', 'name': 'Done'},
              ]),
            );
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/config/issue-types.json') {
            return _contentResponse(
              '[{"id":"epic","name":"Epic"},{"id":"story","name":"Story"}]',
            );
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/config/fields.json') {
            return _contentResponse(
              '[{"id":"summary","name":"Summary","type":"string","required":true}]',
            );
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/config/priorities.json') {
            return _contentResponse('[{"id":"high","name":"High"}]');
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/config/versions.json') {
            return _contentResponse('[]');
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/config/components.json') {
            return _contentResponse('[]');
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/DEMO-1/main.md' &&
              request.method == 'GET') {
            return _contentResponse('''
---
key: DEMO-1
project: DEMO
issueType: story
status: building
priority: high
summary: Issue
assignee: demo-user
reporter: demo-admin
---
''');
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/DEMO-1/main.md' &&
              request.method == 'PUT') {
            savedBody = jsonDecode(request.body) as Map<String, Object?>;
            return http.Response('{"content":{"sha":"next"}}', 200);
          }
          return http.Response('', 404);
        }),
      );

      final snapshot = await repository.loadSnapshot();
      final user = await repository.connect(
        const RepositoryConnection(
          repository: SetupTrackStateRepository.repositoryName,
          branch: 'main',
          token: 'token',
        ),
      );
      final updated = await repository.updateIssueStatus(
        snapshot.issues.single,
        IssueStatus.done,
      );

      expect(user.login, 'demo-user');
      expect(updated.status, IssueStatus.done);
      expect(updated.statusId, 'accepted');
      expect(savedBody?['branch'], 'main');
      expect(savedBody?['message'], 'Move DEMO-1 to Done');
      final content = utf8.decode(
        base64Decode(savedBody?['content']! as String),
      );
      expect(content, contains('status: accepted'));
      expect(content, isNot(contains('status: done')));
    },
  );

  test('setup repository honors configPath from project.json', () async {
    final repository = _mockSetupRepository(
      files: {
        'DEMO/project.json': jsonEncode({
          'key': 'DEMO',
          'name': 'Demo Project',
          'configPath': 'tracker-config',
        }),
        'DEMO/tracker-config/statuses.json': jsonEncode([
          {'name': 'To Do'},
          {'name': 'Done'},
        ]),
        'DEMO/tracker-config/issue-types.json': jsonEncode([
          {'name': 'Epic'},
          {'name': 'Story'},
        ]),
        'DEMO/tracker-config/fields.json': jsonEncode([
          {'name': 'Summary'},
          {'name': 'Priority'},
        ]),
        'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: Story
status: In Progress
priority: High
summary: Config-aware issue
assignee: user
reporter: admin
parent: null
epic: null
updated: 2026-05-05T00:00:00Z
---

# Description

Loaded from setup data.
''',
      },
    );

    final snapshot = await repository.loadSnapshot();

    expect(snapshot.project.statuses, ['To Do', 'Done']);
    expect(snapshot.project.issueTypes, ['Epic', 'Story']);
    expect(snapshot.project.fields, ['Summary', 'Priority']);
  });

  test(
    'github provider evaluates LFS rules against the requested path',
    () async {
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          if (request.url.path.endsWith('/contents/.gitattributes')) {
            return _contentResponse('''
*.png filter=lfs diff=lfs merge=lfs -text
docs/**/*.zip filter=lfs diff=lfs merge=lfs -text
README.md -filter
''');
          }
          return http.Response('', 404);
        }),
      );

      expect(await provider.isLfsTracked('attachments/screenshot.png'), isTrue);
      expect(await provider.isLfsTracked('docs/releases/archive.zip'), isTrue);
      expect(await provider.isLfsTracked('README.md'), isFalse);
      expect(await provider.isLfsTracked('notes/todo.txt'), isFalse);
    },
  );

  test(
    'github provider reads non-LFS binary attachments without UTF-8 decoding',
    () async {
      final bytes = Uint8List.fromList(const [
        0x89,
        0x50,
        0x4E,
        0x47,
        0x00,
        0xFF,
      ]);
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          if (request.url.path.endsWith(
            '/contents/attachments/screenshot.png',
          )) {
            return _binaryContentResponse(bytes);
          }
          return http.Response('', 404);
        }),
      );

      final attachment = await provider.readAttachment(
        'attachments/screenshot.png',
        ref: 'main',
      );

      expect(attachment.bytes, bytes);
      expect(attachment.lfsOid, isNull);
      expect(attachment.declaredSizeBytes, isNull);
    },
  );

  test(
    'github provider downloads LFS attachment content after pointer detection',
    () async {
      final pointer = '''
version https://git-lfs.github.com/spec/v1
oid sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
size 6
''';
      final bytes = Uint8List.fromList(const [
        0x25,
        0x50,
        0x44,
        0x46,
        0x00,
        0x01,
      ]);
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          if (request.url.path.endsWith('/contents/attachments/manual.pdf')) {
            return _contentResponse(
              pointer,
              downloadUrl: 'https://example.test/lfs/manual.pdf',
            );
          }
          if (request.url.toString() == 'https://example.test/lfs/manual.pdf') {
            return http.Response.bytes(bytes, 200);
          }
          return http.Response('', 404);
        }),
      );

      final attachment = await provider.readAttachment(
        'attachments/manual.pdf',
        ref: 'main',
      );

      expect(attachment.bytes, bytes);
      expect(
        attachment.lfsOid,
        '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
      );
      expect(attachment.declaredSizeBytes, 6);
    },
  );

  test(
    'github provider reports LFS attachment uploads as unsupported',
    () async {
      var putAttempted = false;
      final provider = GitHubTrackStateProvider(
        repositoryName: 'IstiN/trackstate',
        dataRef: 'main',
        client: MockClient((request) async {
          final path = request.url.path;
          if (path.endsWith('/repos/IstiN/trackstate') &&
              request.method == 'GET') {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path.endsWith('/user') && request.method == 'GET') {
            return http.Response('{"login":"octocat","name":"Mona"}', 200);
          }
          if (path.endsWith('/contents/.gitattributes') &&
              request.method == 'GET') {
            return _contentResponse(
              '*.png filter=lfs diff=lfs merge=lfs -text\n',
            );
          }
          if (path.endsWith('/contents/attachments/screenshot.png') &&
              request.method == 'PUT') {
            putAttempted = true;
            return http.Response('{"content":{"sha":"uploaded-sha"}}', 201);
          }
          return http.Response('', 404);
        }),
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'IstiN/trackstate',
          branch: 'main',
          token: 'token',
        ),
      );

      await expectLater(
        () => provider.writeAttachment(
          RepositoryAttachmentWriteRequest(
            path: 'attachments/screenshot.png',
            bytes: Uint8List.fromList(const [1, 2, 3]),
            message: 'Upload screenshot',
            branch: 'main',
          ),
        ),
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            contains('not yet implemented'),
          ),
        ),
      );
      expect(putAttempted, isFalse);
    },
  );

  test(
    'github provider evaluates LFS upload rules against the target branch',
    () async {
      var putAttempted = false;
      final provider = GitHubTrackStateProvider(
        repositoryName: 'IstiN/trackstate',
        dataRef: 'main',
        client: MockClient((request) async {
          final path = request.url.path;
          if (path.endsWith('/repos/IstiN/trackstate') &&
              request.method == 'GET') {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path.endsWith('/user') && request.method == 'GET') {
            return http.Response('{"login":"octocat","name":"Mona"}', 200);
          }
          if (path.endsWith('/contents/.gitattributes') &&
              request.method == 'GET') {
            final ref = request.url.queryParameters['ref'];
            if (ref == 'feature/lfs') {
              return _contentResponse(
                '*.png filter=lfs diff=lfs merge=lfs -text\n',
              );
            }
            return _contentResponse('README.md -filter\n');
          }
          if (path.endsWith('/contents/attachments/screenshot.png') &&
              request.method == 'PUT') {
            putAttempted = true;
            return http.Response('{"content":{"sha":"uploaded-sha"}}', 201);
          }
          return http.Response('', 404);
        }),
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'IstiN/trackstate',
          branch: 'feature/lfs',
          token: 'token',
        ),
      );

      expect(
        await provider.isLfsTracked('attachments/screenshot.png'),
        isFalse,
      );
      await expectLater(
        () => provider.writeAttachment(
          RepositoryAttachmentWriteRequest(
            path: 'attachments/screenshot.png',
            bytes: Uint8List.fromList(const [1, 2, 3]),
            message: 'Upload screenshot',
            branch: 'feature/lfs',
          ),
        ),
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            contains('not yet implemented'),
          ),
        ),
      );
      expect(putAttempted, isFalse);
    },
  );
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

http.Response _contentResponse(String content, {String? downloadUrl}) {
  final encoded = base64Encode(utf8.encode(content));
  return http.Response(
    jsonEncode({
      'content': encoded,
      'sha': 'abc123',
      if (downloadUrl != null) 'download_url': downloadUrl,
    }),
    200,
  );
}

http.Response _binaryContentResponse(Uint8List content, {String? downloadUrl}) {
  final encoded = base64Encode(content);
  return http.Response(
    jsonEncode({
      'content': encoded,
      'sha': 'abc123',
      if (downloadUrl != null) 'download_url': downloadUrl,
    }),
    200,
  );
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
