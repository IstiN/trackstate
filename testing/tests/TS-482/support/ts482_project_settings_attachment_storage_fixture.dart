import 'dart:convert';
import 'dart:io';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts482ProjectSettingsAttachmentStorageFixture {
  Ts482ProjectSettingsAttachmentStorageFixture._(this._repositoryFixture);

  final LocalGitRepositoryFixture _repositoryFixture;

  static const String projectKey = 'DEMO';
  static const String projectJsonPath = '$projectKey/project.json';

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts482ProjectSettingsAttachmentStorageFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-482 Tester',
      userEmail: 'ts482@example.com',
    );
    final fixture = Ts482ProjectSettingsAttachmentStorageFixture._(
      repositoryFixture,
    );
    await fixture._seedRepository();
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

  Future<Map<String, Object?>> readProjectJson() async {
    final content = await File(
      '$repositoryPath/$projectJsonPath',
    ).readAsString();
    final decoded = jsonDecode(content);
    if (decoded is! Map) {
      throw StateError('Expected $projectJsonPath to decode to a JSON object.');
    }
    return decoded.cast<String, Object?>();
  }

  Future<void> _seedRepository() async {
    await _repositoryFixture.writeFile(
      projectJsonPath,
      '${jsonEncode({
        'key': projectKey,
        'name': 'Attachment storage defaults demo',
        'defaultLocale': 'en',
        'supportedLocales': ['en'],
        'issueKeyPattern': '$projectKey-{number}',
        'dataModel': 'nested-tree',
        'configPath': 'config',
      })}\n',
    );
    await _repositoryFixture.writeFile(
      '$projectKey/config/statuses.json',
      '${jsonEncode([
        {'id': 'todo', 'name': 'To Do', 'category': 'new'},
        {'id': 'in-progress', 'name': 'In Progress', 'category': 'indeterminate'},
        {'id': 'done', 'name': 'Done', 'category': 'done'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      '$projectKey/config/workflows.json',
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
      '$projectKey/config/issue-types.json',
      '${jsonEncode([
        {'id': 'story', 'name': 'Story', 'workflowId': 'default', 'hierarchyLevel': 0},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      '$projectKey/config/fields.json',
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
            {'id': 'medium', 'name': 'Medium'},
            {'id': 'high', 'name': 'High'},
          ],
        },
        {'id': 'assignee', 'name': 'Assignee', 'type': 'user', 'required': false},
        {'id': 'labels', 'name': 'Labels', 'type': 'array', 'required': false},
        {'id': 'storyPoints', 'name': 'Story Points', 'type': 'number', 'required': false},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      '$projectKey/config/priorities.json',
      '${jsonEncode([
        {'id': 'medium', 'name': 'Medium'},
        {'id': 'high', 'name': 'High'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      '$projectKey/config/components.json',
      '${jsonEncode([
        {'id': 'tracker-core', 'name': 'Tracker Core'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      '$projectKey/config/versions.json',
      '${jsonEncode([
        {'id': 'mvp', 'name': 'MVP'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      '$projectKey/config/resolutions.json',
      '${jsonEncode([
        {'id': 'done', 'name': 'Done'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      '$projectKey/config/i18n/en.json',
      '${jsonEncode({
        'statuses': {'todo': 'To Do', 'in-progress': 'In Progress', 'done': 'Done'},
        'issueTypes': {'story': 'Story'},
        'fields': {'summary': 'Summary', 'description': 'Description', 'acceptanceCriteria': 'Acceptance Criteria', 'priority': 'Priority', 'assignee': 'Assignee', 'labels': 'Labels', 'storyPoints': 'Story Points'},
        'priorities': {'medium': 'Medium', 'high': 'High'},
        'components': {'tracker-core': 'Tracker Core'},
        'versions': {'mvp': 'MVP'},
        'resolutions': {'done': 'Done'},
      })}\n',
    );
    await _repositoryFixture.writeFile('$projectKey/DEMO-1/main.md', '''
---
key: DEMO-1
project: DEMO
issueType: story
status: todo
priority: medium
summary: TS-482 baseline issue
assignee: ts482-user
reporter: ts482-user
updated: 2026-05-12T00:00:00Z
---

# Description

Baseline issue for attachment storage settings persistence coverage.
''');
    await _repositoryFixture.writeFile(
      '$projectKey/DEMO-1/acceptance_criteria.md',
      '# Acceptance Criteria\n\n- Project settings persist attachment storage safely.\n',
    );
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-482 attachment storage fixture');
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString().trim();
  }
}
