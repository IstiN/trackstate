import '../../../core/utils/local_git_repository_fixture.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';

class Ts303IssueHierarchyFixture {
  Ts303IssueHierarchyFixture._(this._repositoryFixture);

  static const epicKey = 'DEMO-100';
  static const epicSummary = 'Product launch epic';
  static const parentKey = 'DEMO-101';
  static const parentSummary = 'Story under epic';
  static const parentOptionLabel = '$parentKey · $parentSummary';
  static const derivedEpicLabel = '$epicKey · $epicSummary';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts303IssueHierarchyFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-303 Tester',
      userEmail: 'ts303@example.com',
    );
    final fixture = Ts303IssueHierarchyFixture._(repositoryFixture);
    await fixture._seedHierarchyRepository();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<List<String>> describeIssues() async {
    final snapshot = await LocalTrackStateRepository(
      repositoryPath: repositoryPath,
    ).loadSnapshot();
    return snapshot.issues
        .map(
          (issue) =>
              '${issue.key}:${issue.issueTypeId}:${issue.parentKey ?? 'null'}:${issue.epicKey ?? 'null'}:${issue.summary}',
        )
        .toList(growable: false)
      ..sort();
  }

  Future<void> _seedHierarchyRepository() async {
    await _repositoryFixture.writeFile('DEMO/config/statuses.json', '''
[
  {"id":"todo","name":"To Do"},
  {"id":"in-progress","name":"In Progress"},
  {"id":"done","name":"Done"}
]
''');
    await _repositoryFixture.writeFile('DEMO/config/issue-types.json', '''
[
  {"id":"epic","name":"Epic"},
  {"id":"story","name":"Story"},
  {"id":"subtask","name":"Sub-task"}
]
''');
    await _repositoryFixture.writeFile('DEMO/config/priorities.json', '''
[
  {"id":"medium","name":"Medium"},
  {"id":"high","name":"High"}
]
''');
    await _repositoryFixture.writeFile('DEMO/config/fields.json', '''
[
  {"id":"summary","name":"Summary","type":"string","required":true},
  {"id":"description","name":"Description","type":"markdown","required":false},
  {"id":"priority","name":"Priority","type":"enum","required":false},
  {"id":"parent","name":"Parent","type":"relation","required":false},
  {"id":"epic","name":"Epic","type":"relation","required":false}
]
''');
    await _repositoryFixture.writeFile('DEMO/DEMO-100/main.md', '''
---
key: $epicKey
project: DEMO
issueType: epic
status: in-progress
priority: high
summary: "$epicSummary"
assignee: ts303-owner
reporter: ts303-owner
updated: 2026-05-11T00:00:00Z
---

# Description

Epic used to validate create-issue hierarchy rules.
''');
    await _repositoryFixture.writeFile('DEMO/DEMO-101/main.md', '''
---
key: $parentKey
project: DEMO
issueType: story
status: todo
priority: medium
summary: "$parentSummary"
assignee: ts303-owner
reporter: ts303-owner
epic: $epicKey
updated: 2026-05-11T00:05:00Z
---

# Description

Story linked to the epic so Sub-task creation can derive Epic automatically.
''');
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-303 hierarchy fixture');
  }
}
