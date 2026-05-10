import 'dart:io';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts239LocalGitFixture {
  Ts239LocalGitFixture._(this._repositoryFixture);

  static const configDirectoryPath = 'DEMO/config';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts239LocalGitFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-239 Tester',
      userEmail: 'ts239@example.com',
    );
    final fixture = Ts239LocalGitFixture._(repositoryFixture);
    await fixture._seedMissingConfigDirectory();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<bool> configDirectoryExists() =>
      Directory('$repositoryPath/$configDirectoryPath').exists();

  Future<List<String>> worktreeStatusLines() async {
    final output = await _gitOutput(['status', '--short']);
    return output
        .split('\n')
        .map((line) => line.trimRight())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }

  Future<void> _seedMissingConfigDirectory() async {
    final configDirectory = Directory('$repositoryPath/$configDirectoryPath');
    if (await configDirectory.exists()) {
      await configDirectory.delete(recursive: true);
    }

    await _repositoryFixture.writeFile('DEMO/DEMO-1/main.md', '''
---
key: DEMO-1
project: DEMO
issueType: story
status: todo
summary: "Missing config directory fallback coverage"
assignee: ts239-user
reporter: ts239-user
updated: 2026-05-09T00:00:00Z
---

# Description

Existing Local Git issue used to launch the app before opening Create issue.
''');
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit(
      'Seed TS-239 missing config directory fixture',
    );
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString().trim();
  }
}
