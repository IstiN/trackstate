import 'dart:convert';
import 'dart:io';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts405LocalGitFixture {
  Ts405LocalGitFixture._(this._repositoryFixture);

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts405LocalGitFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-405 Tester',
      userEmail: 'ts405@example.com',
    );
    final fixture = Ts405LocalGitFixture._(repositoryFixture);
    await fixture._seedProjectConfiguration();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<String> headRevision() => _gitOutput(['rev-parse', 'HEAD']);

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
        {'id': 'todo', 'name': 'To Do', 'category': 'new'},
        {'id': 'in-progress', 'name': 'In Progress', 'category': 'indeterminate'},
        {'id': 'done', 'name': 'Done', 'category': 'done'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/workflows.json',
      '${jsonEncode({
        'default': {
          'name': 'Default Workflow',
          'statuses': ['todo', 'in-progress', 'done'],
          'transitions': [
            {'id': 'start-progress', 'name': 'Start progress', 'from': 'todo', 'to': 'in-progress'},
            {'id': 'finish-work', 'name': 'Finish work', 'from': 'in-progress', 'to': 'done'},
          ],
        },
      })}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/issue-types.json',
      '${jsonEncode([
        {'id': 'story', 'name': 'Story', 'workflowId': 'default', 'hierarchyLevel': 0},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/fields.json',
      '${jsonEncode([
        {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
        {'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
        {'id': 'acceptanceCriteria', 'name': 'Acceptance Criteria', 'type': 'markdown', 'required': false},
        {
          'id': 'priority',
          'name': 'Priority',
          'type': 'option',
          'required': false,
          'options': [
            {'id': 'high', 'name': 'High'},
            {'id': 'medium', 'name': 'Medium'},
          ],
        },
        {'id': 'assignee', 'name': 'Assignee', 'type': 'user', 'required': false},
        {'id': 'labels', 'name': 'Labels', 'type': 'array', 'required': false},
        {'id': 'storyPoints', 'name': 'Story Points', 'type': 'number', 'required': false},
      ])}\n',
    );
    await _repositoryFixture.writeFile('DEMO/DEMO-1/main.md', '''
---
key: DEMO-1
project: DEMO
issueType: story
status: in-progress
priority: high
summary: TS-405 baseline issue
assignee: ts405-user
reporter: ts405-user
updated: 2026-05-10T00:00:00Z
---

# Description

Baseline issue for TS-405 status validation coverage.
''');
    await _repositoryFixture.writeFile(
      'DEMO/DEMO-1/acceptance_criteria.md',
      '# Acceptance Criteria\n\n- Status settings validation blocks invalid writes.\n',
    );
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-405 Local Git fixture');
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString().trim();
  }
}
