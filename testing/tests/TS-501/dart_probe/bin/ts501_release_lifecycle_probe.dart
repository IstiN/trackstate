import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import '../../../../../lib/data/providers/github/github_trackstate_provider.dart';
import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

Future<void> main() async {
  final result = <String, Object?>{'status': 'failed'};

  try {
    final repositoryName = _requireEnv('TS501_REPOSITORY');
    final ref = _requireEnv('TS501_REF');
    final token = _requireEnv('TS501_TOKEN');
    final issueKey = _requireEnv('TS501_ISSUE_KEY');
    final attachmentName = _requireEnv('TS501_ATTACHMENT_NAME');
    final attachmentText = _requireEnv('TS501_ATTACHMENT_TEXT');
    final releaseTagPrefix = _requireEnv('TS501_RELEASE_TAG_PREFIX');

    final provider = GitHubTrackStateProvider(
      repositoryName: repositoryName,
      sourceRef: ref,
      dataRef: ref,
    );
    final repository = ProviderBackedTrackStateRepository(provider: provider);

    await repository.connect(
      RepositoryConnection(
        repository: repositoryName,
        branch: ref,
        token: token,
      ),
    );

    final snapshot = await repository.loadSnapshot();
    final issue = snapshot.issues.firstWhere(
      (candidate) => candidate.key == issueKey,
      orElse: () => throw StateError('Issue $issueKey was not found in the live snapshot.'),
    );
    final resolvedWriteBranch = await provider.resolveWriteBranch();
    final uploadedIssue = await repository.uploadIssueAttachment(
      issue: issue,
      name: attachmentName,
      bytes: Uint8List.fromList(utf8.encode(attachmentText)),
    );
    final uploadedAttachment = uploadedIssue.attachments
        .where((attachment) => attachment.name == attachmentName)
        .toList(growable: false)
        .lastOrNull;

    result.addAll(<String, Object?>{
      'status': 'passed',
      'repository': repositoryName,
      'ref': ref,
      'issueKey': issueKey,
      'issueSummary': issue.summary,
      'resolvedWriteBranch': resolvedWriteBranch,
      'expectedReleaseTag': '${releaseTagPrefix}${issueKey.toUpperCase()}',
      'uploadedIssue': _serializeIssue(uploadedIssue),
      'uploadedAttachment': _serializeAttachment(uploadedAttachment),
      'providerSession': _serializeSession(repository.session),
    });
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  print(jsonEncode(result));
}

String _requireEnv(String key) {
  final value = Platform.environment[key]?.trim() ?? '';
  if (value.isEmpty) {
    throw StateError('Missing required environment variable $key.');
  }
  return value;
}

Map<String, Object?> _serializeIssue(TrackStateIssue issue) {
  return <String, Object?>{
    'key': issue.key,
    'summary': issue.summary,
    'attachmentCount': issue.attachments.length,
    'attachments': issue.attachments.map(_serializeAttachment).toList(growable: false),
  };
}

Map<String, Object?>? _serializeAttachment(IssueAttachment? attachment) {
  if (attachment == null) {
    return null;
  }
  return <String, Object?>{
    'id': attachment.id,
    'name': attachment.name,
    'storageBackend': attachment.storageBackend.persistedValue,
    'githubReleaseTag': attachment.githubReleaseTag,
    'githubReleaseAssetName': attachment.githubReleaseAssetName,
    'sizeBytes': attachment.sizeBytes,
  };
}

Map<String, Object?>? _serializeSession(ProviderSession? session) {
  if (session == null) {
    return null;
  }
  return <String, Object?>{
    'providerType': session.providerType.toString(),
    'connectionState': session.connectionState.toString(),
    'resolvedUserIdentity': session.resolvedUserIdentity,
    'canRead': session.canRead,
    'canWrite': session.canWrite,
    'supportsReleaseAttachmentWrites': session.supportsReleaseAttachmentWrites,
  };
}

extension<T> on List<T> {
  T? get lastOrNull => isEmpty ? null : last;
}
