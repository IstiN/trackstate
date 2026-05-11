import 'dart:convert';
import 'dart:io';
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
      expect(result.stdout, contains('trackstate attachment upload'));
      expect(result.stdout, contains('jira_execute_request'));
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

    test('returns flattened paged search metadata for CLI consumers', () async {
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
      final issues = data['issues']! as List<Object?>;

      expect(result.exitCode, 0);
      expect(data['command'], 'search');
      expect(data['jql'], 'text ~ "pagination"');
      expect(data['startAt'], 0);
      expect(data['maxResults'], 1);
      expect(data['total'], 3);
      expect(data['isLastPage'], isFalse);
      expect(data['nextStartAt'], 1);
      expect(data['nextPageToken'], 'offset:1');
      expect(data.containsKey('page'), isFalse);
      expect(issues, hasLength(1));
      expect((issues.single as Map<String, Object?>)['key'], 'TRACK-2');
    });

    test(
      'supports Jira-style search flags without an explicit target and returns top-level pagination fields',
      () async {
        final repository = _FakeSearchRepository(
          page: TrackStateIssueSearchPage(
            issues: const [
              TrackStateIssue(
                key: 'TRACK-1',
                project: 'TRACK',
                issueType: IssueType.story,
                issueTypeId: 'story',
                status: IssueStatus.todo,
                statusId: 'todo',
                priority: IssuePriority.medium,
                priorityId: 'medium',
                summary: 'Issue 1',
                description: 'First issue.',
                assignee: 'ana',
                reporter: 'ana',
                labels: [],
                components: [],
                fixVersionIds: [],
                watchers: [],
                customFields: {},
                parentKey: null,
                epicKey: null,
                parentPath: null,
                epicPath: null,
                progress: 0,
                updatedLabel: 'just now',
                acceptanceCriteria: [],
                comments: [],
                links: [],
                attachments: [],
                isArchived: false,
              ),
              TrackStateIssue(
                key: 'TRACK-2',
                project: 'TRACK',
                issueType: IssueType.story,
                issueTypeId: 'story',
                status: IssueStatus.todo,
                statusId: 'todo',
                priority: IssuePriority.medium,
                priorityId: 'medium',
                summary: 'Issue 2',
                description: 'Second issue.',
                assignee: 'sam',
                reporter: 'sam',
                labels: [],
                components: [],
                fixVersionIds: [],
                watchers: [],
                customFields: {},
                parentKey: null,
                epicKey: null,
                parentPath: null,
                epicPath: null,
                progress: 0,
                updatedLabel: 'just now',
                acceptanceCriteria: [],
                comments: [],
                links: [],
                attachments: [],
                isArchived: false,
              ),
            ],
            startAt: 0,
            maxResults: 2,
            total: 2,
          ),
        );
        final repositoryFactory = _FakeTrackStateCliRepositoryFactory(
          localRepository: repository,
        );
        final cli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            workingDirectory: '/workspace/repo',
          ),
          repositoryFactory: repositoryFactory,
        );

        final result = await cli.run(const <String>[
          'search',
          '--jql',
          'project = TRACK',
          '--startAt',
          '0',
          '--maxResults',
          '2',
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final data = json['data'] as Map<String, Object?>?;

        expect(result.exitCode, 0);
        expect(repositoryFactory.lastRepositoryPath, '/workspace/repo');
        expect(repository.lastJql, 'project = TRACK');
        expect(repository.lastStartAt, 0);
        expect(repository.lastMaxResults, 2);
        expect(data, isNotNull);
        expect(data!['startAt'], 0);
        expect(data['maxResults'], 2);
        expect(data['total'], 2);
        expect(data['isLastPage'], isTrue);
        expect(data['issues'], isA<List<Object?>>());
      },
    );

    test(
      'uploads attachments through the Jira alias and returns attachment metadata in the envelope',
      () async {
        final tempDir = await Directory.systemTemp.createTemp(
          'trackstate-cli-upload',
        );
        addTearDown(() => tempDir.delete(recursive: true));
        final uploadFile = File('${tempDir.path}/design.png');
        await uploadFile.writeAsBytes(const <int>[1, 2, 3, 4]);
        final repository = _FakeSearchRepository(
          snapshot: _sampleSnapshot(),
          user: const RepositoryUser(
            login: 'uploader',
            displayName: 'Upload User',
          ),
        );
        final cli = TrackStateCli(
          environment: TrackStateCliEnvironment(
            workingDirectory: '/workspace/repo',
            resolvePath: (path) => path,
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
                canWrite: true,
                isAdmin: false,
                canManageAttachments: true,
              ),
            ),
          ),
          repositoryFactory: _FakeTrackStateCliRepositoryFactory(
            localRepository: repository,
          ),
        );

        final result = await cli.run(<String>[
          'jira_attach_file_to_ticket',
          '--target',
          'local',
          '--issueKey',
          'TRACK-1',
          '--file',
          uploadFile.path,
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final data = json['data']! as Map<String, Object?>;
        final attachment = data['attachment']! as Map<String, Object?>;

        expect(result.exitCode, 0);
        expect(data['command'], 'attachment-upload');
        expect(data['issue'], 'TRACK-1');
        expect(attachment['name'], 'design.png');
        expect(attachment['sizeBytes'], 4);
        expect(repository.lastUploadIssue?.key, 'TRACK-1');
        expect(repository.lastUploadName, 'design.png');
      },
    );

    test(
      'downloads attachments through the Jira alias and writes the requested output file',
      () async {
        final tempDir = await Directory.systemTemp.createTemp(
          'trackstate-cli-download',
        );
        addTearDown(() => tempDir.delete(recursive: true));
        final outFile = '${tempDir.path}/downloads/design.png';
        final repository = _FakeSearchRepository(
          snapshot: _sampleSnapshot(),
          downloadBytes: <String, List<int>>{
            'TRACK/TRACK-1/attachments/design.png': <int>[9, 8, 7],
          },
        );
        final cli = TrackStateCli(
          environment: TrackStateCliEnvironment(
            workingDirectory: '/workspace/repo',
            resolvePath: (path) => path,
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
                canWrite: true,
                isAdmin: false,
                canManageAttachments: true,
              ),
            ),
          ),
          repositoryFactory: _FakeTrackStateCliRepositoryFactory(
            localRepository: repository,
          ),
        );

        final result = await cli.run(<String>[
          'jira_download_attachment',
          '--target',
          'local',
          '--attachmentId',
          'TRACK/TRACK-1/attachments/design.png',
          '--out',
          outFile,
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final data = json['data']! as Map<String, Object?>;

        expect(result.exitCode, 0);
        expect(data['command'], 'attachment-download');
        expect(data['savedFile'], outFile);
        expect(await File(outFile).readAsBytes(), <int>[9, 8, 7]);
        expect(
          repository.lastDownloadedAttachmentId,
          'TRACK/TRACK-1/attachments/design.png',
        );
      },
    );

    test(
      'returns raw Jira-compatible search JSON for jira_execute_request',
      () async {
        final repository = _FakeSearchRepository(
          snapshot: _sampleSnapshot(),
          page: TrackStateIssueSearchPage(
            issues: const <TrackStateIssue>[_sampleIssue],
            startAt: 0,
            maxResults: 1,
            total: 1,
          ),
        );
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
                canWrite: true,
                isAdmin: false,
              ),
            ),
          ),
          repositoryFactory: _FakeTrackStateCliRepositoryFactory(
            localRepository: repository,
          ),
        );

        final result = await cli.run(const <String>[
          'jira_execute_request',
          '--target',
          'local',
          '--method',
          'GET',
          '--request-path',
          '/rest/api/2/search',
          '--query',
          'jql=project = TRACK',
          '--query',
          'maxResults=1',
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final issues = json['issues']! as List<Object?>;
        final firstIssue = issues.single as Map<String, Object?>;
        final fields = firstIssue['fields']! as Map<String, Object?>;

        expect(result.exitCode, 0);
        expect(json.containsKey('schemaVersion'), isFalse);
        expect(json['startAt'], 0);
        expect(json['maxResults'], 1);
        expect(fields['summary'], 'Implement attachments');
        expect(
          (fields['attachment'] as List<Object?>).single,
          isA<Map<String, Object?>>(),
        );
      },
    );

    test(
      'supports POST jira_execute_request bodies with field selection',
      () async {
        final repository = _FakeSearchRepository(
          snapshot: _sampleSnapshot(),
          page: TrackStateIssueSearchPage(
            issues: const <TrackStateIssue>[_sampleIssue],
            startAt: 0,
            maxResults: 1,
            total: 1,
          ),
        );
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
                canWrite: true,
                isAdmin: false,
              ),
            ),
          ),
          repositoryFactory: _FakeTrackStateCliRepositoryFactory(
            localRepository: repository,
          ),
        );

        final result = await cli.run(const <String>[
          'jira_execute_request',
          '--target',
          'local',
          '--method',
          'POST',
          '--request-path',
          '/rest/api/2/search',
          '--body',
          '{"jql":"project = TRACK","fields":["summary"]}',
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final firstIssue =
            (json['issues']! as List<Object?>).single as Map<String, Object?>;
        final fields = firstIssue['fields']! as Map<String, Object?>;

        expect(result.exitCode, 0);
        expect(fields.keys, <String>['summary']);
      },
    );

    test(
      'supports hosted jira_execute_request through the shared repository contract',
      () async {
        final repository = _FakeSearchRepository(
          snapshot: _sampleSnapshot(),
          page: TrackStateIssueSearchPage(
            issues: const <TrackStateIssue>[_sampleIssue],
            startAt: 0,
            maxResults: 1,
            total: 1,
          ),
        );
        final cli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            environment: <String, String>{
              trackStateCliTokenEnvironmentVariable: 'env-token',
            },
          ),
          repositoryFactory: _FakeTrackStateCliRepositoryFactory(
            hostedRepository: repository,
          ),
        );

        final result = await cli.run(const <String>[
          'jira_execute_request',
          '--target',
          'hosted',
          '--provider',
          'github',
          '--repository',
          'owner/repo',
          '--method',
          'GET',
          '--request-path',
          '/rest/api/2/issue/TRACK-1',
          '--query',
          'fields=summary',
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final fields = json['fields']! as Map<String, Object?>;

        expect(result.exitCode, 0);
        expect(fields.keys, <String>['summary']);
      },
    );

    test(
      'rejects unsupported attachment paths for jira_execute_request',
      () async {
        final cli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            workingDirectory: '/workspace/repo',
          ),
        );

        final result = await cli.run(const <String>[
          'jira_execute_request',
          '--target',
          'local',
          '--method',
          'GET',
          '--request-path',
          '/rest/api/2/attachment/123',
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final error = json['error']! as Map<String, Object?>;

        expect(result.exitCode, 5);
        expect(error['code'], 'UNSUPPORTED_REQUEST');
        expect(error['category'], 'unsupported');
      },
    );
  });
}

