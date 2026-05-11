import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:trackstate/cli/trackstate_cli.dart';
import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  group('TrackStateCli', () {
    test('prints root help when no command is provided', () async {
      final cli = TrackStateCli();

      final result = await cli.run(const <String>[]);

      expect(result.exitCode, 0);
      expect(result.stdout, contains('trackstate session --target local'));
      expect(result.stdout, contains('trackstate search --target local'));
    });

    test('reports validation errors in the JSON envelope', () async {
      final cli = TrackStateCli();

      final result = await cli.run(const <String>['session']);
      final json = jsonDecode(result.stdout) as Map<String, Object?>;
      final error = json['error']! as Map<String, Object?>;

      expect(result.exitCode, 2);
      expect(json['ok'], isFalse);
      expect(error['code'], 'INVALID_TARGET');
      expect(error['category'], 'validation');
    });

    test('uses the current directory for local targets by default', () async {
      final cli = TrackStateCli(
        environment: TrackStateCliEnvironment(
          workingDirectory: '/workspace/repo',
          resolvePath: (path) => path,
        ),
        providerFactory: _FakeTrackStateCliProviderFactory(
          localProvider: _FakeLocalGitTrackStateProvider(
            repositoryPath: '/workspace/repo',
            branch: 'feature/local',
            user: const RepositoryUser(
              login: 'local@example.com',
              displayName: 'Local User',
            ),
            permission: const RepositoryPermission(
              canRead: true,
              canWrite: true,
              isAdmin: false,
              canCreateBranch: true,
              canManageAttachments: true,
              canCheckCollaborators: false,
            ),
          ),
        ),
      );

      final result = await cli.run(const <String>[
        'session',
        '--target',
        'local',
      ]);
      final json = jsonDecode(result.stdout) as Map<String, Object?>;
      final data = json['data']! as Map<String, Object?>;

      expect(result.exitCode, 0);
      expect(json['provider'], 'local-git');
      expect(json['target'], <String, Object?>{
        'type': 'local',
        'value': '/workspace/repo',
      });
      expect(data['branch'], 'feature/local');
      expect(data['authSource'], 'none');
    });

    test('rejects hosted targets without credentials', () async {
      final cli = TrackStateCli(
        environment: const TrackStateCliEnvironment(
          environment: <String, String>{},
          readGhAuthToken: _emptyGhToken,
        ),
      );

      final result = await cli.run(const <String>[
        'session',
        '--target',
        'hosted',
        '--provider',
        'github',
        '--repository',
        'owner/repo',
      ]);
      final json = jsonDecode(result.stdout) as Map<String, Object?>;
      final error = json['error']! as Map<String, Object?>;

      expect(result.exitCode, 3);
      expect(error['code'], 'AUTHENTICATION_FAILED');
      expect(error['category'], 'auth');
    });

    test(
      'treats a throwing gh auth token lookup as missing credentials',
      () async {
        final cli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            environment: <String, String>{},
            readGhAuthToken: _throwingGhToken,
          ),
        );

        final result = await cli.run(const <String>[
          'session',
          '--target',
          'hosted',
          '--provider',
          'github',
          '--repository',
          'owner/repo',
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final error = json['error']! as Map<String, Object?>;

        expect(result.exitCode, 3);
        expect(error['code'], 'AUTHENTICATION_FAILED');
        expect(error['category'], 'auth');
      },
    );

    test(
      'rejects malformed hosted repositories as invalid targets before provider access',
      () async {
        for (final repository in const <String>[
          '/name',
          'owner/',
          'owner/name/extra',
        ]) {
          final hostedProvider = _FakeHostedTrackStateProvider(
            user: const RepositoryUser(
              login: 'octocat',
              displayName: 'Octo Cat',
            ),
            permission: const RepositoryPermission(
              canRead: true,
              canWrite: true,
              isAdmin: false,
            ),
          );
          final cli = TrackStateCli(
            environment: const TrackStateCliEnvironment(
              environment: <String, String>{
                trackStateCliTokenEnvironmentVariable: 'env-token',
              },
            ),
            providerFactory: _FakeTrackStateCliProviderFactory(
              hostedProvider: hostedProvider,
            ),
          );

          final result = await cli.run(<String>[
            'session',
            '--target',
            'hosted',
            '--provider',
            'github',
            '--repository',
            repository,
          ]);
          final json = jsonDecode(result.stdout) as Map<String, Object?>;
          final error = json['error']! as Map<String, Object?>;

          expect(result.exitCode, 2, reason: repository);
          expect(error['code'], 'INVALID_TARGET', reason: repository);
          expect(error['category'], 'validation', reason: repository);
          expect(hostedProvider.connection, isNull, reason: repository);
        }
      },
    );

    test(
      'uses credential precedence flag over env over gh for hosted targets',
      () async {
        final hostedProvider = _FakeHostedTrackStateProvider(
          user: const RepositoryUser(login: 'octocat', displayName: 'Octo Cat'),
          permission: const RepositoryPermission(
            canRead: true,
            canWrite: true,
            isAdmin: true,
          ),
        );
        final cli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            environment: <String, String>{
              trackStateCliTokenEnvironmentVariable: 'env-token',
            },
            readGhAuthToken: _ghToken,
          ),
          providerFactory: _FakeTrackStateCliProviderFactory(
            hostedProvider: hostedProvider,
          ),
        );

        final result = await cli.run(const <String>[
          'session',
          '--target',
          'hosted',
          '--provider',
          'github',
          '--repository',
          'owner/repo',
          '--token',
          'flag-token',
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final data = json['data']! as Map<String, Object?>;

        expect(result.exitCode, 0);
        expect(data['authSource'], 'flag');
        expect(hostedProvider.connection?.token, 'flag-token');
      },
    );

    test(
      'falls back to environment and gh auth token for hosted targets',
      () async {
        final envProvider = _FakeHostedTrackStateProvider(
          user: const RepositoryUser(login: 'octocat', displayName: 'Env User'),
          permission: const RepositoryPermission(
            canRead: true,
            canWrite: false,
            isAdmin: false,
          ),
        );
        final envCli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            environment: <String, String>{
              trackStateCliTokenEnvironmentVariable: 'env-token',
            },
            readGhAuthToken: _ghToken,
          ),
          providerFactory: _FakeTrackStateCliProviderFactory(
            hostedProvider: envProvider,
          ),
        );

        final envResult = await envCli.run(const <String>[
          'session',
          '--target',
          'hosted',
          '--provider',
          'github',
          '--repository',
          'owner/repo',
        ]);
        final envJson = jsonDecode(envResult.stdout) as Map<String, Object?>;
        final envData = envJson['data']! as Map<String, Object?>;

        expect(envResult.exitCode, 0);
        expect(envData['authSource'], 'env');
        expect(envProvider.connection?.token, 'env-token');

        final ghProvider = _FakeHostedTrackStateProvider(
          user: const RepositoryUser(login: 'octocat', displayName: 'Gh User'),
          permission: const RepositoryPermission(
            canRead: true,
            canWrite: true,
            isAdmin: false,
          ),
        );
        final ghCli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            environment: <String, String>{},
            readGhAuthToken: _ghToken,
          ),
          providerFactory: _FakeTrackStateCliProviderFactory(
            hostedProvider: ghProvider,
          ),
        );

        final ghResult = await ghCli.run(const <String>[
          'session',
          '--target',
          'hosted',
          '--provider',
          'github',
          '--repository',
          'owner/repo',
        ]);
        final ghJson = jsonDecode(ghResult.stdout) as Map<String, Object?>;
        final ghData = ghJson['data']! as Map<String, Object?>;

        expect(ghResult.exitCode, 0);
        expect(ghData['authSource'], 'gh');
        expect(ghProvider.connection?.token, 'gh-token');
      },
    );

    test(
      'maps hosted authentication failures to the documented auth envelope',
      () async {
        final cli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            environment: <String, String>{
              trackStateCliTokenEnvironmentVariable: 'env-token',
            },
          ),
          providerFactory: _FakeTrackStateCliProviderFactory(
            hostedProvider: _ThrowingHostedTrackStateProvider(
              const TrackStateProviderException(
                'GitHub connection failed (401): {"message":"Bad credentials"}',
              ),
            ),
          ),
        );

        final result = await cli.run(const <String>[
          'session',
          '--target',
          'hosted',
          '--provider',
          'github',
          '--repository',
          'owner/repo',
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final error = json['error']! as Map<String, Object?>;

        expect(result.exitCode, 3);
        expect(error['code'], 'AUTHENTICATION_FAILED');
        expect(error['category'], 'auth');
      },
    );

    test('supports text output for successful session resolution', () async {
      final cli = TrackStateCli(
        environment: const TrackStateCliEnvironment(
          workingDirectory: '/workspace/repo',
        ),
        providerFactory: _FakeTrackStateCliProviderFactory(
          localProvider: _FakeLocalGitTrackStateProvider(
            repositoryPath: '/workspace/repo',
            branch: 'main',
            user: const RepositoryUser(
              login: 'local@example.com',
              displayName: 'Local User',
            ),
            permission: const RepositoryPermission(
              canRead: true,
              canWrite: false,
              isAdmin: false,
            ),
          ),
        ),
      );

      final result = await cli.run(const <String>[
        'session',
        '--target',
        'local',
        '--output',
        'text',
      ]);

      expect(result.exitCode, 0);
      expect(result.stdout, contains('Session ready'));
      expect(result.stdout, contains('Provider: local-git'));
    });

    test('returns paged search metadata for CLI consumers', () async {
      final cli = TrackStateCli(
        environment: const TrackStateCliEnvironment(
          workingDirectory: '/workspace/repo',
        ),
        repositoryFactory: _FakeTrackStateCliRepositoryFactory(
          localRepository: _FakeSearchRepository(
            page: TrackStateIssueSearchPage(
              issues: const [
                TrackStateIssue(
                  key: 'TRACK-2',
                  project: 'TRACK',
                  issueType: IssueType.story,
                  issueTypeId: 'story',
                  status: IssueStatus.inProgress,
                  statusId: 'in-progress',
                  priority: IssuePriority.high,
                  priorityId: 'high',
                  summary: 'Implement pagination',
                  description: 'Adds paged JQL output.',
                  assignee: 'ana',
                  reporter: 'ana',
                  labels: ['release'],
                  components: [],
                  fixVersionIds: [],
                  watchers: [],
                  customFields: {},
                  parentKey: null,
                  epicKey: 'TRACK-1',
                  parentPath: null,
                  epicPath: null,
                  progress: 0,
                  updatedLabel: 'just now',
                  acceptanceCriteria: ['Expose next page tokens.'],
                  comments: [],
                  links: [],
                  attachments: [],
                  isArchived: false,
                ),
              ],
              startAt: 0,
              maxResults: 1,
              total: 3,
              nextStartAt: 1,
              nextPageToken: 'offset:1',
            ),
          ),
        ),
      );

      final result = await cli.run(const <String>[
        'search',
        '--target',
        'local',
        '--jql',
        'text ~ "pagination"',
        '--max-results',
        '1',
      ]);
      final json = jsonDecode(result.stdout) as Map<String, Object?>;
      final data = json['data']! as Map<String, Object?>;
      final page = data['page']! as Map<String, Object?>;
      final issues = data['issues']! as List<Object?>;

      expect(result.exitCode, 0);
      expect(data['command'], 'search');
      expect(data['jql'], 'text ~ "pagination"');
      expect(page['startAt'], 0);
      expect(page['maxResults'], 1);
      expect(page['total'], 3);
      expect(page['nextStartAt'], 1);
      expect(page['nextPageToken'], 'offset:1');
      expect(issues, hasLength(1));
      expect((issues.single as Map<String, Object?>)['key'], 'TRACK-2');
    });
  });
}

