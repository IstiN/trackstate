import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts66DeletedIssueFixture {
  Ts66DeletedIssueFixture._({
    required this.directory,
    required this.beforeDeletionRef,
    required this.afterDeletionRef,
  });

  final Directory directory;
  final String beforeDeletionRef;
  final String afterDeletionRef;

  static const deletedIssueKey = 'TRACK-123';
  static const survivingIssueKey = 'TRACK-122';
  static const deletedIssuePath = 'TRACK/$deletedIssueKey/main.md';
  static const deletedIndexPath = 'TRACK/.trackstate/index/deleted.json';

  static Future<Ts66DeletedIssueFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-66-',
    );
    final fixture = Ts66DeletedIssueFixture._(
      directory: directory,
      beforeDeletionRef: '',
      afterDeletionRef: '',
    );
    return fixture._seedRepository();
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts66DeletedIssueObservation> observeBeforeDeletionState() =>
      _observeRepositoryState(beforeDeletionRef);

  Future<Ts66DeletedIssueObservation> observeAfterDeletionState() =>
      _observeRepositoryState(afterDeletionRef);

  Future<Ts66DeletedIssueObservation> _observeRepositoryState(
    String ref,
  ) async {
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
      dataRef: ref,
    );
    final snapshot = await repository.loadSnapshot();
    final deletedIssueFileExists = await _pathExistsAtRef(
      ref,
      deletedIssuePath,
    );
    final deletedIndexExists = await _pathExistsAtRef(ref, deletedIndexPath);
    final deletedIndexEntries = deletedIndexExists
        ? _jsonList(await _readTextAtRef(ref, deletedIndexPath))
        : const <Map<String, Object?>>[];

    return Ts66DeletedIssueObservation(
      snapshot: snapshot,
      deletedIssuePath: deletedIssuePath,
      deletedIssueFileExists: deletedIssueFileExists,
      deletedIndexPath: deletedIndexPath,
      deletedIndexExists: deletedIndexExists,
      deletedIndexEntries: List<Map<String, Object?>>.unmodifiable(
        deletedIndexEntries,
      ),
      deletedIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $deletedIssueKey'),
      ),
      activeIssueSearchResults: List<TrackStateIssue>.unmodifiable(
        await repository.searchIssues('project = TRACK $survivingIssueKey'),
      ),
    );
  }

  Future<Ts66DeletedIssueFixture> _seedRepository() async {
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
    await _writeFile('TRACK/$survivingIssueKey/main.md', '''
---
key: $survivingIssueKey
project: TRACK
issueType: story
status: todo
summary: Surviving issue
updated: 2026-05-06T10:00:00Z
---

# Description

This issue remains active after TRACK-123 is deleted.
''');
    await _writeFile(deletedIssuePath, '''
---
key: $deletedIssueKey
project: TRACK
issueType: story
status: done
summary: Deleted story
updated: 2026-05-06T12:00:00Z
---

# Description

This issue is deleted in the second repository revision.
''');

    await _git(['init', '-b', 'main']);
    await _git(['config', 'user.name', 'Local Tester']);
    await _git(['config', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed active issues for TS-66']);
    final beforeDeletionRef = await _gitOutput(['rev-parse', 'HEAD']);

    final deletedIssue = await _loadDeletedIssueRecord(deletedIssuePath);
    await _git(['rm', '--', deletedIssuePath]);
    await _rebuildDeletedIndexFromStagedDeletes([deletedIssue]);
    await _git(['add', '-A']);
    await _git(['commit', '-m', 'Delete TRACK-123 and reserve its key']);
    final afterDeletionRef = await _gitOutput(['rev-parse', 'HEAD']);

    return Ts66DeletedIssueFixture._(
      directory: directory,
      beforeDeletionRef: beforeDeletionRef,
      afterDeletionRef: afterDeletionRef,
    );
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
    return result.stdout.toString().trim();
  }

  Future<void> _rebuildDeletedIndexFromStagedDeletes(
    List<_DeletedIssueRecord> deletedIssues,
  ) async {
    final deletedPaths = (await _gitOutput([
      'diff',
      '--cached',
      '--name-only',
      '--diff-filter=D',
    ])).split('\n')..removeWhere((path) => path.trim().isEmpty);
    final entries = deletedIssues
        .where((issue) => deletedPaths.contains(issue.formerPath))
        .map((issue) => issue.toJson())
        .toList(growable: false);
    if (entries.isEmpty) {
      throw StateError(
        'Expected a staged deleted issue before rebuilding TS-66 deleted.json.',
      );
    }
    await _writeFile(
      deletedIndexPath,
      const JsonEncoder.withIndent('  ').convert(entries),
    );
  }

  Future<_DeletedIssueRecord> _loadDeletedIssueRecord(
    String relativePath,
  ) async {
    final content = await File(
      '${directory.path}/$relativePath',
    ).readAsString();
    final metadata = _frontmatter(content);
    return _DeletedIssueRecord(
      key: metadata['key'] ?? '',
      project: metadata['project'] ?? '',
      formerPath: relativePath,
      deletedAt: metadata['updated'] ?? '',
      summary: metadata['summary'] ?? '',
      issueType: metadata['issueType'] ?? '',
      parent: _nullable(metadata['parent']),
      epic: _nullable(metadata['epic']),
    );
  }

  Future<bool> _pathExistsAtRef(String ref, String path) async {
    final result = await Process.run('git', [
      '-C',
      directory.path,
      'cat-file',
      '-e',
      '$ref:$path',
    ]);
    return result.exitCode == 0;
  }

  Future<String> _readTextAtRef(String ref, String path) async {
    final result = await Process.run('git', [
      '-C',
      directory.path,
      'show',
      '$ref:$path',
    ]);
    if (result.exitCode != 0) {
      throw StateError('git show $ref:$path failed: ${result.stderr}');
    }
    return result.stdout.toString();
  }

  List<Map<String, Object?>> _jsonList(String content) {
    final json = jsonDecode(content);
    if (json is! List) {
      throw StateError('Expected a JSON list.');
    }
    return json
        .whereType<Map>()
        .map(
          (entry) => {
            for (final mapEntry in entry.entries)
              mapEntry.key.toString(): mapEntry.value,
          },
        )
        .toList(growable: false);
  }

  Map<String, String> _frontmatter(String markdown) {
    final lines = const LineSplitter().convert(markdown);
    if (lines.length < 3 || lines.first.trim() != '---') {
      throw StateError(
        'Expected YAML frontmatter in TS-66 fixture issue markdown.',
      );
    }
    final metadata = <String, String>{};
    for (final line in lines.skip(1)) {
      if (line.trim() == '---') {
        break;
      }
      final separator = line.indexOf(':');
      if (separator <= 0) {
        continue;
      }
      metadata[line.substring(0, separator).trim()] = line
          .substring(separator + 1)
          .trim();
    }
    return metadata;
  }

  String? _nullable(String? value) {
    if (value == null) {
      return null;
    }
    final normalized = value.trim();
    if (normalized.isEmpty || normalized.toLowerCase() == 'null') {
      return null;
    }
    return normalized;
  }
}

class Ts66DeletedIssueObservation {
  const Ts66DeletedIssueObservation({
    required this.snapshot,
    required this.deletedIssuePath,
    required this.deletedIssueFileExists,
    required this.deletedIndexPath,
    required this.deletedIndexExists,
    required this.deletedIndexEntries,
    required this.deletedIssueSearchResults,
    required this.activeIssueSearchResults,
  });

  final TrackerSnapshot snapshot;
  final String deletedIssuePath;
  final bool deletedIssueFileExists;
  final String deletedIndexPath;
  final bool deletedIndexExists;
  final List<Map<String, Object?>> deletedIndexEntries;
  final List<TrackStateIssue> deletedIssueSearchResults;
  final List<TrackStateIssue> activeIssueSearchResults;
}

class _DeletedIssueRecord {
  const _DeletedIssueRecord({
    required this.key,
    required this.project,
    required this.formerPath,
    required this.deletedAt,
    required this.summary,
    required this.issueType,
    required this.parent,
    required this.epic,
  });

  final String key;
  final String project;
  final String formerPath;
  final String deletedAt;
  final String summary;
  final String issueType;
  final String? parent;
  final String? epic;

  Map<String, Object?> toJson() => {
    'key': key,
    'project': project,
    'formerPath': formerPath,
    'deletedAt': deletedAt,
    'summary': summary,
    'issueType': issueType,
    'parent': parent,
    'epic': epic,
  };
}
