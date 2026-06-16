import 'dart:convert';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts469LocalesFixture {
  Ts469LocalesFixture._(this._repositoryFixture);

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts469LocalesFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-469 Tester',
      userEmail: 'ts469@example.com',
    );
    final fixture = Ts469LocalesFixture._(repositoryFixture);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<void> _seedRepository() async {
    await _repositoryFixture.writeFile(
      'DEMO/project.json',
      '${jsonEncode({
        'key': 'DEMO',
        'name': 'Locales accessibility demo',
        'defaultLocale': 'en',
        'supportedLocales': ['en', 'fr'],
      })}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/statuses.json',
      '${jsonEncode([
        {'id': 'todo', 'name': 'To Do', 'category': 'new'},
        {'id': 'done', 'name': 'Done', 'category': 'done'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/workflows.json',
      '${jsonEncode({
        'delivery': {
          'name': 'Delivery workflow',
          'statuses': ['To Do', 'Done'],
          'transitions': [
            {'id': 'finish', 'name': 'Finish work', 'from': 'To Do', 'to': 'Done'},
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
        {'id': 'tracker-core', 'name': 'Tracker Core'},
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
    await _repositoryFixture.writeFile(
      'DEMO/config/i18n/fr.json',
      '${jsonEncode({
        'statuses': {'todo': 'A faire'},
        'issueTypes': {'story': 'Recit'},
        'fields': {'summary': 'Resume'},
        'priorities': {'high': 'Haute'},
        'versions': {'mvp': 'Version MVP'},
      })}\n',
    );
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit(
      'Seed TS-469 locales accessibility fixture',
    );
  }
}
