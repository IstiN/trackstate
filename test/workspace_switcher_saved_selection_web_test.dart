import 'package:flutter/foundation.dart';
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

  testWidgets(
    'desktop web workspace switcher enables Save and switch after selecting another row',
    (tester) async {
      if (!kIsWeb) {
        return;
      }

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
      final semantics = tester.ensureSemantics();
      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;

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

        final trigger = find.byKey(const ValueKey('workspace-switcher-trigger'));
        expect(trigger, findsOneWidget);
        final triggerButton = tester.widget<FilledButton>(
          find.descendant(of: trigger, matching: find.byType(FilledButton)).first,
        );
        expect(triggerButton.onPressed, isNotNull);
        triggerButton.onPressed!();
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
          find.byKey(ValueKey('workspace-${alternateWorkspace.id}')),
          warnIfMissed: false,
        );
        await tester.pumpAndSettle();

        final saveButtonAfterSelection = tester.widget<FilledButton>(
          find.byKey(const ValueKey('workspace-add-button')),
        );
        expect(saveButtonAfterSelection.onPressed, isNotNull);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
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
