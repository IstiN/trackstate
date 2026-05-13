import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../fixtures/settings/local_git_settings_screen_context.dart';
import '../TS-483/support/ts483_attachments_settings_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-606 tabbing after Release tag prefix reaches Reset then Save settings',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = createLocalGitSettingsScreenRobot(tester);
      Ts483AttachmentsSettingsFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts483AttachmentsSettingsFixture.create);
        if (fixture == null) {
          throw StateError('TS-606 fixture creation did not complete.');
        }

        final failures = <String>[];

        await robot.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        await robot.openSettings();
        await robot.selectTab('Attachments');
        await robot.selectAttachmentStorageMode('GitHub Releases');

        if (!await robot.showsAttachmentReleaseTagPrefixField()) {
          failures.add(
            'Step 3 failed: switching Attachment storage mode to "GitHub Releases" did not render the visible "Release tag prefix" field.',
          );
        }

        final visibleTexts = robot.visibleTexts();
        for (final requiredText in const <String>[
          'Attachments',
          'Attachment storage mode',
          'GitHub Releases',
          'Release tag prefix',
          'Reset',
          'Save settings',
        ]) {
          if (!visibleTexts.contains(requiredText)) {
            failures.add(
              'Human-style verification failed: Settings > Attachments did not keep the visible "$requiredText" text on screen. '
              'Visible texts: ${_formatSnapshot(visibleTexts)}.',
            );
          }
        }

        final focusCandidates = <String, Finder>{
          'Release tag prefix': find.bySemanticsLabel(RegExp('Release tag prefix')),
          'Reset': robot.resetSettingsButton,
          'Save settings': robot.saveSettingsButton,
          'Create issue': find.bySemanticsLabel(RegExp('Create issue')),
          'Settings': find.bySemanticsLabel(RegExp('Settings')),
        };

        await robot.clearFocus();
        final focusedReleaseTagPrefix = await _focusByTab(
          tester,
          robot: robot,
          label: 'Release tag prefix',
          finder: focusCandidates['Release tag prefix']!,
          maxTabs: 24,
        );
        if (!focusedReleaseTagPrefix) {
          failures.add(
            'Step 4 failed: keyboard Tab navigation did not move focus into the visible "Release tag prefix" field. '
            'Focused semantics snapshot: ${_formatSnapshot(_focusedSemanticsLabels(tester))}.',
          );
        } else {
          final focusTrace = await _collectFocusTraceFromCurrent(
            tester,
            robot: robot,
            candidates: focusCandidates,
            tabSteps: 2,
          );
          final focusOrder = <String>[
            for (final step in focusTrace) step.candidateLabel,
          ];
          final focusOrderFailure = _exactFocusOrderFailure(
            focusOrder,
            expectedOrder: const <String>[
              'Release tag prefix',
              'Reset',
              'Save settings',
            ],
          );
          if (focusOrderFailure != null) {
            failures.add(
              'Expected result failed: keyboard Tab traversal after "Release tag prefix" did not move to "Reset" and then "Save settings". '
              '$focusOrderFailure Observed focus cycle: ${_formatFocusTrace(focusTrace)}.',
            );
          }
          if (focusOrder.contains('Create issue') || focusOrder.contains('Settings')) {
            failures.add(
              'Expected result failed: focus leaked from the Attachments workflow into global navigation instead of staying on the local action buttons. '
              'Observed focus cycle: ${_formatFocusTrace(focusTrace)}.',
            );
          }
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Future<bool> _focusByTab(
  WidgetTester tester, {
  required SettingsScreenRobot robot,
  required String label,
  required Finder finder,
  int maxTabs = 16,
}) async {
  for (var index = 0; index < maxTabs; index += 1) {
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    if (robot.focusedLabel(<String, Finder>{label: finder}) == label) {
      return true;
    }
  }
  return false;
}

Future<List<({String candidateLabel, List<String> focusedSemanticsLabels})>>
_collectFocusTraceFromCurrent(
  WidgetTester tester, {
  required SettingsScreenRobot robot,
  required Map<String, Finder> candidates,
  required int tabSteps,
}) async {
  final order =
      <({String candidateLabel, List<String> focusedSemanticsLabels})>[
        (
          candidateLabel:
              robot.focusedLabel(candidates) ?? '<outside candidates>',
          focusedSemanticsLabels: _focusedSemanticsLabels(tester),
        ),
      ];
  for (var index = 0; index < tabSteps; index += 1) {
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    order.add((
      candidateLabel: robot.focusedLabel(candidates) ?? '<outside candidates>',
      focusedSemanticsLabels: _focusedSemanticsLabels(tester),
    ));
  }
  return order;
}

String? _exactFocusOrderFailure(
  List<String> observed, {
  required List<String> expectedOrder,
}) {
  if (observed.length != expectedOrder.length) {
    return 'the captured cycle had ${observed.length} focus stops instead of ${expectedOrder.length}.';
  }

  for (var index = 0; index < expectedOrder.length; index += 1) {
    if (observed[index] == expectedOrder[index]) {
      continue;
    }
    return 'focus stop ${index + 1} was "${observed[index]}" instead of "${expectedOrder[index]}".';
  }

  return null;
}

List<String> _focusedSemanticsLabels(WidgetTester tester) {
  final root = tester.binding.pipelineOwner.semanticsOwner?.rootSemanticsNode;
  if (root == null) {
    return const <String>['<no semantics tree>'];
  }

  final labels = <String>[];
  void visit(SemanticsNode node) {
    final data = node.getSemanticsData();
    if (data.flagsCollection.isFocused) {
      final label = data.label.trim();
      labels.add(label.isEmpty ? '<empty label>' : label);
    }
    for (final child in node.debugListChildrenInOrder(
      DebugSemanticsDumpOrder.traversalOrder,
    )) {
      visit(child);
    }
  }

  visit(root);
  return labels.isEmpty ? const <String>['<no focused semantics>'] : labels;
}

String _formatFocusTrace(
  List<({String candidateLabel, List<String> focusedSemanticsLabels})> trace,
) {
  return trace
      .map(
        (step) =>
            '${step.candidateLabel} [${step.focusedSemanticsLabels.join(' | ')}]',
      )
      .join(' -> ');
}

String _formatSnapshot(List<String> values, {int limit = 16}) {
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
