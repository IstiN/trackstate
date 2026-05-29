import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../../../lib/data/providers/github/github_trackstate_provider.dart';
import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

class ScriptedHttpClient extends http.Client {
  ScriptedHttpClient(this._responses);

  final List<http.Response> _responses;
  final List<String> requestedUrls = <String>[];
  int getCalls = 0;

  @override
  Future<http.Response> get(
    Uri url, {
    Map<String, String>? headers,
  }) async {
    requestedUrls.add(url.toString());
    if (getCalls >= _responses.length) {
      throw StateError(
        'No scripted HTTP response was provided for request #${getCalls + 1} '
        'to $url.',
      );
    }
    return _responses[getCalls++];
  }

  @override
  Future<http.Response> put(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
  }) async {
    throw StateError('TS-117 should not perform PUT requests during connect().');
  }
}

Map<String, Object?>? _serializeSession(ProviderSession? session) {
  if (session == null) {
    return null;
  }
  return {
    'providerType': session.providerType.toString(),
    'connectionState': session.connectionState.toString(),
    'resolvedUserIdentity': session.resolvedUserIdentity,
    'canRead': session.canRead,
    'canWrite': session.canWrite,
    'canCreateBranch': session.canCreateBranch,
    'canManageAttachments': session.canManageAttachments,
    'canCheckCollaborators': session.canCheckCollaborators,
  };
}

Future<Map<String, Object?>> _runScenario({
  required int statusCode,
  required String body,
}) async {
  final client = ScriptedHttpClient(<http.Response>[
    http.Response(body, statusCode),
  ]);
  final provider = GitHubTrackStateProvider(
    client: client,
    repositoryName: 'mock/error-repository',
    sourceRef: 'main',
    dataRef: 'main',
  );
  final repository = ProviderBackedTrackStateRepository(provider: provider);

  final result = <String, Object?>{
    'status': 'failed',
    'statusCode': statusCode,
  };

  try {
    try {
      await repository.connect(
        const RepositoryConnection(
          repository: 'mock/error-repository',
          branch: 'main',
          token: 'mock-token',
        ),
      );
      throw StateError(
        'HTTP $statusCode connect() unexpectedly succeeded instead of exposing '
        'the restricted failure state.',
      );
    } catch (error, stackTrace) {
      result['connectError'] = error.toString();
      result['connectStackTrace'] = stackTrace.toString();
    }

    result['getCalls'] = client.getCalls;
    result['requestedUrls'] = client.requestedUrls;
    result['session'] = _serializeSession(repository.session);
    result['status'] = 'passed';
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  return result;
}

Future<void> main() async {
  final result = <String, Object?>{'status': 'failed'};

  try {
    result['scenarios'] = <Map<String, Object?>>[
      await _runScenario(
        statusCode: 403,
        body: '{"message":"Forbidden"}',
      ),
      await _runScenario(
        statusCode: 500,
        body: '{"message":"Internal Server Error"}',
      ),
    ];
    result['status'] = 'passed';
  } catch (error, stackTrace) {
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  }

  print(jsonEncode(result));
}
