import 'dart:convert';
import 'dart:io';

import 'package:trackstate/domain/models/trackstate_models.dart';

import '../components/services/issue_aggregate_probe.dart';
import '../components/services/issue_link_storage_probe.dart';
import '../core/interfaces/dirty_local_issue_write_client.dart';
import '../core/interfaces/local_git_repository_factory.dart';

class LocalGitLinkStorageFixtureConfig {
  const LocalGitLinkStorageFixtureConfig({
    required this.ticketKey,
    required this.tempDirectoryPrefix,
    required this.seedCommitMessage,
    required this.projectKey,
    required this.projectName,
    required this.epicKey,
    required this.sourceIssueKey,
    required this.sourceIssueSummary,
    required this.sourceIssueDescription,
    required this.targetIssueKey,
    required this.targetIssueSummary,
    required this.targetIssueDescription,
    required this.sourceIssuePath,
    required this.targetIssuePath,
    required this.sourceLinksPath,
  });

  final String ticketKey;
  final String tempDirectoryPrefix;
  final String seedCommitMessage;
  final String projectKey;
  final String projectName;
  final String epicKey;
  final String sourceIssueKey;
  final String sourceIssueSummary;
  final String sourceIssueDescription;
  final String targetIssueKey;
  final String targetIssueSummary;
  final String targetIssueDescription;
  final String sourceIssuePath;
  final String targetIssuePath;
  final String sourceLinksPath;

  Map<String, String> buildFixtureFiles() => <String, String>{
    '$projectKey/project.json': '{"key":"$projectKey","name":"$projectName"}\n',
    '$projectKey/config/statuses.json':
        '${jsonEncode(<Map<String, String>>[
          <String, String>{'id': 'todo', 'name': 'To Do'},
          <String, String>{'id': 'in-review', 'name': 'In Review'},
        ])}\n',
    '$projectKey/config/issue-types.json':
        '${jsonEncode(<Map<String, Object?>>[
          <String, Object?>{'id': 'epic', 'name': 'Epic', 'hierarchyLevel': 1},
          <String, Object?>{'id': 'story', 'name': 'Story', 'hierarchyLevel': 0},
        ])}\n',
    '$projectKey/config/fields.json':
        '${jsonEncode(<Map<String, Object?>>[
          <String, Object?>{'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
          <String, Object?>{'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
        ])}\n',
    '$projectKey/config/priorities.json':
        '${jsonEncode(<Map<String, String>>[
          <String, String>{'id': 'medium', 'name': 'Medium'},
          <String, String>{'id': 'high', 'name': 'High'},
        ])}\n',
    '$projectKey/.trackstate/index/issues.json':
        '${jsonEncode(<Map<String, Object?>>[
          <String, Object?>{
            'key': epicKey,
            'path': '$projectKey/$epicKey/main.md',
            'parent': null,
            'epic': null,
            'children': <String>[sourceIssueKey],
            'archived': false,
          },
          <String, Object?>{'key': sourceIssueKey, 'path': sourceIssuePath, 'parent': null, 'epic': epicKey, 'children': const <String>[], 'archived': false},
          <String, Object?>{'key': targetIssueKey, 'path': targetIssuePath, 'parent': null, 'epic': null, 'children': const <String>[], 'archived': false},
        ])}\n',
    '$projectKey/.trackstate/index/tombstones.json': '[]\n',
    '$projectKey/$epicKey/main.md':
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

Root epic for $ticketKey.
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

$sourceIssueDescription
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

$targetIssueDescription
''',
  };
}

typedef DirtyLocalIssueWriteClientBuilder =
    DirtyLocalIssueWriteClient Function(String repositoryPath);

class LocalGitLinkStorageFixture {
  LocalGitLinkStorageFixture._({
    required this.directory,
    required this.config,
    required LocalGitRepositoryFactory repositoryFactory,
    required DirtyLocalIssueWriteClient writeClient,
  }) : _repositoryFactory = repositoryFactory,
       _storageProbe = IssueLinkStorageProbe(writeClient: writeClient);

  final Directory directory;
  final LocalGitLinkStorageFixtureConfig config;
  final LocalGitRepositoryFactory _repositoryFactory;
  final IssueLinkStorageProbe _storageProbe;

  String get repositoryPath => directory.path;

  static Future<LocalGitLinkStorageFixture> create({
    required LocalGitLinkStorageFixtureConfig config,
    required LocalGitRepositoryFactory repositoryFactory,
    required DirtyLocalIssueWriteClientBuilder writeClientBuilder,
  }) async {
    final directory = await Directory.systemTemp.createTemp(
      config.tempDirectoryPrefix,
    );
    final fixture = LocalGitLinkStorageFixture._(
      directory: directory,
      config: config,
      repositoryFactory: repositoryFactory,
      writeClient: writeClientBuilder(directory.path),
    );
    await fixture._seedRepository();
    return fixture;
  }

  String encodeLinksJson(List<Map<String, String>> records) =>
      '${jsonEncode(records)}\n';

  Future<void> dispose() => directory.delete(recursive: true);

  Future<LocalGitLinkStorageRepositoryObservation>
  observeRepositoryState() async {
    final repository = await _repositoryFactory.create(
      repositoryPath: repositoryPath,
    );
    final sourceIssue = await IssueAggregateProbe(
      repository,
    ).loadIssue(config.sourceIssueKey);
    final projectSearchResults = await repository.searchIssues(
      'project = ${config.projectKey}',
    );
    final linksFile = File('$repositoryPath/${config.sourceLinksPath}');
    final linksFileExists = await linksFile.exists();
    final linksFileContent = linksFileExists
        ? await linksFile.readAsString()
        : null;
    return LocalGitLinkStorageRepositoryObservation(
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

  Future<LocalGitLinkStorageAttemptObservation> attemptLinksWrite({
    required String content,
    required String message,
  }) async {
    final writeResult = await _storageProbe.attemptWrite(
      path: config.sourceLinksPath,
      content: content,
      message: message,
      expectedRevision: null,
    );

    return LocalGitLinkStorageAttemptObservation(
      branch: writeResult.branch,
      attemptedPath: config.sourceLinksPath,
      attemptedContent: content,
      writeRevision: writeResult.writeRevision,
      errorType: writeResult.errorType,
      errorMessage: writeResult.errorMessage,
      afterObservation: await observeRepositoryState(),
    );
  }

  Future<void> _seedRepository() async {
    for (final entry in config.buildFixtureFiles().entries) {
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
    await _git(<String>['commit', '-m', config.seedCommitMessage]);
  }

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

class LocalGitLinkStorageRepositoryObservation {
  const LocalGitLinkStorageRepositoryObservation({
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

class LocalGitLinkStorageAttemptObservation {
  const LocalGitLinkStorageAttemptObservation({
    required this.branch,
    required this.attemptedPath,
    required this.attemptedContent,
    required this.writeRevision,
    required this.errorType,
    required this.errorMessage,
    required this.afterObservation,
  });

  final String branch;
  final String attemptedPath;
  final String attemptedContent;
  final String? writeRevision;
  final String? errorType;
  final String? errorMessage;
  final LocalGitLinkStorageRepositoryObservation afterObservation;
}
