import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/screens/settings_screen_robot.dart';
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
      final robot = SettingsScreenRobot(tester);
      final failures = <String>[];
      Ts724WorkspaceSwitchValidationFixture? fixture;

      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;

        fixture = await Ts724WorkspaceSwitchValidationFixture.create(tester);
        await tester.pumpWidget(fixture.buildApp());
        await _pumpUntil(
          tester,
          condition: () =>
              find
                  .byKey(const ValueKey<String>('workspace-switcher-trigger'))
                  .evaluate()
                  .isNotEmpty &&
              find.bySemanticsLabel(RegExp('Board')).evaluate().isNotEmpty,
          timeout: const Duration(seconds: 10),
          failureMessage:
              'Precondition failed: Workspace-A did not finish rendering the workspace switcher trigger and Board navigation. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
              'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
        );

        if (fixture.deletedWorkspaceExists) {
          failures.add(
            'Precondition failed: Workspace-B still exists at ${fixture.deletedWorkspacePath} instead of representing a deleted local folder.',
          );
        }

        final boardTab = find.bySemanticsLabel(RegExp('Board'));
        if (boardTab.evaluate().isEmpty) {
          failures.add(
            'Precondition failed: the Board section navigation control was not visible for Workspace-A. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          await tester.tap(boardTab.first);
          await _pumpUntil(
            tester,
            condition: () => _boardColumn.evaluate().isNotEmpty,
            timeout: const Duration(seconds: 5),
            failureMessage:
                'Precondition failed: selecting Board did not reveal the board column for Workspace-A. '
                'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
                'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        if (_boardColumn.evaluate().isEmpty) {
          failures.add(
            'Precondition failed: Workspace-A did not render the Board surface before attempting the invalid switch. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final trigger = find.byKey(
          const ValueKey<String>('workspace-switcher-trigger'),
        );
        if (trigger.evaluate().isEmpty) {
          failures.add(
            'Step 1 failed: the workspace switcher trigger was not visible while Workspace-A was active.',
          );
        } else {
          _expectDescendantTextContaining(
            failures,
            scope: trigger,
            text: Ts724WorkspaceSwitchValidationFixture.workspaceADisplayName,
            step: 'Precondition',
            context:
                'the workspace switcher trigger should summarize the current active workspace before the invalid switch',
          );
          await tester.tap(trigger.first, warnIfMissed: false);
          await _pumpUntil(
            tester,
            condition: () =>
                find.text('Workspace switcher').evaluate().isNotEmpty,
            timeout: const Duration(seconds: 5),
            failureMessage:
                'Step 1 failed: opening the workspace switcher did not reveal the workspace switcher sheet. '
                'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
                'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        if (find.text('Workspace switcher').evaluate().isEmpty) {
          failures.add(
            'Step 1 failed: opening the workspace switcher did not show the Workspace switcher sheet. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
          );
        }

        _expectDescendantText(
          failures,
          scope: _workspaceRow(fixture.workspaceA.id),
          text: 'Active',
          step: 'Step 1',
          context:
              'Workspace-A should be marked Active before selecting the invalid workspace',
        );
        _expectDescendantText(
          failures,
          scope: _workspaceRow(fixture.workspaceB.id),
          text: Ts724WorkspaceSwitchValidationFixture.workspaceBDisplayName,
          step: 'Step 1',
          context:
              'Workspace-B should still be listed in the switcher even though its folder is missing',
        );

        final invalidWorkspaceOpenButton = _workspaceOpenButton(
          fixture.workspaceB.id,
        );
        if (invalidWorkspaceOpenButton.evaluate().isEmpty) {
          failures.add(
            'Step 2 failed: the switcher did not expose an Open action for Workspace-B. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
          );
        } else {
          await tester.tap(
            invalidWorkspaceOpenButton.first,
            warnIfMissed: false,
          );
          await _pumpUntil(
            tester,
            condition: () =>
                _workspaceSwitchFailureMessage(
                  Ts724WorkspaceSwitchValidationFixture.workspaceBDisplayName,
                ).evaluate().isNotEmpty &&
                _boardColumn.evaluate().isNotEmpty,
            timeout: const Duration(seconds: 5),
            failureMessage:
                'Step 2 failed: selecting Workspace-B did not surface the failure message and keep the current board visible. '
                'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
                'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final failureMessage = _workspaceSwitchFailureMessage(
          Ts724WorkspaceSwitchValidationFixture.workspaceBDisplayName,
        );
        if (failureMessage.evaluate().isEmpty) {
          failures.add(
            'Step 3 failed: the UI did not show a non-blocking explanation after Workspace-B failed to open. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
          );
        } else {
          _expectVisibleText(
            failures,
            text: Ts724WorkspaceSwitchValidationFixture.missingWorkspaceReason,
            step: 'Step 3',
            context:
                'the failure message should explain that the deleted local folder could not be opened',
          );
        }

        if (!fixture.localOpenRequests.contains(fixture.deletedWorkspacePath)) {
          failures.add(
            'Step 2 failed: the app never attempted to validate Workspace-B at ${fixture.deletedWorkspacePath}. '
            'Observed open attempts: ${_formatSnapshot(fixture.localOpenRequests)}.',
          );
        }

        final workspaceStateAfterFailure = await fixture.loadWorkspaceState();
        if (workspaceStateAfterFailure.activeWorkspaceId !=
            fixture.workspaceA.id) {
          failures.add(
            'Step 4 failed: the saved active workspace changed to ${workspaceStateAfterFailure.activeWorkspaceId} after Workspace-B failed validation instead of remaining ${fixture.workspaceA.id}.',
          );
        }

        if (_boardColumn.evaluate().isEmpty) {
          failures.add(
            'Human-style verification failed: the Board content from Workspace-A disappeared after the invalid switch attempt, indicating the current session was torn down. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
          );
        }

        _expectDescendantTextContaining(
          failures,
          scope: trigger,
          text: Ts724WorkspaceSwitchValidationFixture.workspaceADisplayName,
          step: 'Step 4',
          context:
              'the workspace switcher trigger should still show Workspace-A after the failed switch',
        );

        if (trigger.evaluate().isNotEmpty) {
          await tester.tap(trigger.first, warnIfMissed: false);
          await _pumpUntil(
            tester,
            condition: () =>
                find.text('Workspace switcher').evaluate().isNotEmpty,
            timeout: const Duration(seconds: 5),
            failureMessage:
                'Human-style verification failed: re-opening the workspace switcher did not show the saved workspace list again. '
                'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
                'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        _expectDescendantText(
          failures,
          scope: _workspaceRow(fixture.workspaceA.id),
          text: 'Active',
          step: 'Human-style verification',
          context:
              're-opening the switcher should still mark Workspace-A as the active selection',
        );
        _expectDescendantText(
          failures,
          scope: _workspaceRow(fixture.workspaceB.id),
          text: 'Unavailable',
          step: 'Human-style verification',
          context:
              'the invalid local workspace should be labeled Unavailable after validation fails',
        );
        if (_workspaceOpenButton(fixture.workspaceA.id).evaluate().isNotEmpty) {
          failures.add(
            'Human-style verification failed: Workspace-A still exposed an Open action after the invalid switch attempt instead of remaining the active row.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        await fixture?.dispose();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

final Finder _boardColumn = find.bySemanticsLabel(RegExp('To Do column'));

Finder _workspaceRow(String workspaceId) {
  return find.byKey(ValueKey<String>('workspace-$workspaceId'));
}

Finder _workspaceOpenButton(String workspaceId) {
  return find.byKey(ValueKey<String>('workspace-open-$workspaceId'));
}

Finder _workspaceSwitchFailureMessage(String workspaceName) {
  return find.textContaining('Could not open $workspaceName.');
}

void _expectVisibleText(
  List<String> failures, {
  required String text,
  required String step,
  required String context,
}) {
  if (find.textContaining(text, findRichText: true).evaluate().isEmpty) {
    failures.add('$step failed: $context.');
  }
}

void _expectDescendantText(
  List<String> failures, {
  required Finder scope,
  required String text,
  required String step,
  required String context,
}) {
  if (scope.evaluate().isEmpty) {
    failures.add('$step failed: $context (scope was not visible).');
    return;
  }
  final match = find.descendant(
    of: scope,
    matching: find.text(text, findRichText: true),
  );
  if (match.evaluate().isEmpty) {
    failures.add('$step failed: $context.');
  }
}

void _expectDescendantTextContaining(
  List<String> failures, {
  required Finder scope,
  required String text,
  required String step,
  required String context,
}) {
  if (scope.evaluate().isEmpty) {
    failures.add('$step failed: $context (scope was not visible).');
    return;
  }
  final match = find.descendant(
    of: scope,
    matching: find.textContaining(text, findRichText: true),
  );
  if (match.evaluate().isEmpty) {
    failures.add('$step failed: $context.');
  }
}

Future<void> _pumpUntil(
  WidgetTester tester, {
  required bool Function() condition,
  required Duration timeout,
  required String failureMessage,
  Duration step = const Duration(milliseconds: 100),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (condition()) {
      await tester.pump();
      return;
    }
    await tester.pump(step);
  }
  if (!condition()) {
    fail(failureMessage);
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
