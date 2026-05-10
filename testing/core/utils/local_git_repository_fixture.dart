import 'dart:io';

import 'package:trackstate/domain/models/trackstate_models.dart';

class LocalGitRepositoryFixture {
  LocalGitRepositoryFixture._({
    required this.directory,
    required this.userName,
    required this.userEmail,
    required this.branch,
  });

  final Directory directory;
  final String userName;
  final String userEmail;
  final String branch;

  RepositoryConnection get connection => RepositoryConnection(
    repository: directory.path,
    branch: branch,
    token: '',
  );

  Future<void> dispose() => directory.delete(recursive: true);

  Future<void> configureAuthor({String? userName, String? userEmail}) async {
    if (userName == null) {
      await _git(['config', '--local', '--unset-all', 'user.name']);
    } else {
      await _git(['config', '--local', 'user.name', userName]);
    }
    if (userEmail == null) {
      await _git(['config', '--local', '--unset-all', 'user.email']);
    } else {
      await _git(['config', '--local', 'user.email', userEmail]);
    }
  }

  Future<void> writeFile(String relativePath, String content) async {
    final file = File('${directory.path}/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<void> stageAll() => _git(['add', '.']);

  Future<void> commit(String message) => _git(['commit', '-m', message]);

  static Future<LocalGitRepositoryFixture> create({
    String userName = 'Local Tester',
    String userEmail = 'local@example.com',
    String branch = 'main',
  }) async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-43-',
    );
    final fixture = LocalGitRepositoryFixture._(
      directory: directory,
      userName: userName,
      userEmail: userEmail,
      branch: branch,
    );
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> _seedRepository() async {
    await writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await writeFile(
      'DEMO/project.json',
      '{"key":"DEMO","name":"Local Demo"}\n',
    );
    await writeFile(
      'DEMO/config/statuses.json',
      '[{"name":"To Do"},{"name":"Done"}]\n',
    );
    await writeFile('DEMO/config/issue-types.json', '[{"name":"Story"}]\n');
    await writeFile(
      'DEMO/config/fields.json',
      '[{"name":"Summary"},{"name":"Priority"}]\n',
    );
    await writeFile('DEMO/DEMO-1/main.md', '''
---
key: DEMO-1
project: DEMO
issueType: Story
status: To Do
priority: High
summary: Local identity issue
assignee: Fixture Assignee
reporter: fixture@example.com
updated: 2026-05-05T00:00:00Z
---

# Description

Loaded from local Git.
''');
    await writeFile(
      'DEMO/DEMO-1/acceptance_criteria.md',
      '- Loads through the local Git runtime\n',
    );

    await _git(['init', '-b', branch]);
    await _git(['config', '--local', 'user.name', userName]);
    await _git(['config', '--local', 'user.email', userEmail]);
    await stageAll();
    await commit('Initial local runtime fixture');
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', ['-C', directory.path, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }
}
