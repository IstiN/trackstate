import 'dart:collection';
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
    'startup exposes the shell before delayed auth completes in web-style restore flow',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final service = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await service.createProfile(
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
          workspaceProfileService: service,
          authStore: authStore,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => _QueuedLoadTrackStateRepository(
                loadResults: [
                  UnsupportedError(
                    'Unsupported operation: Process.run is not supported on the web.',
                  ),
                ],
              ),
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
      await tester.pump(const Duration(milliseconds: 500));

      expect(
        find.bySemanticsLabel(
          'Workspace switcher: Active local workspace, Local, Local Git',
        ),
        findsOneWidget,
      );
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

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) =>
      _connectCompleter.future;

  void completeConnect() {
    if (_connectCompleter.isCompleted) {
      return;
    }
    _connectCompleter.complete(
      const RepositoryUser(login: 'demo-user', displayName: 'Demo User'),
    );
  }
}

class _QueuedLoadTrackStateRepository extends DemoTrackStateRepository {
  _QueuedLoadTrackStateRepository({required List<Object> loadResults})
    : _loadResults = Queue<Object>.from(loadResults);

  final Queue<Object> _loadResults;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    if (_loadResults.isEmpty) {
      return super.loadSnapshot();
    }
    final next = _loadResults.removeFirst();
    if (next is TrackerSnapshot) {
      return next;
    }
    throw next;
  }
}
