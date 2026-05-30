import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/providers/github/github_auth_probe_stub.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  test(
    'GitHub provider falls back to the source branch when the session branch is a commit SHA',
    () async {
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          switch (request.url.path) {
            case '/repos/owner/current':
              return http.Response(
                jsonEncode({
                  'full_name': 'owner/current',
                  'permissions': <String, Object?>{
                    'pull': true,
                    'push': true,
                    'admin': false,
                  },
                }),
                200,
              );
            case '/user':
              return http.Response(
                jsonEncode({
                  'login': 'workspace-tester',
                  'name': 'Workspace Tester',
                }),
                200,
              );
          }
          throw StateError('Unexpected request: ${request.url}');
        }),
        repositoryName: 'owner/current',
        dataRef: 'main',
        sourceRef: 'main',
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'owner/current',
          branch: '679af646b17eacb271c050376c4737c82cd0cfc7',
          token: 'token',
        ),
      );

      expect(await provider.resolveWriteBranch(), 'main');
    },
  );

  test(
    'GitHub provider falls back to dataRef when both sourceRef and session branch are commit SHAs (stale write ref)',
    () async {
      const staleSha = '59c6bb158aadd5b519207735181ee530eba4fc80';
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          switch (request.url.path) {
            case '/repos/owner/current':
              return http.Response(
                jsonEncode({
                  'full_name': 'owner/current',
                  'permissions': <String, Object?>{
                    'pull': true,
                    'push': true,
                    'admin': false,
                  },
                }),
                200,
              );
            case '/user':
              return http.Response(
                jsonEncode({
                  'login': 'workspace-tester',
                  'name': 'Workspace Tester',
                }),
                200,
              );
          }
          throw StateError('Unexpected request: ${request.url}');
        }),
        repositoryName: 'owner/current',
        dataRef: 'main',
        sourceRef: staleSha,
      );

      // Unauthenticated: configuredBranch is empty, sourceRef is a SHA → dataRef
      expect(await provider.resolveWriteBranch(), 'main');

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'owner/current',
          branch: staleSha,
          token: 'token',
        ),
      );

      // Authenticated with SHA branch: sourceRef is also a SHA → dataRef
      expect(await provider.resolveWriteBranch(), 'main');
    },
  );

  test(
    'GitHub provider emits hosted snapshot reload for compare commits with load_snapshot_delta=1',
    () async {
      final provider = await _createAuthenticatedProvider(
        comparePayload: <String, Object?>{
          'files': const <Object?>[],
          'commits': <Object?>[
            <String, Object?>{
              'commit': <String, Object?>{
                'message': 'Hosted sync refresh\n\nload_snapshot_delta=1',
              },
            },
          ],
        },
      );

      final baseline = await provider.checkSync();
      final result = await provider.checkSync(
        previousState: _previousStateWithRevision(
          baseline.state,
          repositoryRevision: 'old-revision',
        ),
      );

      expect(
        result.signals,
        containsAll(<WorkspaceSyncSignal>{
          WorkspaceSyncSignal.hostedRepository,
          WorkspaceSyncSignal.hostedSnapshotReload,
        }),
      );
      expect(result.changedPaths, isEmpty);
      expect(
        result.hostedSnapshotReloadDirective,
        HostedSnapshotReloadDirective.enabled,
      );
    },
  );

  test(
    'GitHub provider does not emit hosted snapshot reload without an explicit compare marker',
    () async {
      final provider = await _createAuthenticatedProvider(
        comparePayload: <String, Object?>{
          'files': const <Object?>[],
          'commits': <Object?>[
            <String, Object?>{
              'commit': <String, Object?>{
                'message': 'Hosted sync refresh without explicit reload',
              },
            },
          ],
        },
      );

      final baseline = await provider.checkSync();
      final result = await provider.checkSync(
        previousState: _previousStateWithRevision(
          baseline.state,
          repositoryRevision: 'old-revision',
        ),
      );

      expect(result.signals, contains(WorkspaceSyncSignal.hostedRepository));
      expect(
        result.signals,
        isNot(contains(WorkspaceSyncSignal.hostedSnapshotReload)),
      );
      expect(result.changedPaths, isEmpty);
      expect(result.hostedSnapshotReloadDirective, isNull);
    },
  );

  test(
    'GitHub provider cache-busts hosted sync revision checks without extra headers',
    () async {
      Uri? branchRequestUri;
      Map<String, String>? branchRequestHeaders;
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          switch (request.url.path) {
            case '/repos/owner/current':
              return http.Response(
                jsonEncode({
                  'full_name': 'owner/current',
                  'permissions': <String, Object?>{
                    'pull': true,
                    'push': true,
                    'admin': false,
                  },
                }),
                200,
              );
            case '/user':
              return http.Response(
                jsonEncode({
                  'login': 'workspace-tester',
                  'name': 'Workspace Tester',
                }),
                200,
              );
            case '/repos/owner/current/branches/main':
              branchRequestUri = request.url;
              branchRequestHeaders = Map<String, String>.from(request.headers);
              return http.Response(
                jsonEncode({
                  'commit': <String, Object?>{'sha': 'new-revision'},
                }),
                200,
              );
          }
          throw StateError('Unexpected request: ${request.url}');
        }),
        repositoryName: 'owner/current',
        dataRef: 'main',
        sourceRef: 'main',
        disableHostedSyncRequestCaching: true,
        hostedSyncCacheBustTokenFactory: () => 'fixed-cache-bust-token',
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'owner/current',
          branch: 'main',
          token: 'token',
        ),
      );

      await provider.checkSync();

      expect(branchRequestUri, isNotNull);
      expect(
        branchRequestUri!.queryParameters['_trackstate_refresh'],
        'fixed-cache-bust-token',
      );
      expect(branchRequestHeaders, isNotNull);
      expect(branchRequestHeaders, isNot(contains('cache-control')));
      expect(branchRequestHeaders, isNot(contains('pragma')));
    },
  );

  test(
    'GitHub provider keeps hosted branch polling responsive after consecutive auth failures',
    () async {
      final delayedSecondBranchResponse = Completer<http.Response>();
      var branchRequestCount = 0;
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          switch (request.url.path) {
            case '/repos/owner/current':
              return http.Response(
                jsonEncode({
                  'full_name': 'owner/current',
                  'permissions': <String, Object?>{
                    'pull': true,
                    'push': true,
                    'admin': false,
                  },
                }),
                200,
              );
            case '/user':
              return http.Response(
                jsonEncode({
                  'login': 'workspace-tester',
                  'name': 'Workspace Tester',
                }),
                200,
              );
            case '/repos/owner/current/branches/main':
              branchRequestCount += 1;
              if (branchRequestCount == 1) {
                return http.Response(
                  jsonEncode({'message': 'Bad credentials'}),
                  401,
                  headers: const {'www-authenticate': 'Bearer realm="GitHub"'},
                );
              }
              return delayedSecondBranchResponse.future;
          }
          throw StateError('Unexpected request: ${request.url}');
        }),
        repositoryName: 'owner/current',
        dataRef: 'main',
        sourceRef: 'main',
        getResponseFetcher:
            (uri, {required headers, http.Client? client}) async {
              switch (uri.path) {
                case '/repos/owner/current':
                  return GitHubAuthProbeResponse(
                    statusCode: 200,
                    body: jsonEncode({
                      'full_name': 'owner/current',
                      'permissions': <String, Object?>{
                        'pull': true,
                        'push': true,
                        'admin': false,
                      },
                    }),
                  );
                case '/user':
                  return GitHubAuthProbeResponse(
                    statusCode: 200,
                    body: jsonEncode({
                      'login': 'workspace-tester',
                      'name': 'Workspace Tester',
                    }),
                  );
                case '/repos/owner/current/branches/main':
                  return GitHubAuthProbeResponse(
                    statusCode: 401,
                    body: jsonEncode({'message': 'Bad credentials'}),
                    headers: const {
                      'www-authenticate': 'Bearer realm="GitHub"',
                    },
                  );
              }
              throw StateError('Unexpected request: $uri');
            },
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'owner/current',
          branch: 'main',
          token: 'token',
        ),
      );

      final previousState = RepositorySyncState(
        providerType: ProviderType.github,
        repositoryRevision: 'current-revision',
        sessionRevision: 'connected:true:true',
        connectionState: ProviderConnectionState.connected,
      );

      Future<Duration> measureFailedCheck() async {
        final stopwatch = Stopwatch()..start();
        try {
          await provider.checkSync(previousState: previousState);
          fail('Expected the hosted branch check to fail.');
        } on TrackStateProviderException {
          stopwatch.stop();
          return stopwatch.elapsed;
        }
      }

      final firstFailureElapsed = await measureFailedCheck();
      final secondFailureElapsed = await measureFailedCheck().timeout(
        const Duration(milliseconds: 100),
      );

      expect(firstFailureElapsed, lessThan(const Duration(milliseconds: 100)));
      expect(secondFailureElapsed, lessThan(const Duration(milliseconds: 100)));
    },
  );

  test(
    'Hosted sync revision query parameters stay empty when cache busting is disabled',
    () {
      expect(
        hostedSyncRevisionQueryParametersForTesting(
          disableCache: false,
          cacheBustTokenFactory: () => 'unused',
        ),
        isNull,
      );
    },
  );

  test(
    'GitHub provider cache-busts hosted tree and content reads when hosted sync caching is disabled',
    () async {
      Uri? treeRequestUri;
      Uri? contentsRequestUri;
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          switch (request.url.path) {
            case '/repos/owner/current':
              return http.Response(
                jsonEncode({
                  'full_name': 'owner/current',
                  'permissions': <String, Object?>{
                    'pull': true,
                    'push': true,
                    'admin': false,
                  },
                }),
                200,
              );
            case '/user':
              return http.Response(
                jsonEncode({
                  'login': 'workspace-tester',
                  'name': 'Workspace Tester',
                }),
                200,
              );
            case '/repos/owner/current/git/trees/main':
              treeRequestUri = request.url;
              return http.Response(
                jsonEncode({
                  'tree': [
                    <String, Object?>{
                      'path': 'DEMO/config/fields.json',
                      'type': 'blob',
                      'sha': 'tree-fields-sha',
                    },
                  ],
                }),
                200,
              );
            case '/repos/owner/current/contents/DEMO/config/fields.json':
              contentsRequestUri = request.url;
              return http.Response(
                jsonEncode({
                  'content': base64Encode(
                    utf8.encode(
                      '[{"id":"summary","name":"Summary","type":"string","required":true}]',
                    ),
                  ),
                  'sha': 'content-fields-sha',
                }),
                200,
              );
          }
          throw StateError('Unexpected request: ${request.url}');
        }),
        repositoryName: 'owner/current',
        dataRef: 'main',
        sourceRef: 'main',
        disableHostedSyncRequestCaching: true,
        hostedSyncCacheBustTokenFactory: () => 'fixed-cache-bust-token',
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'owner/current',
          branch: 'main',
          token: 'token',
        ),
      );

      await provider.listTree(ref: 'main');
      await provider.readTextFile('DEMO/config/fields.json', ref: 'main');

      expect(treeRequestUri, isNotNull);
      expect(treeRequestUri!.queryParameters, containsPair('recursive', '1'));
      expect(
        treeRequestUri!.queryParameters['_trackstate_refresh'],
        'fixed-cache-bust-token',
      );
      expect(contentsRequestUri, isNotNull);
      expect(contentsRequestUri!.queryParameters['ref'], 'main');
      expect(
        contentsRequestUri!.queryParameters['_trackstate_refresh'],
        'fixed-cache-bust-token',
      );
    },
  );

  test(
    'GitHub provider preserves explicit load_snapshot_delta=0 as a public bypass directive',
    () async {
      final provider = await _createAuthenticatedProvider(
        comparePayload: <String, Object?>{
          'files': const <Object?>[],
          'commits': <Object?>[
            <String, Object?>{
              'commit': <String, Object?>{
                'message': 'Hosted sync refresh\n\nload_snapshot_delta=0',
              },
            },
          ],
        },
      );

      final baseline = await provider.checkSync();
      final result = await provider.checkSync(
        previousState: _previousStateWithRevision(
          baseline.state,
          repositoryRevision: 'old-revision',
        ),
      );

      expect(result.signals, contains(WorkspaceSyncSignal.hostedRepository));
      expect(
        result.signals,
        isNot(contains(WorkspaceSyncSignal.hostedSnapshotReload)),
      );
      expect(result.changedPaths, isEmpty);
      expect(
        result.hostedSnapshotReloadDirective,
        HostedSnapshotReloadDirective.disabled,
      );
    },
  );

  test(
    'GitHub provider validates file revisions from one tree snapshot during applyFileChanges',
    () async {
      var contentsRequestCount = 0;
      var treeValidationRequestCount = 0;
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          switch (request.url.path) {
            case '/repos/owner/current':
              return http.Response(
                jsonEncode({
                  'full_name': 'owner/current',
                  'permissions': <String, Object?>{
                    'pull': true,
                    'push': true,
                    'admin': false,
                  },
                }),
                200,
              );
            case '/user':
              return http.Response(
                jsonEncode({
                  'login': 'workspace-tester',
                  'name': 'Workspace Tester',
                }),
                200,
              );
            case '/repos/owner/current/git/ref/heads/main':
              return http.Response(
                jsonEncode({
                  'object': <String, Object?>{'sha': 'head-commit'},
                }),
                200,
              );
            case '/repos/owner/current/git/commits/head-commit':
              return http.Response(
                jsonEncode({
                  'tree': <String, Object?>{'sha': 'base-tree'},
                }),
                200,
              );
            case '/repos/owner/current/git/trees/base-tree':
              treeValidationRequestCount += 1;
              expect(request.url.queryParameters['recursive'], '1');
              return http.Response(
                jsonEncode({
                  'tree': <Object?>[
                    <String, Object?>{
                      'path': 'DEMO/config/priorities.json',
                      'type': 'blob',
                      'sha': 'priority-sha',
                    },
                  ],
                }),
                200,
              );
            case '/repos/owner/current/git/trees':
              return http.Response(jsonEncode({'sha': 'updated-tree'}), 201);
            case '/repos/owner/current/git/commits':
              return http.Response(jsonEncode({'sha': 'new-commit'}), 201);
            case '/repos/owner/current/git/refs/heads/main':
              return http.Response(jsonEncode(<String, Object?>{}), 200);
          }

          if (request.url.path.startsWith('/repos/owner/current/contents/')) {
            contentsRequestCount += 1;
            return http.Response('', 500);
          }

          throw StateError('Unexpected request: ${request.url}');
        }),
        repositoryName: 'owner/current',
        dataRef: 'main',
        sourceRef: 'main',
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'owner/current',
          branch: 'main',
          token: 'token',
        ),
      );

      final result = await provider.applyFileChanges(
        const RepositoryFileChangeRequest(
          branch: 'main',
          message: 'Update priorities',
          changes: <RepositoryFileChange>[
            RepositoryTextFileChange(
              path: 'DEMO/config/priorities.json',
              content: '[{"id":"high","name":"High"}]\n',
              expectedRevision: 'priority-sha',
            ),
          ],
        ),
      );

      expect(result.revision, 'new-commit');
      expect(treeValidationRequestCount, 1);
      expect(contentsRequestCount, 0);
    },
  );

  test(
    'GitHub provider falls back to per-path revision lookups when the tree snapshot is truncated',
    () async {
      var contentsRequestCount = 0;
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          switch (request.url.path) {
            case '/repos/owner/current':
              return http.Response(
                jsonEncode({
                  'full_name': 'owner/current',
                  'permissions': <String, Object?>{
                    'pull': true,
                    'push': true,
                    'admin': false,
                  },
                }),
                200,
              );
            case '/user':
              return http.Response(
                jsonEncode({
                  'login': 'workspace-tester',
                  'name': 'Workspace Tester',
                }),
                200,
              );
            case '/repos/owner/current/git/ref/heads/main':
              return http.Response(
                jsonEncode({
                  'object': <String, Object?>{'sha': 'head-commit'},
                }),
                200,
              );
            case '/repos/owner/current/git/commits/head-commit':
              return http.Response(
                jsonEncode({
                  'tree': <String, Object?>{'sha': 'base-tree'},
                }),
                200,
              );
            case '/repos/owner/current/git/trees/base-tree':
              return http.Response(
                jsonEncode({'truncated': true, 'tree': const <Object?>[]}),
                200,
              );
            case '/repos/owner/current/git/trees':
              return http.Response(jsonEncode({'sha': 'updated-tree'}), 201);
            case '/repos/owner/current/git/commits':
              return http.Response(jsonEncode({'sha': 'new-commit'}), 201);
            case '/repos/owner/current/git/refs/heads/main':
              return http.Response(jsonEncode(<String, Object?>{}), 200);
            case '/repos/owner/current/contents/DEMO/config/priorities.json':
              contentsRequestCount += 1;
              expect(request.url.queryParameters['ref'], 'head-commit');
              return http.Response(jsonEncode({'sha': 'priority-sha'}), 200);
          }

          throw StateError('Unexpected request: ${request.url}');
        }),
        repositoryName: 'owner/current',
        dataRef: 'main',
        sourceRef: 'main',
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'owner/current',
          branch: 'main',
          token: 'token',
        ),
      );

      final result = await provider.applyFileChanges(
        const RepositoryFileChangeRequest(
          branch: 'main',
          message: 'Update priorities',
          changes: <RepositoryFileChange>[
            RepositoryTextFileChange(
              path: 'DEMO/config/priorities.json',
              content: '[{"id":"high","name":"High"}]\n',
              expectedRevision: 'priority-sha',
            ),
          ],
        ),
      );

      expect(result.revision, 'new-commit');
      expect(contentsRequestCount, 1);
    },
  );
}

