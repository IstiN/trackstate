import 'dart:convert';

import '../../core/utils/local_git_repository_fixture.dart';

class Ts467LocaleResolutionFixture {
  Ts467LocaleResolutionFixture._(this._repositoryFixture);

  static const issueKey = 'DEMO-2';
  static const issueSummary = 'Explore the locale-aware issue list';
  static const defaultLocale = 'en';
  static const viewerLocale = 'de';
  static const canonicalInProgressStatus = 'In Progress';
  static const defaultLocaleInProgressStatus = 'In Progress (default locale)';
  static const viewerLocaleInProgressStatus = 'In Bearbeitung';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts467LocaleResolutionFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-467 Tester',
      userEmail: 'ts467@example.com',
    );
    final fixture = Ts467LocaleResolutionFixture._(repositoryFixture);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<void> _seedRepository() async {
    await _repositoryFixture.writeFile(
      'DEMO/project.json',
      '${jsonEncode({
        'key': 'DEMO',
        'name': 'Viewer locale resolution demo',
        'defaultLocale': defaultLocale,
        'supportedLocales': [defaultLocale, viewerLocale],
      })}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/statuses.json',
      '${jsonEncode([
        {'id': 'todo', 'name': 'To Do', 'category': 'new'},
        {'id': 'in-progress', 'name': canonicalInProgressStatus, 'category': 'indeterminate'},
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
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/priorities.json',
      '${jsonEncode([
        {'id': 'high', 'name': 'High'},
      ])}\n',
    );
    await _repositoryFixture.writeFile('DEMO/config/components.json', '[]\n');
    await _repositoryFixture.writeFile('DEMO/config/versions.json', '[]\n');
    await _repositoryFixture.writeFile('DEMO/config/resolutions.json', '[]\n');
    await _repositoryFixture.writeFile(
      'DEMO/config/i18n/en.json',
      '${jsonEncode({
        'statuses': {'todo': 'To Do', 'in-progress': defaultLocaleInProgressStatus, 'done': 'Done'},
      })}\n',
    );
    await _repositoryFixture.writeFile(
      'DEMO/config/i18n/de.json',
      '${jsonEncode({
        'statuses': {'in-progress': viewerLocaleInProgressStatus},
      })}\n',
    );
    await _repositoryFixture.writeFile('DEMO/$issueKey/main.md', '''
---
key: $issueKey
project: DEMO
issueType: story
status: in-progress
priority: high
summary: "$issueSummary"
assignee: ts467-user
reporter: ts467-user
updated: 2026-05-12T00:00:00Z
---

# Description

Verify that the visible JQL Search status label follows the viewer locale and
refreshes after locale translation edits.
''');
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed TS-467 locale resolution fixture');
  }
}
