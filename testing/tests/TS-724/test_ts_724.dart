import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/ts724_workspace_switch_validation_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-724 invalid workspace selection keeps the active local session alive',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final failures = <String>[];
      Ts724WorkspaceSwitchValidationFixture? fixture;
      Ts724WorkspaceSwitchValidationScreen? screen;

      try {
        fixture = await Ts724WorkspaceSwitchValidationFixture.create(tester);
        screen = await fixture.launch();
        await screen.waitForReady();
        final currentFixture = fixture!;

        if (currentFixture.deletedWorkspaceExists) {
          failures.add(
            'Precondition failed: Workspace-B still exists at ${currentFixture.deletedWorkspacePath} instead of representing a deleted local folder.',
          );
        }

        if (!screen.isBoardNavigationVisible) {
          failures.add(
            'Precondition failed: the Board section navigation control was not visible for Workspace-A. '
            'Visible texts: ${_formatSnapshot(screen.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          await screen.openBoardSection();
        }

        if (!screen.isBoardVisible) {
          failures.add(
            'Precondition failed: Workspace-A did not render the Board surface before attempting the invalid switch. '
            'Visible texts: ${_formatSnapshot(screen.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        if (!screen.isWorkspaceSwitcherTriggerVisible) {
          failures.add(
            'Step 1 failed: the workspace switcher trigger was not visible while Workspace-A was active.',
          );
        } else {
          _expectTrue(
            failures,
            condition: screen.triggerContainsText(
              Ts724WorkspaceSwitchValidationFixture.workspaceADisplayName,
            ),
            step: 'Precondition',
            context:
                'the workspace switcher trigger should summarize the current active workspace before the invalid switch',
          );
          await screen.openWorkspaceSwitcher();
        }

        if (!screen.isWorkspaceSwitcherVisible) {
          failures.add(
            'Step 1 failed: opening the workspace switcher did not show the Workspace switcher sheet. '
            'Visible texts: ${_formatSnapshot(screen.visibleTexts())}.',
          );
        }

        _expectTrue(
          failures,
          condition: screen.workspaceRowContainsText(
            currentFixture.workspaceA.id,
            'Active',
          ),
          step: 'Step 1',
          context:
              'Workspace-A should be marked Active before selecting the invalid workspace',
        );
        _expectTrue(
          failures,
          condition: screen.workspaceRowContainsTextContaining(
            currentFixture.workspaceB.id,
            Ts724WorkspaceSwitchValidationFixture.workspaceBDisplayName,
          ),
          step: 'Step 1',
          context:
              'Workspace-B should still be listed in the switcher even though its folder is missing',
        );

        final openRequestCountBeforeSwitch =
            currentFixture.localOpenRequests.length;

        if (!screen.canOpenWorkspace(currentFixture.workspaceB.id)) {
          failures.add(
            'Step 2 failed: the switcher did not expose an Open action for Workspace-B. '
            'Visible texts: ${_formatSnapshot(screen.visibleTexts())}.',
          );
        } else {
          await screen.attemptWorkspaceOpen(currentFixture.workspaceB.id);
          await screen.waitForFailedWorkspaceSwitch(
            Ts724WorkspaceSwitchValidationFixture.workspaceBDisplayName,
          );
        }

        if (!screen.isWorkspaceSwitchFailureVisible(
          Ts724WorkspaceSwitchValidationFixture.workspaceBDisplayName,
        )) {
          failures.add(
            'Step 3 failed: the UI did not show a non-blocking explanation after Workspace-B failed to open. '
            'Visible texts: ${_formatSnapshot(screen.visibleTexts())}.',
          );
        } else {
          _expectTrue(
            failures,
            condition: screen.isTextVisible(
              Ts724WorkspaceSwitchValidationFixture.missingWorkspaceReason,
            ),
            step: 'Step 3',
            context:
                'the failure message should explain that the deleted local folder could not be opened',
          );
        }

        final openRequestsAfterSwitch = currentFixture.localOpenRequests
            .skip(openRequestCountBeforeSwitch)
            .toList();
        if (!openRequestsAfterSwitch.contains(
          currentFixture.deletedWorkspacePath,
        )) {
          failures.add(
            'Step 2 failed: the app never attempted to validate Workspace-B at ${currentFixture.deletedWorkspacePath}. '
            'Observed open attempts: ${_formatSnapshot(currentFixture.localOpenRequests)}.',
          );
        }
        if (currentFixture.localOpenRequests.isEmpty ||
            currentFixture.localOpenRequests.first !=
                currentFixture.workspaceA.target) {
          failures.add(
            'Step 2 failed: the app did not start by opening Workspace-A before the invalid switch attempt. '
            'Expected the first local open request to target ${currentFixture.workspaceA.target}. '
            'Observed open attempts: ${_formatSnapshot(currentFixture.localOpenRequests)}.',
          );
        }
        if (openRequestsAfterSwitch.any(
          (path) => path == currentFixture.workspaceA.target,
        )) {
          failures.add(
            'Step 2 failed: Workspace-A was opened again after the failed Workspace-B switch attempt, which indicates the active runtime may have been torn down and recreated. '
            'Post-switch open attempts: ${_formatSnapshot(openRequestsAfterSwitch)}. '
            'Full open sequence: ${_formatSnapshot(currentFixture.localOpenRequests)}.',
          );
        }

        final workspaceStateAfterFailure = await currentFixture
            .loadWorkspaceState();
        if (workspaceStateAfterFailure.activeWorkspaceId !=
            currentFixture.workspaceA.id) {
          failures.add(
            'Step 4 failed: the saved active workspace changed to ${workspaceStateAfterFailure.activeWorkspaceId} after Workspace-B failed validation instead of remaining ${currentFixture.workspaceA.id}.',
          );
        }

        if (!screen.isBoardVisible) {
          failures.add(
            'Human-style verification failed: the Board content from Workspace-A disappeared after the invalid switch attempt, indicating the current session was torn down. '
            'Visible texts: ${_formatSnapshot(screen.visibleTexts())}.',
          );
        }

        _expectTrue(
          failures,
          condition: screen.triggerContainsText(
            Ts724WorkspaceSwitchValidationFixture.workspaceADisplayName,
          ),
          step: 'Step 4',
          context:
              'the workspace switcher trigger should still show Workspace-A after the failed switch',
        );

        if (screen.isWorkspaceSwitcherTriggerVisible) {
          await screen.openWorkspaceSwitcher();
        }

        _expectTrue(
          failures,
          condition: screen.workspaceRowContainsText(
            currentFixture.workspaceA.id,
            'Active',
          ),
          step: 'Human-style verification',
          context:
              're-opening the switcher should still mark Workspace-A as the active selection',
        );
        _expectTrue(
          failures,
          condition: screen.workspaceRowContainsText(
            currentFixture.workspaceB.id,
            'Unavailable',
          ),
          step: 'Human-style verification',
          context:
              'the invalid local workspace should be labeled Unavailable after validation fails',
        );
        if (screen.canOpenWorkspace(currentFixture.workspaceA.id)) {
          failures.add(
            'Human-style verification failed: Workspace-A still exposed an Open action after the invalid switch attempt instead of remaining the active row.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        screen?.dispose();
        await fixture?.dispose();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

void _expectTrue(
  List<String> failures, {
  required bool condition,
  required String step,
  required String context,
}) {
  if (!condition) {
    failures.add('$step failed: $context.');
  }
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}
