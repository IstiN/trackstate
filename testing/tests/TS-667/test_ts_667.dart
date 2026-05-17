import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../fixtures/saved_workspace_settings_screen_fixture.dart';
import '../../fixtures/workspace_profile_deletion_probe_fixture.dart';
import 'support/ts667_probe_workspace_profile_service.dart';

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
      final workspaceProfileService = Ts667ProbeWorkspaceProfileService(
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
      final screen = await launchSavedWorkspaceSettingsFixture(
        tester,
        repository: const DemoTrackStateRepository(),
        workspaceProfileService: workspaceProfileService,
        openHostedRepository:
            ({
              required String repository,
              required String defaultBranch,
              required String writeBranch,
            }) async => const DemoTrackStateRepository(),
      );

      try {
        await screen.open();

        final initialState = screen.captureState();
        expect(initialState.isSavedWorkspacesVisible, isTrue);
        expect(
          initialState.workspaceLabels,
          containsAll(<String>[_workspaceOneName, _workspaceTwoName]),
        );
        expect(initialState.selectedWorkspaceLabels, <String>[
          _workspaceTwoName,
        ]);
        expect(initialState.activeLabelCount, 1);

        await screen.requestWorkspaceDeletion(_workspaceTwoName);

        final dialogState = screen.captureState();
        expect(dialogState.dialogTexts, contains(_dialogTitle));
        expect(dialogState.dialogTexts, contains(_dialogMessage));
        expect(
          dialogState.dialogTexts,
          containsAll(<String>['Cancel', 'Delete']),
        );

        await screen.confirmDeletion();

        final postDeleteState = screen.captureState();
        expect(workspaceProfileService.deletedWorkspaceIds, <String>[
          _workspaceTwoId,
        ]);
        expect(postDeleteState.workspaceLabels, <String>[_workspaceOneName]);
        expect(postDeleteState.selectedWorkspaceLabels, <String>[
          _workspaceOneName,
        ]);
        expect(postDeleteState.activeLabelCount, 1);

        print(
          'TS-667-UI:${jsonEncode(<String, Object?>{
            'dialogTitle': _dialogTitle,
            'dialogMessage': _dialogMessage,
            'deletedWorkspaceId': workspaceProfileService.deletedWorkspaceIds.single,
            'remainingWorkspaceNames': postDeleteState.workspaceLabels,
            'selectedWorkspaceNames': postDeleteState.selectedWorkspaceLabels,
            'visibleTexts': postDeleteState.visibleTexts,
            'activeLabelCount': postDeleteState.activeLabelCount,
            'confirmationButtons': <String>['Cancel', 'Delete'],
            'humanVerification': 'Observed the confirmation dialog and, after confirming deletion, the visible saved-workspaces section updated to leave ts667-workspace-one as the only active workspace.',
            'matchedExpectedResult': true,
          })}',
        );
      } finally {
        screen.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );

  test(
    'TS-667 deleting the active workspace clears scoped credentials and falls back to the remaining profile',
    () async {
      final clock = _SequencedNow(<DateTime>[
        DateTime.utc(2026, 5, 13, 20, 0, 0),
        DateTime.utc(2026, 5, 13, 20, 5, 0),
        DateTime.utc(2026, 5, 13, 20, 10, 0),
      ]);
      final deletionProbe =
          createSharedPreferencesWorkspaceProfileDeletionProbe(now: clock.call);

      final observation = await deletionProbe.inspectActiveWorkspaceDeletion(
        remainingProfileInput: const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'trackstate/ts667-one',
          defaultBranch: 'main',
        ),
        deletedActiveProfileInput: const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'trackstate/ts667-two',
          defaultBranch: 'main',
        ),
        deletedActiveProfileToken: 'ts667-token',
      );

      expect(observation.activeBeforeDelete, observation.deletedWorkspaceId);
      expect(observation.activeAfterDelete, observation.remainingWorkspaceId);
      expect(observation.remainingWorkspaces, <String>[
        observation.remainingWorkspaceDisplayName,
      ]);
      expect(observation.deletedWorkspaceTokenAfterDelete, isNull);
      expect(observation.fallbackWorkspaceToken, isNull);
      expect(observation.workspaceTokenKeysBeforeDelete, hasLength(1));
      expect(observation.workspaceTokenKeysAfterDelete, isEmpty);

      print(
        'TS-667-SERVICE:${jsonEncode(<String, Object?>{'workspaceOneId': observation.remainingWorkspaceId, 'workspaceOneDisplayName': observation.remainingWorkspaceDisplayName, 'workspaceTwoId': observation.deletedWorkspaceId, 'workspaceTwoDisplayName': observation.deletedWorkspaceDisplayName, 'activeBeforeDelete': observation.activeBeforeDelete, 'activeAfterDelete': observation.activeAfterDelete, 'remainingWorkspaces': observation.remainingWorkspaces, 'workspaceTokenKeysBeforeDelete': observation.workspaceTokenKeysBeforeDelete, 'workspaceTokenKeysAfterDelete': observation.workspaceTokenKeysAfterDelete, 'deletedWorkspaceTokenAfterDelete': observation.deletedWorkspaceTokenAfterDelete, 'fallbackWorkspaceToken': observation.fallbackWorkspaceToken, 'humanVerification': 'Observed the production workspace profile service persist only the remaining workspace and the auth store stop returning a token for the deleted workspace id.', 'matchedExpectedResult': true})}',
      );
    },
  );
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
