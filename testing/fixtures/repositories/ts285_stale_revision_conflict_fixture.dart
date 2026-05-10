import 'dart:io';

import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts285StaleRevisionConflictFixture {
  Ts285StaleRevisionConflictFixture._({
    required this.directory,
    required _ConflictInjectingGitProcessRunner processRunner,
  }) : _processRunner = processRunner;

  static const issueKey = 'TRACK-122';
  static const issuePath = 'TRACK/$issueKey/main.md';
  static const issueSummary = 'Stale revision conflict target';
  static const originalDescription =
      'This description represents the original committed revision.';
  static const concurrentDescription =
      'A concurrent writer committed this newer description before updateFields saved.';
  static const attemptedDescription =
      'TS-285 attempted to overwrite the issue after the revision became stale.';

  final Directory directory;
  final _ConflictInjectingGitProcessRunner _processRunner;

  String get repositoryPath => directory.path;

  LocalTrackStateRepository get repository => LocalTrackStateRepository(
    repositoryPath: repositoryPath,
    processRunner: _processRunner,
  );

  IssueMutationService get mutationService =>
      IssueMutationService(repository: repository);

  static Future<Ts285StaleRevisionConflictFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-285-',
    );
    final processRunner = _ConflictInjectingGitProcessRunner(
      repositoryPath: directory.path,
      targetPath: issuePath,
    );
    final fixture = Ts285StaleRevisionConflictFixture._(
      directory: directory,
      processRunner: processRunner,
    );
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts285InitialObservation> observeBeforeConflict() async {
    final snapshot = await repository.loadSnapshot();
    final issue = snapshot.issues.singleWhere(
      (candidate) => candidate.key == issueKey,
    );
    return Ts285InitialObservation(
      snapshot: snapshot,
      issue: issue,
      issueFileRevision: await _gitOutput(['rev-parse', 'HEAD:$issuePath']),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
      issueMarkdown: await File('$repositoryPath/$issuePath').readAsString(),
    );
  }

  Future<Ts285ConflictObservation> triggerStaleRevisionConflict() async {
    _processRunner.armConflictInjection();
    final result = await mutationService.updateFields(
      issueKey: issueKey,
      fields: const {'description': attemptedDescription},
    );
    final refreshedSnapshot = await repository.loadSnapshot();
    final issue = refreshedSnapshot.issues.singleWhere(
      (candidate) => candidate.key == issueKey,
    );
    return Ts285ConflictObservation(
      result: result,
      snapshot: refreshedSnapshot,
      issue: issue,
      currentFileRevision: await _gitOutput(['rev-parse', 'HEAD:$issuePath']),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      latestCommitSubject: await _gitOutput(['log', '-1', '--pretty=%s']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
      issueMarkdown: await File('$repositoryPath/$issuePath').readAsString(),
      injectedFileRevision: _processRunner.injectedFileRevision,
      injectedHeadRevision: _processRunner.injectedHeadRevision,
      injectedCommitSubject: _processRunner.injectedCommitSubject,
    );
  }

  Future<void> _seedRepository() async {
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      'TRACK/project.json',
      '{"key":"TRACK","name":"Track Mutation Demo"}\n',
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
      '[{"id":"summary","name":"Summary","type":"string","required":true},{"id":"description","name":"Description","type":"markdown"}]\n',
    );
    await _writeFile(issuePath, '''
---
key: $issueKey
project: TRACK
issueType: story
status: todo
summary: $issueSummary
updated: 2026-05-10T21:30:00Z
---

# Description

$originalDescription
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed mutation conflict fixture']);
  }

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('$repositoryPath/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return (result.stdout as String).trim();
  }

  Future<List<String>> _gitOutputLines(List<String> args) async {
    final output = await _gitOutput(args);
    if (output.isEmpty) {
      return const [];
    }
    return output
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }
}

class Ts285InitialObservation {
  const Ts285InitialObservation({
    required this.snapshot,
    required this.issue,
    required this.issueFileRevision,
    required this.headRevision,
    required this.worktreeStatusLines,
    required this.issueMarkdown,
  });

  final TrackerSnapshot snapshot;
  final TrackStateIssue issue;
  final String issueFileRevision;
  final String headRevision;
  final List<String> worktreeStatusLines;
  final String issueMarkdown;
}

class Ts285ConflictObservation {
  const Ts285ConflictObservation({
    required this.result,
    required this.snapshot,
    required this.issue,
    required this.currentFileRevision,
    required this.headRevision,
    required this.latestCommitSubject,
    required this.worktreeStatusLines,
    required this.issueMarkdown,
    required this.injectedFileRevision,
    required this.injectedHeadRevision,
    required this.injectedCommitSubject,
  });

  final IssueMutationResult<TrackStateIssue> result;
  final TrackerSnapshot snapshot;
  final TrackStateIssue issue;
  final String currentFileRevision;
  final String headRevision;
  final String latestCommitSubject;
  final List<String> worktreeStatusLines;
  final String issueMarkdown;
  final String? injectedFileRevision;
  final String? injectedHeadRevision;
  final String? injectedCommitSubject;
}

class _ConflictInjectingGitProcessRunner implements GitProcessRunner {
  _ConflictInjectingGitProcessRunner({
    required this.repositoryPath,
    required this.targetPath,
  });

  final String repositoryPath;
  final String targetPath;
  final IoGitProcessRunner _delegate = const IoGitProcessRunner();
  int _targetRevisionReads = 0;
  bool _isArmed = false;
  bool _didInjectConflict = false;

  String? injectedFileRevision;
  String? injectedHeadRevision;
  String? injectedCommitSubject;

  @override
  Future<GitCommandResult> run(
    String repositoryPath,
    List<String> args, {
    bool binaryOutput = false,
  }) async {
    if (_shouldInjectConflict(repositoryPath, args)) {
      await _injectConcurrentCommit();
      _didInjectConflict = true;
    }
    if (repositoryPath == this.repositoryPath &&
        args.length == 2 &&
        args.first == 'rev-parse' &&
        args.last == 'HEAD:$targetPath') {
      _targetRevisionReads += 1;
    }
    return _delegate.run(repositoryPath, args, binaryOutput: binaryOutput);
  }

  void armConflictInjection() {
    _isArmed = true;
    _didInjectConflict = false;
    _targetRevisionReads = 0;
    injectedFileRevision = null;
    injectedHeadRevision = null;
    injectedCommitSubject = null;
  }

  bool _shouldInjectConflict(String repositoryPath, List<String> args) {
    return _isArmed &&
        !_didInjectConflict &&
        repositoryPath == this.repositoryPath &&
        args.length == 2 &&
        args.first == 'rev-parse' &&
        args.last == 'HEAD:$targetPath' &&
        _targetRevisionReads == 1;
  }

  Future<void> _injectConcurrentCommit() async {
    final file = File('$repositoryPath/$targetPath');
    final original = await file.readAsString();
    final updated = original.replaceFirst(
      Ts285StaleRevisionConflictFixture.originalDescription,
      Ts285StaleRevisionConflictFixture.concurrentDescription,
    );
    await file.writeAsString(updated);

    await _runGit(['add', '--', targetPath]);
    injectedCommitSubject = 'Concurrent update before TS-285 save';
    await _runGit(['commit', '-m', injectedCommitSubject!, '--', targetPath]);
    injectedFileRevision = await _gitOutput(['rev-parse', 'HEAD:$targetPath']);
    injectedHeadRevision = await _gitOutput(['rev-parse', 'HEAD']);
    _isArmed = false;
  }

  Future<void> _runGit(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return (result.stdout as String).trim();
  }
}
