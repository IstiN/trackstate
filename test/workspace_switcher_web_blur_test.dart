import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'desktop web workspace switcher stays dismissible after keyboard navigation',
    (tester) async {
      if (!kIsWeb) {
        return;
      }

      final semantics = tester.ensureSemantics();
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
              id: 'hosted:beta/repo@main',
              displayName: 'beta/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'beta/repo',
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
      try {
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
        await _pumpUntilVisible(tester, find.byType(TextField));

        await tester.tap(
          find.byKey(const ValueKey('workspace-switcher-trigger')),
          warnIfMissed: false,
        );
        await tester.pumpAndSettle();

        await _pumpUntilVisible(
          tester,
          find.widgetWithText(TextFormField, 'Repository'),
        );

        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.pump();
        await tester.pumpAndSettle();

        expect(
          find.byKey(const ValueKey('workspace-hosted:alpha/repo@main')),
          findsOneWidget,
        );

        await tester.sendKeyEvent(LogicalKeyboardKey.escape);
        await tester.pump();
        await tester.pumpAndSettle();

        await _pumpUntilGone(tester, find.text('Saved workspaces'));
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'desktop web workspace open action switches workspaces and closes the panel',
    (tester) async {
      if (!kIsWeb) {
        return;
      }

      final semantics = tester.ensureSemantics();
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
              id: 'hosted:beta/repo@main',
              displayName: 'beta/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'beta/repo',
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
      try {
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
        await _pumpUntilVisible(tester, find.byType(TextField));

        await tester.tap(
          find.byKey(const ValueKey('workspace-switcher-trigger')),
          warnIfMissed: false,
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const ValueKey('workspace-switcher-sheet')),
          findsOneWidget,
        );

        await tester.tap(
          find.byKey(const ValueKey('workspace-open-hosted:beta/repo@main')),
          warnIfMissed: false,
        );
        await tester.pump();
        await tester.pumpAndSettle();

        expect(service.state.activeWorkspaceId, 'hosted:beta/repo@main');
        expect(
          find.byKey(const ValueKey('workspace-switcher-sheet')),
          findsNothing,
        );
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

Future<void> _pumpUntilVisible(
  WidgetTester tester,
  Finder finder, {
  int maxPumps = 60,
  Duration step = const Duration(milliseconds: 100),
}) async {
  for (var index = 0; index < maxPumps; index += 1) {
    await tester.pump(step);
    if (finder.evaluate().isNotEmpty) {
      return;
    }
  }
  throw TestFailure('Expected $finder to become visible.');
}

Future<void> _pumpUntilGone(
  WidgetTester tester,
  Finder finder, {
  int maxPumps = 60,
  Duration step = const Duration(milliseconds: 100),
}) async {
  for (var index = 0; index < maxPumps; index += 1) {
    await tester.pump(step);
    if (finder.evaluate().isEmpty) {
      return;
    }
  }
  throw TestFailure('Expected $finder to disappear.');
}
