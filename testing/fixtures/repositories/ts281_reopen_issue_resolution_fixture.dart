import 'dart:convert';
import 'dart:io';

class Ts281ReopenIssueResolutionFixture {
  Ts281ReopenIssueResolutionFixture._(this.directory);

  static const projectKey = 'TRACK';
  static const issueKey = 'TRACK-122';
  static const issuePath = '$projectKey/$issueKey/main.md';
  static const issueSummary = 'Closed issue can be reopened cleanly';
  static const doneStatusId = 'done';
  static const reopenedStatusId = 'to-do';
  static const reopenedStatusLabel = 'To Do';
  static const resolutionId = 'fixed';
  static const initialUpdatedAt = '2026-05-10T22:00:00Z';

  final Directory directory;

  String get repositoryPath => directory.path;

  static Future<Ts281ReopenIssueResolutionFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-281-',
    );
    final fixture = Ts281ReopenIssueResolutionFixture._(directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts281PersistedRepositoryObservation>
  observePersistedRepositoryState() async {
    return Ts281PersistedRepositoryObservation(
      issueMarkdown: await File('$repositoryPath/$issuePath').readAsString(),
      issueFileRevision: await _gitOutput(['rev-parse', 'HEAD:$issuePath']),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
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
      '{"key":"$projectKey","name":"TrackState TS-281"}\n',
    );
    await _writeFile(
      '$projectKey/config/statuses.json',
      '${jsonEncode([
        {'id': reopenedStatusId, 'name': reopenedStatusLabel},
        {'id': 'in-progress', 'name': 'In Progress'},
        {'id': doneStatusId, 'name': 'Done'},
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
      '$projectKey/config/resolutions.json',
      '${jsonEncode([
        {'id': resolutionId, 'name': 'Fixed'},
        {'id': 'wont-fix', 'name': 'Won\'t Fix'},
      ])}\n',
    );
    await _writeFile(
      '$projectKey/config/workflows.json',
      '${jsonEncode({
        'default': {
          'statuses': [reopenedStatusLabel, 'In Progress', 'Done'],
          'transitions': [
            {'id': 'start', 'name': 'Start work', 'from': reopenedStatusLabel, 'to': 'In Progress'},
            {'id': 'complete', 'name': 'Complete', 'from': 'In Progress', 'to': 'Done'},
            {'id': 'reopen', 'name': 'Reopen', 'from': 'Done', 'to': reopenedStatusLabel},
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
status: $doneStatusId
summary: "$issueSummary"
assignee: ts281-user
reporter: ts281-user
updated: $initialUpdatedAt
resolution: $resolutionId
---

# Summary

$issueSummary

# Description

This issue starts in Done with a Fixed resolution so TS-281 can verify reopening clears the resolution.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'TS-281 Tester']);
    await _git(['config', '--local', 'user.email', 'ts281@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed TS-281 reopen issue fixture']);
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

class Ts281PersistedRepositoryObservation {
  const Ts281PersistedRepositoryObservation({
    required this.issueMarkdown,
    required this.issueFileRevision,
    required this.headRevision,
    required this.worktreeStatusLines,
  });

  final String issueMarkdown;
  final String issueFileRevision;
  final String headRevision;
  final List<String> worktreeStatusLines;
}
