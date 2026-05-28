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
        getResponseFetcher: (uri, {required headers, http.Client? client}) async {
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
                headers: const {'www-authenticate': 'Bearer realm="GitHub"'},
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
