import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../../components/services/issue_aggregate_probe.dart';

class Ts627NonCanonicalLinkStorageFixture {
  Ts627NonCanonicalLinkStorageFixture._(this.directory);

  final Directory directory;

  static const projectKey = 'DEMO';
  static const epicKey = 'DEMO-1';
  static const sourceIssueKey = 'DEMO-2';
  static const sourceIssueSummary = 'Source story';
  static const targetIssueKey = 'DEMO-10';
  static const targetIssueSummary = 'Blocking epic';
  static const sourceIssuePath = 'DEMO/DEMO-1/DEMO-2/main.md';
  static const targetIssuePath = 'DEMO/DEMO-10/main.md';
  static const sourceLinksPath = 'DEMO/DEMO-1/DEMO-2/links.json';
  static const writeMessage = 'Attempt non-canonical link storage for TS-627';
  static const Map<String, String> invalidLinkRecord = <String, String>{
    'type': 'blocks',
    'target': targetIssueKey,
    'direction': 'inward',
  };

  String get repositoryPath => directory.path;

  String get invalidLinksJsonContent =>
      '${jsonEncode(<Map<String, String>>[invalidLinkRecord])}\n';

  static Future<Ts627NonCanonicalLinkStorageFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-627-',
    );
    final fixture = Ts627NonCanonicalLinkStorageFixture._(directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts627RepositoryObservation> observeRepositoryState() async {
    final opened = await _openRepository();
    final sourceIssue = await opened.issueLoader.loadIssue(sourceIssueKey);
    final projectSearchResults = await opened.repository.searchIssues(
      'project = $projectKey',
    );
    final linksFile = File('$repositoryPath/$sourceLinksPath');
    final linksFileExists = await linksFile.exists();
    final linksFileContent = linksFileExists
        ? await linksFile.readAsString()
        : null;
    return Ts627RepositoryObservation(
      repositoryPath: repositoryPath,
      sourceIssue: sourceIssue,
      projectSearchResults: List<TrackStateIssue>.unmodifiable(
        projectSearchResults,
      ),
      linksFileExists: linksFileExists,
      linksFileContent: linksFileContent,
      headRevision: await _gitStdout(<String>['rev-parse', 'HEAD']),
      latestCommitSubject: await _gitStdout(<String>[
        'log',
        '-1',
        '--pretty=%s',
      ]),
      worktreeStatusLines: List<String>.unmodifiable(
        await _gitLines(<String>['status', '--short']),
      ),
    );
  }

  Future<Ts627StorageAttemptObservation> attemptInvalidLinksWrite() async {
    final opened = await _openRepository();
    final branch = await opened.provider.resolveWriteBranch();
    RepositoryWriteResult? writeResult;
    String? errorType;
    String? errorMessage;

    try {
      writeResult = await opened.provider.writeTextFile(
        RepositoryWriteRequest(
          path: sourceLinksPath,
          content: invalidLinksJsonContent,
          message: writeMessage,
          branch: branch,
          expectedRevision: null,
        ),
      );
    } catch (error) {
      errorType = error.runtimeType.toString();
      errorMessage = error.toString();
    }

    return Ts627StorageAttemptObservation(
      branch: branch,
      attemptedPath: sourceLinksPath,
      attemptedContent: invalidLinksJsonContent,
      writeResult: writeResult,
      errorType: errorType,
      errorMessage: errorMessage,
      afterObservation: await observeRepositoryState(),
    );
  }

  Future<_OpenedRepository> _openRepository() async {
    final provider = LocalGitTrackStateProvider(repositoryPath: repositoryPath);
    final repository = ProviderBackedTrackStateRepository(
      provider: provider,
      usesLocalPersistence: true,
      supportsGitHubAuth: false,
    );
    final snapshot = await repository.loadSnapshot();
    await repository.connect(
      RepositoryConnection(
        repository: snapshot.project.repository,
        branch: snapshot.project.branch,
        token: '',
      ),
    );
    return _OpenedRepository(
      repository: repository,
      provider: provider,
      issueLoader: IssueAggregateProbe(repository),
    );
  }

  Future<void> _seedRepository() async {
    for (final entry in _fixtureFiles().entries) {
      await _writeFile(entry.key, entry.value);
    }

    await _git(<String>['init', '-b', 'main']);
    await _git(<String>['config', '--local', 'user.name', 'Local Tester']);
    await _git(<String>[
      'config',
      '--local',
      'user.email',
      'local@example.com',
    ]);
    await _git(<String>['add', '.']);
    await _git(<String>[
      'commit',
      '-m',
      'Seed non-canonical link fixture for TS-627',
    ]);
  }

  Map<String, String> _fixtureFiles() => <String, String>{
    'DEMO/project.json': '{"key":"DEMO","name":"Mutation Demo"}\n',
    'DEMO/config/statuses.json':
        '${jsonEncode(<Map<String, String>>[
          <String, String>{'id': 'todo', 'name': 'To Do'},
          <String, String>{'id': 'in-review', 'name': 'In Review'},
        ])}\n',
    'DEMO/config/issue-types.json':
        '${jsonEncode(<Map<String, Object?>>[
          <String, Object?>{'id': 'epic', 'name': 'Epic', 'hierarchyLevel': 1},
          <String, Object?>{'id': 'story', 'name': 'Story', 'hierarchyLevel': 0},
        ])}\n',
    'DEMO/config/fields.json':
        '${jsonEncode(<Map<String, Object?>>[
          <String, Object?>{'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
          <String, Object?>{'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
        ])}\n',
    'DEMO/config/priorities.json':
        '${jsonEncode(<Map<String, String>>[
          <String, String>{'id': 'medium', 'name': 'Medium'},
          <String, String>{'id': 'high', 'name': 'High'},
        ])}\n',
    'DEMO/.trackstate/index/issues.json':
        '${jsonEncode(<Map<String, Object?>>[
          <String, Object?>{
            'key': epicKey,
            'path': 'DEMO/DEMO-1/main.md',
            'parent': null,
            'epic': null,
            'children': <String>[sourceIssueKey],
            'archived': false,
          },
          <String, Object?>{'key': sourceIssueKey, 'path': sourceIssuePath, 'parent': null, 'epic': epicKey, 'children': const <String>[], 'archived': false},
          <String, Object?>{'key': targetIssueKey, 'path': targetIssuePath, 'parent': null, 'epic': null, 'children': const <String>[], 'archived': false},
        ])}\n',
    'DEMO/.trackstate/index/tombstones.json': '[]\n',
    'DEMO/DEMO-1/main.md':
        '''
---
key: $epicKey
project: $projectKey
issueType: epic
status: in-review
priority: high
summary: Platform epic
updated: 2026-05-05T00:00:00Z
---

# Summary

Platform epic

# Description

Root epic for TS-627.
''',
    sourceIssuePath:
        '''
---
key: $sourceIssueKey
project: $projectKey
issueType: story
status: in-review
priority: medium
summary: $sourceIssueSummary
epic: $epicKey
updated: 2026-05-05T00:05:00Z
---

# Summary

$sourceIssueSummary

# Description

Issue used as the source issue for TS-627 invalid link storage attempts.
''',
    targetIssuePath:
        '''
---
key: $targetIssueKey
project: $projectKey
issueType: epic
status: todo
priority: medium
summary: $targetIssueSummary
updated: 2026-05-05T00:15:00Z
---

# Summary

$targetIssueSummary

# Description

Issue used as the linked target for TS-627 invalid link storage attempts.
''',
  };

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('${directory.path}/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', <String>[
      '-C',
      directory.path,
      ...args,
    ]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }

  Future<String> _gitStdout(List<String> args) async {
    final result = await Process.run('git', <String>[
      '-C',
      directory.path,
      ...args,
    ]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString().trim();
  }

  Future<List<String>> _gitLines(List<String> args) async {
    final stdout = await _gitStdout(args);
    if (stdout.isEmpty) {
      return const <String>[];
    }
    return LineSplitter.split(stdout).toList(growable: false);
  }
}

