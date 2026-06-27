import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../fixtures/settings/local_git_settings_screen_context.dart';
import '../TS-483/support/ts483_attachments_settings_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-607 attachments focus cycle stays inside the local workflow until the action buttons',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = createLocalGitSettingsScreenRobot(tester);
      Ts483AttachmentsSettingsFixture? fixture;
      final failures = <String>[];

      const releasePrefixValue = 'release-assets-';
      const expectedLocalFocusOrder = <String>[
        'Attachment storage mode',
        'Release tag prefix',
        'Reset',
        'Save settings',
      ];

      try {
        fixture = await tester.runAsync(Ts483AttachmentsSettingsFixture.create);
        if (fixture == null) {
          throw StateError('TS-607 fixture creation did not complete.');
        }

        await robot.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        await robot.openSettings();
        await robot.selectTab('Attachments');

        final attachmentsTexts = robot.visibleTexts();
        for (final requiredText in const <String>[
          'Project Settings',
          'Attachments',
          'Attachment storage mode',
          'Reset',
          'Save settings',
        ]) {
          if (!_containsSnapshot(attachmentsTexts, requiredText)) {
            failures.add(
              'Step 1 failed: navigating to Project Settings -> Attachments did not keep the visible "$requiredText" text on screen. '
              'Visible text: ${_formatSnapshot(attachmentsTexts)}.',
            );
          }
        }

        await robot.selectAttachmentStorageMode('GitHub Releases');
        await robot.enterAttachmentReleaseTagPrefix(releasePrefixValue);

        if (!await robot.showsAttachmentReleaseTagPrefixField()) {
          failures.add(
            'Step 2 failed: enabling "GitHub Releases" did not render the visible "Release tag prefix" field.',
          );
        }

        final githubReleasesTexts = robot.visibleTexts();
        for (final requiredText in const <String>[
          'GitHub Releases',
          'Release tag prefix',
          'Reset',
          'Save settings',
        ]) {
          if (!_containsSnapshot(githubReleasesTexts, requiredText)) {
            failures.add(
              'Step 2 failed: the GitHub Releases Attachments workflow did not keep the visible "$requiredText" text on screen. '
              'Visible text: ${_formatSnapshot(githubReleasesTexts)}.',
            );
          }
        }

        final localCandidates = <String, Finder>{
          'Attachment storage mode': find.bySemanticsLabel(
            RegExp('Attachment storage mode'),
          ),
          'Release tag prefix': find.bySemanticsLabel(
            RegExp('Release tag prefix'),
          ),
          'Reset': robot.resetSettingsButton,
          'Save settings': robot.saveSettingsButton,
        };
        final globalCandidates = <String, Finder>{
          'Create issue': find.bySemanticsLabel(RegExp(r'^Create issue$')),
          'Search issues': find.bySemanticsLabel(RegExp('Search issues')),
          'Settings': find.bySemanticsLabel(RegExp(r'^Settings$')),
          'Local Git': robot.localGitTopBarControl,
          'Dark theme': robot.darkThemeControl,
        };

        await robot.clearFocus();
        final reachedStorageSelector = await _focusByTab(
          tester,
          robot: robot,
          label: 'Attachment storage mode',
          finder: localCandidates['Attachment storage mode']!,
          maxTabs: 24,
        );
        if (!reachedStorageSelector) {
          failures.add(
            'Step 3 failed: keyboard Tab traversal did not reach the Attachment storage mode selector to start the Attachments workflow cycle. '
            'Focused semantics: ${_formatSnapshot(_focusedSemanticsLabels(tester))}.',
          );
        } else {
          final focusTrace = await _collectFocusTraceFromCurrent(
            tester,
            robot: robot,
            candidates: <String, Finder>{
              ...localCandidates,
              ...globalCandidates,
            },
            tabSteps: 4,
          );
          final observedLocalFocusOrder = <String>[
            for (final step in focusTrace.take(expectedLocalFocusOrder.length))
              step.candidateLabel,
          ];
          final localFocusFailure = _exactFocusOrderFailure(
            observedLocalFocusOrder,
            expectedOrder: expectedLocalFocusOrder,
          );
          if (localFocusFailure != null) {
            failures.add(
              'Step 4 failed: keyboard Tab traversal did not preserve the Attachments workflow order [Attachment storage mode, Release tag prefix, Reset, Save settings]. '
              '$localFocusFailure Observed focus cycle: ${_formatFocusTrace(focusTrace)}.',
            );
          }

          final nextFocus = focusTrace.last;
          if (localCandidates.containsKey(nextFocus.candidateLabel)) {
            failures.add(
              'Step 4 failed: focus stayed inside the local Attachments workflow after "Save settings" and landed on "${nextFocus.candidateLabel}" instead of leaving for a global navigation control. '
              'Observed focus cycle: ${_formatFocusTrace(focusTrace)}.',
            );
          } else if (!globalCandidates.containsKey(nextFocus.candidateLabel)) {
            failures.add(
              'Step 4 failed: focus left "Save settings" but did not land on a recognized global navigation control. '
              'Observed focus cycle: ${_formatFocusTrace(focusTrace)}.',
            );
          } else {
            final globalFinder = globalCandidates[nextFocus.candidateLabel]!;
            if (globalFinder.evaluate().isEmpty) {
              failures.add(
                'Step 4 failed: the next focused global navigation control "${nextFocus.candidateLabel}" was not visible on screen. '
                'Observed focus cycle: ${_formatFocusTrace(focusTrace)}.',
              );
            } else if (find
                .descendant(
                  of: robot.settingsAdminSection,
                  matching: globalFinder,
                )
                .evaluate()
                .isNotEmpty) {
              failures.add(
                'Human-style verification failed: after leaving "Save settings", focus remained inside the Project Settings Attachments workspace instead of moving to the visible global navigation control "${nextFocus.candidateLabel}". '
                'Observed focus cycle: ${_formatFocusTrace(focusTrace)}.',
              );
            }
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

bool _containsSnapshot(List<String> values, String expected) {
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed == expected ||
        trimmed.startsWith(expected) ||
        trimmed.contains(expected)) {
      return true;
    }
  }
  return false;
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
