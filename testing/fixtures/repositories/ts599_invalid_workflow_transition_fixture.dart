import 'dart:convert';
import 'dart:io';

class Ts599InvalidWorkflowTransitionFixture {
  Ts599InvalidWorkflowTransitionFixture._(this.directory);

  static const projectKey = 'TRACK';
  static const issueKey = 'TRACK-599';
  static const issuePath = '$projectKey/$issueKey/main.md';
  static const workflowsPath = '$projectKey/config/workflows.json';
  static const issueSummary = 'Block direct To Do to Done transitions';
  static const issueDescription =
      'Workflow validation must reject a direct move from To Do to Done.';
  static const todoStatusId = 'todo';
  static const todoStatusLabel = 'To Do';
  static const inProgressStatusId = 'in-progress';
  static const inProgressStatusLabel = 'In Progress';
  static const doneStatusId = 'done';
  static const doneStatusLabel = 'Done';
  static const expectedFailureMessage =
      'Workflow does not allow moving $issueKey from $todoStatusId to $doneStatusId.';

  final Directory directory;

  String get repositoryPath => directory.path;

  static Future<Ts599InvalidWorkflowTransitionFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-599-',
    );
    final fixture = Ts599InvalidWorkflowTransitionFixture._(directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts599PersistedRepositoryObservation>
  observePersistedRepositoryState() async {
    return Ts599PersistedRepositoryObservation(
      workflowJson: await File('$repositoryPath/$workflowsPath').readAsString(),
      issueMarkdown: await File('$repositoryPath/$issuePath').readAsString(),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      latestCommitSubject: await _gitOutput(['log', '-1', '--pretty=%s']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
    );
  }

  Future<void> _seedRepository() async {
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      '$projectKey/project.json',
      '{"key":"$projectKey","name":"TrackState TS-599"}\n',
    );
    await _writeFile(
      '$projectKey/config/statuses.json',
      '${jsonEncode([
        {'id': todoStatusId, 'name': todoStatusLabel},
        {'id': inProgressStatusId, 'name': inProgressStatusLabel},
        {'id': doneStatusId, 'name': doneStatusLabel},
      ])}\n',
    );
    await _writeFile(
      '$projectKey/config/issue-types.json',
      '${jsonEncode([
        {'id': 'story', 'name': 'Story'},
      ])}\n',
    );
    await _writeFile(
      '$projectKey/config/fields.json',
      '${jsonEncode([
        {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
        {'id': 'description', 'name': 'Description', 'type': 'markdown'},
      ])}\n',
    );
    await _writeFile(
      '$projectKey/config/priorities.json',
      '${jsonEncode([
        {'id': 'medium', 'name': 'Medium'},
      ])}\n',
    );
    await _writeFile('$projectKey/config/resolutions.json', '[]\n');
    await _writeFile(
      workflowsPath,
      '${jsonEncode({
        'default': {
          'statuses': [todoStatusLabel, inProgressStatusLabel, doneStatusLabel],
          'transitions': [
            {'id': 'start', 'name': 'Start work', 'from': todoStatusLabel, 'to': inProgressStatusLabel},
            {'id': 'complete', 'name': 'Complete', 'from': inProgressStatusLabel, 'to': doneStatusLabel},
          ],
        },
      })}\n',
    );
    await _writeFile(
      '$projectKey/.trackstate/index/issues.json',
      '${jsonEncode([
        {'key': issueKey, 'path': issuePath, 'parent': null, 'epic': null, 'children': <String>[], 'archived': false},
      ])}\n',
    );
    await _writeFile('$projectKey/.trackstate/index/tombstones.json', '[]\n');
    await _writeFile(issuePath, '''
---
key: $issueKey
project: $projectKey
issueType: story
status: $todoStatusId
priority: medium
summary: "$issueSummary"
assignee: ts599-user
reporter: ts599-user
updated: 2026-05-13T00:00:00Z
---

# Summary

$issueSummary

# Description

$issueDescription
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'TS-599 Tester']);
    await _git(['config', '--local', 'user.email', 'ts599@example.com']);
    await _git(['add', '.']);
    await _git([
      'commit',
      '-m',
      'Seed TS-599 invalid workflow transition fixture',
    ]);
  }

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('$repositoryPath/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return (result.stdout as String).trim();
  }

  Future<List<String>> _gitOutputLines(List<String> args) async {
    final output = await _gitOutput(args);
    if (output.isEmpty) {
      return const [];
    }
    return output
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }
}

class Ts599PersistedRepositoryObservation {
  const Ts599PersistedRepositoryObservation({
    required this.workflowJson,
    required this.issueMarkdown,
    required this.headRevision,
    required this.latestCommitSubject,
    required this.worktreeStatusLines,
  });

  final String workflowJson;
  final String issueMarkdown;
  final String headRevision;
  final String latestCommitSubject;
  final List<String> worktreeStatusLines;
}
