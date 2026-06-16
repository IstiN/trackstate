import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts280TerminalTransitionDefaultResolutionFixture {
  Ts280TerminalTransitionDefaultResolutionFixture._(this.directory);

  static const projectKey = 'TRACK';
  static const issueKey = 'TRACK-280';
  static const issuePath = '$projectKey/$issueKey/main.md';
  static const workflowsPath = '$projectKey/config/workflows.json';
  static const resolutionsPath = '$projectKey/config/resolutions.json';
  static const expectedResolutionId = 'fixed';
  static const expectedResolutionLabel = 'Fixed';
  static const expectedTargetStatusId = 'done';
  static const expectedTargetStatusLabel = 'Done';
  static const expectedCommitSubject =
      'Move $issueKey to $expectedTargetStatusLabel';
  static const expectedDescription =
      'Transitioning this issue to Done should automatically apply the only configured terminal resolution.';

  final Directory directory;

  String get repositoryPath => directory.path;

  LocalTrackStateRepository get repository =>
      LocalTrackStateRepository(repositoryPath: repositoryPath);

  IssueMutationService get mutationService =>
      IssueMutationService(repository: repository);

  static Future<Ts280TerminalTransitionDefaultResolutionFixture>
  create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-280-',
    );
    final fixture = Ts280TerminalTransitionDefaultResolutionFixture._(
      directory,
    );
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts280InitialObservation> observeBeforeTransition() async {
    final snapshot = await repository.loadSnapshot();
    final issue = _issueFrom(snapshot);
    return Ts280InitialObservation(
      snapshot: snapshot,
      issue: issue,
      workflowJson: await _readRepositoryFile(workflowsPath),
      resolutionsJson: await _readRepositoryFile(resolutionsPath),
      issueMarkdown: await _readRepositoryFile(issuePath),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      latestCommitSubject: await _gitOutput(['log', '-1', '--pretty=%s']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
    );
  }

  Future<Ts280TransitionObservation> transitionWithoutResolution() async {
    final result = await mutationService.transitionIssue(
      issueKey: issueKey,
      status: expectedTargetStatusId,
    );
    final snapshot = await repository.loadSnapshot();
    final issue = _issueFrom(snapshot);
    return Ts280TransitionObservation(
      result: result,
      snapshot: snapshot,
      issue: issue,
      issueMarkdown: await _readRepositoryFile(issuePath),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      latestCommitSubject: await _gitOutput(['log', '-1', '--pretty=%s']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
      searchResults: await repository.searchIssues(issueKey),
    );
  }

  TrackStateIssue _issueFrom(TrackerSnapshot snapshot) {
    return snapshot.issues.singleWhere(
      (candidate) => candidate.key == issueKey,
    );
  }

  Future<void> _seedRepository() async {
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      '$projectKey/project.json',
      '{"key":"$projectKey","name":"Transition Resolution Demo"}\n',
    );
    await _writeFile(
      '$projectKey/config/statuses.json',
      '[{"id":"todo","name":"To Do"},{"id":"in-progress","name":"In Progress"},{"id":"done","name":"Done"}]\n',
    );
    await _writeFile(
      '$projectKey/config/issue-types.json',
      '[{"id":"story","name":"Story"}]\n',
    );
    await _writeFile(
      '$projectKey/config/fields.json',
      '[{"id":"summary","name":"Summary","type":"string","required":true},{"id":"description","name":"Description","type":"markdown","required":false}]\n',
    );
    await _writeFile(
      '$projectKey/config/priorities.json',
      '[{"id":"medium","name":"Medium"}]\n',
    );
    await _writeFile(resolutionsPath, '[{"id":"fixed","name":"Fixed"}]\n');
    await _writeFile(
      workflowsPath,
      '{"default":{"transitions":[{"from":"in-progress","to":"done"}]}}\n',
    );
    await _writeFile(issuePath, '''
---
key: $issueKey
project: $projectKey
issueType: story
status: in-progress
priority: medium
summary: Automatically apply the terminal resolution when moving to Done
updated: 2026-05-10T22:15:00Z
---

# Description

$expectedDescription
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed TS-280 transition fixture']);
  }

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('$repositoryPath/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<String> _readRepositoryFile(String relativePath) =>
      File('$repositoryPath/$relativePath').readAsString();

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

class Ts280InitialObservation {
  const Ts280InitialObservation({
    required this.snapshot,
    required this.issue,
    required this.workflowJson,
    required this.resolutionsJson,
    required this.issueMarkdown,
    required this.headRevision,
    required this.latestCommitSubject,
    required this.worktreeStatusLines,
  });

  final TrackerSnapshot snapshot;
  final TrackStateIssue issue;
  final String workflowJson;
  final String resolutionsJson;
  final String issueMarkdown;
  final String headRevision;
  final String latestCommitSubject;
  final List<String> worktreeStatusLines;
}

class Ts280TransitionObservation {
  const Ts280TransitionObservation({
    required this.result,
    required this.snapshot,
    required this.issue,
    required this.issueMarkdown,
    required this.headRevision,
    required this.latestCommitSubject,
    required this.worktreeStatusLines,
    required this.searchResults,
  });

  final IssueMutationResult<TrackStateIssue> result;
  final TrackerSnapshot snapshot;
  final TrackStateIssue issue;
  final String issueMarkdown;
  final String headRevision;
  final String latestCommitSubject;
  final List<String> worktreeStatusLines;
  final List<TrackStateIssue> searchResults;
}
