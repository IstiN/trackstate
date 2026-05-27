@TestOn('browser')
library;

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
    'desktop web pristine workspace switcher exports an Active marker for the selected saved workspace row',
    (tester) async {
      const primaryWorkspace = WorkspaceProfile(
        id: 'hosted:primary/repo@main',
        displayName: 'Hosted main workspace',
        targetType: WorkspaceProfileTargetType.hosted,
        target: 'primary/repo',
        defaultBranch: 'main',
        writeBranch: 'main',
      );
      const alternateWorkspace = WorkspaceProfile(
        id: 'hosted:alternate/repo@main',
        displayName: 'Hosted alt workspace',
        targetType: WorkspaceProfileTargetType.hosted,
        target: 'alternate/repo',
        defaultBranch: 'main',
        writeBranch: 'ts-954-alt',
      );
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [primaryWorkspace, alternateWorkspace],
          activeWorkspaceId: primaryWorkspace.id,
          migrationComplete: true,
        ),
      );

      tester.view.physicalSize = const Size(1440, 900);
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

      final trigger = find.byKey(const ValueKey('workspace-switcher-trigger'));
      final triggerButton = tester.widget<FilledButton>(
        find.descendant(of: trigger, matching: find.byType(FilledButton)).first,
      );
      triggerButton.onPressed!();
      await tester.pumpAndSettle();

      expect(find.byKey(const ValueKey('workspace-switcher-sheet')), findsOneWidget);
      expect(
        find.descendant(
          of: find.byKey(ValueKey('workspace-${primaryWorkspace.id}')),
          matching: find.byWidgetPredicate(
            (widget) =>
                widget is Opacity &&
                widget.opacity == 0 &&
                widget.alwaysIncludeSemantics,
            description:
                'web-only hidden semantics export for the active workspace row',
          ),
        ),
        findsAtLeastNWidgets(1),
      );
      expect(
        find.descendant(
          of: find.byKey(ValueKey('workspace-${primaryWorkspace.id}')),
          matching: find.text('Active'),
        ),
        findsNWidgets(2),
        reason:
            'The selected saved workspace row needs both the visible Active chip '
            'and a web-exported hidden Active semantics marker so browser '
            'automation can still identify the selected row in pristine state.',
      );
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
