import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts214LegacyDeletedIndexCreateFixture {
  Ts214LegacyDeletedIndexCreateFixture._(this.directory);

  static const activeIssueKey = 'TRACK-699';
  static const legacyDeletedIssueKey = 'TRACK-700';
  static const activeIssuePath = 'TRACK/$activeIssueKey/main.md';
  static const legacyDeletedIndexPath = 'TRACK/.trackstate/index/deleted.json';
  static const legacyDeletedIndexContent =
      '''
[{"key":"$legacyDeletedIssueKey","project":"TRACK","formerPath":"TRACK/$legacyDeletedIssueKey/main.md","deletedAt":"2026-05-01T08:30:00Z","summary":"Legacy deleted issue","issueType":"story","parent":null,"epic":null}]
''';

  final Directory directory;

  String get repositoryPath => directory.path;

  static Future<Ts214LegacyDeletedIndexCreateFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-214-',
    );
    final fixture = Ts214LegacyDeletedIndexCreateFixture._(directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts214LegacyDeletedIndexCreateObservation> observeBeforeCreateState() =>
      _observeState();

  Future<Ts214LegacyDeletedIndexCreateObservation>
  createIssueViaRepositoryService({
    required String summary,
    required String description,
  }) async {
    final repository = LocalTrackStateRepository(
      repositoryPath: repositoryPath,
    );
    final createdIssue = await repository.createIssue(
      summary: summary,
      description: description,
    );
    return _observeState(createdIssue: createdIssue);
  }

  Future<Ts214LegacyDeletedIndexCreateObservation> _observeState({
    TrackStateIssue? createdIssue,
  }) async {
    final repository = LocalTrackStateRepository(
      repositoryPath: repositoryPath,
    );
    final snapshot = await repository.loadSnapshot();
    final legacyDeletedIndexFile = File(
      '$repositoryPath/$legacyDeletedIndexPath',
    );
    final legacyDeletedIndexExists = await legacyDeletedIndexFile.exists();
    final createdIssuePath =
        createdIssue?.storagePath ?? 'TRACK/${createdIssue?.key ?? ''}/main.md';
    final createdIssueFile = createdIssue == null
        ? null
        : File('$repositoryPath/$createdIssuePath');
    final headRevision = await _gitOutput(['rev-parse', 'HEAD']);
    return Ts214LegacyDeletedIndexCreateObservation(
      snapshot: snapshot,
      legacyDeletedIndexPath: legacyDeletedIndexPath,
      legacyDeletedIndexExists: legacyDeletedIndexExists,
      legacyDeletedIndexContent: legacyDeletedIndexExists
          ? await legacyDeletedIndexFile.readAsString()
          : null,
      activeIssuePath: activeIssuePath,
      activeIssueFileExists: await File(
        '$repositoryPath/$activeIssuePath',
      ).exists(),
      createdIssue: createdIssue,
      createdIssuePath: createdIssue?.storagePath,
      createdIssueFileExists: createdIssueFile != null
          ? await createdIssueFile.exists()
          : false,
      createdIssueMarkdown:
          createdIssueFile != null && await createdIssueFile.exists()
          ? await createdIssueFile.readAsString()
          : null,
      createdIssueSearchResults: createdIssue == null
          ? const <TrackStateIssue>[]
          : List<TrackStateIssue>.unmodifiable(
              await repository.searchIssues(
                'project = TRACK ${createdIssue.key}',
              ),
            ),
      activeIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $activeIssueKey'),
      ),
      projectSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK'),
      ),
      headRevision: headRevision,
      parentOfHead: createdIssue == null
          ? null
          : await _gitOutput(['rev-parse', 'HEAD^']),
      latestCommitSubject: createdIssue == null
          ? null
          : await _gitOutput(['log', '-1', '--pretty=%s']),
      latestCommitFiles: createdIssue == null
          ? const <String>[]
          : await _latestCommitFiles(),
      worktreeStatusLines: await _worktreeStatusLines(),
    );
  }

  Future<void> _seedRepository() async {
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      'TRACK/project.json',
      '{"key":"TRACK","name":"Track Demo"}\n',
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
    await _writeFile(legacyDeletedIndexPath, legacyDeletedIndexContent);
    await _writeFile(activeIssuePath, '''
---
key: $activeIssueKey
project: TRACK
issueType: story
status: todo
summary: Existing active issue
updated: 2026-05-06T10:00:00Z
---

# Description

This issue remains active while TS-214 creates a new issue.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issues for TS-214']);
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
    return result.stdout.toString().trim();
  }

  Future<List<String>> _latestCommitFiles() async {
    final output = await _gitOutput([
      'show',
      '--name-only',
      '--format=',
      'HEAD',
    ]);
    return output
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }

  Future<List<String>> _worktreeStatusLines() async {
    final output = await _gitOutput(['status', '--short']);
    return output
        .split('\n')
        .map((line) => line.trimRight())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }
}

class Ts214LegacyDeletedIndexCreateObservation {
  const Ts214LegacyDeletedIndexCreateObservation({
    required this.snapshot,
    required this.legacyDeletedIndexPath,
    required this.legacyDeletedIndexExists,
    required this.legacyDeletedIndexContent,
    required this.activeIssuePath,
    required this.activeIssueFileExists,
    required this.createdIssue,
    required this.createdIssuePath,
    required this.createdIssueFileExists,
    required this.createdIssueMarkdown,
    required this.createdIssueSearchResults,
    required this.activeIssueSearchResults,
    required this.projectSearchResults,
    required this.headRevision,
    required this.parentOfHead,
    required this.latestCommitSubject,
    required this.latestCommitFiles,
    required this.worktreeStatusLines,
  });

  final TrackerSnapshot snapshot;
  final String legacyDeletedIndexPath;
  final bool legacyDeletedIndexExists;
  final String? legacyDeletedIndexContent;
  final String activeIssuePath;
  final bool activeIssueFileExists;
  final TrackStateIssue? createdIssue;
  final String? createdIssuePath;
  final bool createdIssueFileExists;
  final String? createdIssueMarkdown;
  final List<TrackStateIssue> createdIssueSearchResults;
  final List<TrackStateIssue> activeIssueSearchResults;
  final List<TrackStateIssue> projectSearchResults;
  final String headRevision;
  final String? parentOfHead;
  final String? latestCommitSubject;
  final List<String> latestCommitFiles;
  final List<String> worktreeStatusLines;
}
