import 'dart:io';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts208LocalGitFixture {
  Ts208LocalGitFixture._(this._repositoryFixture);

  static const malformedFieldsJson = '''
[
  {"id":"summary","name":"Summary","type":"string","required":true}
  {"id":"description","name":"Description","type":"markdown","required":false}
]
''';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts208LocalGitFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-208 Tester',
      userEmail: 'ts208@example.com',
    );
    final fixture = Ts208LocalGitFixture._(repositoryFixture);
    await fixture._seedMalformedFieldsConfiguration();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

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
key: DEMO-1
project: DEMO
issueType: story
status: todo
summary: "Malformed fields fallback coverage"
assignee: ts208-user
reporter: ts208-user
updated: 2026-05-09T00:00:00Z
---

# Description

Existing Local Git issue used to launch the app before opening Create issue.
''');
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-208 malformed fields fixture');
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString().trim();
  }
}
