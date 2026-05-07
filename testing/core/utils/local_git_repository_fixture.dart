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
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      'DEMO/project.json',
      '{"key":"DEMO","name":"Local Demo"}\n',
    );
    await _writeFile(
      'DEMO/config/statuses.json',
      '[{"name":"To Do"},{"name":"Done"}]\n',
    );
    await _writeFile('DEMO/config/issue-types.json', '[{"name":"Story"}]\n');
    await _writeFile(
      'DEMO/config/fields.json',
      '[{"name":"Summary"},{"name":"Priority"}]\n',
    );
    await _writeFile('DEMO/DEMO-1/main.md', '''
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
    await _writeFile(
      'DEMO/DEMO-1/acceptance_criteria.md',
      '- Loads through the local Git runtime\n',
    );

    await _git(['init', '-b', branch]);
    await _git(['config', 'user.name', userName]);
    await _git(['config', 'user.email', userEmail]);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Initial local runtime fixture']);
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
