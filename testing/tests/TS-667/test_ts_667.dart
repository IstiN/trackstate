import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

const String _workspaceOneName = 'ts667-workspace-one';
const String _workspaceTwoName = 'ts667-workspace-two';
const String _workspaceOneId = 'hosted:trackstate/ts667-one@main';
const String _workspaceTwoId = 'hosted:trackstate/ts667-two@main';
const String _dialogTitle = 'Delete saved workspace';
const String _dialogMessage =
    'Delete ts667-workspace-two and remove its stored credentials? This action cannot be undone.';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-667 prompts before deleting the active saved workspace from Settings',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final service = _DialogProbeWorkspaceProfileService(
        const WorkspaceProfilesState(
          profiles: <WorkspaceProfile>[
            WorkspaceProfile(
              id: _workspaceTwoId,
              displayName: _workspaceTwoName,
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'trackstate/ts667-two',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: _workspaceOneId,
              displayName: _workspaceOneName,
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'trackstate/ts667-one',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: _workspaceTwoId,
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
      expect(find.text(_workspaceOneName), findsOneWidget);
      expect(find.text(_workspaceTwoName), findsWidgets);
      expect(find.text('Active'), findsOneWidget);

      await tester.tap(find.widgetWithText(TextButton, 'Delete').first);
      await tester.pumpAndSettle();

      expect(find.text(_dialogTitle), findsOneWidget);
      expect(find.text(_dialogMessage), findsOneWidget);
      expect(find.widgetWithText(TextButton, 'Cancel'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Delete'), findsOneWidget);

      await tester.tap(find.widgetWithText(FilledButton, 'Delete'));
      await tester.pump();

      expect(service.deletedWorkspaceIds, <String>[_workspaceTwoId]);

      print(
        'TS-667-UI:${jsonEncode(<String, Object?>{
          'dialogTitle': _dialogTitle,
          'dialogMessage': _dialogMessage,
          'deletedWorkspaceId': service.deletedWorkspaceIds.single,
          'visibleTexts': _visibleTexts(tester),
          'activeLabelCount': find.text('Active').evaluate().length,
          'savedWorkspacesVisible': find.text('Saved workspaces').evaluate().isNotEmpty,
          'confirmationButtons': <String>['Cancel', 'Delete'],
          'humanVerification': 'Observed the visible confirmation dialog title, warning copy, and action buttons before confirming deletion of the active workspace.',
          'matchedExpectedResult': true,
        })}',
      );
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );

  test(
    'TS-667 deleting the active workspace clears scoped credentials and falls back to the remaining profile',
    () async {
      final authStore = const SharedPreferencesTrackStateAuthStore();
      final clock = _SequencedNow(<DateTime>[
        DateTime.utc(2026, 5, 13, 20, 0, 0),
        DateTime.utc(2026, 5, 13, 20, 5, 0),
        DateTime.utc(2026, 5, 13, 20, 10, 0),
      ]);
      final service = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
        now: clock.call,
      );

      final workspaceOne = await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'trackstate/ts667-one',
          defaultBranch: 'main',
        ),
      );
      final workspaceTwo = await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'trackstate/ts667-two',
          defaultBranch: 'main',
        ),
      );
      await authStore.saveToken('ts667-token', workspaceId: workspaceTwo.id);

      final stateBeforeDelete = await service.loadState();
      final prefsBeforeDelete = await SharedPreferences.getInstance();
      final workspaceTokenKeysBeforeDelete = prefsBeforeDelete.getKeys().where((
        key,
      ) {
        return key.startsWith('trackstate.githubToken.workspace.');
      }).toList()..sort();
      final nextState = await service.deleteProfile(workspaceTwo.id);
      final persistedState = await service.loadState();
      final prefsAfterDelete = await SharedPreferences.getInstance();
      final workspaceTokenKeysAfterDelete = prefsAfterDelete.getKeys().where((
        key,
      ) {
        return key.startsWith('trackstate.githubToken.workspace.');
      }).toList()..sort();
      final deletedToken = await authStore.readToken(
        workspaceId: workspaceTwo.id,
      );
      final fallbackToken = await authStore.readToken(
        workspaceId: workspaceOne.id,
      );

      expect(stateBeforeDelete.activeWorkspaceId, workspaceTwo.id);
      expect(
        stateBeforeDelete.activeWorkspace?.displayName,
        workspaceTwo.displayName,
      );
      expect(nextState.activeWorkspaceId, workspaceOne.id);
      expect(persistedState.activeWorkspaceId, workspaceOne.id);
      expect(
        nextState.profiles.map((profile) => profile.displayName).toList(),
        <String>[workspaceOne.displayName],
      );
      expect(deletedToken, isNull);
      expect(fallbackToken, isNull);
      expect(workspaceTokenKeysBeforeDelete, hasLength(1));
      expect(workspaceTokenKeysAfterDelete, isEmpty);

      print(
        'TS-667-SERVICE:${jsonEncode(<String, Object?>{'workspaceOneId': workspaceOne.id, 'workspaceOneDisplayName': workspaceOne.displayName, 'workspaceTwoId': workspaceTwo.id, 'workspaceTwoDisplayName': workspaceTwo.displayName, 'activeBeforeDelete': stateBeforeDelete.activeWorkspaceId, 'activeAfterDelete': persistedState.activeWorkspaceId, 'remainingWorkspaces': persistedState.profiles.map((profile) => profile.displayName).toList(), 'workspaceTokenKeysBeforeDelete': workspaceTokenKeysBeforeDelete, 'workspaceTokenKeysAfterDelete': workspaceTokenKeysAfterDelete, 'deletedWorkspaceTokenAfterDelete': deletedToken, 'fallbackWorkspaceToken': fallbackToken, 'humanVerification': 'Observed the production workspace profile service persist only the remaining workspace and the auth store stop returning a token for the deleted workspace id.', 'matchedExpectedResult': true})}',
      );
    },
  );
}

List<String> _visibleTexts(WidgetTester tester) {
  final texts = <String>[];
  for (final widget in tester.widgetList<Text>(find.byType(Text))) {
    final label = widget.data?.trim();
    if (label == null || label.isEmpty || texts.contains(label)) {
      continue;
    }
    texts.add(label);
  }
  return texts;
}

class _DialogProbeWorkspaceProfileService implements WorkspaceProfileService {
  _DialogProbeWorkspaceProfileService(this._state);

  WorkspaceProfilesState _state;
  final List<String> deletedWorkspaceIds = <String>[];
  final _pendingDeletion = Completer<WorkspaceProfilesState>();

  @override
  Future<WorkspaceProfile> createProfile(
    WorkspaceProfileInput input, {
    bool select = true,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) async {
    deletedWorkspaceIds.add(workspaceId);
    _state = WorkspaceProfilesState(
      profiles: _state.profiles
          .where((profile) => profile.id != workspaceId)
          .toList(growable: false),
      activeWorkspaceId: _workspaceOneId,
      migrationComplete: true,
    );
    return _pendingDeletion.future;
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

class _SequencedNow {
  _SequencedNow(this._values);

  final List<DateTime> _values;
  var _index = 0;

  DateTime call() {
    if (_index >= _values.length) {
      return _values.last;
    }
    final value = _values[_index];
    _index += 1;
    return value;
  }
}
