import 'dart:io';

class Ts800ExistingGitRepositoryFixture {
  Ts800ExistingGitRepositoryFixture._(this.directory);

  final Directory directory;

  static const String defaultBranch = 'main';

  String get repositoryPath => directory.path;

  String get repositoryFolderName =>
      repositoryPath.split(Platform.pathSeparator).last;

  static Future<Ts800ExistingGitRepositoryFixture> create() async {
    final directory = await Directory.systemTemp.createTemp('ts800-git-only-');
    await _writeFile(
      directory,
      'README.md',
      '# Plain Git repository fixture\n\n'
          'This repository contains a normal committed file tree but no '
          'TrackState metadata.\n',
    );
    await _writeFile(
      directory,
      'docs/notes.txt',
      'TS-800 plain Git repository fixture\n',
    );
    await _git(directory.path, ['init', '-b', defaultBranch]);
    await _git(directory.path, [
      'config',
      '--local',
      'user.name',
      'TS-800 Test',
    ]);
    await _git(directory.path, [
      'config',
      '--local',
      'user.email',
      'ts800@example.com',
    ]);
    await _git(directory.path, ['add', '.']);
    await _git(directory.path, ['commit', '-m', 'Initial plain git fixture']);
    return Ts800ExistingGitRepositoryFixture._(directory);
  }

  Future<Ts800RepositorySnapshot> captureSnapshot() async {
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
    return Ts800RepositorySnapshot(
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

class Ts800RepositorySnapshot {
  const Ts800RepositorySnapshot({
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