const TrackStateIssue _sampleIssue = TrackStateIssue(
  key: 'TRACK-1',
  project: 'TRACK',
  issueType: IssueType.story,
  issueTypeId: 'story',
  status: IssueStatus.inProgress,
  statusId: 'in-progress',
  priority: IssuePriority.high,
  priorityId: 'high',
  summary: 'Implement attachments',
  description: 'Add upload and download support.',
  assignee: 'ana',
  reporter: 'sam',
  labels: <String>['cli'],
  components: <String>['tracker-cli'],
  fixVersionIds: <String>['2026.05'],
  watchers: <String>[],
  customFields: <String, Object?>{'customfield_10001': 'CLI'},
  parentKey: null,
  epicKey: null,
  parentPath: null,
  epicPath: null,
  progress: 0.5,
  updatedLabel: 'just now',
  acceptanceCriteria: <String>['Expose attachment commands.'],
  comments: <IssueComment>[
    IssueComment(
      id: '0001',
      author: 'sam',
      body: 'Please keep the contract explicit.',
      updatedLabel: '2026-05-11T00:00:00Z',
      createdAt: '2026-05-11T00:00:00Z',
      updatedAt: '2026-05-11T00:00:00Z',
      storagePath: 'TRACK/TRACK-1/comments/0001.md',
    ),
  ],
  links: <IssueLink>[],
  attachments: <IssueAttachment>[
    IssueAttachment(
      id: 'TRACK/TRACK-1/attachments/design.png',
      name: 'design.png',
      mediaType: 'image/png',
      sizeBytes: 3,
      author: 'sam',
      createdAt: '2026-05-11T00:00:00Z',
      storagePath: 'TRACK/TRACK-1/attachments/design.png',
      revisionOrOid: 'oid-design',
    ),
  ],
  isArchived: false,
  storagePath: 'TRACK/TRACK-1/main.md',
);

