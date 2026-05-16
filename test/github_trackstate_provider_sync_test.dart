import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
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
