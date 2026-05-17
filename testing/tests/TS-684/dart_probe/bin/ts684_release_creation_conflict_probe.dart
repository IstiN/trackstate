import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart';
import 'package:http/testing.dart';

import '../../../../../lib/cli/trackstate_cli.dart';
import '../../../../../lib/data/providers/github/github_trackstate_provider.dart';
import '../../../../../lib/data/providers/local/local_git_trackstate_provider.dart';
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
  Directory? repositoryDirectory;
  File? attachmentFile;

  try {
    final exchanges = <RecordedGitHubExchange>[];
    repositoryDirectory = await Directory.systemTemp.createTemp(
      'ts684-cli-repository-',
    );
    attachmentFile = File('${repositoryDirectory.path}/$_attachmentName');
    await attachmentFile.writeAsBytes(
      Uint8List.fromList(
        utf8.encode('%PDF-1.4\nTS-684 CLI release creation conflict payload\n'),
      ),
    );

    final repository = _CliProbeRepository(
      seededSnapshot: TrackerSnapshot(project: _projectConfig, issues: [_seedIssue]),
      githubRepositoryName: _repositoryName,
      githubBranch: _branch,
      githubClient: MockClient((request) async {
        final recorded = await RecordedGitHubExchange.fromRequest(request);
        final response = _responseFor(recorded);
        exchanges.add(recorded.withResponseStatusCode(response.statusCode));
        return response;
      }),
    );
    final cli = TrackStateCli(
      environment: TrackStateCliEnvironment(
        workingDirectory: repositoryDirectory.path,
        resolvePath: (path) => path,
        environment: const <String, String>{
          trackStateCliTokenEnvironmentVariable: 'mock-token',
        },
      ),
      providerFactory: _CliProbeProviderFactory(
        branch: _branch,
        repositoryName: _repositoryName,
      ),
      repositoryFactory: _CliProbeRepositoryFactory(repository),
    );

    final requestedCommand = <String>[
      'attachment',
      'upload',
      '--target',
      'local',
      '--issue',
      _issueKey,
      '--file',
      attachmentFile.path,
    ];
    final cliResult = await cli.run(requestedCommand);
    final cliPayload = _tryJson(cliResult.stdout);

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
      'requestedCommand': requestedCommand,
      'requestedCommandText':
          'trackstate attachment upload --target local --issue $_issueKey --file $_attachmentName',
      'repositoryPath': repositoryDirectory.path,
      'attachmentPath': attachmentFile.path,
      'cliExitCode': cliResult.exitCode,
      'cliStdout': cliResult.stdout,
      'cliStderr': '',
      'cliPayload': cliPayload,
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
      'uploadBytesLength': await attachmentFile.length(),
    });
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  } finally {
    if (attachmentFile != null && await attachmentFile.exists()) {
      await attachmentFile.delete();
    }
    if (repositoryDirectory != null && await repositoryDirectory.exists()) {
      await repositoryDirectory.delete(recursive: true);
    }
  }

  print(jsonEncode(result));
}

