import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../../components/services/issue_attachment_upload_service.dart';
import '../../../core/interfaces/issue_attachment_upload_port.dart';
import '../../../frameworks/api/github/github_issue_attachment_upload_framework.dart';

class Ts502ReleaseResolutionFixture {
  Ts502ReleaseResolutionFixture._({
    required this.attachmentUploadPort,
    required this.issue,
    required List<RecordedGitHubExchange> exchanges,
  }) : _exchanges = exchanges;

  static const String repositoryName = 'IstiN/trackstate';
  static const String branch = 'main';
  static const String issueKey = 'TS-200';
  static const String issueStoragePath = 'TRACK/TS-200/main.md';
  static const String attachmentName = 'release-repair evidence.png';
  static const String sanitizedAttachmentName = 'release-repair-evidence.png';
  static const String attachmentMetadataPath = 'TRACK/TS-200/attachments.json';
  static const String releaseId = 'release-200';
  static const String assetId = 'asset-200';
  static const String tagPrefix = 'trackstate-attachments-';
  static const String releaseTag = '${tagPrefix}TS-200';
  static const String releaseTitle = 'Attachments for TS-200';

  final IssueAttachmentUploadPort attachmentUploadPort;
  final TrackStateIssue issue;
  final List<RecordedGitHubExchange> _exchanges;

  static Future<Ts502ReleaseResolutionFixture> create() async {
    final exchanges = <RecordedGitHubExchange>[];
    final attachmentUploadPort = IssueAttachmentUploadService(
      attachmentDriver: await GitHubIssueAttachmentUploadFramework.create(
        repositoryName: repositoryName,
        branch: branch,
        token: 'test-token',
        responder: (request) async {
          final recorded = await RecordedGitHubExchange.fromRequest(request);
          final response = _responseFor(recorded);
          exchanges.add(recorded.withResponseStatusCode(response.statusCode));
          return response;
        },
      ),
    );
    attachmentUploadPort.replaceCachedState(
      snapshot: TrackerSnapshot(project: _projectConfig, issues: [_seedIssue]),
      tree: const <RepositoryTreeEntry>[],
    );
    return Ts502ReleaseResolutionFixture._(
      attachmentUploadPort: attachmentUploadPort,
      issue: _seedIssue,
      exchanges: exchanges,
    );
  }

  Future<Ts502ReleaseResolutionRun> uploadAttachment() async {
    final uploadBytes = Uint8List.fromList(
      utf8.encode('TS-502 synthetic release auto-repair payload\n'),
    );
    try {
      final updatedIssue = await attachmentUploadPort.uploadIssueAttachment(
        issue: issue,
        name: attachmentName,
        bytes: uploadBytes,
      );
      return Ts502ReleaseResolutionRun(
        updatedIssue: updatedIssue,
        cachedSnapshot: attachmentUploadPort.cachedSnapshot,
        recordedExchanges: List<RecordedGitHubExchange>.unmodifiable(
          _exchanges,
        ),
        uploadBytes: uploadBytes,
      );
    } catch (error, stackTrace) {
      return Ts502ReleaseResolutionRun(
        error: error,
        stackTrace: stackTrace,
        cachedSnapshot: attachmentUploadPort.cachedSnapshot,
        recordedExchanges: List<RecordedGitHubExchange>.unmodifiable(
          _exchanges,
        ),
        uploadBytes: uploadBytes,
      );
    }
  }

