import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'workspace switcher preserves a pending selection while recovery refreshes the active workspace',
    () {
      const primaryWorkspace = WorkspaceProfile(
        id: 'hosted:primary/repo@main',
        displayName: 'TrackState setup (main)',
        targetType: WorkspaceProfileTargetType.hosted,
        target: 'primary/repo',
        defaultBranch: 'main',
        writeBranch: 'main',
      );
      const alternateWorkspace = WorkspaceProfile(
        id: 'hosted:retry-target/repo@main',
        displayName: 'TrackState setup (retry target)',
        targetType: WorkspaceProfileTargetType.hosted,
        target: 'retry-target/repo',
        defaultBranch: 'main',
        writeBranch: 'main',
      );
      final previousWorkspaces = WorkspaceProfilesState(
        profiles: [primaryWorkspace, alternateWorkspace],
        activeWorkspaceId: null,
        migrationComplete: true,
      );
      final nextWorkspaces = WorkspaceProfilesState(
        profiles: [primaryWorkspace, alternateWorkspace],
        activeWorkspaceId: primaryWorkspace.id,
        migrationComplete: true,
      );

      expect(
        resolveWorkspaceSwitcherSelectedWorkspaceId(
          currentSelectedWorkspaceId: alternateWorkspace.id,
          previousWorkspaces: previousWorkspaces,
          nextWorkspaces: nextWorkspaces,
        ),
        alternateWorkspace.id,
      );
    },
  );

  test(
    'workspace selection preserves a newer hosted restore when a stale refresh finishes later',
    () {
      const localWorkspace = WorkspaceProfile(
        id: 'local:/tmp/trackstate-demo@main',
        displayName: 'Active local workspace',
        targetType: WorkspaceProfileTargetType.local,
        target: '/tmp/trackstate-demo',
        defaultBranch: 'main',
        writeBranch: 'main',
      );
      const hostedWorkspace = WorkspaceProfile(
        id: 'hosted:stable/repo@main',
        displayName: 'Hosted setup workspace',
        targetType: WorkspaceProfileTargetType.hosted,
        target: 'stable/repo',
        defaultBranch: 'main',
        writeBranch: 'main',
      );
      final startupWorkspaces = WorkspaceProfilesState(
        profiles: [localWorkspace, hostedWorkspace],
        activeWorkspaceId: localWorkspace.id,
        migrationComplete: true,
      );
      final staleRefreshWorkspaces = WorkspaceProfilesState(
        profiles: [localWorkspace, hostedWorkspace],
        activeWorkspaceId: localWorkspace.id,
        migrationComplete: true,
        unavailableLocalWorkspaceIds: {localWorkspace.id},
      );

      expect(
        resolveWorkspaceSwitcherSelectedWorkspaceId(
          currentSelectedWorkspaceId: hostedWorkspace.id,
          previousWorkspaces: startupWorkspaces,
          nextWorkspaces: staleRefreshWorkspaces,
        ),
        hostedWorkspace.id,
      );
    },
  );

  testWidgets(
    'workspace switcher enables Save and switch after selecting a different saved workspace row',
    (tester) async {
      const primaryWorkspace = WorkspaceProfile(
        id: 'hosted:primary/repo@main',
        displayName: 'TrackState setup (main)',
        targetType: WorkspaceProfileTargetType.hosted,
        target: 'primary/repo',
        defaultBranch: 'main',
        writeBranch: 'main',
      );
      const alternateWorkspace = WorkspaceProfile(
        id: 'hosted:retry-target/repo@main',
        displayName: 'TrackState setup (retry target)',
        targetType: WorkspaceProfileTargetType.hosted,
        target: 'retry-target/repo',
        defaultBranch: 'main',
        writeBranch: 'main',
      );
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [primaryWorkspace, alternateWorkspace],
          activeWorkspaceId: primaryWorkspace.id,
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
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => const DemoTrackStateRepository(),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );
      await tester.pumpAndSettle();

      final workspaceSwitcherSheet = find.byKey(
        const ValueKey('workspace-switcher-sheet'),
      );
      expect(workspaceSwitcherSheet, findsOneWidget);

      final saveButtonBeforeSelection = tester.widget<FilledButton>(
        find.byKey(const ValueKey('workspace-add-button')),
      );
      expect(saveButtonBeforeSelection.onPressed, isNull);

      await tester.tap(
        find.descendant(
          of: workspaceSwitcherSheet,
          matching: find.widgetWithText(
            OutlinedButton,
            'TrackState setup (retry target)',
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(workspaceSwitcherSheet, findsOneWidget);
      final saveButtonAfterSelection = tester.widget<FilledButton>(
        find.byKey(const ValueKey('workspace-add-button')),
      );
      expect(saveButtonAfterSelection.onPressed, isNotNull);

      await tester.tap(find.byKey(const ValueKey('workspace-add-button')));
      await tester.pumpAndSettle();

      expect(service.state.activeWorkspaceId, alternateWorkspace.id);
      expect(workspaceSwitcherSheet, findsNothing);
    },
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
    final profile = WorkspaceProfile.create(input);
    state = WorkspaceProfilesState(
      profiles: [...state.profiles, profile],
      activeWorkspaceId: select ? profile.id : state.activeWorkspaceId,
      migrationComplete: true,
    );
    return profile;
  }

  @override
  Future<WorkspaceProfilesState> clearActiveWorkspaceSelection() async {
    state = state.copyWith(activeWorkspaceId: null);
    return state;
  }

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) async {
    state = WorkspaceProfilesState(
      profiles: state.profiles
          .where((profile) => profile.id != workspaceId)
          .toList(),
      activeWorkspaceId: state.activeWorkspaceId == workspaceId
          ? null
          : state.activeWorkspaceId,
      migrationComplete: true,
      unavailableLocalWorkspaceIds: state.unavailableLocalWorkspaceIds,
    );
    return state;
  }

  @override
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  ) async => state.activeWorkspace;

  @override
  Future<WorkspaceProfilesState> loadState() async => state;

  @override
  Future<WorkspaceProfilesState> saveHostedAccessMode(
    String workspaceId,
    HostedWorkspaceAccessMode? accessMode,
  ) async => state;

  @override
  Future<WorkspaceProfilesState> saveLocalWorkspaceAvailability(
    String workspaceId, {
    required bool isAvailable,
  }) async => state;

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
    throw UnimplementedError();
  }
}
