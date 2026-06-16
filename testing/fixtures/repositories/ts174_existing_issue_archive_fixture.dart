import 'dart:io';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts174ExistingIssueArchiveFixture {
  Ts174ExistingIssueArchiveFixture._({required this.directory});

  final Directory directory;

  static const issueKey = 'TRACK-122';
  static const issuePath = 'TRACK/$issueKey/main.md';

  static Future<Ts174ExistingIssueArchiveFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-174-',
    );
    final fixture = Ts174ExistingIssueArchiveFixture._(directory: directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts174ExistingIssueArchiveObservation> observeRepositoryState({
    required TrackStateRepository repository,
    TrackStateIssue? archivedIssue,
  }) => _observeRepositoryState(
    repository: repository,
    archivedIssue: archivedIssue,
  );

  Future<TrackStateIssue> archiveIssueViaRepositoryService({
    required TrackStateRepository repository,
  }) async {
    final snapshot = await repository.loadSnapshot();
    final issue = snapshot.issues.singleWhere(
      (candidate) => candidate.key == issueKey,
    );
    return repository.archiveIssue(issue);
  }

  Future<Ts174ExistingIssueArchiveObservation> _observeRepositoryState({
    required TrackStateRepository repository,
    TrackStateIssue? archivedIssue,
  }) async {
    final snapshot = await repository.loadSnapshot();
    final issueFile = File('${directory.path}/$issuePath');
    return Ts174ExistingIssueArchiveObservation(
      repositoryPath: directory.path,
      snapshot: snapshot,
      issuePath: issuePath,
      issueFileExists: await issueFile.exists(),
      currentIssue: snapshot.issues.singleWhere(
        (candidate) => candidate.key == issueKey,
      ),
      archivedIssue: archivedIssue,
      visibleIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $issueKey'),
      ),
      mainMarkdown: await _readFileIfExists(issueFile),
      headIssueMarkdown: await _tryGitOutput(['show', 'HEAD:$issuePath']),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      latestCommitSubject: await _gitOutput(['log', '-1', '--pretty=%s']),
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
summary: Active issue ready to be archived
updated: 2026-05-09T08:00:00Z
---

# Description

This active issue exists so TS-174 can verify the successful archive flow for a
real repository artifact.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issue for TS-174']);
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

  Future<String?> _readFileIfExists(File file) async {
    if (!await file.exists()) {
      return null;
    }
    return file.readAsString();
  }

  Future<String?> _tryGitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', directory.path, ...args]);
    if (result.exitCode != 0) {
      return null;
    }
    return (result.stdout as String).trimRight();
  }
}

class Ts174ExistingIssueArchiveObservation {
  const Ts174ExistingIssueArchiveObservation({
    required this.repositoryPath,
    required this.snapshot,
    required this.issuePath,
    required this.issueFileExists,
    required this.currentIssue,
    required this.visibleIssueSearchResults,
    required this.mainMarkdown,
    required this.headIssueMarkdown,
    required this.headRevision,
    required this.latestCommitSubject,
    required this.worktreeStatusLines,
    this.archivedIssue,
  });

  final String repositoryPath;
  final TrackerSnapshot snapshot;
  final String issuePath;
  final bool issueFileExists;
  final TrackStateIssue currentIssue;
  final TrackStateIssue? archivedIssue;
  final List<TrackStateIssue> visibleIssueSearchResults;
  final String? mainMarkdown;
  final String? headIssueMarkdown;
  final String headRevision;
  final String latestCommitSubject;
  final List<String> worktreeStatusLines;
}
