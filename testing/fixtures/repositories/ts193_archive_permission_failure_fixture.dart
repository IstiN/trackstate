import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';

import 'ts163_archive_provider_failure_fixture.dart';

class Ts193ArchivePermissionFailureFixture {
  Ts193ArchivePermissionFailureFixture._({
    required Ts163ArchiveProviderFailureFixture seed,
  }) : _seed = seed;

  final Ts163ArchiveProviderFailureFixture _seed;

  Directory get directory => _seed.directory;

  static const issueKey = Ts163ArchiveProviderFailureFixture.issueKey;
  static const issuePath = Ts163ArchiveProviderFailureFixture.issuePath;
  static const archiveDirectoryPath = 'TRACK/.trackstate/archive';

  String get archiveDirectoryAbsolutePath =>
      '${directory.path}/$archiveDirectoryPath';

  static Future<Ts193ArchivePermissionFailureFixture> create() async {
    final seed = await Ts163ArchiveProviderFailureFixture.create();
    final fixture = Ts193ArchivePermissionFailureFixture._(seed: seed);
    await fixture._restrictArchiveDestinationPermissions();
    return fixture;
  }

  Future<void> dispose() async {
    await _restoreArchiveDestinationPermissions();
    await _seed.dispose();
  }

  Future<Ts163ArchiveProviderFailureObservation> observeBeforeArchiveState() =>
      _seed.observeBeforeArchiveState();

  Future<Ts163ArchiveProviderFailureObservation>
  archiveIssueViaRepositoryService() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    final issue = snapshot.issues.singleWhere(
      (candidate) => candidate.key == issueKey,
    );

    Object? error;
    StackTrace? stackTrace;
    try {
      await repository.archiveIssue(issue);
    } catch (caughtError, caughtStackTrace) {
      error = caughtError;
      stackTrace = caughtStackTrace;
    }

    if (error == null) {
      throw StateError(
        'Archiving $issueKey with a non-writable archive destination should fail.',
      );
    }

    final refreshedRepository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final refreshedSnapshot = await refreshedRepository.loadSnapshot();
    final resolvedIssuePath = refreshedSnapshot.issues
        .singleWhere((candidate) => candidate.key == issueKey)
        .storagePath;

    return Ts163ArchiveProviderFailureObservation(
      repositoryPath: directory.path,
      snapshot: refreshedSnapshot,
      errorType: error.runtimeType.toString(),
      errorMessage: error.toString(),
      errorStackTrace: stackTrace?.toString(),
      issuePath: resolvedIssuePath,
      issueFileExists: await File(
        '${directory.path}/$resolvedIssuePath',
      ).exists(),
      visibleIssueSearchResults: List.unmodifiable(
        await refreshedRepository.searchIssues('project = TRACK $issueKey'),
      ),
      headIssueMarkdown: await _gitOutput(['show', 'HEAD:$issuePath']),
      worktreeIssueMarkdown:
          await _readFileIfExists('${directory.path}/$resolvedIssuePath') ?? '',
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
    );
  }

  Future<void> _restrictArchiveDestinationPermissions() async {
    final archiveDirectory = Directory(archiveDirectoryAbsolutePath);
    await archiveDirectory.create(recursive: true);
    await _chmod('500', archiveDirectoryAbsolutePath);
  }

  Future<void> _restoreArchiveDestinationPermissions() async {
    final archiveDirectory = Directory(archiveDirectoryAbsolutePath);
    if (!await archiveDirectory.exists()) {
      return;
    }
    await _chmod('700', archiveDirectoryAbsolutePath);
  }

  Future<void> _chmod(String mode, String path) async {
    final result = await Process.run('chmod', [mode, path]);
    if (result.exitCode != 0) {
      throw StateError(
        'chmod $mode $path failed: ${(result.stderr as String).trim()}',
      );
    }
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', directory.path, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return (result.stdout as String).trimRight();
  }

  Future<List<String>> _gitOutputLines(List<String> args) async {
    final output = await _gitOutput(args);
    if (output.trim().isEmpty) {
      return const [];
    }
    return output
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }

  Future<String?> _readFileIfExists(String path) async {
    final file = File(path);
    if (!await file.exists()) {
      return null;
    }
    return file.readAsString();
  }
}
