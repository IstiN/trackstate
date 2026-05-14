import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/utils/color_contrast.dart';
import 'support/ts716_workspace_sync_accessibility_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-716 workspace sync accessibility exposes descriptive error semantics, readable contrast, and logical recovery order',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final repository = Ts716WorkspaceSyncAccessibilityRepository();

      try {
        await robot.pumpApp(
          repository: repository,
          sharedPreferences: const <String, Object>{
            Ts716WorkspaceSyncAccessibilityRepository.hostedTokenKey:
                Ts716WorkspaceSyncAccessibilityRepository.hostedTokenValue,
          },
        );

        await _pumpUntil(
          tester,
          condition: () =>
              _workspaceSyncPill.evaluate().isNotEmpty &&
              find
                  .text(
                    Ts716WorkspaceSyncAccessibilityRepository.topBarStatusLabel,
                    findRichText: true,
                  )
                  .evaluate()
                  .isNotEmpty &&
              find
                  .textContaining(
                    'This repository session is read-only',
                    findRichText: true,
                  )
                  .evaluate()
                  .isNotEmpty,
          timeout: const Duration(seconds: 5),
          failureMessage:
              'TS-716 could not reach the hosted read-only Attention needed state. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
              'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
        );

        final failures = <String>[];
        final topBarSemantics = robot.visibleSemanticsLabelsSnapshot();
        final topBarTexts = robot.visibleTexts();

        if (_workspaceSyncPill.evaluate().isEmpty) {
          failures.add(
            'Precondition failed: the top-bar workspace sync pill was not rendered in the hosted shell. '
            'Visible texts: ${_formatSnapshot(topBarTexts)}. '
            'Visible semantics: ${_formatSnapshot(topBarSemantics)}.',
          );
        } else {
          final semanticsLabel = tester
              .getSemantics(_workspaceSyncPill.first)
              .label;
          if (!_hasDescriptiveSyncErrorSemantics(semanticsLabel)) {
            failures.add(
              'Step 2 failed: the top-bar sync pill semantics label was "$semanticsLabel", '
              'which did not include both sync context and descriptive error-state wording '
              '(for example "Sync error, attention needed").',
            );
          }

          final pillBackground = robot.decoratedContainerBackgroundColor(
            _workspaceSyncPill,
          );
          if (pillBackground == null) {
            failures.add(
              'Step 3 failed: the top-bar sync pill did not expose a decorated error background, '
              'so contrast could not be measured.',
            );
          } else {
            final contrast = contrastRatio(
              robot.renderedTextColorWithin(
                _workspaceSyncPill,
                Ts716WorkspaceSyncAccessibilityRepository.topBarStatusLabel,
              ),
              pillBackground,
            );
            if (contrast < 4.5) {
              failures.add(
                'Step 3 failed: the visible "${Ts716WorkspaceSyncAccessibilityRepository.topBarStatusLabel}" '
                'label contrast was ${contrast.toStringAsFixed(2)}:1, below the WCAG AA 4.5:1 threshold.',
              );
            }
          }
        }

        await tester.tap(_workspaceSyncPill.first, warnIfMissed: false);
        await tester.pumpAndSettle();

        final workspaceSyncHeading = find.text(
          Ts716WorkspaceSyncAccessibilityRepository.workspaceSyncSectionLabel,
          findRichText: true,
        );
        if (workspaceSyncHeading.evaluate().isEmpty) {
          failures.add(
            'Human-style verification failed: tapping the top-bar sync pill did not open Settings with the Workspace sync card visible. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          _expectVisibleText(
            failures,
            text: Ts716WorkspaceSyncAccessibilityRepository
                .workspaceSyncSectionLabel,
            step: 'Human-style verification',
            context:
                'the Settings surface should show the Workspace sync heading after the user opens the sync pill',
          );
          _expectVisibleText(
            failures,
            text: Ts716WorkspaceSyncAccessibilityRepository.topBarStatusLabel,
            step: 'Step 4',
            context:
                'the Workspace sync card should keep the visible Attention needed state on screen',
          );
          _expectVisibleText(
            failures,
            text: Ts716WorkspaceSyncAccessibilityRepository.syncErrorMessage,
            step: 'Human-style verification',
            context:
                'the Workspace sync card should show the user-facing sync error message',
          );
          _expectVisibleText(
            failures,
            text: 'Latest error',
            step: 'Human-style verification',
            context:
                'the Workspace sync diagnostics should show the Latest error row',
          );
          _expectVisibleText(
            failures,
            text: Ts716WorkspaceSyncAccessibilityRepository.syncError,
            step: 'Human-style verification',
            context:
                'the Workspace sync diagnostics should surface the exact latest error text',
          );
        }

        final retryAction = _buttonByLabel(
          null,
          Ts716WorkspaceSyncAccessibilityRepository.retryLabel,
        );
        final reconnectAction = _buttonByLabel(
          null,
          Ts716WorkspaceSyncAccessibilityRepository.reconnectLabel,
        );

        if (retryAction.evaluate().isEmpty) {
          failures.add(
            'Step 4 failed: the Workspace sync card did not expose the visible '
            '"${Ts716WorkspaceSyncAccessibilityRepository.retryLabel}" recovery action. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
          );
        } else {
          await tester.ensureVisible(retryAction.first);
          await tester.pumpAndSettle();
        }

        if (reconnectAction.evaluate().isEmpty) {
          failures.add(
            'Step 4 failed: the Repository access settings area did not expose the visible '
            '"${Ts716WorkspaceSyncAccessibilityRepository.reconnectLabel}" recovery action requested by the ticket. '
            'Observed repository-access buttons: ${_formatSnapshot(robot.buttonLabelsWithin(robot.repositoryAccessSection))}. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          await tester.ensureVisible(reconnectAction.first);
          await tester.pumpAndSettle();
          await robot.clearFocus();
          final focusOrder = await robot.collectFocusOrder(
            candidates: <String, Finder>{
              Ts716WorkspaceSyncAccessibilityRepository.retryLabel: retryAction,
              Ts716WorkspaceSyncAccessibilityRepository.reconnectLabel:
                  reconnectAction,
            },
            tabs: 20,
          );

          final retryIndex = focusOrder.indexOf(
            Ts716WorkspaceSyncAccessibilityRepository.retryLabel,
          );
          final reconnectIndex = focusOrder.indexOf(
            Ts716WorkspaceSyncAccessibilityRepository.reconnectLabel,
          );

          if (retryIndex == -1) {
            failures.add(
              'Step 4 failed: keyboard Tab traversal never reached the visible '
              '"${Ts716WorkspaceSyncAccessibilityRepository.retryLabel}" action. '
              'Observed focus order: ${_formatSnapshot(focusOrder)}.',
            );
          }
          if (reconnectIndex == -1) {
            failures.add(
              'Step 4 failed: keyboard Tab traversal never reached the visible '
              '"${Ts716WorkspaceSyncAccessibilityRepository.reconnectLabel}" action. '
              'Observed focus order: ${_formatSnapshot(focusOrder)}.',
            );
          }
          if (retryIndex != -1 && reconnectIndex != -1) {
            final expectedFirstLabel =
                _compareVisualOrder(
                      tester.getRect(retryAction.first),
                      tester.getRect(reconnectAction.first),
                    ) <=
                    0
                ? Ts716WorkspaceSyncAccessibilityRepository.retryLabel
                : Ts716WorkspaceSyncAccessibilityRepository.reconnectLabel;
            final expectedSecondLabel =
                expectedFirstLabel ==
                    Ts716WorkspaceSyncAccessibilityRepository.retryLabel
                ? Ts716WorkspaceSyncAccessibilityRepository.reconnectLabel
                : Ts716WorkspaceSyncAccessibilityRepository.retryLabel;
            final actualFirstLabel = retryIndex < reconnectIndex
                ? Ts716WorkspaceSyncAccessibilityRepository.retryLabel
                : Ts716WorkspaceSyncAccessibilityRepository.reconnectLabel;
            final actualSecondLabel =
                actualFirstLabel ==
                    Ts716WorkspaceSyncAccessibilityRepository.retryLabel
                ? Ts716WorkspaceSyncAccessibilityRepository.reconnectLabel
                : Ts716WorkspaceSyncAccessibilityRepository.retryLabel;
            if (actualFirstLabel != expectedFirstLabel ||
                actualSecondLabel != expectedSecondLabel) {
              failures.add(
                'Step 4 failed: keyboard focus did not follow the visible top-to-bottom order of the recovery actions. '
                'Expected $expectedFirstLabel before $expectedSecondLabel based on their rendered positions, '
                'but observed ${focusOrder.join(' -> ')}.',
              );
            }
          }
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        semantics.dispose();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

final Finder _workspaceSyncPill = find.byKey(
  const ValueKey<String>('workspace-sync-pill'),
);

Finder _buttonByLabel(Finder? scope, String label) {
  final textMatch = find.ancestor(
    of: find.text(label, findRichText: true),
    matching: find.bySubtype<ButtonStyleButton>(),
  );
  final semanticsMatch = find.bySemanticsLabel(
    RegExp('^${RegExp.escape(label)}\$'),
  );
  final finder = textMatch.evaluate().isNotEmpty ? textMatch : semanticsMatch;
  if (scope == null) {
    return finder;
  }
  return find.descendant(of: scope, matching: finder);
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

int _compareVisualOrder(Rect left, Rect right) {
  final vertical = left.top.compareTo(right.top);
  if (vertical != 0) {
    return vertical;
  }
  return left.left.compareTo(right.left);
}

bool _hasDescriptiveSyncErrorSemantics(String label) {
  final normalizedLabel = label
      .toLowerCase()
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();
  if (normalizedLabel.isEmpty) {
    return false;
  }

  const syncTerms = <String>['sync', 'workspace sync', 'repository sync'];
  const errorTerms = <String>[
    'error',
    'failed',
    'failure',
    'attention needed',
    'attention',
    'warning',
    'problem',
  ];

  final hasSyncContext = syncTerms.any(normalizedLabel.contains);
  final hasErrorContext = errorTerms.any(normalizedLabel.contains);
  return hasSyncContext && hasErrorContext;
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
