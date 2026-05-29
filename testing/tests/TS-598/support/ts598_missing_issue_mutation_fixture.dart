import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts598MissingIssueMutationFixture {
  Ts598MissingIssueMutationFixture._({required this.directory});

  static const missingIssueKey = 'MISSING-404';
  static const survivingIssueKey = 'TRACK-122';
  static const missingIssuePath = 'TRACK/$missingIssueKey/main.md';
  static const survivingIssuePath = 'TRACK/$survivingIssueKey/main.md';
  static const updatedSummary =
      'Updated summary for a missing issue should never persist.';

  final Directory directory;

  String get repositoryPath => directory.path;

  LocalTrackStateRepository get repository =>
      LocalTrackStateRepository(repositoryPath: repositoryPath);

  IssueMutationService get mutationService =>
      IssueMutationService(repository: repository);

  static Future<Ts598MissingIssueMutationFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-598-',
    );
    final fixture = Ts598MissingIssueMutationFixture._(directory: directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts598MissingIssueMutationObservation> observeBeforeMutation() async {
    final snapshot = await repository.loadSnapshot();
    return Ts598MissingIssueMutationObservation(
      snapshot: snapshot,
      missingIssueFileExists: await File(
        '$repositoryPath/$missingIssuePath',
      ).exists(),
      survivingIssueMarkdown: await File(
        '$repositoryPath/$survivingIssuePath',
      ).readAsString(),
      missingIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $missingIssueKey'),
      ),
      survivingIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $survivingIssueKey'),
      ),
      projectSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK'),
      ),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
    );
  }

  Future<Ts598MissingIssueMutationObservation>
  attemptMissingIssueUpdateFields() async {
    final result = await mutationService.updateFields(
      issueKey: missingIssueKey,
      fields: const {'summary': updatedSummary},
    );
    final refreshedRepository = repository;
    final refreshedSnapshot = await refreshedRepository.loadSnapshot();
    return Ts598MissingIssueMutationObservation(
      snapshot: refreshedSnapshot,
      result: result,
      missingIssueFileExists: await File(
        '$repositoryPath/$missingIssuePath',
      ).exists(),
      survivingIssueMarkdown: await File(
        '$repositoryPath/$survivingIssuePath',
      ).readAsString(),
      missingIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await refreshedRepository.searchIssues(
          'project = TRACK $missingIssueKey',
        ),
      ),
      survivingIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await refreshedRepository.searchIssues(
          'project = TRACK $survivingIssueKey',
        ),
      ),
      projectSearchResults: List<TrackStateIssue>.unmodifiable(
        await refreshedRepository.searchIssues('project = TRACK'),
      ),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
    );
  }

  Future<void> _seedRepository() async {
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      'TRACK/project.json',
      '{"key":"TRACK","name":"Track Mutation Result Demo"}\n',
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
    await _writeFile(survivingIssuePath, '''
---
key: $survivingIssueKey
project: TRACK
issueType: story
status: todo
summary: Surviving issue
updated: 2026-05-13T08:00:00Z
---

# Description

This active issue must remain unchanged after the missing mutation attempt.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed typed mutation not-found fixture']);
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

class Ts598MissingIssueMutationObservation {
  const Ts598MissingIssueMutationObservation({
    required this.snapshot,
    required this.missingIssueFileExists,
    required this.survivingIssueMarkdown,
    required this.missingIssueSearchResults,
    required this.survivingIssueSearchResults,
    required this.projectSearchResults,
    required this.headRevision,
    required this.worktreeStatusLines,
    this.result,
  });

  final TrackerSnapshot snapshot;
  final IssueMutationResult<TrackStateIssue>? result;
  final bool missingIssueFileExists;
  final String survivingIssueMarkdown;
  final List<TrackStateIssue> missingIssueSearchResults;
  final List<TrackStateIssue> survivingIssueSearchResults;
  final List<TrackStateIssue> projectSearchResults;
  final String headRevision;
  final List<String> worktreeStatusLines;
}