  static http.Response _responseFor(RecordedGitHubExchange request) {
    if (request.host == 'api.github.com' &&
        request.method == 'GET' &&
        request.path == '/repos/$repositoryName') {
      return http.Response(
        '{"permissions":{"pull":true,"push":true,"admin":false}}',
        200,
      );
    }

    if (request.host == 'api.github.com' &&
        request.method == 'GET' &&
        request.path == '/user') {
      return http.Response(
        '{"login":"release-tester","name":"Release Tester","id":502}',
        200,
      );
    }

    if (request.host == 'api.github.com' &&
        request.method == 'GET' &&
        request.path == '/repos/$repositoryName/releases/tags/$releaseTag') {
      return http.Response('{"message":"Not Found"}', 404);
    }

    if (request.host == 'api.github.com' &&
        request.method == 'POST' &&
        request.path == '/repos/$repositoryName/releases') {
      return http.Response(
        jsonEncode(<String, Object?>{
          'id': releaseId,
          'tag_name': releaseTag,
          'name': releaseTitle,
          'draft': true,
          'prerelease': false,
          'assets': const <Object?>[],
        }),
        201,
      );
    }

    if (request.host == 'uploads.github.com' &&
        request.method == 'POST' &&
        request.path == '/repos/$repositoryName/releases/$releaseId/assets') {
      return http.Response(
        jsonEncode(<String, Object?>{
          'id': assetId,
          'name': request.query['name'],
          'size': request.bodyBytes.length,
        }),
        201,
      );
    }

    if (request.host == 'api.github.com' &&
        request.method == 'PUT' &&
        request.path ==
            '/repos/$repositoryName/contents/$attachmentMetadataPath') {
      return http.Response('{"content":{"sha":"attachments-json-sha"}}', 201);
    }

    return http.Response(
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
}

class Ts502ReleaseResolutionRun {
  const Ts502ReleaseResolutionRun({
    this.updatedIssue,
    this.cachedSnapshot,
    this.error,
    this.stackTrace,
    required this.recordedExchanges,
    required this.uploadBytes,
  });

  final TrackStateIssue? updatedIssue;
  final TrackerSnapshot? cachedSnapshot;
  final Object? error;
  final StackTrace? stackTrace;
  final List<RecordedGitHubExchange> recordedExchanges;
  final Uint8List uploadBytes;

  List<String> get requestSequence => recordedExchanges
      .map((exchange) => exchange.describe())
      .toList(growable: false);

  RecordedGitHubExchange? get releaseLookup => _firstWhere(
    (exchange) =>
        exchange.method == 'GET' &&
        exchange.host == 'api.github.com' &&
        exchange.path ==
            '/repos/${Ts502ReleaseResolutionFixture.repositoryName}/releases/tags/${Ts502ReleaseResolutionFixture.releaseTag}',
  );

  RecordedGitHubExchange? get releaseCreate => _firstWhere(
    (exchange) =>
        exchange.method == 'POST' &&
        exchange.host == 'api.github.com' &&
        exchange.path ==
            '/repos/${Ts502ReleaseResolutionFixture.repositoryName}/releases',
  );

  RecordedGitHubExchange? get releaseAssetUpload => _firstWhere(
    (exchange) =>
        exchange.method == 'POST' &&
        exchange.host == 'uploads.github.com' &&
        exchange.path ==
            '/repos/${Ts502ReleaseResolutionFixture.repositoryName}/releases/${Ts502ReleaseResolutionFixture.releaseId}/assets',
  );

  RecordedGitHubExchange? get metadataWrite => _firstWhere(
    (exchange) =>
        exchange.method == 'PUT' &&
        exchange.host == 'api.github.com' &&
        exchange.path ==
            '/repos/${Ts502ReleaseResolutionFixture.repositoryName}/contents/${Ts502ReleaseResolutionFixture.attachmentMetadataPath}',
  );

  bool get attemptedRepositoryContentsBinaryUpload => recordedExchanges.any(
    (exchange) =>
        exchange.method == 'PUT' &&
        exchange.host == 'api.github.com' &&
        exchange.path.endsWith(
          '/contents/TRACK/TS-200/attachments/${Ts502ReleaseResolutionFixture.sanitizedAttachmentName}',
        ),
  );

  IssueAttachment? get uploadedAttachment {
    final issue = updatedIssue;
    if (issue == null) {
      return null;
    }
    for (final attachment in issue.attachments) {
      if (attachment.name ==
          Ts502ReleaseResolutionFixture.sanitizedAttachmentName) {
        return attachment;
      }
    }
    return null;
  }

  IssueAttachment? get cachedUploadedAttachment {
    final snapshot = cachedSnapshot;
    if (snapshot == null) {
      return null;
    }
    for (final issue in snapshot.issues) {
      if (issue.key != Ts502ReleaseResolutionFixture.issueKey) {
        continue;
      }
      for (final attachment in issue.attachments) {
        if (attachment.name ==
            Ts502ReleaseResolutionFixture.sanitizedAttachmentName) {
          return attachment;
        }
      }
    }
    return null;
  }

  Map<String, Object?>? get releaseCreateJson {
    final json = releaseCreate?.jsonBody;
    return json is Map<String, Object?>
        ? json
        : json is Map
        ? json.map((key, value) => MapEntry(key.toString(), value))
        : null;
  }

  Map<String, Object?>? get metadataWriteJson {
    final json = metadataWrite?.jsonBody;
    return json is Map<String, Object?>
        ? json
        : json is Map
        ? json.map((key, value) => MapEntry(key.toString(), value))
        : null;
  }

  String? get decodedManifestContent {
    final metadataJson = metadataWriteJson;
    final encoded = metadataJson?['content']?.toString();
    if (encoded == null || encoded.isEmpty) {
      return null;
    }
    return utf8.decode(base64Decode(encoded));
  }

  List<Map<String, Object?>> get manifestEntries {
    final content = decodedManifestContent;
    if (content == null || content.trim().isEmpty) {
      return const <Map<String, Object?>>[];
    }
    final decoded = jsonDecode(content);
    if (decoded is! List) {
      return const <Map<String, Object?>>[];
    }
    return decoded
        .whereType<Map>()
        .map(
          (entry) => entry.map((key, value) => MapEntry(key.toString(), value)),
        )
        .toList(growable: false);
  }

  Map<String, Object?>? get uploadedManifestEntry {
    for (final entry in manifestEntries) {
      if (entry['name'] ==
          Ts502ReleaseResolutionFixture.sanitizedAttachmentName) {
        return entry;
      }
    }
    return null;
  }

  RecordedGitHubExchange? _firstWhere(
    bool Function(RecordedGitHubExchange exchange) predicate,
  ) {
    for (final exchange in recordedExchanges) {
      if (predicate(exchange)) {
        return exchange;
      }
    }
    return null;
  }
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

  static Future<RecordedGitHubExchange> fromRequest(
    http.BaseRequest request,
  ) async {
    final bodyBytes = switch (request) {
      http.Request() => request.bodyBytes,
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
}

const TrackStateIssue _seedIssue = TrackStateIssue(
  key: Ts502ReleaseResolutionFixture.issueKey,
  project: 'TRACK',
  issueType: IssueType.story,
  issueTypeId: 'story',
  status: IssueStatus.todo,
  statusId: 'todo',
  priority: IssuePriority.medium,
  priorityId: 'medium',
  summary: 'Restore release when tag already exists',
  description:
      'Synthetic issue used to verify GitHub Releases auto-repair for a missing release container.',
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
  storagePath: Ts502ReleaseResolutionFixture.issueStoragePath,
  rawMarkdown: '# Summary\n\nRestore release when tag already exists\n',
);

const ProjectConfig _projectConfig = ProjectConfig(
  key: 'TRACK',
  name: 'TrackState.AI',
  repository: Ts502ReleaseResolutionFixture.repositoryName,
  branch: Ts502ReleaseResolutionFixture.branch,
  defaultLocale: 'en',
  issueTypeDefinitions: <TrackStateConfigEntry>[],
  statusDefinitions: <TrackStateConfigEntry>[],
  fieldDefinitions: <TrackStateFieldDefinition>[],
  attachmentStorage: ProjectAttachmentStorageSettings(
    mode: AttachmentStorageMode.githubReleases,
    githubReleases: GitHubReleasesAttachmentStorageSettings(
      tagPrefix: Ts502ReleaseResolutionFixture.tagPrefix,
    ),
  ),
);
