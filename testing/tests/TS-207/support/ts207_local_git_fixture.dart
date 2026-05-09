import 'dart:convert';
import 'dart:io';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts207LocalGitFixture {
  Ts207LocalGitFixture._(this._repositoryFixture);

  static const existingIssueKey = 'DEMO-1';
  static const existingIssueSummary = 'Local issue with resettable create form';
  static const createdIssueKey = 'DEMO-2';
  static const createdIssuePath = 'DEMO/DEMO-2/main.md';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts207LocalGitFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-207 Tester',
      userEmail: 'ts207@example.com',
    );
    final fixture = Ts207LocalGitFixture._(repositoryFixture);
    await fixture._seedProjectConfiguration();
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

  Future<void> _seedProjectConfiguration() async {
    await _repositoryFixture.writeFile(
      'DEMO/config/statuses.json',
      '${jsonEncode([
        {'id': 'todo', 'name': 'To Do'},
        {'id': 'in-progress', 'name': 'In Progress'},
        {'id': 'done', 'name': 'Done'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/issue-types.json',
      '${jsonEncode([
        {'id': 'story', 'name': 'Story'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/fields.json',
      '${jsonEncode([
        {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
        {'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
        {'id': 'solution', 'name': 'Solution', 'type': 'markdown', 'required': false},
        {'id': 'acceptanceCriteria', 'name': 'Acceptance Criteria', 'type': 'markdown', 'required': false},
      ])}\n',
    );
    await _repositoryFixture.writeFile('DEMO/DEMO-1/main.md', '''
---
key: $existingIssueKey
project: DEMO
issueType: story
status: in-progress
summary: "$existingIssueSummary"
assignee: ts207-user
reporter: ts207-user
updated: 2026-05-09T00:00:00Z
---

# Description

Loaded from a Local Git fixture that declares resettable create-form fields.
''');
    await _repositoryFixture.writeFile(
      'DEMO/DEMO-1/acceptance_criteria.md',
      '# Acceptance Criteria\n\n- Existing issue stays searchable in Local Git mode.\n',
    );
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-207 Local Git fixture');
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString().trim();
  }
}
