import 'dart:convert';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts465LocaleRemovalFixture {
  Ts465LocaleRemovalFixture._(this._repositoryFixture);

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts465LocaleRemovalFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-465 Tester',
      userEmail: 'ts465@example.com',
    );
    final fixture = Ts465LocaleRemovalFixture._(repositoryFixture);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<void> _seedRepository() async {
    await _repositoryFixture.writeFile(
      'DEMO/project.json',
      '${jsonEncode({
        'key': 'DEMO',
        'name': 'Locale removal rules demo',
        'defaultLocale': 'en',
        'supportedLocales': ['en', 'de'],
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
      'DEMO/config/i18n/en.json',
      '${jsonEncode({
        'statuses': {'todo': 'To Do', 'done': 'Done'},
        'issueTypes': {'story': 'Story'},
        'fields': {'summary': 'Summary', 'description': 'Description'},
        'priorities': {'high': 'High'},
        'components': {'tracker-core': 'Tracker Core'},
        'versions': {'mvp': 'MVP'},
        'resolutions': {'done': 'Done'},
      })}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/i18n/de.json',
      '${jsonEncode({
        'statuses': {'todo': 'Offen', 'done': 'Erledigt'},
        'issueTypes': {'story': 'Story'},
        'fields': {'summary': 'Zusammenfassung', 'description': 'Beschreibung'},
        'priorities': {'high': 'Hoch'},
        'components': {'tracker-core': 'Tracker-Kern'},
        'versions': {'mvp': 'MVP'},
        'resolutions': {'done': 'Erledigt'},
      })}\n',
    );
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-465 locale removal fixture');
  }
}
