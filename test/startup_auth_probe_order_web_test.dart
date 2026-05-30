@TestOn('browser')
library;

import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'web hosted startup starts the shared /user probe before the secondary bootstrap read',
    (tester) async {
      const workspaceId = 'hosted:stable/repo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      await authStore.saveToken('github-token', workspaceId: workspaceId);

      final harness = _StartupProbeOrderHarness();
      final repository = _StartupProbeOrderRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
        harness: harness,
      );
      final viewModel = TrackerViewModel(
        repository: repository,
        authStore: authStore,
        workspaceId: workspaceId,
      );

      await viewModel.load();

      final userIndex = harness.requestedPaths.indexOf('/user');
      final secondaryIndex = harness.requestedPaths.indexOf(
        '/repos/stable/repo/contents/DEMO/project.json',
      );

      expect(userIndex, isNonNegative);
      expect(secondaryIndex, isNonNegative);
      expect(
        userIndex,
        lessThan(secondaryIndex),
        reason:
            'The startup auth probe must be armed before secondary hosted bootstrap reads begin.',
      );
      expect(viewModel.isConnected, isTrue);
      viewModel.dispose();
    },
  );

  testWidgets(
    'web startup auth probe evicts failed shared /user requests before retrying authenticate',
    (tester) async {
      final harness = _RetryingStartupAuthProbeHarness();
      final provider = GitHubTrackStateProvider(
        client: MockClient(harness.handle),
        repositoryName: 'stable/repo',
        dataRef: 'main',
        sourceRef: 'main',
      );
      final probeErrors = <Object>[];

      runZonedGuarded(
        () {
          provider.startStartupAuthProbe('github-token');
        },
        (error, stackTrace) {
          probeErrors.add(error);
        },
      );
      await tester.pump();

      expect(probeErrors, hasLength(1));
      expect(probeErrors.single, isA<TrackStateProviderException>());

      final user = await provider.authenticate(
        const RepositoryConnection(
          repository: 'stable/repo',
          branch: 'main',
          token: 'github-token',
        ),
      );

      expect(user.login, 'demo-user');
      expect(harness.userRequests, 2);
      expect(
        harness.requestedPaths,
        containsAllInOrder(<String>['/user', '/repos/stable/repo', '/user']),
      );
    },
  );
}

Future<TrackerSnapshot> _snapshotForRepository(String repository) async {
  final base = await const DemoTrackStateRepository().loadSnapshot();
  return TrackerSnapshot(
    project: ProjectConfig(
      key: base.project.key,
      name: base.project.name,
      repository: repository,
      branch: base.project.branch,
      defaultLocale: base.project.defaultLocale,
      supportedLocales: base.project.supportedLocales,
      issueTypeDefinitions: base.project.issueTypeDefinitions,
      statusDefinitions: base.project.statusDefinitions,
      fieldDefinitions: base.project.fieldDefinitions,
      workflowDefinitions: base.project.workflowDefinitions,
      priorityDefinitions: base.project.priorityDefinitions,
      versionDefinitions: base.project.versionDefinitions,
      componentDefinitions: base.project.componentDefinitions,
      resolutionDefinitions: base.project.resolutionDefinitions,
      attachmentStorage: base.project.attachmentStorage,
    ),
    issues: base.issues,
    repositoryIndex: base.repositoryIndex,
    loadWarnings: base.loadWarnings,
    readiness: base.readiness,
    startupRecovery: base.startupRecovery,
  );
}

class _StartupProbeOrderRepository extends ProviderBackedTrackStateRepository {
  _StartupProbeOrderRepository({
    required TrackerSnapshot snapshot,
    required _StartupProbeOrderHarness harness,
  }) : _snapshotOverride = snapshot,
       super(
         provider: GitHubTrackStateProvider(
           client: MockClient(harness.handle),
           repositoryName: 'stable/repo',
           dataRef: 'main',
           sourceRef: 'main',
         ),
       );

  final TrackerSnapshot _snapshotOverride;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    await providerAdapter.readTextFile('DEMO/project.json', ref: 'main');
    replaceCachedState(snapshot: _snapshotOverride);
    return _snapshotOverride;
  }
}

class _StartupProbeOrderHarness {
  final List<String> requestedPaths = <String>[];

  Future<http.Response> handle(http.Request request) async {
    requestedPaths.add(request.url.path);
    switch (request.url.path) {
      case '/repos/stable/repo':
        return http.Response(
          jsonEncode({
            'full_name': 'stable/repo',
            'permissions': <String, Object?>{
              'pull': true,
              'push': true,
              'admin': false,
            },
          }),
          200,
        );
      case '/repos/stable/repo/contents/DEMO/project.json':
        return http.Response(
          jsonEncode({
            'content': base64Encode(
              utf8.encode('{"key":"DEMO","name":"Demo Project"}'),
            ),
            'encoding': 'base64',
          }),
          200,
        );
      case '/user':
        return http.Response(
          jsonEncode({
            'login': 'demo-user',
            'name': 'Demo User',
            'id': 1,
            'email': 'demo@example.com',
          }),
          200,
        );
      case '/repos/stable/repo/branches/main':
        return http.Response(
          jsonEncode({
            'name': 'main',
            'commit': <String, Object?>{'sha': 'mock-revision'},
          }),
          200,
        );
    }
    throw StateError('Unexpected request: ${request.method} ${request.url}');
  }
}

class _RetryingStartupAuthProbeHarness {
  final List<String> requestedPaths = <String>[];
  int userRequests = 0;

  Future<http.Response> handle(http.Request request) async {
    requestedPaths.add(request.url.path);
    switch (request.url.path) {
      case '/repos/stable/repo':
        return http.Response(
          jsonEncode({
            'full_name': 'stable/repo',
            'permissions': <String, Object?>{
              'pull': true,
              'push': true,
              'admin': false,
            },
          }),
          200,
        );
      case '/user':
        userRequests += 1;
        if (userRequests == 1) {
          return http.Response(
            jsonEncode({'message': 'temporary startup failure'}),
            503,
          );
        }
        return http.Response(
          jsonEncode({
            'login': 'demo-user',
            'name': 'Demo User',
            'id': 1,
            'email': 'demo@example.com',
          }),
          200,
        );
      case '/repos/stable/repo/branches/main':
        return http.Response(
          jsonEncode({
            'name': 'main',
            'commit': <String, Object?>{'sha': 'mock-revision'},
          }),
          200,
        );
    }
    throw StateError('Unexpected request: ${request.method} ${request.url}');
  }
}
