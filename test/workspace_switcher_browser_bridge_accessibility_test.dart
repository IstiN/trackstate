import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../testing/core/utils/color_contrast.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'workspace switcher sheet controls expose stable semantics identifiers for browser focus bridging',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        const WorkspaceProfilesState(
          profiles: [
            WorkspaceProfile(
              id: 'hosted:alpha/repo@main',
              displayName: 'alpha/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alpha/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:beta/repo@main',
              displayName: 'beta/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'beta/repo',
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
          unavailableLocalWorkspaceIds: {'local:/tmp/demo@main'},
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
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async =>
                  throw StateError('Missing repository $repositoryPath'),
        ),
      );
      await tester.pumpAndSettle();

      final trigger = tester.widget<FilledButton>(
        find.descendant(
          of: find.byKey(const ValueKey('workspace-switcher-trigger')),
          matching: find.byType(FilledButton),
        ),
      );
      trigger.onPressed!.call();
      await tester.pumpAndSettle();

      final hostedToggleSemantics = tester
          .widgetList<Semantics>(
            find.byWidgetPredicate(
              (widget) =>
                  widget is Semantics && widget.properties.label == 'Hosted',
              description:
                  'hosted add-workspace toggle semantics with stable identifier',
            ),
          )
          .map((widget) => widget.properties.identifier)
          .toList();
      expect(
        hostedToggleSemantics,
        contains('trackstate-workspace-switcher-target-type-hosted'),
      );

      final localToggleSemantics = tester
          .widgetList<Semantics>(
            find.byWidgetPredicate(
              (widget) =>
                  widget is Semantics && widget.properties.label == 'Local',
              description:
                  'local add-workspace toggle semantics with stable identifier',
            ),
          )
          .map((widget) => widget.properties.identifier)
          .toList();
      expect(
        localToggleSemantics,
        contains('trackstate-workspace-switcher-target-type-local'),
      );

      final deleteSemantics = tester
          .widgetList<Semantics>(
            find.byWidgetPredicate(
              (widget) =>
                  widget is Semantics &&
                  widget.properties.label == 'Delete: beta/repo',
              description:
                  'delete workspace semantics matching the browser focus target',
            ),
          )
          .map((widget) => widget.properties.identifier)
          .toList();
      expect(
        deleteSemantics,
        contains('trackstate-workspace-switcher-delete-hosted:beta/repo@main'),
      );

      final saveSemantics = tester
          .widgetList<Semantics>(
            find.byWidgetPredicate(
              (widget) =>
                  widget is Semantics &&
                  widget.properties.label == 'Save and switch',
              description:
                  'save and switch semantics matching the browser focus target',
            ),
          )
          .map((widget) => widget.properties.identifier)
          .toList();
      expect(saveSemantics, contains('trackstate-workspace-switcher-save'));
    },
  );

  testWidgets(
    'workspace switcher disabled Save and switch keeps accessible text contrast',
    (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        const TrackStateApp(repository: DemoTrackStateRepository()),
      );
      await tester.pumpAndSettle();

      final trigger = tester.widget<FilledButton>(
        find.descendant(
          of: find.byKey(const ValueKey('workspace-switcher-trigger')),
          matching: find.byType(FilledButton),
        ),
      );
      trigger.onPressed!.call();
      await tester.pumpAndSettle();

      final saveButtonFinder = find.byKey(
        const ValueKey('workspace-add-button'),
      );
      final saveButtonTextFinder = find.descendant(
        of: saveButtonFinder,
        matching: find.text('Save and switch'),
      );
      final colors = Theme.of(
        tester.element(saveButtonFinder),
      ).extension<TrackStateColors>()!;
      final foreground = DefaultTextStyle.of(
        tester.element(saveButtonTextFinder),
      ).style.color!;
      final buttonMaterial = tester
          .widgetList<Material>(
            find.ancestor(
              of: saveButtonTextFinder,
              matching: find.byType(Material),
            ),
          )
          .firstWhere((material) => material.color != null);
      final renderedBackground = Color.alphaBlend(
        buttonMaterial.color!,
        colors.surface,
      );

      expect(
        contrastRatio(foreground, renderedBackground),
        greaterThanOrEqualTo(4.5),
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
  }) {
    throw UnimplementedError();
  }

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) {
    throw UnimplementedError();
  }

  @override
  Future<WorkspaceProfilesState> clearActiveWorkspaceSelection() async {
    state = state.copyWith(activeWorkspaceId: null);
    return state;
  }

  @override
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  ) async => null;

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
  }) {
    throw UnimplementedError();
  }
}
