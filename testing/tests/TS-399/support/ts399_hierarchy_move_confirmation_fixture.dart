import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts399HierarchyMoveConfirmationFixture {
  Ts399HierarchyMoveConfirmationFixture._(this._repositoryFixture);

  static const epic1Key = 'EPIC-1';
  static const epic1Summary = 'Epic-1 platform rollout';
  static const epic2Key = 'EPIC-2';
  static const epic2Summary = 'Epic-2 mobile refresh';
  static const storyAKey = 'STORY-A';
  static const storyASummary = 'Story-A hierarchy move candidate';
  static const subtask1Key = 'SUBTASK-1';
  static const subtask1Summary = 'Subtask-1 stays with Story-A';
  static const subtask2Key = 'SUBTASK-2';
  static const subtask2Summary = 'Subtask-2 stays with Story-A';
  static const subtask3Key = 'SUBTASK-3';
  static const subtask3Summary = 'Subtask-3 stays with Story-A';
  static const epic1OptionLabel = '$epic1Key · $epic1Summary';
  static const epic2OptionLabel = '$epic2Key · $epic2Summary';
  static const oldStoryPath = 'DEMO/$epic1Key/$storyAKey/main.md';
  static const newStoryPath = 'DEMO/$epic2Key/$storyAKey/main.md';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts399HierarchyMoveConfirmationFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-399 Tester',
      userEmail: 'ts399@example.com',
    );
    final fixture = Ts399HierarchyMoveConfirmationFixture._(repositoryFixture);
    await fixture._seedHierarchyRepository();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<Ts399HierarchyObservation> observeHierarchy() async {
    final snapshot = await LocalTrackStateRepository(
      repositoryPath: repositoryPath,
    ).loadSnapshot();
    final story = snapshot.issues.singleWhere(
      (issue) => issue.key == storyAKey,
    );
    final storyRoot = _issueRoot(story.storagePath);
    final descendants =
        snapshot.issues
            .where(
              (issue) =>
                  issue.key != story.key &&
                  issue.storagePath.startsWith('$storyRoot/'),
            )
            .map((issue) => issue.key)
            .toList(growable: false)
          ..sort();

    return Ts399HierarchyObservation(
      headRevision: await _gitSingleLine(['rev-parse', 'HEAD']),
      storyStoragePath: story.storagePath,
      storyEpicKey: story.epicKey,
      descendantKeys: descendants,
    );
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
assignee: ts399-owner
reporter: ts399-owner
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
assignee: ts399-owner
reporter: ts399-owner
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
assignee: ts399-owner
reporter: ts399-owner
epic: $epic1Key
updated: 2026-05-11T00:02:00Z
---

# Description

Story-A starts in Epic-1 and owns three sub-tasks that should move together.
''');
    await _repositoryFixture.writeFile(
      'DEMO/EPIC-1/STORY-A/$subtask1Key/main.md',
      '''
---
key: $subtask1Key
project: DEMO
issueType: subtask
status: todo
priority: medium
summary: "$subtask1Summary"
assignee: ts399-owner
reporter: ts399-owner
parent: $storyAKey
epic: $epic1Key
updated: 2026-05-11T00:03:00Z
---

# Description

$subtask1Summary
''',
    );
    await _repositoryFixture.writeFile(
      'DEMO/EPIC-1/STORY-A/$subtask2Key/main.md',
      '''
---
key: $subtask2Key
project: DEMO
issueType: subtask
status: in-progress
priority: medium
summary: "$subtask2Summary"
assignee: ts399-owner
reporter: ts399-owner
parent: $storyAKey
epic: $epic1Key
updated: 2026-05-11T00:04:00Z
---

# Description

$subtask2Summary
''',
    );
    await _repositoryFixture.writeFile(
      'DEMO/EPIC-1/STORY-A/$subtask3Key/main.md',
      '''
---
key: $subtask3Key
project: DEMO
issueType: subtask
status: done
priority: medium
summary: "$subtask3Summary"
assignee: ts399-owner
reporter: ts399-owner
parent: $storyAKey
epic: $epic1Key
updated: 2026-05-11T00:05:00Z
---

# Description

$subtask3Summary
''',
    );
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit(
      'Seed TS-399 hierarchy move confirmation fixture',
    );
  }

  Future<String> _gitSingleLine(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    final output = result.stdout.toString().trim();
    if (output.isEmpty) {
      throw StateError('git ${args.join(' ')} returned no output.');
    }
    return output.split('\n').first.trim();
  }

  String _issueRoot(String issuePath) =>
      issuePath.substring(0, issuePath.lastIndexOf('/'));
}

class Ts399HierarchyObservation {
  const Ts399HierarchyObservation({
    required this.headRevision,
    required this.storyStoragePath,
    required this.storyEpicKey,
    required this.descendantKeys,
  });

  final String headRevision;
  final String storyStoragePath;
  final String? storyEpicKey;
  final List<String> descendantKeys;
}
