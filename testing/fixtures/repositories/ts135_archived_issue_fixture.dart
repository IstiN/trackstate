import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts135ArchivedIssueFixture {
  Ts135ArchivedIssueFixture._({
    required this.directory,
    required this.initiallyArchived,
  });

  final Directory directory;
  final bool initiallyArchived;

  static const archivedIssueKey = 'TRACK-555';
  static const archivedIssuePath = 'TRACK/$archivedIssueKey/main.md';
  static const archivedIssueSummary = 'Archive target issue';
  static const siblingIssueKey = 'TRACK-556';

  static Future<Ts135ArchivedIssueFixture> create({
    bool initiallyArchived = false,
  }) async {
    final directory = await Directory.systemTemp.createTemp(
      initiallyArchived ? 'trackstate-ts-152-' : 'trackstate-ts-135-',
    );
    final fixture = Ts135ArchivedIssueFixture._(
      directory: directory,
      initiallyArchived: initiallyArchived,
    );
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts135ArchivedIssueObservation> observeCurrentState() =>
      _observeRepositoryState();

  Future<Ts135ArchivedIssueObservation> observeBeforeArchivalState() =>
      observeCurrentState();

  Future<Ts135ArchivedIssueObservation>
  archiveIssueViaRepositoryService() async {
    final dynamic repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot() as TrackerSnapshot;
    final issue = snapshot.issues.singleWhere(
      (candidate) => candidate.key == archivedIssueKey,
    );
    await repository.archiveIssue(issue);
    return _observeRepositoryState();
  }

  Future<Ts135ArchivedIssueObservation> _observeRepositoryState() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    final issue = snapshot.issues.singleWhere(
      (candidate) => candidate.key == archivedIssueKey,
    );
    final issueFile = File('${directory.path}/$archivedIssuePath');
    return Ts135ArchivedIssueObservation(
      snapshot: snapshot,
      issue: issue,
      indexEntry: snapshot.repositoryIndex.entryForKey(archivedIssueKey),
      issueFileExists: await issueFile.exists(),
      mainMarkdown: await issueFile.readAsString(),
      standardSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $archivedIssueKey'),
      ),
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
    await _writeFile(archivedIssuePath, '''
---
key: $archivedIssueKey
project: TRACK
issueType: story
status: todo
summary: $archivedIssueSummary
updated: 2026-05-09T07:00:00Z
${initiallyArchived ? 'archived: true\n' : ''}---

# Description

${initiallyArchived ? 'This issue starts archived so redundant archive requests can be verified.' : 'This active issue should become archived through the repository service.'}
''');
    await _writeFile('TRACK/$siblingIssueKey/main.md', '''
---
key: $siblingIssueKey
project: TRACK
issueType: story
status: done
summary: Sibling issue remains active
updated: 2026-05-09T07:05:00Z
---

# Description

This control issue proves the repository contains more than one issue.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git([
      'commit',
      '-m',
      initiallyArchived
          ? 'Seed archived issue for TS-152'
          : 'Seed active issues for TS-135',
    ]);
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
}

class Ts135ArchivedIssueObservation {
  const Ts135ArchivedIssueObservation({
    required this.snapshot,
    required this.issue,
    required this.indexEntry,
    required this.issueFileExists,
    required this.mainMarkdown,
    required this.standardSearchResults,
  });

  final TrackerSnapshot snapshot;
  final TrackStateIssue issue;
  final RepositoryIssueIndexEntry? indexEntry;
  final bool issueFileExists;
  final String mainMarkdown;
  final List<TrackStateIssue> standardSearchResults;
}
