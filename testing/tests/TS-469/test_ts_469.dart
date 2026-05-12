import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/utils/color_contrast.dart';
import '../../fixtures/settings/local_git_settings_screen_context.dart';
import 'support/ts469_locales_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-469 Locales workspace keeps the translation editor accessible and visually readable',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = createLocalGitSettingsScreenRobot(tester);
      Ts469LocalesFixture? fixture;

      const locale = 'fr';
      const descriptionWarning =
          'Missing translation. Using fallback "Description" from en.';
      const trackerCoreWarning =
          'Missing translation. Using fallback "Tracker Core" from en.';
      const resolutionWarning =
          'Missing translation. Using fallback "Done" from en.';

      try {
        fixture = await tester.runAsync(Ts469LocalesFixture.create);
        if (fixture == null) {
          throw StateError('TS-469 fixture creation did not complete.');
        }

        await robot.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        await robot.openSettings();
        await robot.openLocalesTab();
        await robot.selectLocaleChip(locale);

        final failures = <String>[];
        final visibleTexts = robot.visibleTexts();

        for (final requiredText in const [
          'Project Settings',
          'Project settings administration',
          'Locales',
          'en (default)',
          'fr',
          'Default locale',
          'Remove locale',
          'Statuses',
          'Issue Types',
          'Fields',
          'Priorities',
          'Components',
          'Versions',
          'Resolutions',
          'To Do · todo',
          'Story · story',
          'Summary · summary',
          'Description · description',
          'High · high',
          'Tracker Core · tracker-core',
          'MVP · mvp',
          'Done · done',
          descriptionWarning,
          trackerCoreWarning,
          resolutionWarning,
        ]) {
          if (!visibleTexts.contains(requiredText)) {
            failures.add(
              'Step 1 failed: opening Settings > Locales for "$locale" did not keep the visible "$requiredText" text on screen. '
              'Visible texts: ${_formatSnapshot(visibleTexts)}.',
            );
          }
        }

        const translationTargets = <({String label, String id})>[
          (label: 'Status To Do', id: 'todo'),
          (label: 'Issue type Story', id: 'story'),
          (label: 'Field Summary', id: 'summary'),
          (label: 'Field Description', id: 'description'),
          (label: 'Priority High', id: 'high'),
          (label: 'Component Tracker Core', id: 'tracker-core'),
          (label: 'Version MVP', id: 'mvp'),
          (label: 'Resolution Done', id: 'done'),
        ];

        for (final target in translationTargets) {
          final semanticsLabel = robot.localeTranslationFieldSemanticsLabel(
            locale: locale,
            id: target.id,
          );
          if (semanticsLabel.trim().isEmpty) {
            failures.add(
              'Step 2 failed: the ${target.label} translation field did not expose a non-empty semantics label in Settings > Locales. '
              'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
            );
          }
        }

        for (final warningText in const [
          descriptionWarning,
          trackerCoreWarning,
          resolutionWarning,
        ]) {
          final icon = robot.localeWarningIcon(warningText);
          if (icon.evaluate().isEmpty) {
            failures.add(
              'Step 2 failed: the fallback warning "$warningText" did not render any visible warning icon next to the user-facing text. '
              'Visible texts: ${_formatSnapshot(visibleTexts)}.',
            );
            continue;
          }
          final semanticsLabel = robot.localeWarningIconSemanticsLabel(
            warningText,
          );
          if (semanticsLabel == null || semanticsLabel.trim().isEmpty) {
            failures.add(
              'Step 2 failed: the fallback warning icon for "$warningText" did not expose a non-empty semantics label. '
              'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
            );
          }
        }

        final warningTextColor = robot.localeWarningTextColor(
          descriptionWarning,
        );
        final warningBackground = robot.localeWarningBackgroundColor(
          descriptionWarning,
        );
        final warningBorder = robot.localeWarningBorderColor(
          descriptionWarning,
        );
        final warningTextContrast = contrastRatio(
          warningTextColor,
          warningBackground ?? robot.colors().surfaceAlt,
        );

        if (_rgbHex(warningTextColor) != _rgbHex(robot.colors().warning)) {
          failures.add(
            'Step 3 failed: the visible fallback warning text did not use the TrackState warning token. '
            'Rendered=${_rgbHex(warningTextColor)} token=${_rgbHex(robot.colors().warning)}.',
          );
        }
        if (warningBackground == null ||
            _rgbHex(warningBackground) != _rgbHex(robot.colors().surfaceAlt)) {
          failures.add(
            'Step 3 failed: the visible fallback warning background did not use the TrackState surfaceAlt token. '
            'Rendered=${warningBackground == null ? '<missing>' : _rgbHex(warningBackground)} token=${_rgbHex(robot.colors().surfaceAlt)}.',
          );
        }
        if (warningBorder == null ||
            _rgbHex(warningBorder) != _rgbHex(robot.colors().warning)) {
          failures.add(
            'Step 3 failed: the visible fallback warning border did not use the TrackState warning token. '
            'Rendered=${warningBorder == null ? '<missing>' : _rgbHex(warningBorder)} token=${_rgbHex(robot.colors().warning)}.',
          );
        }
        if (warningTextContrast < 4.5) {
          failures.add(
            'Step 3 failed: the fallback warning text contrast was only ${warningTextContrast.toStringAsFixed(2)}:1 '
            '(${_rgbHex(warningTextColor)} on '
            '${warningBackground == null ? '<missing>' : _rgbHex(warningBackground)}), below the required 4.5:1 threshold.',
          );
        }

        final warningIconColor = robot.localeWarningIconColor(
          descriptionWarning,
        );
        if (warningIconColor == null) {
          failures.add(
            'Step 3 failed: the fallback warning treatment did not expose any visible warning icon color for "$descriptionWarning".',
          );
        } else {
          final iconContrast = contrastRatio(
            warningIconColor,
            warningBackground ?? robot.colors().surfaceAlt,
          );
          if (_rgbHex(warningIconColor) != _rgbHex(robot.colors().warning)) {
            failures.add(
              'Step 3 failed: the fallback warning icon did not use the TrackState warning token. '
              'Rendered=${_rgbHex(warningIconColor)} token=${_rgbHex(robot.colors().warning)}.',
            );
          }
          if (iconContrast < 3.0) {
            failures.add(
              'Step 3 failed: the fallback warning icon contrast was only ${iconContrast.toStringAsFixed(2)}:1 '
              '(${_rgbHex(warningIconColor)} on '
              '${warningBackground == null ? '<missing>' : _rgbHex(warningBackground)}), below the required 3.0:1 threshold.',
            );
          }
        }

        final placeholderColor = robot.localeTranslationFieldPlaceholderColor(
          locale: locale,
          id: 'description',
        );
        final placeholderContrast = contrastRatio(
          placeholderColor,
          robot.colors().surface,
        );
        if (placeholderContrast < 3.0) {
          failures.add(
            'Step 4 failed: the empty Description translation placeholder contrast was ${placeholderContrast.toStringAsFixed(2)}:1 '
            '(${_rgbHex(placeholderColor)} on ${_rgbHex(robot.colors().surface)}), below the required 3.0:1 threshold.',
          );
        }

        final focusCandidates = <String, Finder>{
          for (final target in translationTargets)
            target.label: robot.localeEntryFieldScope(
              locale: locale,
              id: target.id,
            ),
        };
        await robot.clearFocus();
        await robot.focusLocaleTranslationField(locale: locale, id: 'todo');
        final focusedOrder = <String>[];
        final firstFocused = robot.focusedLabel(focusCandidates);
        if (firstFocused == null) {
          failures.add(
            'Step 5 failed: the first translation field did not retain keyboard focus after tapping the Status To Do translation input.',
          );
        } else {
          focusedOrder.add(firstFocused);
        }
        focusedOrder.addAll(
          await robot.collectFocusOrder(
            candidates: focusCandidates,
            tabs: translationTargets.length - 1,
          ),
        );
        final focusFailure = _orderedSubsequenceFailure(
          focusedOrder,
          expectedOrder: [
            for (final target in translationTargets) target.label,
          ],
        );
        if (focusFailure != null) {
          failures.add(
            'Step 5 failed: keyboard Tab traversal did not keep the translation matrix in logical top-to-bottom order. '
            '$focusFailure Observed Tab order: ${focusedOrder.join(' -> ')}.',
          );
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

String? _orderedSubsequenceFailure(
  List<String> observed, {
  required List<String> expectedOrder,
}) {
  var previousIndex = -1;
  for (final label in expectedOrder) {
    final index = observed.indexOf(label);
    if (index == -1) {
      return 'The translation focus order did not expose "$label" as a reachable target.';
    }
    if (index <= previousIndex) {
      return 'The translation focus order did not keep the locale inputs in logical section order.';
    }
    previousIndex = index;
  }
  return null;
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
  final rgb = color.toARGB32() & 0x00FFFFFF;
  return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
}
