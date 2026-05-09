import 'dart:io';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import 'ts174_existing_issue_archive_fixture.dart';

class Ts212MissingArchiveDirectoryFixture {
  Ts212MissingArchiveDirectoryFixture._({
    required Ts174ExistingIssueArchiveFixture base,
  }) : _base = base;

  final Ts174ExistingIssueArchiveFixture _base;

  Directory get directory => _base.directory;

  static const issueKey = Ts174ExistingIssueArchiveFixture.issueKey;
  static const issuePath = Ts174ExistingIssueArchiveFixture.issuePath;
  static const archiveRootPath = 'TRACK/.trackstate/archive';
  static const archivedIssueDirectoryPath = '$archiveRootPath/$issueKey';
  static const archivedIssuePath = '$archivedIssueDirectoryPath/main.md';

  static Future<Ts212MissingArchiveDirectoryFixture> create() async {
    final base = await Ts174ExistingIssueArchiveFixture.create();
    return Ts212MissingArchiveDirectoryFixture._(base: base);
  }

  Future<void> dispose() => _base.dispose();

  Future<TrackStateIssue> archiveIssueViaRepositoryService({
    required TrackStateRepository repository,
  }) => _base.archiveIssueViaRepositoryService(repository: repository);

  Future<Ts212MissingArchiveDirectoryObservation> observeRepositoryState({
    required TrackStateRepository repository,
    TrackStateIssue? archivedIssue,
  }) async {
    final snapshot = await repository.loadSnapshot();
    final issueFile = File('${directory.path}/$issuePath');
    final archiveRootDirectory = Directory(
      '${directory.path}/$archiveRootPath',
    );
    final archivedIssueDirectory = Directory(
      '${directory.path}/$archivedIssueDirectoryPath',
    );
    final archivedIssueFile = File('${directory.path}/$archivedIssuePath');

    return Ts212MissingArchiveDirectoryObservation(
      repositoryPath: directory.path,
      snapshot: snapshot,
      currentIssue: snapshot.issues.singleWhere(
        (candidate) => candidate.key == issueKey,
      ),
      archivedIssue: archivedIssue,
      issueFileExists: await issueFile.exists(),
      archiveRootExists: await archiveRootDirectory.exists(),
      archivedIssueDirectoryExists: await archivedIssueDirectory.exists(),
      archivedIssueFileExists: await archivedIssueFile.exists(),
      mainMarkdown: await _readFileIfExists(issueFile),
      archivedMainMarkdown: await _readFileIfExists(archivedIssueFile),
      headIssueMarkdown: await _tryGitOutput(['show', 'HEAD:$issuePath']),
      headArchivedIssueMarkdown: await _tryGitOutput([
        'show',
        'HEAD:$archivedIssuePath',
      ]),
      headRevision: await _gitOutput(['rev-parse', 'HEAD']),
      latestCommitSubject: await _gitOutput(['log', '-1', '--pretty=%s']),
      visibleIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $issueKey'),
      ),
      worktreeStatusLines: await _gitOutputLines(['status', '--short']),
    );
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

class Ts212MissingArchiveDirectoryObservation {
  const Ts212MissingArchiveDirectoryObservation({
    required this.repositoryPath,
    required this.snapshot,
    required this.currentIssue,
    required this.issueFileExists,
    required this.archiveRootExists,
    required this.archivedIssueDirectoryExists,
    required this.archivedIssueFileExists,
    required this.mainMarkdown,
    required this.archivedMainMarkdown,
    required this.headIssueMarkdown,
    required this.headArchivedIssueMarkdown,
    required this.headRevision,
    required this.latestCommitSubject,
    required this.visibleIssueSearchResults,
    required this.worktreeStatusLines,
    this.archivedIssue,
  });

  final String repositoryPath;
  final TrackerSnapshot snapshot;
  final TrackStateIssue currentIssue;
  final TrackStateIssue? archivedIssue;
  final bool issueFileExists;
  final bool archiveRootExists;
  final bool archivedIssueDirectoryExists;
  final bool archivedIssueFileExists;
  final String? mainMarkdown;
  final String? archivedMainMarkdown;
  final String? headIssueMarkdown;
  final String? headArchivedIssueMarkdown;
  final String headRevision;
  final String latestCommitSubject;
  final List<TrackStateIssue> visibleIssueSearchResults;
  final List<String> worktreeStatusLines;
}
