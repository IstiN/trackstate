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

  testWidgets('settings shows saved workspaces and confirms deletion', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
    final service = _FakeWorkspaceProfileService(
      WorkspaceProfilesState(
        profiles: const [
          WorkspaceProfile(
            id: 'hosted:trackstate/trackstate@main',
            displayName: 'trackstate/trackstate',
            targetType: WorkspaceProfileTargetType.hosted,
            target: 'trackstate/trackstate',
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
        activeWorkspaceId: 'hosted:trackstate/trackstate@main',
        migrationComplete: true,
      ),
    );

    await tester.pumpWidget(
      TrackStateApp(
        repository: const DemoTrackStateRepository(),
        workspaceProfileService: service,
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Settings').first);
    await tester.pumpAndSettle();

    expect(find.text('Saved workspaces'), findsOneWidget);
    expect(find.text('Hosted'), findsOneWidget);
    expect(find.text('Local'), findsOneWidget);
    expect(find.text('trackstate/trackstate'), findsWidgets);
    expect(find.text('demo'), findsOneWidget);
    expect(find.text('Active'), findsOneWidget);

    await tester.tap(find.widgetWithText(TextButton, 'Delete').last);
    await tester.pumpAndSettle();

    expect(find.text('Delete saved workspace'), findsOneWidget);
    expect(
      find.textContaining('Delete demo and remove its stored credentials?'),
      findsOneWidget,
    );
  });
}

class _FakeWorkspaceProfileService implements WorkspaceProfileService {
  _FakeWorkspaceProfileService(this._state);

  WorkspaceProfilesState _state;

  @override
  Future<WorkspaceProfile> createProfile(
    WorkspaceProfileInput input, {
    bool select = true,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) async {
    _state = WorkspaceProfilesState(
      profiles: _state.profiles
          .where((profile) => profile.id != workspaceId)
          .toList(growable: false),
      activeWorkspaceId: _state.activeWorkspaceId == workspaceId
          ? null
          : _state.activeWorkspaceId,
      migrationComplete: _state.migrationComplete,
    );
    return _state;
  }

  @override
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  ) async => _state.activeWorkspace;

  @override
  Future<WorkspaceProfilesState> loadState() async => _state;

  @override
  Future<WorkspaceProfilesState> selectProfile(String workspaceId) async {
    _state = _state.copyWith(activeWorkspaceId: workspaceId);
    return _state;
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
