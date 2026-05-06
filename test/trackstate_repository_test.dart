import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
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

  test('setup repository honors configPath from project.json', () async {
    final repository = SetupTrackStateRepository(
      client: MockClient((request) async {
        final path = request.url.path;
        if (path.endsWith('/git/trees/main')) {
          return http.Response('''
{
  "tree": [
    {"path": "DEMO/project.json", "type": "blob"},
    {"path": "DEMO/tracker-config/statuses.json", "type": "blob"},
    {"path": "DEMO/tracker-config/issue-types.json", "type": "blob"},
    {"path": "DEMO/tracker-config/fields.json", "type": "blob"},
    {"path": "DEMO/DEMO-1/main.md", "type": "blob"}
  ]
}
''', 200);
        }
        if (path.endsWith('/contents/DEMO/project.json')) {
          return _contentResponse(
            '{"key":"DEMO","name":"Demo Project","configPath":"tracker-config"}',
          );
        }
        if (path.endsWith('/contents/DEMO/tracker-config/statuses.json')) {
          return _contentResponse('[{"name":"To Do"},{"name":"Done"}]');
        }
        if (path.endsWith('/contents/DEMO/tracker-config/issue-types.json')) {
          return _contentResponse('[{"name":"Epic"},{"name":"Story"}]');
        }
        if (path.endsWith('/contents/DEMO/tracker-config/fields.json')) {
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
summary: Config-aware issue
assignee: user
reporter: admin
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

    expect(snapshot.project.statuses, ['To Do', 'Done']);
    expect(snapshot.project.issueTypes, ['Epic', 'Story']);
    expect(snapshot.project.fields, ['Summary', 'Priority']);
  });
}

http.Response _contentResponse(String content) {
  final encoded = base64Encode(utf8.encode(content));
  return http.Response('{"content":"$encoded","sha":"abc123"}', 200);
}
