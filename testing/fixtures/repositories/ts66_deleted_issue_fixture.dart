import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts66DeletedIssueFixture {
  Ts66DeletedIssueFixture._(this.directory);

  final Directory directory;
  bool _deletedIndexExistsBeforeDeletion = false;
  List<TrackStateIssue> _deletedIssueSearchResultsBeforeDeletion = const [];

  static Future<Ts66DeletedIssueFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-66-',
    );
    final fixture = Ts66DeletedIssueFixture._(directory);
    await fixture._seedRepository();
    await fixture._deleteIssue(
      key: 'TRACK-123',
      deletedAt: '2026-05-06T12:00:00Z',
    );
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts66DeletedIssueObservation> observeDeletedIssueBehavior() async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final snapshot = await repository.loadSnapshot();
    final deletedIndexPath = 'TRACK/.trackstate/index/deleted.json';
    final deletedIndexFile = File('${directory.path}/$deletedIndexPath');
    final deletedIndexExists = await deletedIndexFile.exists();
    final deletedIndexEntries = deletedIndexExists
        ? (jsonDecode(await deletedIndexFile.readAsString()) as List<Object?>)
              .cast<Map<String, Object?>>()
        : const <Map<String, Object?>>[];

    return Ts66DeletedIssueObservation(
      snapshot: snapshot,
      deletedIndexPath: deletedIndexPath,
      deletedIndexExists: deletedIndexExists,
      deletedIndexExistsBeforeDeletion: _deletedIndexExistsBeforeDeletion,
      deletedIndexEntries: List<Map<String, Object?>>.unmodifiable(
        deletedIndexEntries,
      ),
      deletedIssueSearchResultsBeforeDeletion:
          List<TrackStateIssue>.unmodifiable(
            _deletedIssueSearchResultsBeforeDeletion,
          ),
      deletedIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK TRACK-123'),
      ),
      activeIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK TRACK-122'),
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
    await _writeFile(
      'TRACK/.trackstate/index/issues.json',
      jsonEncode([
        {
          'key': 'TRACK-122',
          'path': 'TRACK/TRACK-122/main.md',
          'parent': null,
          'epic': null,
          'children': <String>[],
          'archived': false,
        },
        {
          'key': 'TRACK-123',
          'path': 'TRACK/TRACK-123/main.md',
          'parent': null,
          'epic': null,
          'children': <String>[],
          'archived': false,
        },
      ]),
    );
    await _writeFile('TRACK/TRACK-122/main.md', '''
---
key: TRACK-122
project: TRACK
issueType: story
status: todo
summary: Surviving issue
updated: 2026-05-06T10:00:00Z
---

# Description

This issue remains active after TRACK-123 is deleted.
''');
    await _writeFile('TRACK/TRACK-123/main.md', '''
---
key: TRACK-123
project: TRACK
issueType: story
status: done
summary: Deleted story
updated: 2026-05-06T12:00:00Z
---

# Description

This issue will be deleted through the fixture workflow.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issues for deletion fixture']);
  }

  Future<void> _deleteIssue({
    required String key,
    required String deletedAt,
  }) async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    _deletedIssueSearchResultsBeforeDeletion =
        List<TrackStateIssue>.unmodifiable(
          await repository.searchIssues('project = TRACK $key'),
        );

    final deletedIndexFile = File(
      '${directory.path}/TRACK/.trackstate/index/deleted.json',
    );
    _deletedIndexExistsBeforeDeletion = await deletedIndexFile.exists();

    final issueRootPath = 'TRACK/$key';
    final issueMainPath = '$issueRootPath/main.md';
    final issueFile = File('${directory.path}/$issueMainPath');
    if (!await issueFile.exists()) {
      throw StateError('Expected $issueMainPath to exist before deletion.');
    }

    final frontmatter = _parseFrontmatter(await issueFile.readAsString());
    final issuesIndexFile = File(
      '${directory.path}/TRACK/.trackstate/index/issues.json',
    );
    final issuesIndex =
        (jsonDecode(await issuesIndexFile.readAsString()) as List<Object?>)
            .cast<Map<String, Object?>>();
    final updatedIssuesIndex = issuesIndex
        .where((entry) => entry['key'] != key)
        .toList(growable: false);
    if (updatedIssuesIndex.length != issuesIndex.length - 1) {
      throw StateError('Expected $key to be removed from issues.json.');
    }

    final deletedIndex = _deletedIndexExistsBeforeDeletion
        ? (jsonDecode(await deletedIndexFile.readAsString()) as List<Object?>)
              .cast<Map<String, Object?>>()
        : <Map<String, Object?>>[];
    deletedIndex.add({
      'key': key,
      'project': frontmatter['project'],
      'formerPath': issueMainPath,
      'deletedAt': deletedAt,
      'summary': frontmatter['summary'],
      'issueType': frontmatter['issueType'],
      'parent': frontmatter['parent'],
      'epic': frontmatter['epic'],
    });

    await Directory('${directory.path}/$issueRootPath').delete(recursive: true);
    await issuesIndexFile.writeAsString(jsonEncode(updatedIssuesIndex));
    await deletedIndexFile.parent.create(recursive: true);
    await deletedIndexFile.writeAsString(jsonEncode(deletedIndex));

    await _git(['add', '-A']);
    await _git(['commit', '-m', 'Delete TRACK-123 and reserve tombstone key']);
  }

  Map<String, String?> _parseFrontmatter(String content) {
    final lines = const LineSplitter().convert(content);
    if (lines.length < 3 || lines.first.trim() != '---') {
      throw StateError('Issue content is missing frontmatter.');
    }

    final frontmatter = <String, String?>{};
    for (final line in lines.skip(1)) {
      if (line.trim() == '---') {
        break;
      }
      final separatorIndex = line.indexOf(':');
      if (separatorIndex == -1) continue;
      final key = line.substring(0, separatorIndex).trim();
      final value = line.substring(separatorIndex + 1).trim();
      frontmatter[key] = value == 'null' ? null : value;
    }
    return frontmatter;
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

class Ts66DeletedIssueObservation {
  const Ts66DeletedIssueObservation({
    required this.snapshot,
    required this.deletedIndexPath,
    required this.deletedIndexExists,
    required this.deletedIndexExistsBeforeDeletion,
    required this.deletedIndexEntries,
    required this.deletedIssueSearchResultsBeforeDeletion,
    required this.deletedIssueSearchResults,
    required this.activeIssueSearchResults,
  });

  final TrackerSnapshot snapshot;
  final String deletedIndexPath;
  final bool deletedIndexExists;
  final bool deletedIndexExistsBeforeDeletion;
  final List<Map<String, Object?>> deletedIndexEntries;
  final List<TrackStateIssue> deletedIssueSearchResultsBeforeDeletion;
  final List<TrackStateIssue> deletedIssueSearchResults;
  final List<TrackStateIssue> activeIssueSearchResults;
}
