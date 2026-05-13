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
      expect(result.stdout, contains('trackstate read ticket --key TRACK-1'));
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
      expect(error['category'], 'authentication');
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
        expect(error['category'], 'authentication');
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
        expect(error['category'], 'authentication');
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
            snapshot: _sampleSnapshot(),
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
      expect(json['ok'], isTrue);
      expect(json['provider'], 'local-git');
      expect(data['startAt'], 0);
      expect(data['maxResults'], 1);
      expect(data['total'], 3);
      expect(data['isLastPage'], isFalse);
      expect(data['page'], <String, Object?>{
        'startAt': 0,
        'maxResults': 1,
        'total': 3,
      });
      expect(issues, hasLength(1));
      final issue = issues.single as Map<String, Object?>;
      expect(issue['key'], 'TRACK-2');
      expect(issue['summary'], 'Implement pagination');
      expect(issue['issueType'], 'story');
    });

    test(
      'supports Jira-style search flags without an explicit target and returns top-level pagination fields',
      () async {
        final repository = _FakeSearchRepository(
          snapshot: _sampleSnapshot(),
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
        final data = json['data']! as Map<String, Object?>;
        final issues = data['issues'] as List<Object?>?;

        expect(result.exitCode, 0);
        expect(repositoryFactory.lastRepositoryPath, '/workspace/repo');
        expect(repository.lastJql, 'project = TRACK');
        expect(repository.lastStartAt, 0);
        expect(repository.lastMaxResults, 2);
        expect(json['ok'], isTrue);
        expect(data['startAt'], 0);
        expect(data['maxResults'], 2);
        expect(data['total'], 2);
        expect(data['isLastPage'], isTrue);
        expect(issues, isA<List<Object?>>());
      },
    );

    test(
      'search command forwards the shared HTTP client to local repositories',
      () async {
        final repository = _FakeSearchRepository(
          snapshot: _sampleSnapshot(),
          page: const TrackStateIssueSearchPage.empty(),
        );
        final repositoryFactory = _FakeTrackStateCliRepositoryFactory(
          localRepository: repository,
        );
        final client = http.Client();
        addTearDown(client.close);
        final cli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            workingDirectory: '/workspace/repo',
          ),
          repositoryFactory: repositoryFactory,
          httpClient: client,
        );

        final result = await cli.run(const <String>[
          'search',
          '--jql',
          'project = TRACK',
        ]);

        expect(result.exitCode, 0);
        expect(repositoryFactory.lastLocalClient, same(client));
      },
    );

    test(
      'returns Jira-shaped ticket JSON from the canonical read command',
      () async {
        final cli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            workingDirectory: '/workspace/repo',
          ),
          repositoryFactory: _FakeTrackStateCliRepositoryFactory(
            localRepository: _FakeSearchRepository(
              snapshot: _sampleSnapshot(),
              page: const TrackStateIssueSearchPage.empty(),
            ),
          ),
        );

        final result = await cli.run(const <String>[
          'read',
          'ticket',
          '--key',
          'TRACK-2',
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final fields = json['fields']! as Map<String, Object?>;

        expect(result.exitCode, 0);
        expect(json['key'], 'TRACK-2');
        expect(json['id'], '2');
        expect(fields['summary'], 'Implement pagination');
        expect(fields['project'], <String, Object?>{
          'id': 'TRACK',
          'key': 'TRACK',
          'name': 'TrackState',
        });
        expect(fields['parent'], isNull);
      },
    );

    test(
      'supports compatibility aliases and returns Jira field metadata',
      () async {
        final cli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            workingDirectory: '/workspace/repo',
          ),
          repositoryFactory: _FakeTrackStateCliRepositoryFactory(
            localRepository: _FakeSearchRepository(
              snapshot: _sampleSnapshot(),
              page: const TrackStateIssueSearchPage.empty(),
            ),
          ),
        );

        final result = await cli.run(const <String>['fields', 'list']);
        final json = jsonDecode(result.stdout) as List<Object?>;

        expect(result.exitCode, 0);
        expect(json, isNotEmpty);
        expect(json.first, <String, Object?>{
          'id': 'summary',
          'key': 'summary',
          'name': 'Summary',
          'custom': false,
          'orderable': true,
          'navigable': true,
          'searchable': true,
          'schema': <String, Object?>{'type': 'string', 'system': 'summary'},
        });
      },
    );

    test(
      'adds localized display names and fallback flags for metadata reads',
      () async {
        final cli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            workingDirectory: '/workspace/repo',
          ),
          repositoryFactory: _FakeTrackStateCliRepositoryFactory(
            localRepository: _FakeSearchRepository(
              snapshot: _sampleSnapshot(),
              page: const TrackStateIssueSearchPage.empty(),
            ),
          ),
        );

        final result = await cli.run(const <String>[
          'read',
          'fields',
          '--locale',
          'fr',
        ]);
        final json = jsonDecode(result.stdout) as List<Object?>;

        expect(result.exitCode, 0);
        expect(json.first, <String, Object?>{
          'id': 'summary',
          'key': 'summary',
          'name': 'Summary',
          'displayName': 'Resume',
          'usedFallback': false,
          'custom': false,
          'orderable': true,
          'navigable': true,
          'searchable': true,
          'schema': <String, Object?>{'type': 'string', 'system': 'summary'},
        });
        expect(json[1], <String, Object?>{
          'id': 'description',
          'key': 'description',
          'name': 'Description',
          'displayName': 'Description',
          'usedFallback': true,
          'custom': false,
          'orderable': true,
          'navigable': true,
          'searchable': true,
          'schema': <String, Object?>{
            'type': 'string',
            'system': 'description',
          },
        });
      },
    );

    test(
      'localizes text output for read resources when locale is requested',
      () async {
        final cli = TrackStateCli(
          environment: const TrackStateCliEnvironment(
            workingDirectory: '/workspace/repo',
          ),
          repositoryFactory: _FakeTrackStateCliRepositoryFactory(
            localRepository: _FakeSearchRepository(
              snapshot: _sampleSnapshot(),
              page: const TrackStateIssueSearchPage.empty(),
            ),
          ),
        );

        final ticketResult = await cli.run(const <String>[
          'read',
          'ticket',
          '--key',
          'TRACK-2',
          '--locale',
          'fr',
          '--output',
          'text',
        ]);
        final fieldsResult = await cli.run(const <String>[
          'read',
          'fields',
          '--locale',
          'fr',
          '--output',
          'text',
        ]);
        final statusesResult = await cli.run(const <String>[
          'read',
          'statuses',
          '--project',
          'TRACK',
          '--locale',
          'fr',
          '--output',
          'text',
        ]);
        final issueTypesResult = await cli.run(const <String>[
          'read',
          'issue-types',
          '--project',
          'TRACK',
          '--locale',
          'fr',
          '--output',
          'text',
        ]);
        final componentsResult = await cli.run(const <String>[
          'read',
          'components',
          '--project',
          'TRACK',
          '--locale',
          'fr',
          '--output',
          'text',
        ]);
        final versionsResult = await cli.run(const <String>[
          'read',
          'versions',
          '--project',
          'TRACK',
          '--locale',
          'fr',
          '--output',
          'text',
        ]);

        expect(ticketResult.exitCode, 0);
        expect(ticketResult.stdout, contains('Type: Recit'));
        expect(ticketResult.stdout, contains('Status: En cours'));
        expect(ticketResult.stdout, contains('Priority: Elevee'));
        expect(ticketResult.stdout, isNot(contains('Type: Story')));

        expect(fieldsResult.exitCode, 0);
        expect(fieldsResult.stdout, contains('Resume'));
        expect(fieldsResult.stdout, contains('Description'));

        expect(statusesResult.exitCode, 0);
        expect(statusesResult.stdout, contains('A faire'));

        expect(issueTypesResult.exitCode, 0);
        expect(issueTypesResult.stdout, contains('Recit'));

        expect(componentsResult.exitCode, 0);
        expect(componentsResult.stdout, contains('Interface CLI'));
        expect(componentsResult.stdout, contains('Noyau TrackState'));

        expect(versionsResult.exitCode, 0);
        expect(versionsResult.stdout, contains('Version 2026.05'));
        expect(versionsResult.stdout, contains('Version MVP'));
      },
    );

    test('returns Jira project statuses grouped by issue type', () async {
      final cli = TrackStateCli(
        environment: const TrackStateCliEnvironment(
          workingDirectory: '/workspace/repo',
        ),
        repositoryFactory: _FakeTrackStateCliRepositoryFactory(
          localRepository: _FakeSearchRepository(
            snapshot: _sampleSnapshot(),
            page: const TrackStateIssueSearchPage.empty(),
          ),
        ),
      );

      final result = await cli.run(const <String>[
        'read',
        'statuses',
        '--project',
        'TRACK',
      ]);
      final json = jsonDecode(result.stdout) as List<Object?>;
      final first = json.first as Map<String, Object?>;
      final statuses = first['statuses']! as List<Object?>;

      expect(result.exitCode, 0);
      expect(first['name'], 'Epic');
      expect(statuses.first, <String, Object?>{
        'id': 'todo',
        'name': 'To Do',
        'statusCategory': <String, Object?>{
          'id': 2,
          'key': 'new',
          'name': 'To Do',
        },
      });
    });

    test('returns canonical Jira issue link types', () async {
      final cli = TrackStateCli(
        environment: const TrackStateCliEnvironment(
          workingDirectory: '/workspace/repo',
        ),
        repositoryFactory: _FakeTrackStateCliRepositoryFactory(
          localRepository: _FakeSearchRepository(
            snapshot: _sampleSnapshot(),
            page: const TrackStateIssueSearchPage.empty(),
          ),
        ),
      );

      final result = await cli.run(const <String>['link-types', 'list']);
      final json = jsonDecode(result.stdout) as List<Object?>;

      expect(result.exitCode, 0);
      expect(json, <Object?>[
        {
          'id': 'blocks',
          'name': 'Blocks',
          'outward': 'blocks',
          'inward': 'is blocked by',
        },
        {
          'id': 'relates-to',
          'name': 'Relates',
          'outward': 'relates to',
          'inward': 'relates to',
        },
        {
          'id': 'duplicates',
          'name': 'Duplicates',
          'outward': 'duplicates',
          'inward': 'is duplicated by',
        },
        {
          'id': 'clones',
          'name': 'Clones',
          'outward': 'clones',
          'inward': 'is cloned by',
        },
      ]);
    });

    test(
      'reads the current profile and supports hosted user lookup by login',
      () async {
        final repository = _FakeSearchRepository(
          snapshot: _sampleSnapshot(),
          page: const TrackStateIssueSearchPage.empty(),
          connectedUser: const RepositoryUser(
            login: 'octocat',
            displayName: 'Octo Cat',
            accountId: '42',
            emailAddress: 'octo@example.com',
            active: true,
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
          providerFactory: _FakeTrackStateCliProviderFactory(
            hostedProvider: _FakeHostedTrackStateProvider(
              user: const RepositoryUser(
                login: 'octocat',
                displayName: 'Octo Cat',
                accountId: '42',
                emailAddress: 'octo@example.com',
                active: true,
              ),
              permission: const RepositoryPermission(
                canRead: true,
                canWrite: false,
                isAdmin: false,
              ),
              usersByLogin: const {
                'hubot': RepositoryUser(
                  login: 'hubot',
                  displayName: 'Hubot',
                  accountId: '99',
                  active: true,
                ),
              },
            ),
          ),
        );

        final profileResult = await cli.run(const <String>[
          'read',
          'profile',
          '--target',
          'hosted',
          '--provider',
          'github',
          '--repository',
          'owner/repo',
        ]);
        final profileJson =
            jsonDecode(profileResult.stdout) as Map<String, Object?>;

        final userResult = await cli.run(const <String>[
          'user',
          'get',
          '--target',
          'hosted',
          '--provider',
          'github',
          '--repository',
          'owner/repo',
          '--login',
          'hubot',
        ]);
        final userJson = jsonDecode(userResult.stdout) as Map<String, Object?>;

        expect(profileResult.exitCode, 0);
        expect(profileJson, <String, Object?>{
          'accountId': '42',
          'displayName': 'Octo Cat',
          'active': true,
          'emailAddress': 'octo@example.com',
        });

        expect(userResult.exitCode, 0);
        expect(userJson, <String, Object?>{
          'accountId': '99',
          'displayName': 'Hubot',
          'active': true,
        });
      },
    );

    test('resolves the active local account by email', () async {
      final cli = TrackStateCli(
        environment: const TrackStateCliEnvironment(
          workingDirectory: '/workspace/repo',
        ),
        repositoryFactory: _FakeTrackStateCliRepositoryFactory(
          localRepository: _FakeSearchRepository(
            snapshot: _sampleSnapshot(),
            page: const TrackStateIssueSearchPage.empty(),
            connectedUser: const RepositoryUser(
              login: 'user@example.com',
              displayName: 'Local User',
              accountId: 'local-user',
              emailAddress: 'user@example.com',
              active: true,
            ),
          ),
        ),
      );

      final result = await cli.run(const <String>[
        'read',
        'account-by-email',
        '--email',
        'user@example.com',
      ]);
      final json = jsonDecode(result.stdout) as Map<String, Object?>;

      expect(result.exitCode, 0);
      expect(json, <String, Object?>{
        'accountId': 'local-user',
        'displayName': 'Local User',
        'active': true,
        'emailAddress': 'user@example.com',
      });
    });

    test(
      'supports hosted account-by-email lookup when the provider exposes it',
      () async {
        final repository = _FakeSearchRepository(
          snapshot: _sampleSnapshot(),
          page: const TrackStateIssueSearchPage.empty(),
          connectedUser: const RepositoryUser(
            login: 'octocat',
            displayName: 'Octo Cat',
            accountId: '42',
            emailAddress: 'octo@example.com',
            active: true,
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
          providerFactory: _FakeTrackStateCliProviderFactory(
            hostedProvider: _FakeHostedTrackStateProvider(
              user: const RepositoryUser(
                login: 'octocat',
                displayName: 'Octo Cat',
                accountId: '42',
                emailAddress: 'octo@example.com',
                active: true,
              ),
              permission: const RepositoryPermission(
                canRead: true,
                canWrite: false,
                isAdmin: false,
              ),
              usersByEmail: const {
                'hubot@example.com': RepositoryUser(
                  login: 'hubot',
                  displayName: 'Hubot',
                  accountId: '99',
                  emailAddress: 'hubot@example.com',
                  active: true,
                ),
              },
            ),
          ),
        );

        final result = await cli.run(const <String>[
          'read',
          'account-by-email',
          '--target',
          'hosted',
          '--provider',
          'github',
          '--repository',
          'owner/repo',
          '--email',
          'hubot@example.com',
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;

        expect(result.exitCode, 0);
        expect(json, <String, Object?>{
          'accountId': '99',
          'displayName': 'Hubot',
          'active': true,
          'emailAddress': 'hubot@example.com',
        });
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
      'local release-backed attachment uploads forward optional GitHub credentials',
      () async {
        final uploadFile = File(
          '${Directory.systemTemp.path}/trackstate-cli-local-release-upload.txt',
        );
        addTearDown(() async {
          if (await uploadFile.exists()) {
            await uploadFile.delete();
          }
        });
        await uploadFile.writeAsString('release payload');
        final snapshot = _sampleSnapshot();
        final releaseSnapshot = TrackerSnapshot(
          project: ProjectConfig(
            key: snapshot.project.key,
            name: snapshot.project.name,
            repository: snapshot.project.repository,
            branch: snapshot.project.branch,
            defaultLocale: snapshot.project.defaultLocale,
            supportedLocales: snapshot.project.supportedLocales,
            issueTypeDefinitions: snapshot.project.issueTypeDefinitions,
            statusDefinitions: snapshot.project.statusDefinitions,
            fieldDefinitions: snapshot.project.fieldDefinitions,
            workflowDefinitions: snapshot.project.workflowDefinitions,
            priorityDefinitions: snapshot.project.priorityDefinitions,
            versionDefinitions: snapshot.project.versionDefinitions,
            componentDefinitions: snapshot.project.componentDefinitions,
            resolutionDefinitions: snapshot.project.resolutionDefinitions,
            attachmentStorage: const ProjectAttachmentStorageSettings(
              mode: AttachmentStorageMode.githubReleases,
              githubReleases: GitHubReleasesAttachmentStorageSettings(
                tagPrefix: 'trackstate-attachments-',
              ),
            ),
          ),
          repositoryIndex: snapshot.repositoryIndex,
          issues: snapshot.issues,
        );
        final repository = _FakeSearchRepository(
          snapshot: releaseSnapshot,
          requiredUploadToken: 'env-token',
        );
        final cli = TrackStateCli(
          environment: TrackStateCliEnvironment(
            workingDirectory: '/workspace/repo',
            resolvePath: (path) => path,
            environment: const <String, String>{
              trackStateCliTokenEnvironmentVariable: 'env-token',
            },
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

        final result = await cli.run(<String>[
          'attachment',
          'upload',
          '--target',
          'local',
          '--path',
          '/workspace/repo',
          '--issue',
          'TRACK-1',
          '--file',
          uploadFile.path,
        ]);
        expect(result.exitCode, 0, reason: result.stdout);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final data = json['data']! as Map<String, Object?>;

        expect(data['authSource'], 'env');
        expect(repository.connection?.token, 'env-token');
      },
    );

    test(
      'local release-backed upload without a git remote reports an explicit repository identity error',
      () async {
        final repo = await _createCliLocalRepository();
        addTearDown(() => repo.delete(recursive: true));
        final uploadFile = File('${repo.path}/release-plan.txt');
        await uploadFile.writeAsString('roadmap');
        await _writeCliTestFile(
          repo,
          'DEMO/project.json',
          '{"key":"DEMO","name":"Local Demo","attachmentStorage":{"mode":"github-releases","githubReleases":{"tagPrefix":"trackstate-attachments-"}}}\n',
        );
        await _gitCliTest(repo.path, ['add', 'DEMO/project.json']);
        await _gitCliTest(repo.path, [
          'commit',
          '-m',
          'Configure release-backed attachment storage',
        ]);
        final cli = TrackStateCli(
          environment: TrackStateCliEnvironment(
            workingDirectory: repo.path,
            resolvePath: (path) => path,
          ),
        );

        final result = await cli.run(<String>[
          'attachment',
          'upload',
          '--target',
          'local',
          '--path',
          repo.path,
          '--issue',
          'DEMO-1',
          '--file',
          uploadFile.path,
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final error = json['error']! as Map<String, Object?>;
        final details = error['details']! as Map<String, Object?>;

        expect(result.exitCode, 4);
        expect(error['code'], 'REPOSITORY_OPEN_FAILED');
        expect(
          details['reason'],
          contains(
            'GitHub repository identity cannot be resolved from the local Git configuration because no remote is configured.',
          ),
        );
      },
    );

    test(
      'matches uploaded attachment metadata by sanitized stored name',
      () async {
        final sampleSnapshot = _sampleSnapshot();
        final tempDir = await Directory.systemTemp.createTemp(
          'trackstate-cli-upload-sanitized',
        );
        addTearDown(() => tempDir.delete(recursive: true));
        final uploadFile = File('${tempDir.path}/design draft.png');
        await uploadFile.writeAsBytes(const <int>[1, 2, 3, 4]);
        final repository = _FakeSearchRepository(
          snapshot: TrackerSnapshot(
            project: sampleSnapshot.project,
            repositoryIndex: sampleSnapshot.repositoryIndex,
            issues: <TrackStateIssue>[
              _sampleIssue.copyWith(
                attachments: const <IssueAttachment>[
                  IssueAttachment(
                    id: 'TRACK/TRACK-1/attachments/zzz-existing.png',
                    name: 'zzz-existing.png',
                    mediaType: 'image/png',
                    sizeBytes: 5,
                    author: 'sam',
                    createdAt: '2026-05-10T00:00:00Z',
                    storagePath: 'TRACK/TRACK-1/attachments/zzz-existing.png',
                    revisionOrOid: 'oid-existing',
                  ),
                ],
              ),
              _sampleReadIssue,
            ],
          ),
          uploadedAttachmentNameBuilder: _sanitizeAttachmentTestName,
          sortUploadedAttachmentsByName: true,
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
        expect(attachment['id'], 'TRACK/TRACK-1/attachments/design-draft.png');
        expect(attachment['name'], 'design-draft.png');
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
      'local release-backed attachment download surfaces an authentication contract for missing GitHub credentials',
      () async {
        final tempDir = await Directory.systemTemp.createTemp(
          'trackstate-cli-download-auth',
        );
        addTearDown(() => tempDir.delete(recursive: true));
        final outFile = '${tempDir.path}/downloads/manual.pdf';
        final repository = _FakeSearchRepository(
          snapshot: _sampleSnapshot(),
          downloadException: const TrackStateProviderException(
            'GitHub Releases attachment storage requires GitHub authentication. '
            'Set TRACKSTATE_TOKEN or authenticate with gh before using '
            'release-backed attachments from a local repository.',
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
          'attachment',
          'download',
          '--target',
          'local',
          '--attachment-id',
          'TRACK/TRACK-1/attachments/design.png',
          '--out',
          outFile,
          '--output',
          'json',
        ]);
        final json = jsonDecode(result.stdout) as Map<String, Object?>;
        final error = json['error']! as Map<String, Object?>;
        final details = error['details']! as Map<String, Object?>;

        expect(result.exitCode, 3);
        expect(error['code'], 'AUTHENTICATION_FAILED');
        expect(error['category'], 'authentication');
        expect(details['reason'], contains('GitHub authentication'));
        expect(File(outFile).existsSync(), isFalse);
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
        expect(repository.lastJql, 'project = TRACK');
      },
    );

    test(
      'decodes percent-encoded jira_execute_request query parameters',
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
          'jql=project%20%3D%20TRACK',
          '--query',
          'maxResults=1',
        ]);

        expect(result.exitCode, 0);
        expect(repository.lastJql, 'project = TRACK');
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

const TrackStateIssue _sampleReadIssue = TrackStateIssue(
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
  labels: <String>['release'],
  components: <String>['tracker-core'],
  fixVersionIds: <String>['mvp'],
  watchers: <String>[],
  customFields: <String, Object?>{},
  parentKey: null,
  epicKey: 'TRACK-1',
  parentPath: null,
  epicPath: null,
  progress: 0,
  updatedLabel: 'just now',
  acceptanceCriteria: <String>['Expose next page tokens.'],
  comments: <IssueComment>[],
  links: <IssueLink>[],
  attachments: <IssueAttachment>[],
  isArchived: false,
);

TrackerSnapshot _sampleSnapshot() => TrackerSnapshot(
  project: const ProjectConfig(
    key: 'TRACK',
    name: 'TrackState',
    repository: 'trackstate/trackstate',
    branch: 'main',
    defaultLocale: 'en',
    supportedLocales: <String>['en', 'fr'],
    issueTypeDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(id: 'epic', name: 'Epic'),
      TrackStateConfigEntry(
        id: 'story',
        name: 'Story',
        localizedLabels: <String, String>{'fr': 'Recit'},
      ),
      TrackStateConfigEntry(id: 'subtask', name: 'Sub-task'),
    ],
    statusDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: 'todo',
        name: 'To Do',
        localizedLabels: <String, String>{'fr': 'A faire'},
      ),
      TrackStateConfigEntry(
        id: 'in-progress',
        name: 'In Progress',
        localizedLabels: <String, String>{'fr': 'En cours'},
      ),
      TrackStateConfigEntry(id: 'done', name: 'Done'),
    ],
    fieldDefinitions: <TrackStateFieldDefinition>[
      TrackStateFieldDefinition(
        id: 'summary',
        name: 'Summary',
        type: 'string',
        required: true,
        localizedLabels: <String, String>{'fr': 'Resume'},
      ),
      TrackStateFieldDefinition(
        id: 'description',
        name: 'Description',
        type: 'markdown',
        required: false,
      ),
    ],
    priorityDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: 'high',
        name: 'High',
        localizedLabels: <String, String>{'fr': 'Elevee'},
      ),
      TrackStateConfigEntry(id: 'medium', name: 'Medium'),
    ],
    componentDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: 'tracker-cli',
        name: 'Tracker CLI',
        localizedLabels: <String, String>{'fr': 'Interface CLI'},
      ),
      TrackStateConfigEntry(
        id: 'tracker-core',
        name: 'Tracker Core',
        localizedLabels: <String, String>{'fr': 'Noyau TrackState'},
      ),
    ],
    versionDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: '2026.05',
        name: '2026.05',
        localizedLabels: <String, String>{'fr': 'Version 2026.05'},
      ),
      TrackStateConfigEntry(
        id: 'mvp',
        name: 'MVP',
        localizedLabels: <String, String>{'fr': 'Version MVP'},
      ),
    ],
  ),
  repositoryIndex: const RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      RepositoryIssueIndexEntry(
        key: 'TRACK-1',
        path: 'TRACK/TRACK-1/main.md',
        childKeys: <String>['TRACK-2'],
      ),
      RepositoryIssueIndexEntry(
        key: 'TRACK-2',
        path: 'TRACK/TRACK-1/TRACK-2/main.md',
        childKeys: <String>[],
      ),
    ],
  ),
  issues: const <TrackStateIssue>[_sampleIssue, _sampleReadIssue],
);

