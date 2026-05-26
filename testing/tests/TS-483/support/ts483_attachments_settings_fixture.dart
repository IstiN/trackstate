import 'dart:convert';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts483AttachmentsSettingsFixture {
  Ts483AttachmentsSettingsFixture._(this._repositoryFixture);

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts483AttachmentsSettingsFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-483 Tester',
      userEmail: 'ts483@example.com',
    );
    final fixture = Ts483AttachmentsSettingsFixture._(repositoryFixture);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<void> _seedRepository() async {
    await _repositoryFixture.writeFile(
      'DEMO/project.json',
      '${jsonEncode({
        'key': 'DEMO',
        'name': 'Attachments settings accessibility demo',
        'defaultLocale': 'en',
        'attachmentStorage': {'mode': 'repository-path'},
      })}\n',
    );
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
        'delivery': {
          'name': 'Delivery workflow',
          'statuses': ['To Do', 'In Progress', 'Done'],
          'transitions': [
            {'id': 'start', 'name': 'Start work', 'from': 'To Do', 'to': 'In Progress'},
            {'id': 'finish', 'name': 'Finish work', 'from': 'In Progress', 'to': 'Done'},
          ],
        },
      })}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/issue-types.json',
      '${jsonEncode([
        {'id': 'story', 'name': 'Story', 'workflowId': 'delivery', 'hierarchyLevel': 0},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/fields.json',
      '${jsonEncode([
        {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
        {'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
        {'id': 'priority', 'name': 'Priority', 'type': 'option', 'required': false},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/priorities.json',
      '${jsonEncode([
        {'id': 'high', 'name': 'High'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/components.json',
      '${jsonEncode([
        {'id': 'tracker-shell', 'name': 'Tracker Shell'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/versions.json',
      '${jsonEncode([
        {'id': 'mvp', 'name': 'MVP'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/resolutions.json',
      '${jsonEncode([
        {'id': 'done', 'name': 'Done'},
      ])}\n',
    );
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-483 attachments settings fixture');
  }
}
