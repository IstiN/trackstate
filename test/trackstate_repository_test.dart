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

  test('setup repository loads markdown issues from generated index', () async {
    final repository = SetupTrackStateRepository(
      client: MockClient((request) async {
        final path = request.url.path;
        if (path.endsWith('/trackstate-data/index.json')) {
          return http.Response('{"issues":["DEMO/DEMO-1/main.md"]}', 200);
        }
        if (path.endsWith('/trackstate-data/DEMO/project.json')) {
          return http.Response('{"key":"DEMO","name":"Demo Project"}', 200);
        }
        if (path.endsWith('/trackstate-data/DEMO/config/statuses.json')) {
          return http.Response('[{"name":"To Do"},{"name":"Done"}]', 200);
        }
        if (path.endsWith('/trackstate-data/DEMO/config/issue-types.json')) {
          return http.Response('[{"name":"Epic"},{"name":"Story"}]', 200);
        }
        if (path.endsWith('/trackstate-data/DEMO/config/fields.json')) {
          return http.Response('[{"name":"Summary"},{"name":"Priority"}]', 200);
        }
        if (path.endsWith('/trackstate-data/DEMO/DEMO-1/main.md')) {
          return http.Response('''
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
''', 200);
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
  });
}
