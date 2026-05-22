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
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'desktop web workspace switcher exposes unavailable saved local rows for manual retry',
    (tester) async {
      if (!kIsWeb) {
        return;
      }
      final semantics = tester.ensureSemantics();
      try {
        const hostedWorkspaceId = 'hosted:stable/repo@main';
        const localWorkspaceId = 'local:/tmp/demo@main';
        final service = _MemoryWorkspaceProfileService(
          const WorkspaceProfilesState(
            profiles: [
              WorkspaceProfile(
                id: hostedWorkspaceId,
                displayName: 'stable/repo',
                targetType: WorkspaceProfileTargetType.hosted,
                target: 'stable/repo',
                defaultBranch: 'main',
                writeBranch: 'main',
              ),
              WorkspaceProfile(
                id: localWorkspaceId,
                displayName: 'demo',
                targetType: WorkspaceProfileTargetType.local,
                target: '/tmp/demo',
                defaultBranch: 'main',
                writeBranch: 'main',
              ),
            ],
            activeWorkspaceId: hostedWorkspaceId,
            migrationComplete: true,
            unavailableLocalWorkspaceIds: {localWorkspaceId},
          ),
        );

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
            openLocalRepository:
                ({
                  required String repositoryPath,
                  required String defaultBranch,
                  required String writeBranch,
                }) async => throw StateError('Missing repository $repositoryPath'),
          ),
        );
        await _pumpUntilVisible(tester, find.byType(TextField));

        final trigger = find.byKey(const ValueKey('workspace-switcher-trigger'));
        expect(trigger, findsOneWidget);
        final triggerButton = tester.widget<FilledButton>(
          find.descendant(of: trigger, matching: find.byType(FilledButton)).first,
        );
        expect(triggerButton.onPressed, isNotNull);
        triggerButton.onPressed!();
        await tester.pump();
        await tester.pumpAndSettle();

        expect(
          find.descendant(
            of: find.byKey(const ValueKey('workspace-$localWorkspaceId')),
            matching: find.byWidgetPredicate(
              (widget) =>
                  widget is Semantics &&
                  widget.properties.label ==
                      'demo, Local, Unavailable, /tmp/demo • Branch: main',
              description: 'unavailable local workspace summary semantics',
            ),
          ),
          findsOneWidget,
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
  expect(finder, findsWidgets);
}