Future<String?> _ghToken() async => 'gh-token';

Future<String?> _emptyGhToken() async => '';

Future<String?> _throwingGhToken() async {
  throw Exception('gh is unavailable');
}

class _FakeTrackStateCliProviderFactory
    implements TrackStateCliProviderFactory {
  const _FakeTrackStateCliProviderFactory({
    this.localProvider,
    this.hostedProvider,
  });

  final LocalGitTrackStateProvider? localProvider;
  final TrackStateProviderAdapter? hostedProvider;

  @override
  LocalGitTrackStateProvider createLocal({
    required String repositoryPath,
    required String dataRef,
  }) {
    final provider = localProvider;
    if (provider == null) {
      throw StateError('Expected a fake local provider.');
    }
    return provider;
  }

  @override
  TrackStateProviderAdapter createHosted({
    required String provider,
    required String repository,
    required String branch,
    http.Client? client,
  }) {
    final adapter = hostedProvider;
    if (adapter == null) {
      throw StateError('Expected a fake hosted provider.');
    }
    return adapter;
  }
}

class _FakeTrackStateCliRepositoryFactory
    implements TrackStateCliRepositoryFactory {
  const _FakeTrackStateCliRepositoryFactory({this.localRepository});

  final TrackStateRepository? localRepository;

  @override
  TrackStateRepository createLocal({
    required String repositoryPath,
    required String dataRef,
  }) {
    final repository = localRepository;
    if (repository == null) {
      throw StateError('Expected a fake local repository.');
    }
    return repository;
  }

  @override
  TrackStateRepository createHosted({
    required String provider,
    required String repository,
    required String branch,
    http.Client? client,
  }) {
    throw StateError('Expected only fake local repository usage in this test.');
  }
}