TrackerSnapshot _sampleSnapshot() => TrackerSnapshot(
  project: const ProjectConfig(
    key: 'TRACK',
    name: 'TrackState',
    repository: 'owner/repo',
    branch: 'main',
    defaultLocale: 'en',
    issueTypeDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(id: 'story', name: 'Story'),
    ],
    statusDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(id: 'in-progress', name: 'In Progress'),
    ],
    fieldDefinitions: <TrackStateFieldDefinition>[],
    priorityDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(id: 'high', name: 'High'),
    ],
  ),
  repositoryIndex: const RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      RepositoryIssueIndexEntry(
        key: 'TRACK-1',
        path: 'TRACK/TRACK-1/main.md',
        childKeys: <String>[],
      ),
    ],
  ),
  issues: const <TrackStateIssue>[_sampleIssue],
);

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
  _FakeTrackStateCliRepositoryFactory({
    this.localRepository,
    this.hostedRepository,
  });

  final TrackStateRepository? localRepository;
  final TrackStateRepository? hostedRepository;
  String? lastRepositoryPath;
  String? lastDataRef;
  String? lastHostedRepository;
  String? lastHostedBranch;

  @override
  TrackStateRepository createLocal({
    required String repositoryPath,
    required String dataRef,
  }) {
    lastRepositoryPath = repositoryPath;
    lastDataRef = dataRef;
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
    lastHostedRepository = repository;
    lastHostedBranch = branch;
    final targetRepository = hostedRepository;
    if (targetRepository == null) {
      throw StateError('Expected a fake hosted repository.');
    }
    return targetRepository;
  }
}

