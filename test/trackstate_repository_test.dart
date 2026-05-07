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
  test('demo repository exposes Jira-like project data', () async {
    const repository = DemoTrackStateRepository();

    final snapshot = await repository.loadSnapshot();

    expect(snapshot.project.key, 'TRACK');
    expect(snapshot.issues.map((issue) => issue.key), contains('TRACK-12'));
    expect(snapshot.issues.first.acceptanceCriteria, isNotEmpty);
  });

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
    'setup repository lists and loads markdown issues through GitHub API',
    () async {
      final repository = SetupTrackStateRepository(
        client: MockClient((request) async {
          expect(request.url.host, 'api.github.com');
          final path = request.url.path;
          if (path.endsWith('/git/trees/main')) {
            expect(request.url.queryParameters['recursive'], '1');
            return http.Response('''
{
  "tree": [
    {"path": "DEMO/project.json", "type": "blob"},
    {"path": "DEMO/config/statuses.json", "type": "blob"},
    {"path": "DEMO/config/issue-types.json", "type": "blob"},
    {"path": "DEMO/config/fields.json", "type": "blob"},
    {"path": "DEMO/DEMO-1/main.md", "type": "blob"}
  ]
}
''', 200);
          }
          if (path.endsWith('/contents/DEMO/project.json')) {
            return _contentResponse('{"key":"DEMO","name":"Demo Project"}');
          }
          if (path.endsWith('/contents/DEMO/config/statuses.json')) {
            return _contentResponse('[{"name":"To Do"},{"name":"Done"}]');
          }
          if (path.endsWith('/contents/DEMO/config/issue-types.json')) {
            return _contentResponse('[{"name":"Epic"},{"name":"Story"}]');
          }
          if (path.endsWith('/contents/DEMO/config/fields.json')) {
            return _contentResponse('[{"name":"Summary"},{"name":"Priority"}]');
          }
          if (path.endsWith('/contents/DEMO/DEMO-1/main.md')) {
            return _contentResponse('''
---
key: DEMO-1
project: DEMO
issueType: Story
status: In Progress
priority: High
summary: Real markdown issue
assignee: user
reporter: admin
labels:
  - setup
components:
  - web
parent: null
epic: null
updated: 2026-05-05T00:00:00Z
---

# Description

Loaded from setup data.
''');
          }
          return http.Response('', 404);
        }),
      );

      final snapshot = await repository.loadSnapshot();

      expect(snapshot.project.key, 'DEMO');
      expect(
        snapshot.project.repository,
        SetupTrackStateRepository.repositoryName,
      );
      expect(snapshot.issues.single.key, 'DEMO-1');
      expect(snapshot.issues.single.status, IssueStatus.inProgress);
      expect(snapshot.issues.single.storagePath, 'DEMO/DEMO-1/main.md');
    },
  );

  test(
    'setup repository writes status updates through the provider adapter',
    () async {
      var savedBody = <String, Object?>{};
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
    {"path": "DEMO/DEMO-1/main.md", "type": "blob"}
  ]
}
''', 200);
          }
          if (path.endsWith(
            '/repos/${SetupTrackStateRepository.repositoryName}',
          )) {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path.endsWith('/user')) {
            return http.Response('{"login":"octocat","name":"Mona"}', 200);
          }
          if (path.endsWith('/contents/DEMO/project.json')) {
            return _contentResponse('{"key":"DEMO","name":"Demo Project"}');
          }
          if (path.endsWith('/contents/DEMO/config/statuses.json')) {
            return _contentResponse('[{"name":"To Do"},{"name":"Done"}]');
          }
          if (path.endsWith('/contents/DEMO/config/issue-types.json')) {
            return _contentResponse('[{"name":"Epic"},{"name":"Story"}]');
          }
          if (path.endsWith('/contents/DEMO/config/fields.json')) {
            return _contentResponse('[{"name":"Summary"},{"name":"Priority"}]');
          }
          if (path.endsWith('/contents/DEMO/DEMO-1/main.md') &&
              request.method == 'GET') {
            return _contentResponse('''
---
key: DEMO-1
project: DEMO
issueType: Story
status: In Progress
priority: High
summary: Real markdown issue
assignee: user
reporter: admin
updated: 2026-05-05T00:00:00Z
---

# Description

Loaded from setup data.
''');
          }
          if (path.endsWith('/contents/DEMO/DEMO-1/main.md') &&
              request.method == 'PUT') {
            savedBody = jsonDecode(request.body) as Map<String, Object?>;
            return http.Response(
              '{"content":{"sha":"next-sha"},"commit":{"sha":"commit-sha"}}',
              200,
            );
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

      expect(user.login, 'octocat');
      expect(updated.status, IssueStatus.done);
      expect(savedBody['branch'], 'main');
      expect(savedBody['message'], 'Move DEMO-1 to Done');
      expect(
        utf8.decode(base64Decode(savedBody['content']! as String)),
        contains('status: Done'),
      );
    },
  );

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

  test(
    'provider-backed repository exposes a neutral provider session',
    () async {
      final repository = SetupTrackStateRepository(
        client: MockClient((request) async {
          final path = request.url.path;
          if (path.endsWith(
            '/repos/${SetupTrackStateRepository.repositoryName}',
          )) {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path.endsWith('/user')) {
            return http.Response('{"login":"octocat","name":"Mona"}', 200);
          }
          return http.Response('', 404);
        }),
      );

      await repository.connect(
        const RepositoryConnection(
          repository: SetupTrackStateRepository.repositoryName,
          branch: 'main',
          token: 'token',
        ),
      );

      expect(repository.session, isNotNull);
      expect(repository.session!.providerType, 'github');
      expect(repository.session!.connectionState, 'connected');
      expect(repository.session!.resolvedUserIdentity, 'octocat');
      expect(repository.session!.canRead, isTrue);
      expect(repository.session!.canWrite, isTrue);
      expect(repository.session!.canCreateBranch, isTrue);
      expect(repository.session!.canManageAttachments, isTrue);
      expect(repository.session!.canCheckCollaborators, isTrue);
    },
  );
}

http.Response _contentResponse(String content) {
  final encoded = base64Encode(utf8.encode(content));
  return http.Response('{"content":"$encoded","sha":"abc123"}', 200);
}
