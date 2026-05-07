import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';

class LocalGitTestRepository {
  LocalGitTestRepository._(this._directory);

  final Directory _directory;

  String get path => _directory.path;

  static Future<LocalGitTestRepository> create() async {
    final directory = Directory.systemTemp.createTempSync('trackstate-ts-40-');
    _writeFile(
      directory,
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    _writeFile(
      directory,
      'DEMO/project.json',
      '{"key":"DEMO","name":"Local Demo"}\n',
    );
    _writeFile(
      directory,
      'DEMO/config/statuses.json',
      '[{"name":"To Do"},{"name":"In Progress"},{"name":"Done"}]\n',
    );
    _writeFile(
      directory,
      'DEMO/config/issue-types.json',
      '[{"name":"Story"}]\n',
    );
    _writeFile(
      directory,
      'DEMO/config/fields.json',
      '[{"name":"Summary"},{"name":"Priority"}]\n',
    );
    _writeFile(directory, 'DEMO/DEMO-1/main.md', '''
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
    _writeFile(
      directory,
      'DEMO/DEMO-1/acceptance_criteria.md',
      '- Can be loaded from local Git\n',
    );

    _git(directory.path, ['init', '-b', 'main']);
    _git(directory.path, ['config', 'user.name', 'Local Tester']);
    _git(directory.path, ['config', 'user.email', 'local@example.com']);
    _git(directory.path, ['add', '.']);
    _git(directory.path, ['commit', '-m', 'Initial import']);

    return LocalGitTestRepository._(directory);
  }

  Future<void> dispose() async {
    _directory.deleteSync(recursive: true);
  }

  Future<String> headRevision() async =>
      _git(path, ['rev-parse', 'HEAD']).trim();

  Future<String> parentOfHead() async =>
      _git(path, ['rev-parse', 'HEAD^']).trim();

  Future<String> latestCommitSubject() async =>
      _git(path, ['log', '-1', '--pretty=%s']).trim();

  Future<List<String>> latestCommitFiles() async {
    final output = _git(path, ['show', '--name-only', '--format=', 'HEAD']);
    return const LineSplitter()
        .convert(output)
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList();
  }

  Future<String> readIssueMarkdown() async =>
      File('$path/DEMO/DEMO-1/main.md').readAsStringSync();

  static void _writeFile(Directory root, String relativePath, String content) {
    final file = File('${root.path}/$relativePath');
    file.parent.createSync(recursive: true);
    file.writeAsStringSync(content);
  }

  static String _git(String repositoryPath, List<String> args) {
    final result = Process.runSync(
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

class SyncGitProcessRunner implements GitProcessRunner {
  const SyncGitProcessRunner();

  @override
  Future<GitCommandResult> run(
    String repositoryPath,
    List<String> args, {
    bool binaryOutput = false,
  }) async {
    final result = Process.runSync(
      'git',
      ['-C', repositoryPath, ...args],
      stdoutEncoding: binaryOutput ? null : utf8,
      stderrEncoding: utf8,
    );
    final stdoutBytes = switch (result.stdout) {
      final List<int> bytes => Uint8List.fromList(bytes),
      final String text => Uint8List.fromList(utf8.encode(text)),
      _ => Uint8List(0),
    };
    final stdout = switch (result.stdout) {
      final String text => text,
      final List<int> bytes => utf8.decode(bytes, allowMalformed: true),
      _ => '',
    };
    return GitCommandResult(
      exitCode: result.exitCode,
      stdout: stdout,
      stdoutBytes: stdoutBytes,
      stderr: result.stderr.toString(),
    );
  }
}
