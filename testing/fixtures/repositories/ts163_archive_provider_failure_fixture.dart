import 'dart:io';
import 'dart:typed_data';

import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/utils/local_git_test_repository.dart';

class Ts163ArchiveProviderFailureFixture {
  Ts163ArchiveProviderFailureFixture._({required this.directory});

  final Directory directory;

  static const issueKey = 'TRACK-122';
  static const issuePath = 'TRACK/$issueKey/main.md';
  static const lowLevelGitFailure =
      "fatal: unable to create '.git/index.lock': File exists";

  static Future<Ts163ArchiveProviderFailureFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-163-',
    );
    final fixture = Ts163ArchiveProviderFailureFixture._(directory: directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts163ArchiveProviderFailureObservation>
  observeBeforeArchiveState() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    final resolvedIssuePath = _resolvedIssuePath(snapshot);
    return Ts163ArchiveProviderFailureObservation(
      repositoryPath: directory.path,
      snapshot: snapshot,
      issuePath: resolvedIssuePath,
      issueFileExists: await File(
        '${directory.path}/$resolvedIssuePath',
      ).exists(),
      visibleIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $issueKey'),
      ),
      headIssueMarkdown: await _gitOutput(['show', 'HEAD:$issuePath']),
      worktreeIssueMarkdown:
          await _readFileIfExists('${directory.path}/$resolvedIssuePath') ?? '',
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
      stagedIndexStatusLines: await _gitOutputLines([
        'diff',
        '--cached',
        '--name-status',
      ]),
      unstagedDiffStatusLines: await _gitOutputLines(['diff', '--name-status']),
      untrackedFiles: await _gitOutputLines([
        'ls-files',
        '--others',
        '--exclude-standard',
      ]),
    );
  }

  Future<Ts163ArchiveProviderFailureObservation>
  archiveIssueViaRepositoryService() async {
    final processRunner = _FailOnArchiveCommitProcessRunner();
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
      processRunner: processRunner,
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
        'Archiving $issueKey should fail with a repository-domain exception.',
      );
    }

    final refreshedRepository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final refreshedSnapshot = await refreshedRepository.loadSnapshot();
    final resolvedIssuePath = _resolvedIssuePath(refreshedSnapshot);
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
      visibleIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await refreshedRepository.searchIssues('project = TRACK $issueKey'),
      ),
      headIssueMarkdown: await _gitOutput(['show', 'HEAD:$issuePath']),
      worktreeIssueMarkdown:
          await _readFileIfExists('${directory.path}/$resolvedIssuePath') ?? '',
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
      stagedIndexStatusLines: await _gitOutputLines([
        'diff',
        '--cached',
        '--name-status',
      ]),
      unstagedDiffStatusLines: await _gitOutputLines(['diff', '--name-status']),
      untrackedFiles: await _gitOutputLines([
        'ls-files',
        '--others',
        '--exclude-standard',
      ]),
      forcedArchiveCommitAttempts: processRunner.forcedArchiveCommitAttempts,
    );
  }

  Future<void> _seedRepository() async {
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      'TRACK/project.json',
      '{"key":"TRACK","name":"Track Archive Demo"}\n',
    );
    await _writeFile(
      'TRACK/config/statuses.json',
      '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n',
    );
    await _writeFile(
      'TRACK/config/issue-types.json',
      '[{"id":"story","name":"Story"}]\n',
    );
    await _writeFile(
      'TRACK/config/fields.json',
      '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
    );
    await _writeFile(issuePath, '''
---
key: $issueKey
project: TRACK
issueType: story
status: todo
summary: Active issue for archive failure mapping
updated: 2026-05-09T08:00:00Z
---

# Description

This active issue exists so TS-163 can trigger a generic provider failure
while archiveIssue is processing a real repository artifact.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issue for TS-163']);
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

  String _resolvedIssuePath(TrackerSnapshot snapshot) => snapshot.issues
      .singleWhere((candidate) => candidate.key == issueKey)
      .storagePath;

  Future<String?> _readFileIfExists(String path) async {
    final file = File(path);
    if (!await file.exists()) {
      return null;
    }
    return file.readAsString();
  }
}

class Ts163ArchiveProviderFailureObservation {
  const Ts163ArchiveProviderFailureObservation({
    required this.repositoryPath,
    required this.snapshot,
    required this.issuePath,
    required this.issueFileExists,
    required this.visibleIssueSearchResults,
    required this.headIssueMarkdown,
    required this.worktreeIssueMarkdown,
    required this.headRevision,
    required this.worktreeStatusLines,
    required this.stagedIndexStatusLines,
    required this.unstagedDiffStatusLines,
    required this.untrackedFiles,
    this.errorType,
    this.errorMessage,
    this.errorStackTrace,
    this.forcedArchiveCommitAttempts = 0,
  });

  final String repositoryPath;
  final TrackerSnapshot snapshot;
  final String issuePath;
  final bool issueFileExists;
  final List<TrackStateIssue> visibleIssueSearchResults;
  final String headIssueMarkdown;
  final String worktreeIssueMarkdown;
  final String headRevision;
  final List<String> worktreeStatusLines;
  final List<String> stagedIndexStatusLines;
  final List<String> unstagedDiffStatusLines;
  final List<String> untrackedFiles;
  final String? errorType;
  final String? errorMessage;
  final String? errorStackTrace;
  final int forcedArchiveCommitAttempts;
}

class _FailOnArchiveCommitProcessRunner implements GitProcessRunner {
  _FailOnArchiveCommitProcessRunner({
    GitProcessRunner delegate = const SyncGitProcessRunner(),
  }) : _delegate = delegate;

  final GitProcessRunner _delegate;
  int forcedArchiveCommitAttempts = 0;

  @override
  Future<GitCommandResult> run(
    String repositoryPath,
    List<String> args, {
    bool binaryOutput = false,
  }) async {
    if (args.length >= 3 &&
        args.first == 'commit' &&
        args[1] == '-m' &&
        args[2] == 'Archive ${Ts163ArchiveProviderFailureFixture.issueKey}') {
      forcedArchiveCommitAttempts += 1;
      return GitCommandResult(
        exitCode: 128,
        stdout: '',
        stdoutBytes: Uint8List(0),
        stderr: Ts163ArchiveProviderFailureFixture.lowLevelGitFailure,
      );
    }
    return _delegate.run(repositoryPath, args, binaryOutput: binaryOutput);
  }
}
