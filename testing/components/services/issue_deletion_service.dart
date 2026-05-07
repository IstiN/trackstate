import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class IssueDeletionService {
  const IssueDeletionService({
    required TrackStateRepository repository,
    required String repositoryPath,
  }) : _repository = repository,
       _repositoryPath = repositoryPath;

  final TrackStateRepository _repository;
  final String _repositoryPath;

  Future<DeletedIssueOperationResult> deleteIssue({
    required String key,
    required String deletedAt,
  }) async {
    final snapshot = await _repository.loadSnapshot();
    final issue = _findIssue(snapshot.issues, key);
    final issueIndexPath = '${issue.project}/.trackstate/index/issues.json';
    final deletedIndexPath = '${issue.project}/.trackstate/index/deleted.json';
    final tombstoneArtifactPath =
        '${issue.project}/.trackstate/tombstones/$key.json';
    final tombstoneIndexPath =
        '${issue.project}/.trackstate/index/tombstones.json';
    final issueRootPath = issue.storagePath.substring(
      0,
      issue.storagePath.lastIndexOf('/'),
    );
    final issueDirectory = Directory('$_repositoryPath/$issueRootPath');
    if (!await issueDirectory.exists()) {
      throw StateError(
        'Expected $issueRootPath to exist before deleting $key.',
      );
    }

    final issueIndexEntries = await _readJsonList(issueIndexPath);
    final updatedIssueIndexEntries = issueIndexEntries
        .where((entry) => entry['key'] != key)
        .toList(growable: false);
    if (updatedIssueIndexEntries.length != issueIndexEntries.length - 1) {
      throw StateError('Expected $key to be removed from $issueIndexPath.');
    }

    final tombstoneEntry = <String, Object?>{
      'key': issue.key,
      'project': issue.project,
      'formerPath': issue.storagePath,
      'deletedAt': deletedAt,
      'summary': issue.summary,
      'issueType': issue.issueTypeId,
      'parent': issue.parentKey,
      'epic': issue.epicKey,
    };
    final tombstoneIndexEntries = [
      ...await _readOptionalJsonList(tombstoneIndexPath),
      tombstoneEntry,
    ];
    final deletedIndexEntries = [
      ...await _readOptionalJsonList(deletedIndexPath),
      tombstoneEntry,
    ];

    await _git(['rm', '-r', '--', issueRootPath]);
    await _writeJsonFile(issueIndexPath, updatedIssueIndexEntries);
    await _writeJsonFile(tombstoneArtifactPath, tombstoneEntry);
    await _writeJsonFile(tombstoneIndexPath, tombstoneIndexEntries);
    await _writeJsonFile(deletedIndexPath, deletedIndexEntries);
    await _git(['add', '-A']);
    await _git(['commit', '-m', 'Delete $key and preserve tombstone metadata']);

    return DeletedIssueOperationResult(
      key: key,
      tombstoneArtifactPath: tombstoneArtifactPath,
      tombstoneIndexPath: tombstoneIndexPath,
      deletedIndexPath: deletedIndexPath,
    );
  }

  TrackStateIssue _findIssue(List<TrackStateIssue> issues, String key) {
    for (final issue in issues) {
      if (issue.key == key) {
        return issue;
      }
    }
    throw StateError('Issue $key was not found in the repository snapshot.');
  }

  Future<List<Map<String, Object?>>> _readJsonList(String relativePath) async {
    final file = File('$_repositoryPath/$relativePath');
    if (!await file.exists()) {
      throw StateError('Expected $relativePath to exist.');
    }
    final json = jsonDecode(await file.readAsString());
    if (json is! List) {
      throw StateError('Expected $relativePath to contain a JSON list.');
    }
    return json.whereType<Map>().map(_mapEntry).toList(growable: false);
  }

  Future<List<Map<String, Object?>>> _readOptionalJsonList(
    String relativePath,
  ) async {
    final file = File('$_repositoryPath/$relativePath');
    if (!await file.exists()) {
      return const <Map<String, Object?>>[];
    }
    final json = jsonDecode(await file.readAsString());
    if (json is! List) {
      throw StateError('Expected $relativePath to contain a JSON list.');
    }
    return json.whereType<Map>().map(_mapEntry).toList(growable: false);
  }

  Future<void> _writeJsonFile(String relativePath, Object value) async {
    final file = File('$_repositoryPath/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(
      '${const JsonEncoder.withIndent('  ').convert(value)}\n',
    );
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', ['-C', _repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }

  Map<String, Object?> _mapEntry(Map<dynamic, dynamic> entry) => {
    for (final mapEntry in entry.entries)
      mapEntry.key.toString(): mapEntry.value,
  };
}

class DeletedIssueOperationResult {
  const DeletedIssueOperationResult({
    required this.key,
    required this.tombstoneArtifactPath,
    required this.tombstoneIndexPath,
    required this.deletedIndexPath,
  });

  final String key;
  final String tombstoneArtifactPath;
  final String tombstoneIndexPath;
  final String deletedIndexPath;
}
