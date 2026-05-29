import 'dart:convert';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts404SettingsAdminFixture {
  Ts404SettingsAdminFixture._(this._repositoryFixture);

  static const statusName = 'To Do';
  static const editStatusLabel = 'Edit status $statusName';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts404SettingsAdminFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-404 Tester',
      userEmail: 'ts404@example.com',
    );
    final fixture = Ts404SettingsAdminFixture._(repositoryFixture);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<void> _seedRepository() async {
    await _repositoryFixture.writeFile(
      'DEMO/project.json',
      '${jsonEncode({'key': 'DEMO', 'name': 'Settings admin demo'})}\n',
    );
    await _repositoryFixture.writeFile('DEMO/config/statuses.json', '''
${jsonEncode([
      {'id': 'todo', 'name': 'To Do', 'category': 'new'},
      {'id': 'in-progress', 'name': 'In Progress', 'category': 'indeterminate'},
      {'id': 'done', 'name': 'Done', 'category': 'done'},
    ])}
''');
    await _repositoryFixture.writeFile('DEMO/config/workflows.json', '''
${jsonEncode({
      'delivery': {
        'name': 'Delivery workflow',
        'statuses': ['To Do', 'In Progress', 'Done'],
        'transitions': [
          {'id': 'start', 'name': 'Start work', 'from': 'To Do', 'to': 'In Progress'},
          {'id': 'finish', 'name': 'Finish work', 'from': 'In Progress', 'to': 'Done'},
        ],
      },
    })}
''');
    await _repositoryFixture.writeFile('DEMO/config/issue-types.json', '''
${jsonEncode([
      {'id': 'story', 'name': 'Story', 'workflowId': 'delivery', 'hierarchyLevel': 0},
      {'id': 'subtask', 'name': 'Sub-task', 'workflowId': 'delivery', 'hierarchyLevel': -1},
    ])}
''');
    await _repositoryFixture.writeFile('DEMO/config/fields.json', '''
${jsonEncode([
      {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
      {'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
      {'id': 'acceptanceCriteria', 'name': 'Acceptance Criteria', 'type': 'markdown', 'required': false},
    ])}
''');
    await _repositoryFixture.writeFile(
      'DEMO/config/priorities.json',
      '${jsonEncode([
        {'id': 'medium', 'name': 'Medium'},
        {'id': 'high', 'name': 'High'},
      ])}\n',
    );
    await _repositoryFixture.writeFile('DEMO/config/resolutions.json', '[]\n');
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-404 settings admin fixture');
  }
}
