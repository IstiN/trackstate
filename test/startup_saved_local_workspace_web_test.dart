@TestOn('browser')
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
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
    'web startup begins hosted auth restore immediately when the saved local workspace needs browser reselection',
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

      final delayedRepository = _DelayedConnectRepository(
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

      expect(find.byKey(const ValueKey('workspace-switcher-trigger')), findsOneWidget);
      expect(find.text('Dashboard'), findsWidgets);
      expect(find.text('Git-native. Jira-compatible. Team-proven.'), findsWidgets);

      delayedRepository.completeConnect();
      await tester.pump();
      await tester.pumpAndSettle();
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

class _DelayedConnectRepository extends DemoTrackStateRepository {
  _DelayedConnectRepository({required super.snapshot});

  final Completer<RepositoryUser> _connectCompleter =
      Completer<RepositoryUser>();
  int connectCalls = 0;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) {
    connectCalls += 1;
    return _connectCompleter.future;
  }

  void completeConnect() {
    if (_connectCompleter.isCompleted) {
      return;
    }
    _connectCompleter.complete(
      const RepositoryUser(login: 'demo-user', displayName: 'Demo User'),
    );
  }
}
