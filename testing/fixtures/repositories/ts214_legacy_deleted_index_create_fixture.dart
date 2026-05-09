import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/utils/local_git_repository_fixture.dart';

class Ts214LegacyDeletedIndexCreateFixture {
  Ts214LegacyDeletedIndexCreateFixture._(this._repositoryFixture);

  static const activeIssueKey = 'TRACK-699';
  static const legacyDeletedIssueKey = 'TRACK-700';
  static const activeIssuePath = 'TRACK/$activeIssueKey/main.md';
  static const legacyDeletedIndexPath = 'TRACK/.trackstate/index/deleted.json';
  static const legacyDeletedIndexContent =
      '''
[{"key":"$legacyDeletedIssueKey","project":"TRACK","formerPath":"TRACK/$legacyDeletedIssueKey/main.md","deletedAt":"2026-05-01T08:30:00Z","summary":"Legacy deleted issue","issueType":"story","parent":null,"epic":null}]
''';

  final LocalGitRepositoryFixture _repositoryFixture;

  Directory get directory => _repositoryFixture.directory;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts214LegacyDeletedIndexCreateFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-214 Tester',
      userEmail: 'ts214@example.com',
    );
    final fixture = Ts214LegacyDeletedIndexCreateFixture._(repositoryFixture);
    await fixture._seedProjectConfiguration();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<Ts214LegacyDeletedIndexCreateObservation> observeRepositoryState({
    required TrackStateRepository repository,
    TrackStateIssue? createdIssue,
  }) => _observeState(repository: repository, createdIssue: createdIssue);

  createIssueViaRepositoryService({
    required TrackStateRepository repository,
    required String summary,
    required String description,
  }) => repository.createIssue(summary: summary, description: description);

  Future<Ts214LegacyDeletedIndexCreateObservation> _observeState({
    required TrackStateRepository repository,
    TrackStateIssue? createdIssue,
  }) async {
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

  Future<void> _seedProjectConfiguration() async {
    final defaultProjectDirectory = Directory('$repositoryPath/DEMO');
    if (await defaultProjectDirectory.exists()) {
      await defaultProjectDirectory.delete(recursive: true);
    }
    await _repositoryFixture.writeFile(
      'TRACK/project.json',
      '${jsonEncode({'key': 'TRACK', 'name': 'Track Demo'})}\n',
    );
    await _repositoryFixture.writeFile(
      'TRACK/config/statuses.json',
      '${jsonEncode([
        {'id': 'todo', 'name': 'To Do'},
        {'id': 'done', 'name': 'Done'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'TRACK/config/issue-types.json',
      '${jsonEncode([
        {'id': 'story', 'name': 'Story'},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      'TRACK/config/fields.json',
      '${jsonEncode([
        {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
      ])}\n',
    );
    await _repositoryFixture.writeFile(
      legacyDeletedIndexPath,
      legacyDeletedIndexContent,
    );
    await _repositoryFixture.writeFile(activeIssuePath, '''
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
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit('Seed active issues for TS-214');
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
    if (output.isEmpty) {
      return const <String>[];
    }
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