class _FakeSearchRepository implements TrackStateRepository {
  _FakeSearchRepository({
    this.page,
    this.snapshot,
    this.user = const RepositoryUser(
      login: 'searcher',
      displayName: 'Search User',
    ),
    this.downloadBytes = const <String, List<int>>{},
  });

  final TrackStateIssueSearchPage? page;
  TrackerSnapshot? snapshot;
  final RepositoryUser user;
  final Map<String, List<int>> downloadBytes;
  String? lastJql;
  int? lastStartAt;
  int? lastMaxResults;
  String? lastContinuationToken;
  RepositoryConnection? connection;
  TrackStateIssue? lastUploadIssue;
  String? lastUploadName;
  String? lastDownloadedAttachmentId;

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async {
    this.connection = connection;
    return user;
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final currentSnapshot = snapshot;
    if (currentSnapshot == null) {
      throw StateError('Expected a snapshot for this fake repository.');
    }
    return currentSnapshot;
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    lastJql = jql;
    lastStartAt = startAt;
    lastMaxResults = maxResults;
    lastContinuationToken = continuationToken;
    return page ??
        TrackStateIssueSearchPage(
          issues: snapshot?.issues ?? const <TrackStateIssue>[],
          startAt: startAt,
          maxResults: maxResults,
          total: snapshot?.issues.length ?? 0,
        );
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (page ?? await searchIssuePage(jql)).issues;

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
  }) async {
    lastUploadIssue = issue;
    lastUploadName = name;
    final currentSnapshot = snapshot;
    if (currentSnapshot == null) {
      throw StateError('Expected a snapshot for uploads.');
    }
    final attachment = IssueAttachment(
      id: '${issue.project}/${issue.key}/attachments/$name',
      name: name,
      mediaType: 'image/png',
      sizeBytes: bytes.length,
      author: user.displayName,
      createdAt: '2026-05-11T00:00:00Z',
      storagePath: '${issue.project}/${issue.key}/attachments/$name',
      revisionOrOid: 'revision-$name',
    );
    final updatedIssue = issue.copyWith(
      attachments: <IssueAttachment>[
        ...issue.attachments.where(
          (existing) => existing.name != attachment.name,
        ),
        attachment,
      ],
    );
    snapshot = TrackerSnapshot(
      project: currentSnapshot.project,
      repositoryIndex: currentSnapshot.repositoryIndex,
      issues: <TrackStateIssue>[
        for (final candidate in currentSnapshot.issues)
          if (candidate.key == issue.key) updatedIssue else candidate,
      ],
    );
    return updatedIssue;
  }

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async {
    lastDownloadedAttachmentId = attachment.id;
    return Uint8List.fromList(
      downloadBytes[attachment.id] ?? utf8.encode('download:${attachment.id}'),
    );
  }

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
