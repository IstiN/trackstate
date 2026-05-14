import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'startup restore skips an invalid workspace and opens the next valid saved workspace',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'local:/tmp/missing@main',
              displayName: 'broken',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/missing',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:stable/repo@main',
              displayName: 'stable/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'stable/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: 'local:/tmp/missing@main',
          migrationComplete: true,
        ),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: service,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async =>
                  throw StateError('Missing repository $repositoryPath'),
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
      await tester.pumpAndSettle();

      expect(
        find.textContaining('Skipped broken during restore.'),
        findsOneWidget,
      );
      expect(service.state.activeWorkspaceId, 'hosted:stable/repo@main');
      expect(find.text('stable/repo'), findsWidgets);
    },
  );

  testWidgets(
    'workspace switcher keeps the current section while switching to another saved workspace',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:alpha/repo@main',
              displayName: 'alpha/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alpha/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'local:/tmp/demo@main',
              displayName: 'demo',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/demo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: 'hosted:alpha/repo@main',
          migrationComplete: true,
        ),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repository: const DemoTrackStateRepository(),
          workspaceProfileService: service,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repository),
              ),
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repositoryPath),
              ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.bySemanticsLabel(RegExp('Board')).first);
      await tester.pumpAndSettle();
      expect(find.bySemanticsLabel(RegExp('To Do column')), findsOneWidget);

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();
      expect(find.text('Saved workspaces'), findsOneWidget);

      await tester.tap(
        find.byKey(const ValueKey('workspace-open-local:/tmp/demo@main')),
      );
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel(RegExp('To Do column')), findsOneWidget);
      expect(service.state.activeWorkspaceId, 'local:/tmp/demo@main');
    },
  );

  testWidgets(
    'workspace switcher can add a hosted workspace and switch to it',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        const WorkspaceProfilesState(migrationComplete: true),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repository: const DemoTrackStateRepository(),
          workspaceProfileService: service,
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
      await tester.pumpAndSettle();

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Repository'),
        'new/repo',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Branch'),
        'main',
      );
      await tester.tap(find.byKey(const ValueKey('workspace-add-button')));
      await tester.pumpAndSettle();

      expect(service.state.activeWorkspaceId, 'hosted:new/repo@main');
      expect(find.textContaining('new/repo'), findsWidgets);
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

class _MemoryWorkspaceProfileService implements WorkspaceProfileService {
  _MemoryWorkspaceProfileService(this.state);

  WorkspaceProfilesState state;

  @override
  Future<WorkspaceProfile> createProfile(
    WorkspaceProfileInput input, {
    bool select = true,
  }) async {
    final created = WorkspaceProfile.create(input);
    state = WorkspaceProfilesState(
      profiles: resolveWorkspaceDisplayNames([...state.profiles, created]),
      activeWorkspaceId: select ? created.id : state.activeWorkspaceId,
      migrationComplete: true,
    );
    return state.profiles.firstWhere((profile) => profile.id == created.id);
  }

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) async {
    final nextProfiles = state.profiles
        .where((profile) => profile.id != workspaceId)
        .toList(growable: false);
    state = WorkspaceProfilesState(
      profiles: nextProfiles,
      activeWorkspaceId: state.activeWorkspaceId == workspaceId
          ? nextProfiles.isEmpty
                ? null
                : nextProfiles.first.id
          : state.activeWorkspaceId,
      migrationComplete: true,
    );
    return state;
  }

  @override
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  ) async => null;

  @override
  Future<WorkspaceProfilesState> loadState() async => state;

  @override
  Future<WorkspaceProfilesState> selectProfile(String workspaceId) async {
    state = state.copyWith(activeWorkspaceId: workspaceId);
    return state;
  }

  @override
  Future<WorkspaceProfile> updateProfile(
    String workspaceId,
    WorkspaceProfileInput input, {
    bool select = true,
  }) async {
    final updated = WorkspaceProfile.create(input);
    state = WorkspaceProfilesState(
      profiles: [
        for (final profile in state.profiles)
          if (profile.id == workspaceId) updated else profile,
      ],
      activeWorkspaceId: select ? updated.id : state.activeWorkspaceId,
      migrationComplete: true,
    );
    return updated;
  }
}
