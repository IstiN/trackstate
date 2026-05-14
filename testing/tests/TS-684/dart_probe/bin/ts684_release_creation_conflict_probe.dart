import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart';
import 'package:http/testing.dart';

import '../../../../../lib/data/providers/github/github_trackstate_provider.dart';
import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

const String _repositoryName = 'IstiN/trackstate';
const String _branch = 'main';
const String _issueKey = 'TS-101';
const String _issuePath = 'TS/TS-101';
const String _issueStoragePath = '$_issuePath/main.md';
const String _manifestPath = '$_issuePath/attachments.json';
const String _attachmentName = 'test.pdf';
const String _tagPrefix = 'ts684-';
const String _releaseTag = '${_tagPrefix}TS-101';
const String _releaseTitle = 'Attachments for TS-101';

Future<void> main() async {
  final result = <String, Object?>{'status': 'failed'};

  try {
    final exchanges = <RecordedGitHubExchange>[];
    final repository = ProviderBackedTrackStateRepository(
      provider: GitHubTrackStateProvider(
        repositoryName: _repositoryName,
        dataRef: _branch,
        client: MockClient((request) async {
          final recorded = await RecordedGitHubExchange.fromRequest(request);
          final response = _responseFor(recorded);
          exchanges.add(recorded.withResponseStatusCode(response.statusCode));
          return response;
        }),
      ),
    );
    await repository.connect(
      const RepositoryConnection(
        repository: _repositoryName,
        branch: _branch,
        token: 'mock-token',
      ),
    );

    repository.replaceCachedState(
      snapshot: TrackerSnapshot(project: _projectConfig, issues: [_seedIssue]),
      tree: const <RepositoryTreeEntry>[],
    );

    final uploadBytes = Uint8List.fromList(
      utf8.encode('%PDF-1.4\nTS-684 synthetic release creation conflict payload\n'),
    );
    final uploadOutcome = <String, Object?>{'status': 'unknown'};

    try {
      await repository.uploadIssueAttachment(
        issue: _seedIssue,
        name: _attachmentName,
        bytes: uploadBytes,
      );
      uploadOutcome['status'] = 'success';
    } catch (error, stackTrace) {
      uploadOutcome['status'] = 'error';
      uploadOutcome['message'] = error.toString();
      uploadOutcome['stackTrace'] = stackTrace.toString();
    }

    result.addAll(<String, Object?>{
      'status': 'passed',
      'ticket': 'TS-684',
      'repository': _repositoryName,
      'branch': _branch,
      'issueKey': _issueKey,
      'issuePath': _issuePath,
      'manifestPath': _manifestPath,
      'attachmentName': _attachmentName,
      'releaseTag': _releaseTag,
      'releaseTitle': _releaseTitle,
      'uploadOutcome': uploadOutcome,
      'requestSequence': exchanges
          .map((exchange) => exchange.describe())
          .toList(growable: false),
      'releaseLookup': _findExchange(
        exchanges,
        (exchange) =>
            exchange.method == 'GET' &&
            exchange.host == 'api.github.com' &&
            exchange.path == '/repos/$_repositoryName/releases/tags/$_releaseTag',
      )?.toJson(),
      'releaseCreate': _findExchange(
        exchanges,
        (exchange) =>
            exchange.method == 'POST' &&
            exchange.host == 'api.github.com' &&
            exchange.path == '/repos/$_repositoryName/releases',
      )?.toJson(),
      'releaseAssetUpload': _findExchange(
        exchanges,
        (exchange) =>
            exchange.method == 'POST' &&
            exchange.host == 'uploads.github.com' &&
            exchange.path ==
                '/repos/$_repositoryName/releases/release-684/assets',
      )?.toJson(),
      'metadataWrite': _findExchange(
        exchanges,
        (exchange) =>
            exchange.method == 'PUT' &&
            exchange.host == 'api.github.com' &&
            exchange.path == '/repos/$_repositoryName/contents/$_manifestPath',
      )?.toJson(),
      'cachedAttachmentCount': repository.cachedSnapshot
              ?.issues
              .firstWhere((issue) => issue.key == _issueKey)
              .attachments
              .length ??
          0,
      'cachedAttachmentNames': repository.cachedSnapshot?.issues
              .firstWhere((issue) => issue.key == _issueKey)
              .attachments
              .map((attachment) => attachment.name)
              .toList(growable: false) ??
          const <String>[],
      'uploadBytesLength': uploadBytes.length,
    });
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  print(jsonEncode(result));
}

String httpResponseForReleaseConflict() => jsonEncode(<String, Object?>{
  'message': 'Conflict',
  'errors': <Map<String, Object?>>[
    <String, Object?>{
      'resource': 'Release',
      'field': 'tag_name',
      'code': 'already_exists',
      'message': 'tag already exists',
    },
  ],
});

RecordedGitHubExchange? _findExchange(
  List<RecordedGitHubExchange> exchanges,
  bool Function(RecordedGitHubExchange exchange) predicate,
) {
  for (final exchange in exchanges) {
    if (predicate(exchange)) {
      return exchange;
    }
  }
  return null;
}

Response _responseFor(RecordedGitHubExchange request) {
  if (request.host == 'api.github.com' &&
      request.method == 'GET' &&
      request.path == '/repos/$_repositoryName') {
    return Response(
      '{"permissions":{"pull":true,"push":true,"admin":false}}',
      200,
    );
  }

  if (request.host == 'api.github.com' &&
      request.method == 'GET' &&
      request.path == '/user') {
    return Response(
      '{"login":"release-tester","name":"Release Tester","id":684}',
      200,
    );
  }

  if (request.host == 'api.github.com' &&
      request.method == 'GET' &&
      request.path == '/repos/$_repositoryName/releases/tags/$_releaseTag') {
    return Response('{"message":"Not Found"}', 404);
  }

  if (request.host == 'api.github.com' &&
      request.method == 'GET' &&
      request.path == '/repos/$_repositoryName/releases') {
    return Response('[]', 200);
  }

  if (request.host == 'api.github.com' &&
      request.method == 'POST' &&
      request.path == '/repos/$_repositoryName/releases') {
    return Response(httpResponseForReleaseConflict(), 409);
  }

  return Response(
    jsonEncode(<String, Object?>{
      'message': 'Unhandled test request',
      'method': request.method,
      'host': request.host,
      'path': request.path,
      'query': request.query,
    }),
    404,
  );
}

class RecordedGitHubExchange {
  const RecordedGitHubExchange({
    required this.method,
    required this.host,
    required this.path,
    required this.query,
    required this.bodyBytes,
    this.responseStatusCode,
  });

  final String method;
  final String host;
  final String path;
  final Map<String, String> query;
  final Uint8List bodyBytes;
  final int? responseStatusCode;

  static Future<RecordedGitHubExchange> fromRequest(BaseRequest request) async {
    final bodyBytes = switch (request) {
      Request() => request.bodyBytes,
      _ => Uint8List(0),
    };
    return RecordedGitHubExchange(
      method: request.method,
      host: request.url.host,
      path: request.url.path,
      query: Map<String, String>.from(request.url.queryParameters),
      bodyBytes: bodyBytes,
    );
  }

  RecordedGitHubExchange withResponseStatusCode(int statusCode) =>
      RecordedGitHubExchange(
        method: method,
        host: host,
        path: path,
        query: query,
        bodyBytes: bodyBytes,
        responseStatusCode: statusCode,
      );

  String describe() {
    final querySuffix = query.isEmpty
        ? ''
        : '?${query.entries.map((entry) => '${entry.key}=${entry.value}').join('&')}';
    final statusSuffix = responseStatusCode == null
        ? ''
        : ' -> $responseStatusCode';
    return '$method https://$host$path$querySuffix$statusSuffix';
  }

  String get bodyText => utf8.decode(bodyBytes, allowMalformed: true);

  Object? get jsonBody {
    final trimmed = bodyText.trim();
    if (trimmed.isEmpty) {
      return null;
    }
    try {
      return jsonDecode(trimmed);
    } on FormatException {
      return null;
    }
  }

  Map<String, Object?> toJson() => <String, Object?>{
    'method': method,
    'host': host,
    'path': path,
    'query': query,
    'bodyText': bodyText,
    'jsonBody': jsonBody,
    'responseStatusCode': responseStatusCode,
  };
}

const TrackStateIssue _seedIssue = TrackStateIssue(
  key: _issueKey,
  project: 'TS',
  issueType: IssueType.story,
  issueTypeId: 'story',
  status: IssueStatus.todo,
  statusId: 'todo',
  priority: IssuePriority.medium,
  priorityId: 'medium',
  summary: 'Seeded TS-684 issue',
  description:
      'Synthetic issue used to verify release-creation conflict handling.',
  assignee: 'release-tester',
  reporter: 'release-tester',
  labels: <String>[],
  components: <String>[],
  fixVersionIds: <String>[],
  watchers: <String>[],
  customFields: <String, Object?>{},
  parentKey: null,
  epicKey: null,
  parentPath: null,
  epicPath: null,
  progress: 0,
  updatedLabel: 'just now',
  acceptanceCriteria: <String>[],
  comments: <IssueComment>[],
  links: <IssueLink>[],
  attachments: <IssueAttachment>[],
  isArchived: false,
  hasDetailLoaded: true,
  hasCommentsLoaded: true,
  hasAttachmentsLoaded: true,
  storagePath: _issueStoragePath,
  rawMarkdown: '# Summary\n\nSeeded TS-684 issue\n',
);

const ProjectConfig _projectConfig = ProjectConfig(
  key: 'TS',
  name: 'TS-684 Project',
  repository: _repositoryName,
  branch: _branch,
  defaultLocale: 'en',
  issueTypeDefinitions: <TrackStateConfigEntry>[],
  statusDefinitions: <TrackStateConfigEntry>[],
  fieldDefinitions: <TrackStateFieldDefinition>[],
  attachmentStorage: ProjectAttachmentStorageSettings(
    mode: AttachmentStorageMode.githubReleases,
    githubReleases: GitHubReleasesAttachmentStorageSettings(tagPrefix: _tagPrefix),
  ),
);
