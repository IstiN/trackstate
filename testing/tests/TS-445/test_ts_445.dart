import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/utils/color_contrast.dart';
import 'support/ts445_settings_recovery_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-445 settings recovery callout exposes recovery actions and amber warning styling',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      Ts445SettingsRecoveryRepository? repository;

      try {
        repository = await tester.runAsync(Ts445SettingsRecoveryRepository.create);
        if (repository == null) {
          throw StateError('TS-445 repository fixture creation did not complete.');
        }

        await robot.pumpApp(repository: repository);
        await robot.openSettings();

        final failures = <String>[];
        const expectedTitle = 'GitHub startup limit reached';
        const expectedMessage =
            'Hosted startup loaded the minimum app-shell data, but GitHub rate-limited a deferred repository read. Retry later or connect GitHub for a higher limit to resume full hosted reads.';
        const expectedActions = <String>['Retry startup', 'Connect GitHub'];
        final visibleTexts = _formatSnapshot(robot.visibleTexts());
        final visibleSemantics = _formatSnapshot(
          robot.visibleSemanticsLabelsSnapshot(),
        );

        if (robot.projectSettingsHeading.evaluate().isEmpty) {
          failures.add(
            'Precondition failed: Settings did not render the Project Settings heading. '
            'Visible texts: $visibleTexts. Visible semantics: $visibleSemantics.',
          );
        }

        if (robot.startupRecoveryCallout.evaluate().isEmpty) {
          failures.add(
            'Step 1 failed: the Settings screen did not render the startup recovery callout in the hosted-access area. '
            'Visible texts: $visibleTexts. Visible semantics: $visibleSemantics.',
          );
        } else {
          final calloutRect = tester.getRect(robot.startupRecoveryCallout);
          final repositoryAccessRect = tester.getRect(robot.repositoryAccessSection);
          if (calloutRect.bottom > repositoryAccessRect.top) {
            failures.add(
              'Step 1 failed: the startup recovery callout was not positioned ahead of the hosted repository-access area in Settings. '
              'Callout rect: ${_formatRect(calloutRect)}. Repository access rect: ${_formatRect(repositoryAccessRect)}.',
            );
          }
        }

        if (find.text(expectedTitle).evaluate().isEmpty) {
          failures.add(
            'Step 1 failed: the startup recovery title "$expectedTitle" was not visible in Settings. '
            'Visible texts: $visibleTexts.',
          );
        }

        if (find.text(expectedMessage).evaluate().isEmpty) {
          failures.add(
            'Step 1 failed: the startup recovery body copy did not match the expected user-facing wording. '
            'Expected: "$expectedMessage". Visible texts: $visibleTexts.',
          );
        }

        final observedActionLabels = robot.buttonLabelsWithin(
          robot.startupRecoveryCallout,
        );
        for (final expectedAction in expectedActions) {
          if (!observedActionLabels.contains(expectedAction)) {
            failures.add(
              'Step 2 failed: the recovery callout did not expose the visible "$expectedAction" action required by the ticket. '
              'Observed action labels: ${_formatSnapshot(observedActionLabels)}.',
            );
          }
        }

        final retryAction = _firstRenderedAction(robot, const [
          'Retry startup',
          'Retry',
        ]);
        final connectAction = _firstRenderedAction(robot, const ['Connect GitHub']);

        final calloutBackground =
            robot.decoratedContainerBackgroundColor(robot.startupRecoveryCallout);
        final calloutBorder =
            robot.decoratedContainerBorderColor(robot.startupRecoveryCallout);
        final calloutIcon =
            robot.trackStateIconColorWithin(robot.startupRecoveryCallout);
        final colors = robot.colors();
        final expectedBackground = colors.accent.withValues(alpha: .12);

        if (calloutBackground == null || calloutBorder == null) {
          failures.add(
            'Step 3 failed: the startup recovery callout did not expose a detectable decorated warning surface. '
            'Background=${calloutBackground == null ? '<missing>' : _rgbHex(calloutBackground)}, '
            'border=${calloutBorder == null ? '<missing>' : _rgbHex(calloutBorder)}.',
          );
        } else {
          if (calloutBackground != expectedBackground) {
            failures.add(
              'Step 3 failed: the startup recovery callout background was ${_rgbHex(calloutBackground)} instead of the amber warning surface ${_rgbHex(expectedBackground)}.',
            );
          }
          if (calloutBorder != colors.accent) {
            failures.add(
              'Step 3 failed: the startup recovery callout border was ${_rgbHex(calloutBorder)} instead of the amber A-600 warning token ${_rgbHex(colors.accent)}.',
            );
          }
          final titleContrast = contrastRatio(
            robot.renderedTextColorWithin(robot.startupRecoveryCallout, expectedTitle),
            calloutBackground,
          );
          if (titleContrast < 4.5) {
            failures.add(
              'Step 3 failed: the startup recovery title contrast was ${titleContrast.toStringAsFixed(2)}:1 on ${_rgbHex(calloutBackground)}, below WCAG AA 4.5:1.',
            );
          }
          final bodyContrast = contrastRatio(
            robot.renderedTextColorWithin(
              robot.startupRecoveryCallout,
              expectedMessage,
            ),
            calloutBackground,
          );
          if (bodyContrast < 4.5) {
            failures.add(
              'Step 3 failed: the startup recovery body contrast was ${bodyContrast.toStringAsFixed(2)}:1 on ${_rgbHex(calloutBackground)}, below WCAG AA 4.5:1.',
            );
          }
        }

        if (calloutIcon != colors.accent) {
          failures.add(
            'Step 3 failed: the startup recovery icon used ${calloutIcon == null ? '<missing>' : _rgbHex(calloutIcon)} instead of the amber A-600 warning token ${_rgbHex(colors.accent)}.',
          );
        }

        final focusCandidates = <String, Finder>{};
        if (retryAction != null) {
          focusCandidates[retryAction.label] = retryAction.finder;
        }
        if (connectAction != null) {
          focusCandidates[connectAction.label] = connectAction.finder;
        }
        await robot.clearFocus();
        final focusOrder = focusCandidates.isEmpty
            ? const <String>[]
            : await robot.collectFocusOrder(
                candidates: focusCandidates,
                tabs: 16,
              );

        for (final entry in focusCandidates.entries) {
          if (!focusOrder.contains(entry.key)) {
            failures.add(
              'Step 4 failed: keyboard Tab navigation never reached the visible "${entry.key}" recovery action. '
              'Observed focus order: ${_formatSnapshot(focusOrder)}.',
            );
          }
        }

        if (calloutBackground != null) {
          if (retryAction != null) {
            _verifyInteractiveStateTreatment(
              failures: failures,
              stepLabel: 'Step 4',
              robot: robot,
              action: retryAction,
              calloutBackground: calloutBackground,
            );
          }
          if (connectAction != null) {
            _verifyInteractiveStateTreatment(
              failures: failures,
              stepLabel: 'Step 4',
              robot: robot,
              action: connectAction,
              calloutBackground: calloutBackground,
            );
          }
        }

        if (retryAction == null) {
          failures.add(
            'Human-style verification failed: no tappable retry recovery action was rendered inside the startup recovery callout. '
            'Observed action labels: ${_formatSnapshot(observedActionLabels)}.',
          );
        } else {
          final retryLoadCount = repository.loadCount;
          await tester.tap(retryAction.finder, warnIfMissed: false);
          await tester.pumpAndSettle();
          if (repository.loadCount <= retryLoadCount) {
            failures.add(
              'Human-style verification failed: tapping the visible "${retryAction.label}" recovery action did not trigger another hosted snapshot load. '
              'Initial load count=$retryLoadCount, current load count=${repository.loadCount}.',
            );
          }
          if (robot.projectSettingsHeading.evaluate().isEmpty ||
              robot.startupRecoveryCallout.evaluate().isEmpty) {
            failures.add(
              'Human-style verification failed: after tapping "${retryAction.label}", the user was no longer left on the Settings recovery surface. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
            );
          }
        }

        if (connectAction == null) {
          failures.add(
            'Human-style verification failed: no visible Connect GitHub recovery action was rendered inside the startup recovery callout.',
          );
        } else {
          await tester.tap(connectAction.finder, warnIfMissed: false);
          await tester.pumpAndSettle();
          final connectDialogVisible =
              find.byType(Dialog).evaluate().isNotEmpty &&
              find.text('Connect GitHub').evaluate().isNotEmpty;
          final fineGrainedTokenVisible =
              await robot.isTextFieldVisible('Fine-grained token');
          if (!connectDialogVisible || !fineGrainedTokenVisible) {
            failures.add(
              'Human-style verification failed: tapping the callout Connect GitHub action did not open the expected connection dialog. '
              'Dialog visible=${connectDialogVisible ? 'yes' : 'no'}, Fine-grained token visible=${fineGrainedTokenVisible ? 'yes' : 'no'}. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
            );
          } else {
            await robot.tapActionButton('Cancel');
            final dialogStillVisible = find.byType(Dialog).evaluate().isNotEmpty;
            if (dialogStillVisible) {
              failures.add(
                'Human-style verification failed: dismissing the Connect GitHub dialog left the dialog visible on screen instead of returning the user to Settings.',
              );
            }
          }
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

({String label, Finder finder})? _firstRenderedAction(
  SettingsScreenRobot robot,
  List<String> labels,
) {
  for (final label in labels) {
    final finder = robot.startupRecoveryActionButton(label);
    if (finder.evaluate().isNotEmpty) {
      return (label: label, finder: finder);
    }
  }
  return null;
}

void _verifyInteractiveStateTreatment({
  required List<String> failures,
  required String stepLabel,
  required SettingsScreenRobot robot,
  required ({String label, Finder finder}) action,
  required Color calloutBackground,
}) {
  final idleSurface = _resolvedActionSurface(
    robot,
    action.finder,
    const <WidgetState>{},
    calloutBackground,
  );
  final hoveredSurface = _resolvedActionSurface(
    robot,
    action.finder,
    const <WidgetState>{WidgetState.hovered},
    calloutBackground,
  );
  final focusedSurface = _resolvedActionSurface(
    robot,
    action.finder,
    const <WidgetState>{WidgetState.focused},
    calloutBackground,
  );

  if (hoveredSurface == idleSurface) {
    failures.add(
      '$stepLabel failed: the "${action.label}" recovery action did not expose a distinct hovered surface. '
      'Idle=${_rgbHex(idleSurface)}, hovered=${_rgbHex(hoveredSurface)}.',
    );
  }
  if (focusedSurface == idleSurface) {
    failures.add(
      '$stepLabel failed: the "${action.label}" recovery action did not expose a distinct focused surface. '
      'Idle=${_rgbHex(idleSurface)}, focused=${_rgbHex(focusedSurface)}.',
    );
  }

  final hoveredForeground = robot.resolvedButtonForeground(
    action.finder,
    const <WidgetState>{WidgetState.hovered},
    text: action.label,
  );
  final focusedForeground = robot.resolvedButtonForeground(
    action.finder,
    const <WidgetState>{WidgetState.focused},
    text: action.label,
  );
  final hoveredContrast = contrastRatio(hoveredForeground, hoveredSurface);
  final focusedContrast = contrastRatio(focusedForeground, focusedSurface);
  if (hoveredContrast < 4.5) {
    failures.add(
      '$stepLabel failed: the hovered "${action.label}" recovery action contrast was ${hoveredContrast.toStringAsFixed(2)}:1 '
      '(${_rgbHex(hoveredForeground)} on ${_rgbHex(hoveredSurface)}), below WCAG AA 4.5:1.',
    );
  }
  if (focusedContrast < 4.5) {
    failures.add(
      '$stepLabel failed: the focused "${action.label}" recovery action contrast was ${focusedContrast.toStringAsFixed(2)}:1 '
      '(${_rgbHex(focusedForeground)} on ${_rgbHex(focusedSurface)}), below WCAG AA 4.5:1.',
    );
  }
}

Color _resolvedActionSurface(
  SettingsScreenRobot robot,
  Finder action,
  Set<WidgetState> states,
  Color calloutBackground,
) {
  return Color.alphaBlend(
    robot.resolvedButtonBackground(action, states),
    calloutBackground,
  );
}

String _formatRect(Rect rect) {
  return 'left=${rect.left.toStringAsFixed(1)}, '
      'top=${rect.top.toStringAsFixed(1)}, '
      'right=${rect.right.toStringAsFixed(1)}, '
      'bottom=${rect.bottom.toStringAsFixed(1)}';
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

String _rgbHex(Color color) {
  final value = color.toARGB32();
  return '#${value.toRadixString(16).padLeft(8, '0').substring(2).toUpperCase()}';
}
