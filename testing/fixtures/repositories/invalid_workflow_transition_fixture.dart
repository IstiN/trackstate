import 'dart:convert';
import 'dart:io';

class InvalidWorkflowTransitionScenario {
  const InvalidWorkflowTransitionScenario({
    required this.tempDirectoryPrefix,
    required this.projectName,
    required this.issueKey,
    required this.issueSummary,
    required this.assignee,
    required this.reporter,
    required this.seedAuthorName,
    required this.seedAuthorEmail,
    required this.seedCommitSubject,
    this.projectKey = 'TRACK',
    this.issueDescription =
        'Workflow validation must reject a direct move from To Do to Done.',
    this.todoStatusId = 'todo',
    this.todoStatusLabel = 'To Do',
    this.inProgressStatusId = 'in-progress',
    this.inProgressStatusLabel = 'In Progress',
    this.doneStatusId = 'done',
    this.doneStatusLabel = 'Done',
    this.updatedTimestamp = '2026-05-13T00:00:00Z',
  });

  final String tempDirectoryPrefix;
  final String projectKey;
  final String projectName;
  final String issueKey;
  final String issueSummary;
  final String issueDescription;
  final String assignee;
  final String reporter;
  final String seedAuthorName;
  final String seedAuthorEmail;
  final String seedCommitSubject;
  final String todoStatusId;
  final String todoStatusLabel;
  final String inProgressStatusId;
  final String inProgressStatusLabel;
  final String doneStatusId;
  final String doneStatusLabel;
  final String updatedTimestamp;

  String get issuePath => '$projectKey/$issueKey/main.md';
  String get workflowsPath => '$projectKey/config/workflows.json';
  String get expectedFailureMessage =>
      'Workflow does not allow moving $issueKey from $todoStatusId to $doneStatusId.';
}

class InvalidWorkflowTransitionFixture {
  InvalidWorkflowTransitionFixture._(this.directory, this.scenario);

  final Directory directory;
  final InvalidWorkflowTransitionScenario scenario;

  String get repositoryPath => directory.path;

  static Future<InvalidWorkflowTransitionFixture> create(
    InvalidWorkflowTransitionScenario scenario,
  ) async {
    final directory = await Directory.systemTemp.createTemp(
      scenario.tempDirectoryPrefix,
    );
    final fixture = InvalidWorkflowTransitionFixture._(directory, scenario);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<PersistedRepositoryObservation>
  observePersistedRepositoryState() async {
    return PersistedRepositoryObservation(
      workflowJson: await File(
        '$repositoryPath/${scenario.workflowsPath}',
      ).readAsString(),
      issueMarkdown: await File(
        '$repositoryPath/${scenario.issuePath}',
      ).readAsString(),
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
      '${scenario.projectKey}/project.json',
      '{"key":"${scenario.projectKey}","name":"${scenario.projectName}"}\n',
    );
    await _writeFile(
      '${scenario.projectKey}/config/statuses.json',
      '${jsonEncode([
        {'id': scenario.todoStatusId, 'name': scenario.todoStatusLabel},
        {'id': scenario.inProgressStatusId, 'name': scenario.inProgressStatusLabel},
        {'id': scenario.doneStatusId, 'name': scenario.doneStatusLabel},
      ])}\n',
    );
    await _writeFile(
      '${scenario.projectKey}/config/issue-types.json',
      '${jsonEncode([
        {'id': 'story', 'name': 'Story'},
      ])}\n',
    );
    await _writeFile(
      '${scenario.projectKey}/config/fields.json',
      '${jsonEncode([
        {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
        {'id': 'description', 'name': 'Description', 'type': 'markdown'},
      ])}\n',
    );
    await _writeFile(
      '${scenario.projectKey}/config/priorities.json',
      '${jsonEncode([
        {'id': 'medium', 'name': 'Medium'},
      ])}\n',
    );
    await _writeFile('${scenario.projectKey}/config/resolutions.json', '[]\n');
    await _writeFile(
      scenario.workflowsPath,
      '${jsonEncode({
        'default': {
          'statuses': [scenario.todoStatusLabel, scenario.inProgressStatusLabel, scenario.doneStatusLabel],
          'transitions': [
            {'id': 'start', 'name': 'Start work', 'from': scenario.todoStatusLabel, 'to': scenario.inProgressStatusLabel},
            {'id': 'complete', 'name': 'Complete', 'from': scenario.inProgressStatusLabel, 'to': scenario.doneStatusLabel},
          ],
        },
      })}\n',
    );
    await _writeFile(
      '${scenario.projectKey}/.trackstate/index/issues.json',
      '${jsonEncode([
        {'key': scenario.issueKey, 'path': scenario.issuePath, 'parent': null, 'epic': null, 'children': <String>[], 'archived': false},
      ])}\n',
    );
    await _writeFile(
      '${scenario.projectKey}/.trackstate/index/tombstones.json',
      '[]\n',
    );
    await _writeFile(scenario.issuePath, '''
---
key: ${scenario.issueKey}
project: ${scenario.projectKey}
issueType: story
status: ${scenario.todoStatusId}
priority: medium
summary: "${scenario.issueSummary}"
assignee: ${scenario.assignee}
reporter: ${scenario.reporter}
updated: ${scenario.updatedTimestamp}
---

# Summary

${scenario.issueSummary}

# Description

${scenario.issueDescription}
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', scenario.seedAuthorName]);
    await _git(['config', '--local', 'user.email', scenario.seedAuthorEmail]);
    await _git(['add', '.']);
    await _git(['commit', '-m', scenario.seedCommitSubject]);
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

class PersistedRepositoryObservation {
  const PersistedRepositoryObservation({
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
