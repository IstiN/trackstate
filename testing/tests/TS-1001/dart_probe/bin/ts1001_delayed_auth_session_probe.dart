import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../../../../../lib/data/providers/github/github_trackstate_provider.dart';
import '../../../../../lib/data/providers/trackstate_provider.dart';
import '../../../../../lib/data/repositories/trackstate_repository.dart';
import '../../../../../lib/domain/models/trackstate_models.dart';

class DelayedUserHttpClient extends http.BaseClient {
  DelayedUserHttpClient({
    required Duration userDelay,
    http.Client? inner,
  }) : _userDelay = userDelay,
       _inner = inner ?? http.Client() {
    _stopwatch.start();
  }

  final Duration _userDelay;
  final http.Client _inner;
  final Stopwatch _stopwatch = Stopwatch();
  final List<String> requestedUrls = <String>[];
  final Completer<void> userRequestStarted = Completer<void>();
  final Completer<void> userRequestReleased = Completer<void>();

  double? userRequestStartedAfterStartSeconds;
  double? userRequestReleasedAfterStartSeconds;
  int userRequestCount = 0;
  bool _userRequestPending = false;

  bool get userRequestPending => _userRequestPending;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    requestedUrls.add(request.url.toString());
    final isDelayedUserRequest = _isDelayedUserRequest(request.url);
    if (isDelayedUserRequest) {
      userRequestCount += 1;
      _userRequestPending = true;
      userRequestStartedAfterStartSeconds ??= _elapsedSeconds();
      if (!userRequestStarted.isCompleted) {
        userRequestStarted.complete();
      }
      await Future<void>.delayed(_userDelay);
      _userRequestPending = false;
      userRequestReleasedAfterStartSeconds ??= _elapsedSeconds();
      if (!userRequestReleased.isCompleted) {
        userRequestReleased.complete();
      }
    }
    return _inner.send(request);
  }

  @override
  void close() {
    _inner.close();
    super.close();
  }

  static bool _isDelayedUserRequest(Uri url) {
    final path = url.path.replaceFirst(RegExp(r'/$'), '');
    return path == '/user';
  }

  double _elapsedSeconds() => _stopwatch.elapsedMilliseconds / 1000;
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

Future<void> main() async {
  final repository =
      _requiredEnv('TS1001_REPOSITORY', 'IstiN/trackstate-setup');
  final branch = _requiredEnv('TS1001_BRANCH', 'main');
  final token = _requiredEnv('TS1001_GITHUB_TOKEN');
  final authDelaySeconds = int.parse(
    _requiredEnv('TS1001_AUTH_DELAY_SECONDS', '30'),
  );
  final timeoutAssertionSeconds = int.parse(
    _requiredEnv('TS1001_TIMEOUT_ASSERTION_SECONDS', '12'),
  );

  final result = <String, Object?>{
    'status': 'failed',
    'failureType': 'setup',
    'repository': repository,
    'branch': branch,
    'authDelaySeconds': authDelaySeconds,
    'timeoutAssertionSeconds': timeoutAssertionSeconds,
  };

  final client = DelayedUserHttpClient(
    userDelay: Duration(seconds: authDelaySeconds),
  );
  try {
    final provider = GitHubTrackStateProvider(
      client: client,
      repositoryName: repository,
      sourceRef: branch,
      dataRef: branch,
    );
    final trackstateRepository = ProviderBackedTrackStateRepository(
      provider: provider,
    );

    final connectFuture = trackstateRepository.connect(
      RepositoryConnection(
        repository: repository,
        branch: branch,
        token: token,
      ),
    );

    final userRequestBegan = await _waitFor(
      client.userRequestStarted.future,
      timeout: const Duration(seconds: 45),
    );
    result['userRequestStarted'] = userRequestBegan;
    if (!userRequestBegan) {
      throw StateError(
        'The real GitHub provider never started the delayed `/user` request while connect() was in progress.',
      );
    }

    await Future<void>.delayed(Duration(seconds: timeoutAssertionSeconds));

    final checkpointSession = _serializeSession(trackstateRepository.session);
    result['checkpointSession'] = checkpointSession;
    result['userRequestPendingAtCheckpoint'] = client.userRequestPending;
    result['userRequestStartedAfterStartSeconds'] =
        client.userRequestStartedAfterStartSeconds;
    result['requestedUrls'] = client.requestedUrls;

    if (checkpointSession == null) {
      throw StateError(
        'The repository session was null at the delayed-auth checkpoint.',
      );
    }
    if (checkpointSession['connectionState'] !=
        'ProviderConnectionState.connecting') {
      throw StateError(
        'The session connection state was ${checkpointSession['connectionState']} instead of ProviderConnectionState.connecting at the delayed-auth checkpoint.',
      );
    }
    if (checkpointSession['canWrite'] != false) {
      throw StateError(
        'The session `canWrite` flag was ${checkpointSession['canWrite']} instead of false at the delayed-auth checkpoint.',
      );
    }
    if (checkpointSession['canCreateBranch'] != false) {
      throw StateError(
        'The session `canCreateBranch` flag was ${checkpointSession['canCreateBranch']} instead of false at the delayed-auth checkpoint.',
      );
    }
    if (client.userRequestPending != true) {
      throw StateError(
        'The delayed `/user` request was no longer pending at the delayed-auth checkpoint.',
      );
    }

    await connectFuture.timeout(Duration(seconds: authDelaySeconds + 60));

    result['finalSession'] = _serializeSession(trackstateRepository.session);
    result['userRequestReleasedAfterStartSeconds'] =
        client.userRequestReleasedAfterStartSeconds;
    result['status'] = 'passed';
    result['failureType'] = null;
  } on StateError catch (error, stackTrace) {
    result['failureType'] = 'product';
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  } on Object catch (error, stackTrace) {
    result['failureType'] = 'setup';
    result['error'] = error.toString();
    result['stackTrace'] = stackTrace.toString();
  } finally {
    client.close();
  }

  print(jsonEncode(result));
}

String _requiredEnv(String key, [String? fallback]) {
  final value = Platform.environment[key]?.trim();
  if (value != null && value.isNotEmpty) {
    return value;
  }
  if (fallback != null) {
    return fallback;
  }
  throw StateError('Missing required environment variable $key.');
}

Future<bool> _waitFor(
  Future<void> future, {
  required Duration timeout,
}) async {
  try {
    await future.timeout(timeout);
    return true;
  } on TimeoutException {
    return false;
  }
}
