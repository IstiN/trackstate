import 'dart:io';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts226LocalGitFixture {
  Ts226LocalGitFixture._(this._repositoryFixture);

  static const missingFieldsPath = 'DEMO/config/fields.json';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts226LocalGitFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-226 Tester',
      userEmail: 'ts226@example.com',
    );
    final fixture = Ts226LocalGitFixture._(repositoryFixture);
    await fixture._seedMissingFieldsConfiguration();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<bool> fieldsConfigExists() =>
      File('$repositoryPath/$missingFieldsPath').exists();

  Future<List<String>> worktreeStatusLines() async {
    final output = await _gitOutput(['status', '--short']);
    return output
        .split('\n')
        .map((line) => line.trimRight())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }

  Future<void> _seedMissingFieldsConfiguration() async {
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

    final fieldsFile = File('$repositoryPath/$missingFieldsPath');
    if (await fieldsFile.exists()) {
      await fieldsFile.delete();
    }

    await _repositoryFixture.writeFile('DEMO/DEMO-1/main.md', '''
---
key: DEMO-1
project: DEMO
issueType: story
status: todo
summary: "Missing fields fallback coverage"
assignee: ts226-user
reporter: ts226-user
updated: 2026-05-09T00:00:00Z
---

# Description

Existing Local Git issue used to launch the app before opening Create issue.
''');
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-226 missing fields fixture');
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString().trim();
  }
}
