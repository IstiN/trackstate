import 'dart:convert';
import 'dart:io';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts407IssueTypeAdminFixture {
  Ts407IssueTypeAdminFixture._(this._repositoryFixture);

  static const projectKey = 'DEMO';
  static const storyId = 'story';
  static const storyName = 'Story';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts407IssueTypeAdminFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-407 Tester',
      userEmail: 'ts407@example.com',
    );
    final fixture = Ts407IssueTypeAdminFixture._(repositoryFixture);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<List<Map<String, Object?>>> readIssueTypeEntries() async {
    final file = File(
      '${_repositoryFixture.directory.path}/$projectKey/config/issue-types.json',
    );
    final raw = await file.readAsString();
    final decoded = jsonDecode(raw) as List<dynamic>;
    return decoded
        .map((entry) => Map<String, Object?>.from(entry as Map))
        .toList(growable: false);
  }

  Future<void> _seedRepository() async {
    await _repositoryFixture.writeFile(
      '$projectKey/config/statuses.json',
      '${jsonEncode([
        {'id': 'todo', 'name': 'To Do'},
        {'id': 'in-progress', 'name': 'In Progress'},
        {'id': 'done', 'name': 'Done'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      '$projectKey/config/workflows.json',
      '${jsonEncode({
        'delivery-workflow': {
          'name': 'Delivery workflow',
          'statuses': ['To Do', 'In Progress', 'Done'],
          'transitions': [
            {
              'id': 'start',
              'name': 'Start work',
              'from': 'To Do',
              'to': 'In Progress',
            },
            {
              'id': 'complete',
              'name': 'Complete',
              'from': 'In Progress',
              'to': 'Done',
            },
          ],
        },
      })}\n',
    );
    await _repositoryFixture.writeFile(
      '$projectKey/config/issue-types.json',
      '${jsonEncode([
        {
          'id': 'epic',
          'name': 'Epic',
          'hierarchyLevel': 1,
          'icon': 'epic',
          'workflow': 'delivery-workflow',
        },
        {
          'id': storyId,
          'name': storyName,
          'hierarchyLevel': 0,
          'icon': 'story',
          'workflow': 'delivery-workflow',
        },
        {
          'id': 'subtask',
          'name': 'Sub-task',
          'hierarchyLevel': -1,
          'icon': 'subtask',
          'workflow': 'delivery-workflow',
        },
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      '$projectKey/config/fields.json',
      '${jsonEncode([
        {
          'id': 'summary',
          'name': 'Summary',
          'type': 'string',
          'required': true,
        },
        {
          'id': 'description',
          'name': 'Description',
          'type': 'markdown',
          'required': false,
        },
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      '$projectKey/config/priorities.json',
      '${jsonEncode([
        {'id': 'medium', 'name': 'Medium'},
        {'id': 'high', 'name': 'High'},
      ])}\n',
    );
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-407 issue type admin fixture');
  }
}
