import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts400SubtaskEditHierarchyFixture {
  Ts400SubtaskEditHierarchyFixture._(this._repositoryFixture);

  static const epic1Key = 'EPIC-1';
  static const epic1Summary = 'Epic-1 platform rollout';
  static const epic2Key = 'EPIC-2';
  static const epic2Summary = 'Epic-2 mobile refresh';
  static const storyAKey = 'STORY-A';
  static const storyASummary = 'Story-A parent in Epic-1';
  static const storyBKey = 'STORY-B';
  static const storyBSummary = 'Story-B parent in Epic-2';
  static const subtaskKey = 'SUBTASK-1';
  static const subtaskSummary = 'Subtask-1 inherits epic from parent';
  static const subtaskDescription =
      'Initial sub-task state should derive Epic-1 from Story-A.';
  static const epic1OptionLabel = '$epic1Key · $epic1Summary';
  static const epic2OptionLabel = '$epic2Key · $epic2Summary';
  static const storyAOptionLabel = '$storyAKey · $storyASummary';
  static const storyBOptionLabel = '$storyBKey · $storyBSummary';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts400SubtaskEditHierarchyFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-400 Tester',
      userEmail: 'ts400@example.com',
    );
    final fixture = Ts400SubtaskEditHierarchyFixture._(repositoryFixture);
    await fixture._seedHierarchyRepository();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<TrackStateIssue> loadSubtask() async {
    final snapshot = await LocalTrackStateRepository(
      repositoryPath: repositoryPath,
    ).loadSnapshot();
    return snapshot.issues.singleWhere((issue) => issue.key == subtaskKey);
  }

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
    await _repositoryFixture.writeFile('DEMO/EPIC-1/main.md', '''
---
key: $epic1Key
project: DEMO
issueType: epic
status: in-progress
priority: high
summary: "$epic1Summary"
assignee: ts400-owner
reporter: ts400-owner
updated: 2026-05-11T00:00:00Z
---

# Description

$epic1Summary
''');
    await _repositoryFixture.writeFile('DEMO/EPIC-2/main.md', '''
---
key: $epic2Key
project: DEMO
issueType: epic
status: todo
priority: high
summary: "$epic2Summary"
assignee: ts400-owner
reporter: ts400-owner
updated: 2026-05-11T00:01:00Z
---

# Description

$epic2Summary
''');
    await _repositoryFixture.writeFile('DEMO/EPIC-1/STORY-A/main.md', '''
---
key: $storyAKey
project: DEMO
issueType: story
status: todo
priority: medium
summary: "$storyASummary"
assignee: ts400-owner
reporter: ts400-owner
epic: $epic1Key
updated: 2026-05-11T00:02:00Z
---

# Description

Story-A belongs to Epic-1 so the existing sub-task starts in Epic-1.
''');
    await _repositoryFixture.writeFile('DEMO/EPIC-2/STORY-B/main.md', '''
---
key: $storyBKey
project: DEMO
issueType: story
status: in-progress
priority: medium
summary: "$storyBSummary"
assignee: ts400-owner
reporter: ts400-owner
epic: $epic2Key
updated: 2026-05-11T00:03:00Z
---

# Description

Story-B belongs to Epic-2 so re-parenting the sub-task should re-derive Epic-2.
''');
    await _repositoryFixture.writeFile(
      'DEMO/EPIC-1/STORY-A/SUBTASK-1/main.md',
      '''
---
key: $subtaskKey
project: DEMO
issueType: subtask
status: todo
priority: medium
summary: "$subtaskSummary"
assignee: ts400-owner
reporter: ts400-owner
parent: $storyAKey
epic: $epic1Key
updated: 2026-05-11T00:04:00Z
---

# Description

$subtaskDescription
''',
    );
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit(
      'Seed TS-400 subtask edit hierarchy fixture',
    );
  }
}
