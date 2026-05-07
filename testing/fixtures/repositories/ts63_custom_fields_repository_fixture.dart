import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';

import '../../components/services/issue_resolution_service.dart';

class Ts63CustomFieldsRepositoryFixture {
  Ts63CustomFieldsRepositoryFixture._({
    required Directory repositoryDirectory,
    required this.issueService,
  }) : _repositoryDirectory = repositoryDirectory;

  final Directory _repositoryDirectory;
  final IssueResolutionService issueService;

  static const issueKey = 'DEMO-63';
  static const issuePath = 'DEMO/DEMO-63/main.md';

  static Future<Ts63CustomFieldsRepositoryFixture> create() async {
    final repositoryDirectory = await Directory.systemTemp.createTemp(
      'trackstate-ts-63-',
    );

    _writeFile(
      repositoryDirectory,
      'DEMO/project.json',
      jsonEncode({'key': 'DEMO', 'name': 'Demo Project'}),
    );
    _writeFile(
      repositoryDirectory,
      'DEMO/config/statuses.json',
      jsonEncode([
        {'id': 'todo', 'name': 'To Do'},
        {'id': 'done', 'name': 'Done'},
      ]),
    );
    _writeFile(
      repositoryDirectory,
      'DEMO/config/issue-types.json',
      jsonEncode([
        {'id': 'story', 'name': 'Story'},
      ]),
    );
    _writeFile(
      repositoryDirectory,
      'DEMO/config/fields.json',
      jsonEncode([
        {
          'id': 'summary',
          'name': 'Summary',
          'type': 'string',
          'required': true,
        },
        {
          'id': 'field_101',
          'name': 'Custom Field 101',
          'type': 'string',
          'required': false,
        },
        {
          'id': 'priority',
          'name': 'Priority',
          'type': 'option',
          'required': false,
        },
      ]),
    );
    _writeFile(
      repositoryDirectory,
      'DEMO/config/priorities.json',
      jsonEncode([
        {'id': 'high', 'name': 'High'},
      ]),
    );
    _writeFile(
      repositoryDirectory,
      issuePath,
      '''
---
key: $issueKey
project: DEMO
issueType: story
status: done
priority: high
summary: Inline custom fields issue
assignee: qa-user
reporter: qa-admin
customFields: { "field_101": "value" }
updated: 2026-05-07T00:00:00Z
---

# Description

Created from inline frontmatter custom fields.
''',
    );

    _git(repositoryDirectory.path, ['init', '-b', 'main']);
    _git(repositoryDirectory.path, ['config', 'user.name', 'TS-63 Tester']);
    _git(
      repositoryDirectory.path,
      ['config', 'user.email', 'ts63@example.com'],
    );
    _git(repositoryDirectory.path, ['add', '.']);
    _git(repositoryDirectory.path, ['commit', '-m', 'Seed TS-63 fixture']);

    final repository = LocalTrackStateRepository(
      repositoryPath: repositoryDirectory.path,
    );

    return Ts63CustomFieldsRepositoryFixture._(
      repositoryDirectory: repositoryDirectory,
      issueService: IssueResolutionService(repository),
    );
  }

  Future<IssueResolutionResult> resolveIssueByKey() {
    return issueService.resolveIssueByKey(issueKey);
  }

  Future<void> dispose() async {
    if (await _repositoryDirectory.exists()) {
      await _repositoryDirectory.delete(recursive: true);
    }
  }

  static void _writeFile(
    Directory root,
    String relativePath,
    String content,
  ) {
    final file = File('${root.path}/$relativePath');
    file.parent.createSync(recursive: true);
    file.writeAsStringSync(content);
  }

  static void _git(String repositoryPath, List<String> args) {
    final result = Process.runSync(
      'git',
      ['-C', repositoryPath, ...args],
      stdoutEncoding: utf8,
      stderrEncoding: utf8,
    );
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }
}
