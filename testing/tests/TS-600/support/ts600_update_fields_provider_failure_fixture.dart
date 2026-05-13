import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts600UpdateFieldsProviderFailureFixture {
  Ts600UpdateFieldsProviderFailureFixture._({required this.directory});

  static const issueKey = 'TRACK-122';
  static const issuePath = 'TRACK/$issueKey/main.md';
  static const issueSummary = 'Provider failure normalization target';
  static const originalDescription =
      'This committed description should remain visible after the provider failure.';
  static const attemptedDescription =
      'TS-600 attempted to replace the description during the failing mutation.';
  static const blockingIndexPath = 'TRACK/.trackstate/index';
  static const generatedIndexPath = '$blockingIndexPath/issues.json';
  static const providerFailureMessage =
      'Local repository could not write text file at $generatedIndexPath because the filesystem rejected the change.';

  final Directory directory;

  String get repositoryPath => directory.path;

  LocalTrackStateRepository get repository =>
      LocalTrackStateRepository(repositoryPath: repositoryPath);

  IssueMutationService get mutationService =>
      IssueMutationService(repository: repository);

  static Future<Ts600UpdateFieldsProviderFailureFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-600-',
    );
    final fixture = Ts600UpdateFieldsProviderFailureFixture._(
      directory: directory,
    );
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts600InitialObservation> observeBeforeFailure() async {
    final snapshot = await repository.loadSnapshot();
    final issue = snapshot.issues.singleWhere(
      (candidate) => candidate.key == issueKey,
    );
    return Ts600InitialObservation(
      repositoryPath: repositoryPath,
      snapshot: snapshot,
      issue: issue,
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
      issueMarkdown: await File('$repositoryPath/$issuePath').readAsString(),
      blockerExists: await File('$repositoryPath/$blockingIndexPath').exists(),
    );
  }

  Future<Ts600FailureObservation> triggerFilesystemProviderFailure() async {
    await _installFilesystemBlocker();
    final result = await mutationService.updateFields(
      issueKey: issueKey,
      fields: const <String, Object?>{'description': attemptedDescription},
    );
    final refreshedSnapshot = await repository.loadSnapshot();
    final issue = refreshedSnapshot.issues.singleWhere(
      (candidate) => candidate.key == issueKey,
    );
    return Ts600FailureObservation(
      result: result,
      snapshot: refreshedSnapshot,
      issue: issue,
      repositoryPath: repositoryPath,
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
      headIssueMarkdown: await _gitOutput(['show', 'HEAD:$issuePath']),
      worktreeIssueMarkdown: await File(
        '$repositoryPath/$issuePath',
      ).readAsString(),
      blockerExists: await File('$repositoryPath/$blockingIndexPath').exists(),
      blockerType: await _pathType(blockingIndexPath),
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
updated: 2026-05-13T10:00:00Z
---

# Description

$originalDescription
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed TS-600 provider failure fixture']);
  }

  Future<void> _installFilesystemBlocker() async {
    final blocker = File('$repositoryPath/$blockingIndexPath');
    await blocker.parent.create(recursive: true);
    await blocker.writeAsString(
      'This file intentionally blocks creation of $generatedIndexPath.\n',
    );
  }

  String _pathType(String relativePath) {
    final entity = FileSystemEntity.typeSync('$repositoryPath/$relativePath');
    switch (entity) {
      case FileSystemEntityType.directory:
        return 'directory';
      case FileSystemEntityType.file:
        return 'file';
      case FileSystemEntityType.link:
        return 'link';
      case FileSystemEntityType.notFound:
        return 'not-found';
      case FileSystemEntityType.unixDomainSock:
        return 'socket';
      case FileSystemEntityType.pipe:
        return 'pipe';
      default:
        return 'other';
    }
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
      return const <String>[];
    }
    return output
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }
}

class Ts600InitialObservation {
  const Ts600InitialObservation({
    required this.repositoryPath,
    required this.snapshot,
    required this.issue,
    required this.headRevision,
    required this.worktreeStatusLines,
    required this.issueMarkdown,
    required this.blockerExists,
  });

  final String repositoryPath;
  final TrackerSnapshot snapshot;
  final TrackStateIssue issue;
  final String headRevision;
  final List<String> worktreeStatusLines;
  final String issueMarkdown;
  final bool blockerExists;
}

class Ts600FailureObservation {
  const Ts600FailureObservation({
    required this.result,
    required this.snapshot,
    required this.issue,
    required this.repositoryPath,
    required this.headRevision,
    required this.worktreeStatusLines,
    required this.headIssueMarkdown,
    required this.worktreeIssueMarkdown,
    required this.blockerExists,
    required this.blockerType,
  });

  final IssueMutationResult<TrackStateIssue> result;
  final TrackerSnapshot snapshot;
  final TrackStateIssue issue;
  final String repositoryPath;
  final String headRevision;
  final List<String> worktreeStatusLines;
  final String headIssueMarkdown;
  final String worktreeIssueMarkdown;
  final bool blockerExists;
  final String blockerType;
}