Future<String?> _ghToken() async => 'gh-token';

Future<String?> _emptyGhToken() async => '';

Future<String?> _throwingGhToken() async {
  throw Exception('gh is unavailable');
}

String _sanitizeAttachmentTestName(String value) => value
    .replaceAll('\\', '/')
    .split('/')
    .last
    .replaceAll(RegExp(r'[^A-Za-z0-9._-]+'), '-')
    .replaceAll(RegExp(r'-+'), '-')
    .replaceAll(RegExp(r'^-|-$'), '');

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
  http.Client? lastLocalClient;
  String? lastHostedRepository;
  String? lastHostedBranch;
  String? lastHostedProvider;

  @override
  TrackStateRepository createLocal({
    required String repositoryPath,
    required String dataRef,
    http.Client? client,
  }) {
    lastRepositoryPath = repositoryPath;
    lastDataRef = dataRef;
    lastLocalClient = client;
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
    lastHostedProvider = provider;
    lastHostedRepository = repository;
    lastHostedBranch = branch;
    final hosted = hostedRepository;
    if (hosted == null) {
      throw StateError('Expected a fake hosted repository.');
    }
    return hosted;
  }
}

class _FakeSearchRepository implements TrackStateRepository {
  _FakeSearchRepository({
    this.page = const TrackStateIssueSearchPage.empty(),
    this.snapshot = const TrackerSnapshot(
      project: ProjectConfig(
        key: 'TRACK',
        name: 'TrackState',
        repository: 'trackstate/trackstate',
        branch: 'main',
        defaultLocale: 'en',
        issueTypeDefinitions: [],
        statusDefinitions: [],
        fieldDefinitions: [],
      ),
      issues: [],
    ),
    RepositoryUser? user,
    RepositoryUser? connectedUser,
    this.downloadBytes = const <String, List<int>>{},
    this.downloadException,
    this.uploadedAttachmentNameBuilder,
    this.sortUploadedAttachmentsByName = false,
    this.requiredUploadToken,
  }) : user =
           user ??
           connectedUser ??
           const RepositoryUser(login: 'searcher', displayName: 'Search User'),
       connectedUser =
           connectedUser ??
           user ??
           const RepositoryUser(login: 'searcher', displayName: 'Search User');

