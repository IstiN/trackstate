import 'dart:convert';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_deletion_port.dart';

class IssueDeletionService {
  const IssueDeletionService(this._port);

  final IssueDeletionPort _port;

  Future<DeletedIssueOperationResult> deleteIssue({
    required String key,
    required String deletedAt,
  }) async {
    final permission = await _port.getPermission();
    if (!permission.canWrite) {
      throw StateError('Issue deletion requires repository write access.');
    }

    final snapshot = await _port.loadSnapshot();
    final issue = _findIssue(snapshot.issues, key);
    final writeBranch = await _port.resolveWriteBranch();
    final blobPaths = (await _port.listTree(ref: writeBranch))
        .where((entry) => entry.type == 'blob')
        .map((entry) => entry.path)
        .toSet();
    final issueIndexPath = '${issue.project}/.trackstate/index/issues.json';
    final deletedIndexPath = '${issue.project}/.trackstate/index/deleted.json';
    final tombstoneArtifactPath =
        '${issue.project}/.trackstate/tombstones/$key.json';
    final tombstoneIndexPath =
        '${issue.project}/.trackstate/index/tombstones.json';
    final issueIndexFile = await _port.readTextFile(
      issueIndexPath,
      ref: writeBranch,
    );
    final issueIndexEntries = _readJsonList(
      issueIndexFile.content,
      path: issueIndexPath,
    );
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
      ...await _readOptionalJsonList(
        blobPaths: blobPaths,
        path: tombstoneIndexPath,
        ref: writeBranch,
      ),
      tombstoneEntry,
    ];
    final deletedIndexEntries = [
      ...await _readOptionalJsonList(
        blobPaths: blobPaths,
        path: deletedIndexPath,
        ref: writeBranch,
      ),
      tombstoneEntry,
    ];

    await _writeJsonFile(
      path: issueIndexPath,
      value: updatedIssueIndexEntries,
      branch: writeBranch,
      message: 'Delete $key from the active issue index',
      expectedRevision: issueIndexFile.revision,
    );
    await _writeJsonFile(
      path: tombstoneArtifactPath,
      value: tombstoneEntry,
      branch: writeBranch,
      message: 'Write tombstone artifact for $key',
      expectedRevision: null,
    );
    await _writeJsonFile(
      path: tombstoneIndexPath,
      value: tombstoneIndexEntries,
      branch: writeBranch,
      message: 'Reserve deleted key $key in tombstones index',
      expectedRevision: await _expectedRevisionForOptionalPath(
        blobPaths: blobPaths,
        path: tombstoneIndexPath,
        ref: writeBranch,
      ),
    );
    await _writeJsonFile(
      path: deletedIndexPath,
      value: deletedIndexEntries,
      branch: writeBranch,
      message: 'Mirror deleted tombstone metadata for $key',
      expectedRevision: await _expectedRevisionForOptionalPath(
        blobPaths: blobPaths,
        path: deletedIndexPath,
        ref: writeBranch,
      ),
    );

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

  Future<List<Map<String, Object?>>> _readOptionalJsonList({
    required Set<String> blobPaths,
    required String path,
    required String ref,
  }) async {
    if (!blobPaths.contains(path)) {
      return const <Map<String, Object?>>[];
    }
    final file = await _port.readTextFile(path, ref: ref);
    return _readJsonList(file.content, path: path);
  }

  Future<String?> _expectedRevisionForOptionalPath({
    required Set<String> blobPaths,
    required String path,
    required String ref,
  }) async {
    if (!blobPaths.contains(path)) {
      return null;
    }
    final file = await _port.readTextFile(path, ref: ref);
    return file.revision;
  }

  List<Map<String, Object?>> _readJsonList(
    String content, {
    required String path,
  }) {
    final json = jsonDecode(content);
    if (json is! List) {
      throw StateError('Expected $path to contain a JSON list.');
    }
    return json.whereType<Map>().map(_mapEntry).toList(growable: false);
  }

  Future<void> _writeJsonFile({
    required String path,
    required Object value,
    required String branch,
    required String message,
    required String? expectedRevision,
  }) async {
    await _port.writeTextFile(
      RepositoryWriteRequest(
        path: path,
        content: '${const JsonEncoder.withIndent('  ').convert(value)}\n',
        message: message,
        branch: branch,
        expectedRevision: expectedRevision,
      ),
    );
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
