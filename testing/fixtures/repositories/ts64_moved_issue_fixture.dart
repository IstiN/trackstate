import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';

import '../../components/services/issue_key_resolution_service.dart';

class Ts64MovedIssueFixture {
  Ts64MovedIssueFixture._({
    required this.directory,
    required this.repository,
    required this.service,
  });

  static const projectKey = 'PROJECT';
  static const movedIssueKey = 'PROJECT-1';
  static const movedIssueSummary = 'Moved issue stays discoverable';
  static const movedIssuePath = 'PROJECT/NEW-PARENT/PROJECT-1/main.md';
  static const movedIssueCriterion = 'Lookup stays stable after path move.';
  static const parentIssueKey = 'PROJECT-9';
  static const parentIssuePath = 'PROJECT/NEW-PARENT/main.md';
  static const legacyIssuePath = 'PROJECT/PROJECT-1/main.md';

  final Directory directory;
  final LocalTrackStateRepository repository;
  final IssueKeyResolutionService service;

  String get repositoryPath => directory.path;

  static Future<Ts64MovedIssueFixture> create() async {
    final directory = await Directory.systemTemp.createTemp('trackstate-ts-64-');
    final repository = LocalTrackStateRepository(repositoryPath: directory.path);
    final fixture = Ts64MovedIssueFixture._(
      directory: directory,
      repository: repository,
      service: IssueKeyResolutionService(repository: repository),
    );
    await fixture._seedRepository();
    return fixture;
  }

  Future<bool> legacyIssueExists() async =>
      File('${directory.path}/$legacyIssuePath').exists();

  Future<void> dispose() => directory.delete(recursive: true);

  Future<void> _seedRepository() async {
    await _writeFile(
      'PROJECT/project.json',
      jsonEncode({'key': projectKey, 'name': 'Moved issue demo'}),
    );
    await _writeFile(
      'PROJECT/config/statuses.json',
      jsonEncode([
        {'name': 'To Do'},
        {'name': 'In Progress'},
        {'name': 'Done'},
      ]),
    );
    await _writeFile(
      'PROJECT/config/issue-types.json',
      jsonEncode([
        {'name': 'Story'},
      ]),
    );
    await _writeFile(
      'PROJECT/config/fields.json',
      jsonEncode([
        {'name': 'Summary'},
        {'name': 'Priority'},
      ]),
    );
    await _writeFile(
      'PROJECT/.trackstate/index/issues.json',
      jsonEncode([
        {
          'key': parentIssueKey,
          'path': parentIssuePath,
          'parent': null,
          'epic': null,
          'children': [movedIssueKey],
          'archived': false,
        },
        {
          'key': movedIssueKey,
          'path': movedIssuePath,
          'parent': parentIssueKey,
          'parentPath': 'PROJECT/LEGACY-PARENT/main.md',
          'epic': null,
          'children': const [],
          'archived': false,
        },
      ]),
    );
    await _writeFile(
      'PROJECT/.trackstate/index/hierarchy.json',
      jsonEncode({
        'roots': [
          {
            'key': parentIssueKey,
            'path': parentIssuePath,
            'children': [
              {
                'key': movedIssueKey,
                'path': movedIssuePath,
                'parent': parentIssueKey,
              },
            ],
          },
        ],
      }),
    );
    await _writeFile(
      parentIssuePath,
      '''
---
key: $parentIssueKey
project: $projectKey
issueType: Story
status: To Do
priority: High
summary: New parent after move
assignee: qa-owner
reporter: qa-owner
updated: 2026-05-07T00:00:00Z
---

# Description

Parent issue anchoring the moved child directory.
''',
    );
    await _writeFile(
      movedIssuePath,
      '''
---
key: $movedIssueKey
project: $projectKey
issueType: Story
status: In Progress
priority: High
summary: $movedIssueSummary
assignee: qa-owner
reporter: qa-owner
parent: $parentIssueKey
updated: 2026-05-07T00:05:00Z
---

# Description

Loads from the regenerated repository index.
''',
    );
    await _writeFile(
      'PROJECT/NEW-PARENT/PROJECT-1/acceptance_criteria.md',
      '- $movedIssueCriterion\n',
    );

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed TS-64 moved issue fixture']);
  }

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('${directory.path}/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', ['-C', directory.path, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }
}