  final TrackStateIssueSearchPage page;
  TrackerSnapshot snapshot;
  final RepositoryUser user;
  final RepositoryUser connectedUser;
  final Map<String, List<int>> downloadBytes;
  final TrackStateProviderException? downloadException;
  final String Function(String name)? uploadedAttachmentNameBuilder;
  final bool sortUploadedAttachmentsByName;
  final String? requiredUploadToken;
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
    return connectedUser;
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async => snapshot;

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
    return page;
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (await searchIssuePage(jql)).issues;

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
    final requiredUploadToken = this.requiredUploadToken;
    if (requiredUploadToken != null && connection?.token != requiredUploadToken) {
      throw const TrackStateRepositoryException(
        'GitHub release uploads require an authenticated repository connection.',
      );
    }
    lastUploadIssue = issue;
    lastUploadName = name;
    final storedName = uploadedAttachmentNameBuilder?.call(name) ?? name;
    final attachment = IssueAttachment(
      id: '${issue.project}/${issue.key}/attachments/$storedName',
      name: storedName,
      mediaType: 'image/png',
      sizeBytes: bytes.length,
      author: user.displayName,
      createdAt: '2026-05-11T00:00:00Z',
      storagePath: '${issue.project}/${issue.key}/attachments/$storedName',
      revisionOrOid: 'revision-$storedName',
    );
    final updatedAttachments = <IssueAttachment>[
      ...issue.attachments.where(
        (existing) => existing.storagePath != attachment.storagePath,
      ),
      attachment,
    ];
    if (sortUploadedAttachmentsByName) {
      updatedAttachments.sort((left, right) => left.name.compareTo(right.name));
    }
    final updatedIssue = issue.copyWith(attachments: updatedAttachments);
    final currentSnapshot = snapshot;
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
    final exception = downloadException;
    if (exception != null) {
      throw exception;
    }
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

class _FakeHostedTrackStateProvider
    implements TrackStateProviderAdapter, RepositoryUserLookup {
  _FakeHostedTrackStateProvider({
    required this.user,
    required this.permission,
    this.usersByLogin = const {},
    this.usersByEmail = const {},
  });

  final RepositoryUser user;
  final RepositoryPermission permission;
  final Map<String, RepositoryUser> usersByLogin;
  final Map<String, RepositoryUser> usersByEmail;
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
  Future<RepositoryUser> lookupUserByLogin(String login) async {
    final resolved = usersByLogin[login];
    if (resolved == null) {
      throw const TrackStateProviderException('User was not found.');
    }
    return resolved;
  }

  @override
  Future<RepositoryUser> lookupUserByEmail(String email) async {
    final resolved = usersByEmail[email];
    if (resolved == null) {
      throw const TrackStateProviderException('User was not found.');
    }
    return resolved;
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

Future<Directory> _createCliLocalRepository() async {
  final directory = await Directory.systemTemp.createTemp('trackstate-cli-local-');
  await _writeCliTestFile(
    directory,
    '.gitattributes',
    '*.png filter=lfs diff=lfs merge=lfs -text\n',
  );
  await _writeCliTestFile(
    directory,
    'DEMO/project.json',
    '{"key":"DEMO","name":"Local Demo"}\n',
  );
  await _writeCliTestFile(
    directory,
    'DEMO/config/statuses.json',
    '[{"name":"To Do"},{"name":"Done"}]\n',
  );
  await _writeCliTestFile(
    directory,
    'DEMO/config/issue-types.json',
    '[{"name":"Story"}]\n',
  );
  await _writeCliTestFile(
    directory,
    'DEMO/config/fields.json',
    '[{"name":"Summary"},{"name":"Priority"}]\n',
  );
  await _writeCliTestFile(directory, 'DEMO/DEMO-1/main.md', '''
---
key: DEMO-1
project: DEMO
issueType: Story
status: In Progress
priority: High
summary: Local issue
assignee: local-user
reporter: local-admin
updated: 2026-05-05T00:00:00Z
---

# Description

Loaded from local git.
''');
  await _writeCliTestFile(
    directory,
    'DEMO/DEMO-1/acceptance_criteria.md',
    '- Can be loaded from local Git\n',
  );
  await _gitCliTest(directory.path, ['init', '-b', 'main']);
  await _gitCliTest(directory.path, [
    'config',
    '--local',
    'user.name',
    'Local Tester',
  ]);
  await _gitCliTest(directory.path, [
    'config',
    '--local',
    'user.email',
    'local@example.com',
  ]);
  await _gitCliTest(directory.path, ['add', '.']);
  await _gitCliTest(directory.path, ['commit', '-m', 'Initial import']);
  return directory;
}

Future<void> _writeCliTestFile(
  Directory root,
  String relativePath,
  String content,
) async {
  final file = File('${root.path}/$relativePath');
  await file.parent.create(recursive: true);
  await file.writeAsString(content);
}

Future<void> _gitCliTest(String repositoryPath, List<String> args) async {
  final result = await Process.run('git', ['-C', repositoryPath, ...args]);
  if (result.exitCode != 0) {
    throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
  }
}
