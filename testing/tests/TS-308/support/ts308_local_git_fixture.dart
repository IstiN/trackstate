import 'dart:io';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts308LocalGitFixture {
  Ts308LocalGitFixture._(this._repositoryFixture);

  static const issueKey = 'PROJECT-1';
  static const issueSummary =
      'Local Git comment persistence preserves Jira markup';
  static const issuePath = 'PROJECT/PROJECT-1/main.md';
  static const firstCommentPath = 'PROJECT/PROJECT-1/comments/0001.md';
  static const secondCommentPath = 'PROJECT/PROJECT-1/comments/0002.md';
  static const existingCommentAuthor = 'seeded-reviewer';
  static const existingCommentBody =
      'Existing repository comment visible before posting the new Jira-markup note.';
  static const postedCommentAuthor = 'ts308@example.com';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts308LocalGitFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-308 Tester',
      userEmail: postedCommentAuthor,
    );
    final fixture = Ts308LocalGitFixture._(repositoryFixture);
    await fixture._seedProjectRepository();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<String> headRevision() => _gitOutput(['rev-parse', 'HEAD']);

  Future<String> parentOfHead() => _gitOutput(['rev-parse', 'HEAD^']);

  Future<String> latestCommitSubject() =>
      _gitOutput(['log', '-1', '--pretty=%s']);

  Future<List<String>> latestCommitFiles() async {
    final output = await _gitOutput([
      'show',
      '--name-only',
      '--format=',
      'HEAD',
    ]);
    return output
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }

  Future<List<String>> worktreeStatusLines() async {
    final output = await _gitOutput(['status', '--short']);
    return output
        .split('\n')
        .map((line) => line.trimRight())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }

  Future<String> readRepositoryFile(String relativePath) =>
      File('$repositoryPath/$relativePath').readAsString();

  Future<bool> repositoryPathExists(String relativePath) =>
      File('$repositoryPath/$relativePath').exists();

  Future<void> _seedProjectRepository() async {
    final demoDirectory = Directory('${repositoryPath}/DEMO');
    if (await demoDirectory.exists()) {
      await demoDirectory.delete(recursive: true);
    }

    await _repositoryFixture.writeFile(
      'PROJECT/project.json',
      '{"key":"PROJECT","name":"Project comment persistence"}\n',
    );
    await _repositoryFixture.writeFile(
      'PROJECT/config/statuses.json',
      '[{"id":"todo","name":"To Do"},{"id":"in-progress","name":"In Progress"},{"id":"done","name":"Done"}]\n',
    );
    await _repositoryFixture.writeFile(
      'PROJECT/config/issue-types.json',
      '[{"id":"story","name":"Story"}]\n',
    );
    await _repositoryFixture.writeFile(
      'PROJECT/config/fields.json',
      '[{"id":"summary","name":"Summary","type":"string","required":true},{"id":"priority","name":"Priority","type":"option","required":false}]\n',
    );
    await _repositoryFixture.writeFile(
      'PROJECT/config/priorities.json',
      '[{"id":"high","name":"High"},{"id":"medium","name":"Medium"}]\n',
    );
    await _repositoryFixture.writeFile(issuePath, '''
---
key: $issueKey
project: PROJECT
issueType: story
status: in-progress
priority: high
summary: "$issueSummary"
assignee: ts308-user
reporter: ts308-user
updated: 2026-05-11T00:00:00Z
---

# Description

Track whether Local Git saves posted comments as sequential markdown side-car
files.
''');
    await _repositoryFixture.writeFile(firstCommentPath, '''
---
author: $existingCommentAuthor
created: 2026-05-11T00:05:00Z
updated: 2026-05-11T00:05:00Z
---

$existingCommentBody
''');

    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-308 Local Git fixture');
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString().trim();
  }
}
