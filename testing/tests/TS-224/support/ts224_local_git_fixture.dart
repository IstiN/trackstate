import 'dart:io';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts224LocalGitFixture {
  Ts224LocalGitFixture._(this._repositoryFixture);

  static const existingIssueKey = 'DEMO-1';
  static const existingIssueSummary = 'Malformed fields fallback coverage';
  static const createdIssueKey = 'DEMO-2';
  static const createdIssuePath = 'DEMO/DEMO-2/main.md';
  static const malformedFieldsJson = '''
[
  {"id":"summary","name":"Summary","type":"string","required":true}
  {"id":"description","name":"Description","type":"markdown","required":false}
]
''';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts224LocalGitFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-224 Tester',
      userEmail: 'ts224@example.com',
    );
    final fixture = Ts224LocalGitFixture._(repositoryFixture);
    await fixture._seedMalformedFieldsConfiguration();
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

  Future<void> _seedMalformedFieldsConfiguration() async {
    await _repositoryFixture.writeFile('DEMO/config/statuses.json', '''
[
  {"id":"todo","name":"To Do"},
  {"id":"in-progress","name":"In Progress"},
  {"id":"done","name":"Done"}
]
''');
    await _repositoryFixture.writeFile('DEMO/config/issue-types.json', '''
[
  {"id":"story","name":"Story"}
]
''');
    await _repositoryFixture.writeFile(
      'DEMO/config/fields.json',
      malformedFieldsJson,
    );
    await _repositoryFixture.writeFile('DEMO/DEMO-1/main.md', '''
---
key: $existingIssueKey
project: DEMO
issueType: story
status: todo
summary: "$existingIssueSummary"
assignee: ts224-user
reporter: ts224-user
updated: 2026-05-09T00:00:00Z
---

# Description

Existing Local Git issue used to launch the app before saving a fallback-mode issue.
''');
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-224 malformed fields fixture');
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString().trim();
  }
}
