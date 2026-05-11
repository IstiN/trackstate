import 'dart:convert';
import 'dart:io';

class Ts302HierarchyPrefillFixture {
  Ts302HierarchyPrefillFixture._(this.directory);

  static const projectKey = 'TRACK';
  static const epicKey = 'TRACK-1';
  static const epicSummary = 'Hierarchy parent epic';
  static const storyKey = 'TRACK-2';
  static const storySummary = 'Hierarchy child story';
  static const epicPath = '$projectKey/$epicKey/main.md';
  static const storyPath = '$projectKey/$epicKey/$storyKey/main.md';

  final Directory directory;

  String get repositoryPath => directory.path;

  static Future<Ts302HierarchyPrefillFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-302-',
    );
    final fixture = Ts302HierarchyPrefillFixture._(directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<void> _seedRepository() async {
    for (final entry in _fixtureFiles().entries) {
      await _writeFile(entry.key, entry.value);
    }

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed TS-302 hierarchy prefill fixture']);
  }

  Map<String, String> _fixtureFiles() => {
    '$projectKey/project.json': jsonEncode({
      'key': projectKey,
      'name': 'Hierarchy prefill demo',
    }),
    '$projectKey/config/statuses.json':
        '${jsonEncode([
          {'id': 'todo', 'name': 'To Do'},
          {'id': 'in-progress', 'name': 'In Progress'},
          {'id': 'done', 'name': 'Done'},
        ])}\n',
    '$projectKey/config/issue-types.json':
        '${jsonEncode([
          {'id': 'epic', 'name': 'Epic'},
          {'id': 'story', 'name': 'Story'},
          {'id': 'subtask', 'name': 'Sub-task'},
        ])}\n',
    '$projectKey/config/fields.json':
        '${jsonEncode([
          {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
          {'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
          {'id': 'epic', 'name': 'Epic', 'type': 'string', 'required': false},
          {'id': 'parent', 'name': 'Parent', 'type': 'string', 'required': false},
        ])}\n',
    '$projectKey/config/priorities.json':
        '${jsonEncode([
          {'id': 'medium', 'name': 'Medium'},
          {'id': 'high', 'name': 'High'},
        ])}\n',
    '$projectKey/config/resolutions.json': '[]\n',
    '$projectKey/config/workflows.json':
        '${jsonEncode({
          'default': {
            'statuses': ['To Do', 'In Progress', 'Done'],
            'transitions': [
              {'id': 'start', 'name': 'Start work', 'from': 'To Do', 'to': 'In Progress'},
              {'id': 'complete', 'name': 'Complete', 'from': 'In Progress', 'to': 'Done'},
            ],
          },
        })}\n',
    '$projectKey/.trackstate/index/issues.json':
        '${jsonEncode([
          {
            'key': epicKey,
            'path': epicPath,
            'parent': null,
            'epic': null,
            'children': [storyKey],
            'archived': false,
          },
          {'key': storyKey, 'path': storyPath, 'parent': null, 'epic': epicKey, 'children': <String>[], 'archived': false},
        ])}\n',
    '$projectKey/.trackstate/index/tombstones.json': '[]\n',
    epicPath:
        '''
---
key: $epicKey
project: $projectKey
issueType: epic
status: in-progress
priority: high
summary: $epicSummary
assignee: qa-owner
reporter: qa-owner
updated: 2026-05-11T00:00:00Z
---

# Summary

$epicSummary

# Description

Top-level hierarchy parent used for contextual child creation.
''',
    storyPath:
        '''
---
key: $storyKey
project: $projectKey
issueType: story
status: todo
priority: medium
summary: $storySummary
assignee: qa-owner
reporter: qa-owner
epic: $epicKey
updated: 2026-05-11T00:01:00Z
---

# Summary

$storySummary

# Description

Nested story used to verify sub-task prefills from the Hierarchy view.
''',
  };

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('${directory.path}/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', ['-C', directory.path, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }
}
