import 'dart:io';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts1316ArchivedIssueSearchFixture {
  Ts1316ArchivedIssueSearchFixture._({required this.directory});

  final Directory directory;

  static const projectKey = 'TRACK';
  static const issueKey = 'TRACK-231';
  static const issueSummary = 'Search target that becomes archived';
  static const issuePath = '$projectKey/$issueKey/main.md';
  static const archivedIssuePath =
      '$projectKey/.trackstate/archive/$issueKey/main.md';

  String get repositoryPath => directory.path;

  static Future<Ts1316ArchivedIssueSearchFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-1316-',
    );
    final fixture = Ts1316ArchivedIssueSearchFixture._(directory: directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts1316ArchivedIssueSearchObservation> observeRepositoryState({
    required TrackStateRepository repository,
  }) async {
    final snapshot = await repository.loadSnapshot();
    final issue = snapshot.issues.singleWhere(
      (candidate) => candidate.key == issueKey,
    );
    final issueFile = File('$repositoryPath/$issuePath');
    final archivedIssueFile = File('$repositoryPath/$archivedIssuePath');
    return Ts1316ArchivedIssueSearchObservation(
      snapshot: snapshot,
      issue: issue,
      issueFileExists: await issueFile.exists(),
      archivedIssueFileExists: await archivedIssueFile.exists(),
      issueMarkdown: await _readFileIfExists(issueFile),
      archivedIssueMarkdown: await _readFileIfExists(archivedIssueFile),
      activeSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('archived != true AND key = $issueKey'),
      ),
      archivedSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues(
          'archived = true AND key = $issueKey',
        ),
      ),
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
      '$projectKey/project.json',
      '{"key":"$projectKey","name":"Track Search Demo"}\n',
    );
    await _writeFile(
      '$projectKey/config/statuses.json',
      '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n',
    );
    await _writeFile(
      '$projectKey/config/issue-types.json',
      '[{"id":"story","name":"Story"}]\n',
    );
    await _writeFile(
      '$projectKey/config/fields.json',
      '[{"id":"summary","name":"Summary","type":"string","required":true},{"id":"description","name":"Description","type":"markdown"}]\n',
    );
    await _writeFile(issuePath, '''
---
key: $issueKey
project: $projectKey
issueType: story
status: todo
summary: $issueSummary
updated: 2026-05-14T12:00:00Z
---

# Summary

$issueSummary

# Description

This issue starts active so TS-1316 can archive it and verify the active and archived JQL paths.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed search archive fixture for TS-1316']);
  }

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('$repositoryPath/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<String?> _readFileIfExists(File file) async {
    if (!await file.exists()) {
      return null;
    }
    return file.readAsString();
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

class Ts1316ArchivedIssueSearchObservation {
  const Ts1316ArchivedIssueSearchObservation({
    required this.snapshot,
    required this.issue,
    required this.issueFileExists,
    required this.archivedIssueFileExists,
    required this.issueMarkdown,
    required this.archivedIssueMarkdown,
    required this.activeSearchResults,
    required this.archivedSearchResults,
    required this.headRevision,
    required this.latestCommitSubject,
    required this.worktreeStatusLines,
  });

  final TrackerSnapshot snapshot;
  final TrackStateIssue issue;
  final bool issueFileExists;
  final bool archivedIssueFileExists;
  final String? issueMarkdown;
  final String? archivedIssueMarkdown;
  final List<TrackStateIssue> activeSearchResults;
  final List<TrackStateIssue> archivedSearchResults;
  final String headRevision;
  final String latestCommitSubject;
  final List<String> worktreeStatusLines;
}
