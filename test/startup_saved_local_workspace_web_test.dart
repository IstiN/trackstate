@TestOn('browser')
library;

import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/startup_auth_probe_diagnostics.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'web startup keeps the shell hidden until the delayed /user probe completes when the active local workspace has no browser handle',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken(
        'github-token',
        workspaceId: activeLocalWorkspaceId,
      );

      final delayedRepository = _DelayedGitHubProbeRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repositoryFactory: () => delayedRepository,
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openBrowserLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => null,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repository),
              ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 750));

      expect(delayedRepository.userProbeRequestCount, 1);
      expect(delayedRepository.requestedPaths, contains('/user'));
      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsNothing,
      );
      expect(find.text('Dashboard'), findsNothing);
      expect(
        find.text('Git-native. Jira-compatible. Team-proven.'),
        findsNothing,
      );
      expect(find.text('Add workspace'), findsNothing);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(delayedRepository.session, isNotNull);
      expect(delayedRepository.session?.canRead, isTrue);
      expect(delayedRepository.session?.canWrite, isFalse);
      expect(delayedRepository.session?.canCreateBranch, isFalse);
      final savedStateBeforeProbe = await workspaceProfiles.loadState();
      expect(savedStateBeforeProbe.activeWorkspaceId, activeLocalWorkspaceId);
      expect(
        savedStateBeforeProbe.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );

      delayedRepository.completeUserProbe();
      await tester.pump();
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsOneWidget,
      );
      expect(
        find.text('Git-native. Jira-compatible. Team-proven.'),
        findsWidgets,
      );
      expect(find.text('Dashboard'), findsWidgets);
      expect(find.text('Add workspace'), findsNothing);
      expect(
        delayedRepository.session?.connectionState,
        ProviderConnectionState.connected,
      );
      expect(delayedRepository.session?.canWrite, isTrue);
      expect(delayedRepository.session?.canCreateBranch, isTrue);
      final savedStateAfterProbe = await workspaceProfiles.loadState();
      expect(savedStateAfterProbe.activeWorkspaceId, activeLocalWorkspaceId);
      expect(
        savedStateAfterProbe.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
    },
  );

  testWidgets(
    'web startup logs the delayed /user timeout fallback when the shell opens before the auth probe completes',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken(
        'github-token',
        workspaceId: activeLocalWorkspaceId,
      );

      final delayedRepository = _DelayedGitHubProbeRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );
      final diagnosticLogs = <String>[];
      final previousDiagnostics = startupAuthProbeDiagnostics;
      var elapsed = Duration.zero;

      startupAuthProbeDiagnostics = StartupAuthProbeDiagnostics(
        now: () => DateTime.fromMillisecondsSinceEpoch(elapsed.inMilliseconds),
        logger: diagnosticLogs.add,
      );

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        startupAuthProbeDiagnostics = previousDiagnostics;
      });

      await tester.pumpWidget(
        TrackStateApp(
          repositoryFactory: () => delayedRepository,
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openBrowserLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => null,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repository),
              ),
        ),
      );
      await tester.pump();
      elapsed += const Duration(milliseconds: 750);
      await tester.pump(const Duration(milliseconds: 750));

      expect(delayedRepository.userProbeRequestCount, 1);
      expect(delayedRepository.requestedPaths, contains('/user'));
      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsNothing,
      );
      expect(diagnosticLogs, isEmpty);

      elapsed += const Duration(seconds: 11);
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();

      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsOneWidget,
      );
      expect(find.text('Dashboard'), findsWidgets);
      expect(
        delayedRepository.session?.connectionState,
        isNot(ProviderConnectionState.connected),
      );
      expect(delayedRepository.session?.canWrite, isFalse);
      expect(delayedRepository.session?.canCreateBranch, isFalse);
      expect(find.text('Connect GitHub'), findsOneWidget);
      expect(
        diagnosticLogs,
        contains(
          predicate<String>(
            (entry) =>
                entry.contains('/user') &&
                entry.contains('shell_ready') &&
                entry.contains('timeout') &&
                entry.contains('delta_seconds='),
            'startup timeout diagnostic entry',
          ),
        ),
      );

      delayedRepository.completeUserProbe();
      await tester.pump();
      await tester.pumpAndSettle();

      expect(
        delayedRepository.session?.connectionState,
        ProviderConnectionState.connected,
      );
      expect(delayedRepository.session?.canWrite, isTrue);
      expect(delayedRepository.session?.canCreateBranch, isTrue);
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

class _DelayedGitHubProbeRepository extends ProviderBackedTrackStateRepository {
  _DelayedGitHubProbeRepository({required TrackerSnapshot snapshot})
    : this._(snapshot: snapshot, harness: _DelayedGitHubProbeHarness());

  _DelayedGitHubProbeRepository._({
    required TrackerSnapshot snapshot,
    required _DelayedGitHubProbeHarness harness,
  }) : _snapshotOverride = snapshot,
       _harness = harness,
       super(
         provider: GitHubTrackStateProvider(
           client: MockClient(harness.handle),
           repositoryName: 'stable/repo',
           dataRef: 'main',
           sourceRef: 'main',
         ),
       );

  final TrackerSnapshot _snapshotOverride;
  final _DelayedGitHubProbeHarness _harness;

  List<String> get requestedPaths => _harness.requestedPaths;
  int get userProbeRequestCount => _harness.userProbeRequestCount;

  void completeUserProbe() {
    _harness.completeUserProbe();
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    replaceCachedState(snapshot: _snapshotOverride);
    return _snapshotOverride;
  }
}

class _DelayedGitHubProbeHarness {
  final Completer<void> _userProbeCompleter = Completer<void>();
  final List<String> requestedPaths = <String>[];
  int userProbeRequestCount = 0;

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
      case '/repos/stable/repo/branches/main':
        return http.Response(
          jsonEncode({
            'name': 'main',
            'commit': <String, Object?>{'sha': 'mock-revision'},
          }),
          200,
        );
      case '/user':
        userProbeRequestCount += 1;
        await _userProbeCompleter.future;
        return http.Response(
          jsonEncode({
            'login': 'demo-user',
            'name': 'Demo User',
            'id': 1,
            'email': 'demo@example.com',
          }),
          200,
        );
    }
    throw StateError('Unexpected request: ${request.method} ${request.url}');
  }

  void completeUserProbe() {
    if (_userProbeCompleter.isCompleted) {
      return;
    }
    _userProbeCompleter.complete();
  }
}