class _FakeSearchRepository implements TrackStateRepository {
  const _FakeSearchRepository({required this.page});

  final TrackStateIssueSearchPage page;

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'searcher', displayName: 'Search User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async => throw UnimplementedError();

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async => page;

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async => page.issues;

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw UnimplementedError();

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw UnimplementedError();

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async => throw UnimplementedError();

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async => throw UnimplementedError();

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => throw UnimplementedError();

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async => throw UnimplementedError();

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async => throw UnimplementedError();

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      throw UnimplementedError();

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => throw UnimplementedError();
}

class _FakeLocalGitTrackStateProvider extends LocalGitTrackStateProvider {
  _FakeLocalGitTrackStateProvider({
    required super.repositoryPath,
    required this.branch,
    required this.user,
    required this.permission,
  }) : super(processRunner: const _UnexpectedGitProcessRunner());

  final String branch;
  final RepositoryUser user;
  final RepositoryPermission permission;
  RepositoryConnection? connection;

  @override
  Future<String> resolveWriteBranch() async => branch;

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    this.connection = connection;
    return user;
  }

  @override
  Future<RepositoryPermission> getPermission() async => permission;
}

class _FakeHostedTrackStateProvider implements TrackStateProviderAdapter {
  _FakeHostedTrackStateProvider({required this.user, required this.permission});

  final RepositoryUser user;
  final RepositoryPermission permission;
  RepositoryConnection? connection;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => connection?.repository ?? 'owner/repo';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    this.connection = connection;
    return user;
  }

  @override
  Future<RepositoryPermission> getPermission() async => permission;

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: true);

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
  }) {
    throw UnimplementedError();
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<bool> isLfsTracked(String path) async => false;
}

class _ThrowingHostedTrackStateProvider extends _FakeHostedTrackStateProvider {
  _ThrowingHostedTrackStateProvider(this.exception)
    : super(
        user: const RepositoryUser(login: '', displayName: ''),
        permission: const RepositoryPermission(
          canRead: false,
          canWrite: false,
          isAdmin: false,
        ),
      );

  final TrackStateProviderException exception;

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    throw exception;
  }
}

class _UnexpectedGitProcessRunner implements GitProcessRunner {
  const _UnexpectedGitProcessRunner();

  @override
  Future<GitCommandResult> run(
    String repositoryPath,
    List<String> args, {
    bool binaryOutput = false,
  }) {
    throw StateError('Unexpected git invocation: $args');
  }
}