Future<GitHubTrackStateProvider> _createAuthenticatedProvider({
  required Map<String, Object?> comparePayload,
}) async {
  final client = MockClient((request) async {
    switch (request.url.path) {
      case '/repos/owner/current':
        return http.Response(
          jsonEncode({
            'full_name': 'owner/current',
            'permissions': <String, Object?>{
              'pull': true,
              'push': true,
              'admin': false,
            },
          }),
          200,
        );
      case '/user':
        return http.Response(
          jsonEncode({'login': 'workspace-tester', 'name': 'Workspace Tester'}),
          200,
        );
      case '/repos/owner/current/branches/main':
        return http.Response(
          jsonEncode({
            'commit': <String, Object?>{'sha': 'new-revision'},
          }),
          200,
        );
      case '/repos/owner/current/compare/old-revision...new-revision':
        return http.Response(jsonEncode(comparePayload), 200);
    }
    throw StateError('Unexpected request: ${request.url}');
  });

  final provider = GitHubTrackStateProvider(
    client: client,
    repositoryName: 'owner/current',
    dataRef: 'main',
    sourceRef: 'main',
  );
  await provider.authenticate(
    const RepositoryConnection(
      repository: 'owner/current',
      branch: 'main',
      token: 'token',
    ),
  );
  return provider;
}

RepositorySyncState _previousStateWithRevision(
  RepositorySyncState baseline, {
  required String repositoryRevision,
}) {
  return RepositorySyncState(
    providerType: baseline.providerType,
    repositoryRevision: repositoryRevision,
    sessionRevision: baseline.sessionRevision,
    connectionState: baseline.connectionState,
    permission: baseline.permission,
    workingTreeRevision: baseline.workingTreeRevision,
  );
}