Object? _tryJson(String text) {
  final trimmed = text.trim();
  if (trimmed.isEmpty) {
    return null;
  }
  try {
    return jsonDecode(trimmed);
  } on FormatException {
    return null;
  }
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

class _CliProbeProviderFactory implements TrackStateCliProviderFactory {
  const _CliProbeProviderFactory({
    required this.branch,
    required this.repositoryName,
  });

  final String branch;
  final String repositoryName;

  @override
  LocalGitTrackStateProvider createLocal({
    required String repositoryPath,
    required String dataRef,
  }) => _CliProbeLocalGitProvider(
    repositoryPath: repositoryPath,
    branch: branch,
    repositoryName: repositoryName,
  );

  @override
  TrackStateProviderAdapter createHosted({
    required String provider,
    required String repository,
    required String branch,
    Client? client,
  }) {
    throw UnsupportedError('TS-684 does not create hosted providers.');
  }
}

class _CliProbeRepositoryFactory implements TrackStateCliRepositoryFactory {
  const _CliProbeRepositoryFactory(this.repository);

  final _CliProbeRepository repository;

  @override
  TrackStateRepository createLocal({
    required String repositoryPath,
    required String dataRef,
    Client? client,
  }) => repository;

  @override
  TrackStateRepository createHosted({
    required String provider,
    required String repository,
    required String branch,
    Client? client,
  }) {
    throw UnsupportedError('TS-684 does not create hosted repositories.');
  }
}

class _CliProbeRepository extends ProviderBackedTrackStateRepository {
  _CliProbeRepository({
    required TrackerSnapshot seededSnapshot,
    required String githubRepositoryName,
    required String githubBranch,
    required Client githubClient,
  }) : _seededSnapshot = seededSnapshot,
       _githubRepositoryName = githubRepositoryName,
       _githubBranch = githubBranch,
       _delegate = ProviderBackedTrackStateRepository(
         provider: GitHubTrackStateProvider(
           repositoryName: githubRepositoryName,
           dataRef: githubBranch,
           client: githubClient,
         ),
       ),
       super(
         provider: _CliProbeLocalGitProvider(
           repositoryPath: '/tmp/ts684-cli-probe',
           branch: githubBranch,
           repositoryName: githubRepositoryName,
         ),
         usesLocalPersistence: true,
         supportsGitHubAuth: false,
       );

  final TrackerSnapshot _seededSnapshot;
  final String _githubRepositoryName;
  final String _githubBranch;
  final ProviderBackedTrackStateRepository _delegate;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async {
    final localUser = await super.connect(connection);
    await _delegate.connect(
      RepositoryConnection(
        repository: _githubRepositoryName,
        branch: _githubBranch,
        token: connection.token,
      ),
    );
    return localUser;
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    replaceCachedState(snapshot: _seededSnapshot, tree: const <RepositoryTreeEntry>[]);
    _delegate.replaceCachedState(
      snapshot: _seededSnapshot,
      tree: const <RepositoryTreeEntry>[],
    );
    return _seededSnapshot;
  }

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async {
    try {
      return await _delegate.uploadIssueAttachment(
        issue: issue,
        name: name,
        bytes: bytes,
      );
    } finally {
      replaceCachedState(
        snapshot: _delegate.cachedSnapshot ?? _seededSnapshot,
        tree: const <RepositoryTreeEntry>[],
      );
    }
  }
}

class _CliProbeLocalGitProvider extends LocalGitTrackStateProvider {
  _CliProbeLocalGitProvider({
    required super.repositoryPath,
    required this.branch,
    required this.repositoryName,
  }) : super(processRunner: const _UnexpectedGitProcessRunner());

  final String branch;
  final String repositoryName;

  @override
  Future<String> resolveWriteBranch() async => branch;

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(
        login: 'release-tester@example.com',
        displayName: 'Release Tester',
        accountId: '684',
        emailAddress: 'release-tester@example.com',
        active: true,
      );

  @override
  Future<RepositoryPermission> getPermission() async =>
      const RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: true,
        attachmentUploadMode: AttachmentUploadMode.full,
        supportsReleaseAttachmentWrites: true,
        canCheckCollaborators: false,
      );

  @override
  Future<String?> resolveGitHubRepositoryIdentity() async => repositoryName;

  @override
  Future<String?> releaseAttachmentIdentityFailureReason() async => null;
}

class _UnexpectedGitProcessRunner implements GitProcessRunner {
  const _UnexpectedGitProcessRunner();

  @override
  Future<GitCommandResult> run(
    String repositoryPath,
    List<String> args, {
    bool binaryOutput = false,
  }) async {
    throw UnsupportedError(
      'TS-684 CLI probe should not invoke local git: $repositoryPath ${args.join(' ')}',
    );
  }
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
