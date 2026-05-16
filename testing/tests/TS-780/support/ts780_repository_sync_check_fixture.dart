import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts780RepositorySyncCheckFixture {
  Future<RepositorySyncCheck> readHostedSyncCheck({
    int? loadSnapshotDelta,
  }) async {
    final provider = await _createAuthenticatedProvider(
      comparePayload: _comparePayload(loadSnapshotDelta: loadSnapshotDelta),
    );

    final baseline = await provider.checkSync();
    return provider.checkSync(
      previousState: _previousStateWithRevision(
        baseline.state,
        repositoryRevision: 'old-revision',
      ),
    );
  }

  Map<String, Object?> _comparePayload({int? loadSnapshotDelta}) {
    final message = StringBuffer('Hosted sync refresh');
    if (loadSnapshotDelta != null) {
      message.write('\n\nload_snapshot_delta=$loadSnapshotDelta');
    }

    return <String, Object?>{
      'files': const <Object?>[],
      'commits': <Object?>[
        <String, Object?>{
          'commit': <String, Object?>{'message': message.toString()},
        },
      ],
    };
  }
}

Future<GitHubTrackStateProvider> _createAuthenticatedProvider({
  required Map<String, Object?> comparePayload,
}) async {
  final client = MockClient((request) async {
    switch (request.url.path) {
      case '/repos/owner/current':
        return http.Response(
          jsonEncode(<String, Object?>{
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
          jsonEncode(<String, Object?>{
            'login': 'workspace-tester',
            'name': 'Workspace Tester',
          }),
          200,
        );
      case '/repos/owner/current/branches/main':
        return http.Response(
          jsonEncode(<String, Object?>{
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
    workingTreeRevision: baseline.workingTreeRevision,
    permission: baseline.permission,
  );
}
