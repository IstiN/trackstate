import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../../../../lib/cli/trackstate_cli.dart';
import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

const List<String> _ticketArguments = <String>[
  '--target',
  'hosted',
  '--provider',
  'github',
  '--repository',
  'owner/repo',
  '--branch',
  'main',
];

class _RecordingHostedProvider implements TrackStateProviderAdapter {
  RepositoryConnection? connection;

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async => const RepositorySyncCheck(
    state: RepositorySyncState(
      providerType: ProviderType.github,
      repositoryRevision: 'recording-hosted-provider-revision',
      sessionRevision: 'recording',
      connectionState: ProviderConnectionState.connected,
      permission: RepositoryPermission(
        canRead: true,
        canWrite: false,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: false,
        canCheckCollaborators: false,
      ),
    ),
  );

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => connection?.repository ?? 'owner/repo';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    this.connection = connection;
    return const RepositoryUser(login: 'octocat', displayName: 'Octo Cat');
  }

  @override
  Future<RepositoryPermission> getPermission() async => const RepositoryPermission(
    canRead: true,
    canWrite: false,
    isAdmin: false,
    canCreateBranch: true,
    canManageAttachments: false,
    canCheckCollaborators: false,
  );

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == 'main');

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async =>
      const <RepositoryTreeEntry>[];

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async => const RepositoryTextFile(path: 'noop', content: '');

  @override
  Future<String> resolveWriteBranch() async => 'main';

  @override
  Future<RepositoryWriteResult> writeTextFile(RepositoryWriteRequest request) {
    throw UnimplementedError();
  }

  @override
  Future<RepositoryCommitResult> createCommit(RepositoryCommitRequest request) {
    throw UnimplementedError();
  }

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async => RepositoryAttachment(path: path, bytes: Uint8List(0));

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<bool> isLfsTracked(String path) async => false;
}

class _RecordingTrackStateCliProviderFactory
    implements TrackStateCliProviderFactory {
  _RecordingTrackStateCliProviderFactory({required this.hostedProvider});

  final _RecordingHostedProvider hostedProvider;
  Map<String, Object?>? createHostedCall;

  @override
  Never createLocal({
    required String repositoryPath,
    required String dataRef,
  }) {
    throw StateError(
      'TS-268 should not resolve a local provider while testing hosted target selection.',
    );
  }

  @override
  TrackStateProviderAdapter createHosted({
    required String provider,
    required String repository,
    required String branch,
    http.Client? client,
    bool disableHostedSyncRequestCaching = false,
  }) {
    createHostedCall = <String, Object?>{
      'provider': provider,
      'repository': repository,
      'branch': branch,
      'clientProvided': client != null,
    };
    return hostedProvider;
  }
}

class _RecordingTrackStateCliRepositoryFactory
    implements TrackStateCliRepositoryFactory {
  const _RecordingTrackStateCliRepositoryFactory({
    required this.hostedProvider,
  });

  final _RecordingHostedProvider hostedProvider;

  @override
  Never createLocal({
    required String repositoryPath,
    required String dataRef,
    http.Client? client,
  }) {
    throw StateError(
      'TS-268 should not resolve a local repository while testing hosted target selection.',
    );
  }

  @override
  TrackStateRepository createHosted({
    required String provider,
    required String repository,
    required String branch,
    http.Client? client,
    bool disableHostedSyncRequestCaching = false,
  }) => _RecordingHostedRepository(hostedProvider: hostedProvider);
}

class _RecordingHostedRepository implements TrackStateRepository {
  const _RecordingHostedRepository({required this.hostedProvider});

  final _RecordingHostedProvider hostedProvider;

  @override
  bool get usesLocalPersistence => false;

  @override
  bool get supportsGitHubAuth => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) =>
      hostedProvider.authenticate(connection);

  @override
  Future<TrackerSnapshot> loadSnapshot() async => TrackerSnapshot(
    project: ProjectConfig(
      key: 'DEMO',
      name: 'Demo',
      repository: 'owner/repo',
      branch: 'main',
      defaultLocale: 'en',
      issueTypeDefinitions: const <TrackStateConfigEntry>[
        TrackStateConfigEntry(id: 'story', name: 'Story', workflowId: 'delivery'),
      ],
      statusDefinitions: const <TrackStateConfigEntry>[
        TrackStateConfigEntry(id: 'todo', name: 'To Do', category: 'new'),
      ],
      fieldDefinitions: const <TrackStateFieldDefinition>[
        TrackStateFieldDefinition(
          id: 'summary',
          name: 'Summary',
          type: 'string',
          required: true,
        ),
      ],
      workflowDefinitions: const <TrackStateWorkflowDefinition>[
        TrackStateWorkflowDefinition(
          id: 'delivery',
          name: 'Delivery',
          statusIds: <String>['todo'],
        ),
      ],
    ),
    issues: const <TrackStateIssue>[],
  );

  @override
  Future<TrackStateIssue> addIssueComment(TrackStateIssue issue, String body) =>
      throw UnimplementedError();

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) =>
      throw UnimplementedError();

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) => throw UnimplementedError();

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) =>
      throw UnimplementedError();

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue) =>
      throw UnimplementedError();

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) => throw UnimplementedError();

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) =>
      throw UnimplementedError();

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) =>
      throw UnimplementedError();

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) => throw UnimplementedError();

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) => throw UnimplementedError();

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
    String? sourceName,
  }) => throw UnimplementedError();
}

Future<String?> _ghToken() async => 'gh-probe-token';

Map<String, Object?>? _serializeConnection(RepositoryConnection? connection) {
  if (connection == null) {
    return null;
  }
  return <String, Object?>{
    'repository': connection.repository,
    'branch': connection.branch,
    'token': connection.token,
  };
}

Object? _parseEnvelope(String stdout) {
  final normalized = stdout.trim();
  if (normalized.isEmpty) {
    return null;
  }
  try {
    return jsonDecode(normalized);
  } on FormatException {
    return null;
  }
}

Future<void> main() async {
  final hostedProvider = _RecordingHostedProvider();
  final providerFactory = _RecordingTrackStateCliProviderFactory(
    hostedProvider: hostedProvider,
  );
  final cli = TrackStateCli(
    environment: const TrackStateCliEnvironment(
      environment: <String, String>{},
      readGhAuthToken: _ghToken,
    ),
    providerFactory: providerFactory,
    repositoryFactory: _RecordingTrackStateCliRepositoryFactory(
      hostedProvider: hostedProvider,
    ),
  );

  final result = await cli.run(_ticketArguments);

  print(
    jsonEncode(<String, Object?>{
      'requestedCommand': 'trackstate ${_ticketArguments.join(' ')}',
      'arguments': _ticketArguments,
      'exitCode': result.exitCode,
      'stdout': result.stdout,
      'parsedEnvelope': _parseEnvelope(result.stdout),
      'createHostedCall': providerFactory.createHostedCall,
      'providerConnection': _serializeConnection(hostedProvider.connection),
    }),
  );
}
