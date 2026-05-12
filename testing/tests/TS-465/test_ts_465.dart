import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../fixtures/settings/local_git_settings_screen_context.dart';
import 'support/ts465_locale_removal_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-465 locale validation protects default and last remaining locales',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = createLocalGitSettingsScreenRobot(tester);
      Ts465LocaleRemovalFixture? fixture;

      const initialDefaultChip = 'en (default)';
      const switchedDefaultChip = 'de (default)';

      try {
        fixture = await tester.runAsync(Ts465LocaleRemovalFixture.create);
        if (fixture == null) {
          throw StateError('TS-465 fixture creation did not complete.');
        }

        final failures = <String>[];

        await robot.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        await robot.openSettings();
        await robot.openLocalesTab();

        final initialTexts = _formatSnapshot(robot.visibleTexts());
        for (final requiredText in const [
          'Project Settings',
          'Project settings administration',
          'Locales',
          initialDefaultChip,
          'de',
          'Default locale',
          'Remove locale',
        ]) {
          if (!robot.visibleTexts().contains(requiredText)) {
            failures.add(
              'Step 1 failed: navigating to Settings > Locales did not keep the visible "$requiredText" text on screen. '
              'Visible texts: $initialTexts.',
            );
          }
        }

        final removeEnButton = robot.removeLocaleButton('en');
        final initialDefaultValue = robot.readDropdownFieldValue(
          'Default locale',
        );
        final initialSemantics = _formatSnapshot(
          robot.visibleSemanticsLabelsSnapshot(),
        );
        if (initialDefaultValue != 'en') {
          failures.add(
            'Precondition failed: the visible Default locale dropdown did not start on "en". '
            'Observed value: "${initialDefaultValue ?? '<missing>'}". Visible texts: $initialTexts.',
          );
        }
        if (!robot.visibleSemanticsLabelsSnapshot().contains(
          'Remove locale en',
        )) {
          failures.add(
            'Step 2 failed: the remove action did not describe the selected default locale as "Remove locale en". '
            'Visible semantics: $initialSemantics.',
          );
        }
        if (robot.isButtonEnabled(removeEnButton)) {
          failures.add(
            'Step 2 failed: removing the current default locale "en" stayed enabled instead of being blocked. '
            'Visible texts: $initialTexts.',
          );
        }

        await robot.selectDropdownOption('Default locale', optionText: 'de');
        final afterDefaultSwitchTexts = _formatSnapshot(robot.visibleTexts());
        final switchedDefaultValue = robot.readDropdownFieldValue(
          'Default locale',
        );
        if (switchedDefaultValue != 'de') {
          failures.add(
            'Step 3 failed: changing the Default locale to "de" did not update the visible dropdown value. '
            'Observed value: "${switchedDefaultValue ?? '<missing>'}". Visible texts: $afterDefaultSwitchTexts.',
          );
        }
        if (robot.localeChip(switchedDefaultChip).evaluate().isEmpty) {
          failures.add(
            'Step 3 failed: changing the default locale to "de" did not relabel the visible locale chip to "$switchedDefaultChip". '
            'Visible texts: $afterDefaultSwitchTexts.',
          );
        }
        if (robot.localeChip(initialDefaultChip).evaluate().isNotEmpty) {
          failures.add(
            'Step 3 failed: the previous default chip "$initialDefaultChip" stayed visible after switching the default locale to "de". '
            'Visible texts: $afterDefaultSwitchTexts.',
          );
        }

        await robot.selectLocaleChip(switchedDefaultChip);
        final removeDeWhileDefaultButton = robot.removeLocaleButton('de');
        final switchedSemantics = _formatSnapshot(
          robot.visibleSemanticsLabelsSnapshot(),
        );
        if (!robot.visibleSemanticsLabelsSnapshot().contains(
          'Remove locale de',
        )) {
          failures.add(
            'Step 4 failed: the remove action did not target the selected default locale as "Remove locale de". '
            'Visible semantics: $switchedSemantics.',
          );
        }
        if (robot.isButtonEnabled(removeDeWhileDefaultButton)) {
          failures.add(
            'Step 4 failed: removing "de" stayed enabled even though it was the current default locale. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
          );
        }

        await robot.selectLocaleChip('en');
        final removeEnAfterSwitchButton = robot.removeLocaleButton('en');
        if (!robot.isButtonEnabled(removeEnAfterSwitchButton)) {
          failures.add(
            'Step 5 failed: removing "en" remained blocked after it became a non-default locale. '
            'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
          );
        } else {
          await robot.tapActionButton('Remove locale en');
        }

        final afterRemovalTexts = _formatSnapshot(robot.visibleTexts());
        if (robot.localeChip('en').evaluate().isNotEmpty) {
          failures.add(
            'Step 5 failed: removing the non-default locale "en" did not remove its visible chip from Settings > Locales. '
            'Visible texts: $afterRemovalTexts.',
          );
        }
        if (robot.localeChip(switchedDefaultChip).evaluate().isEmpty) {
          failures.add(
            'Step 5 failed: after removing "en", the remaining locale did not stay visible as "$switchedDefaultChip". '
            'Visible texts: $afterRemovalTexts.',
          );
        }

        await robot.selectLocaleChip(switchedDefaultChip);
        final removeLastLocaleButton = robot.removeLocaleButton('de');
        if (robot.isButtonEnabled(removeLastLocaleButton)) {
          failures.add(
            'Step 6 failed: removing the last remaining locale "de" stayed enabled instead of being blocked. '
            'Visible texts: $afterRemovalTexts.',
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

String _formatSnapshot(List<String> values, {int limit = 20}) {
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
