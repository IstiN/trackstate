import 'dart:io';

class Ts717ReadyWorkspaceFixture {
  Ts717ReadyWorkspaceFixture._(this.directory);

  final Directory directory;

  static const String projectKey = 'READY';
  static const String issueKey = 'READY-1';
  static const String defaultBranch = 'main';
  static const String issuePath = '$projectKey/$issueKey/main.md';

  String get repositoryPath => directory.path;

  String get workspaceFolderName =>
      repositoryPath.split(Platform.pathSeparator).last;

  static Future<Ts717ReadyWorkspaceFixture> create() async {
    final directory = await Directory.systemTemp.createTemp('ts717-ready-');
    await _writeFile(
      directory,
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      directory,
      '$projectKey/project.json',
      '{"key":"$projectKey","name":"Ready Workspace","defaultLocale":"en","configPath":"config","attachmentStorage":{"mode":"repository-path"}}\n',
    );
    await _writeFile(
      directory,
      '$projectKey/config/statuses.json',
      '[{"id":"todo","name":"To Do"}]\n',
    );
    await _writeFile(
      directory,
      '$projectKey/config/issue-types.json',
      '[{"id":"story","name":"Story"}]\n',
    );
    await _writeFile(
      directory,
      '$projectKey/config/fields.json',
      '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
    );
    await _writeFile(
      directory,
      '$projectKey/.trackstate/index/issues.json',
      '[{"key":"$issueKey","path":"$issuePath","summary":"Ready issue","issueType":"story","status":"todo","updated":"2026-05-05T00:00:00Z","children":[],"archived":false}]\n',
    );
    await _writeFile(
      directory,
      '$projectKey/.trackstate/index/tombstones.json',
      '[]\n',
    );
    await _writeFile(directory, issuePath, '''---
key: $issueKey
project: $projectKey
issueType: story
status: todo
summary: Ready issue
updated: 2026-05-05T00:00:00Z
---

# Description

Ready issue.
''');
    await _git(directory.path, ['init', '-b', defaultBranch]);
    await _git(directory.path, [
      'config',
      '--local',
      'user.name',
      'TS-717 Test',
    ]);
    await _git(directory.path, [
      'config',
      '--local',
      'user.email',
      'ts717@example.com',
    ]);
    await _git(directory.path, ['add', '.']);
    await _git(directory.path, ['commit', '-m', 'Initial ready workspace']);
    return Ts717ReadyWorkspaceFixture._(directory);
  }

  Future<Ts717RepositorySnapshot> captureSnapshot() async {
    final headRevision = await _git(directory.path, ['rev-parse', 'HEAD']);
    final worktreeStatusOutput = await _git(directory.path, [
      'status',
      '--short',
    ]);
    final worktreeStatusLines = worktreeStatusOutput
        .split('\n')
        .map((line) => line.trimRight())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
    final files = <String, String>{};
    await for (final entity in directory.list(
      recursive: true,
      followLinks: false,
    )) {
      if (entity is! File) {
        continue;
      }
      final relativePath = _relativePath(entity.path, directory.path);
      if (relativePath == '.git' || relativePath.startsWith('.git/')) {
        continue;
      }
      files[relativePath] = await entity.readAsString();
    }
    final sortedFiles = Map<String, String>.fromEntries(
      files.entries.toList()
        ..sort((left, right) => left.key.compareTo(right.key)),
    );
    return Ts717RepositorySnapshot(
      repositoryPath: directory.path,
      headRevision: headRevision,
      worktreeStatusLines: worktreeStatusLines,
      files: sortedFiles,
    );
  }

  Future<void> dispose() => directory.delete(recursive: true);

  static Future<void> _writeFile(
    Directory root,
    String relativePath,
    String content,
  ) async {
    final file = File('${root.path}${Platform.pathSeparator}$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  static Future<String> _git(String repositoryPath, List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError(
        'git ${args.join(' ')} failed with exit code ${result.exitCode}.\n'
        'stdout:\n${result.stdout}\n'
        'stderr:\n${result.stderr}',
      );
    }
    return result.stdout.toString().trim();
  }

  static String _relativePath(String path, String rootPath) {
    final normalizedRoot = _PathUtils.normalize(rootPath);
    final normalizedPath = _PathUtils.normalize(path);
    return _PathUtils.relative(normalizedPath, from: normalizedRoot);
  }
}

class Ts717RepositorySnapshot {
  const Ts717RepositorySnapshot({
    required this.repositoryPath,
    required this.headRevision,
    required this.worktreeStatusLines,
    required this.files,
  });

  final String repositoryPath;
  final String headRevision;
  final List<String> worktreeStatusLines;
  final Map<String, String> files;
}

final class _PathUtils {
  static String normalize(String path) => path.replaceAll('\\', '/');

  static String relative(String path, {required String from}) {
    final normalizedPath = normalize(path);
    final normalizedFrom = normalize(from);
    if (normalizedPath == normalizedFrom) {
      return '.';
    }
    if (normalizedPath.startsWith('$normalizedFrom/')) {
      return normalizedPath.substring(normalizedFrom.length + 1);
    }
    return normalizedPath;
  }
}
