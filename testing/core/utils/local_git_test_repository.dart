import 'dart:convert';
import 'dart:io';

class LocalGitTestRepository {
  LocalGitTestRepository._(this._directory);

  final Directory _directory;

  String get path => _directory.path;

  static Future<LocalGitTestRepository> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-40-',
    );
    await _writeFile(
      directory,
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      directory,
      'DEMO/project.json',
      '{"key":"DEMO","name":"Local Demo"}\n',
    );
    await _writeFile(
      directory,
      'DEMO/config/statuses.json',
      '[{"name":"To Do"},{"name":"In Progress"},{"name":"Done"}]\n',
    );
    await _writeFile(
      directory,
      'DEMO/config/issue-types.json',
      '[{"name":"Story"}]\n',
    );
    await _writeFile(
      directory,
      'DEMO/config/fields.json',
      '[{"name":"Summary"},{"name":"Priority"}]\n',
    );
    await _writeFile(directory, 'DEMO/DEMO-1/main.md', '''
---
key: DEMO-1
project: DEMO
issueType: Story
status: In Progress
priority: High
summary: Local issue
assignee: local-user
reporter: local-admin
updated: 2026-05-05T00:00:00Z
---

# Description

Loaded from local git.
''');
    await _writeFile(
      directory,
      'DEMO/DEMO-1/acceptance_criteria.md',
      '- Can be loaded from local Git\n',
    );

    await _git(directory.path, ['init', '-b', 'main']);
    await _git(directory.path, ['config', 'user.name', 'Local Tester']);
    await _git(directory.path, ['config', 'user.email', 'local@example.com']);
    await _git(directory.path, ['add', '.']);
    await _git(directory.path, ['commit', '-m', 'Initial import']);

    return LocalGitTestRepository._(directory);
  }

  Future<void> dispose() => _directory.delete(recursive: true);

  Future<String> headRevision() async =>
      (await _git(path, ['rev-parse', 'HEAD'])).trim();

  Future<String> parentOfHead() async =>
      (await _git(path, ['rev-parse', 'HEAD^'])).trim();

  Future<String> latestCommitSubject() async =>
      (await _git(path, ['log', '-1', '--pretty=%s'])).trim();

  Future<List<String>> latestCommitFiles() async {
    final output = await _git(path, [
      'show',
      '--name-only',
      '--format=',
      'HEAD',
    ]);
    return const LineSplitter()
        .convert(output)
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList();
  }

  Future<String> readIssueMarkdown() async =>
      File('$path/DEMO/DEMO-1/main.md').readAsString();

  static Future<void> _writeFile(
    Directory root,
    String relativePath,
    String content,
  ) async {
    final file = File('${root.path}/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  static Future<String> _git(String repositoryPath, List<String> args) async {
    final result = await Process.run(
      'git',
      ['-C', repositoryPath, ...args],
      stdoutEncoding: utf8,
      stderrEncoding: utf8,
    );
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString();
  }
}