class Ts627RepositoryObservation {
  const Ts627RepositoryObservation({
    required this.repositoryPath,
    required this.sourceIssue,
    required this.projectSearchResults,
    required this.linksFileExists,
    required this.linksFileContent,
    required this.headRevision,
    required this.latestCommitSubject,
    required this.worktreeStatusLines,
  });

  final String repositoryPath;
  final TrackStateIssue sourceIssue;
  final List<TrackStateIssue> projectSearchResults;
  final bool linksFileExists;
  final String? linksFileContent;
  final String headRevision;
  final String latestCommitSubject;
  final List<String> worktreeStatusLines;
}

class Ts627StorageAttemptObservation {
  const Ts627StorageAttemptObservation({
    required this.branch,
    required this.attemptedPath,
    required this.attemptedContent,
    required this.writeResult,
    required this.errorType,
    required this.errorMessage,
    required this.afterObservation,
  });

  final String branch;
  final String attemptedPath;
  final String attemptedContent;
  final RepositoryWriteResult? writeResult;
  final String? errorType;
  final String? errorMessage;
  final Ts627RepositoryObservation afterObservation;
}

class _OpenedRepository {
  const _OpenedRepository({
    required this.repository,
    required this.provider,
    required this.issueLoader,
  });

  final ProviderBackedTrackStateRepository repository;
  final LocalGitTrackStateProvider provider;
  final IssueAggregateProbe issueLoader;
}
