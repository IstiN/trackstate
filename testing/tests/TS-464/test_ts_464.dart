import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../fixtures/settings/local_git_settings_screen_context.dart';
import 'support/ts464_locale_addition_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-464 locale management adds fr and scaffolds locale storage immediately',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final robot = createLocalGitSettingsScreenRobot(tester);
      Ts464LocaleAdditionFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts464LocaleAdditionFixture.create);
        if (fixture == null) {
          throw StateError('TS-464 fixture creation did not complete.');
        }

        final projectFile = File('${fixture.repositoryPath}/DEMO/project.json');
        final frenchLocaleFile = File(
          '${fixture.repositoryPath}/DEMO/config/i18n/fr.json',
        );

        final initialProjectJson =
            jsonDecode(await tester.runAsync(projectFile.readAsString) ?? '{}')
                as Map<String, Object?>;
        final initialSupportedLocales = [
          for (final locale
              in (initialProjectJson['supportedLocales'] as List? ?? const []))
            '$locale',
        ];
        final frenchFileExistedBefore =
            await tester.runAsync(frenchLocaleFile.exists) ?? true;

        final failures = <String>[];

        if (initialSupportedLocales.length != 1 ||
            initialSupportedLocales.single != 'en') {
          failures.add(
            'Precondition failed: the seeded project.json did not start with only the "en" supported locale. '
            'Observed supportedLocales: $initialSupportedLocales.',
          );
        }
        if (frenchFileExistedBefore) {
          failures.add(
            'Precondition failed: config/i18n/fr.json already existed before the Add locale flow began.',
          );
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        await screen.openSection('Settings');
        await robot.openLocalesTab();

        final initialTexts = robot.visibleTexts();
        for (final requiredText in const [
          'Project Settings',
          'Project settings administration',
          'Locales',
          'en (default)',
          'Add locale',
        ]) {
          if (!initialTexts.contains(requiredText)) {
            failures.add(
              'Step 1 failed: navigating to Settings > Locales did not keep the visible "$requiredText" text on screen. '
              'Visible texts: ${_formatSnapshot(initialTexts)}.',
            );
          }
        }

        final addLocaleOpened = await screen.tapVisibleControl('Add locale');
        if (!addLocaleOpened) {
          failures.add(
            'Step 2 failed: tapping the visible Add locale control did not open the locale editor.',
          );
        }

        final localeCodeSelectorVisible = await screen.isDropdownFieldVisible(
          'Locale code',
        );
        final localeCodeFieldVisible = await screen.isTextFieldVisible(
          'Locale code',
        );
        if (!localeCodeSelectorVisible && !localeCodeFieldVisible) {
          failures.add(
            'Step 2 failed: the Add locale flow did not expose a visible Locale code selector after tapping Add locale. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }

        if (!localeCodeSelectorVisible) {
          fail(
            'Step 3 failed: the Add locale flow does not expose a validated Locale code list. '
            'The ticket requires selecting "fr" from a validated locale-code list before confirmation, '
            'but the production-visible dialog exposed only a free-text Locale code field. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }

        final localeCodeOptions = await screen.readDropdownOptions(
          'Locale code',
        );
        if (!localeCodeOptions.contains('fr')) {
          fail(
            'Step 3 failed: the validated Locale code list did not offer "fr". '
            'Observed options: ${_formatSnapshot(localeCodeOptions)}.',
          );
        }

        await screen.selectDropdownOption('Locale code', optionText: 'fr');
        final selectedLocaleCode = await screen.readDropdownFieldValue(
          'Locale code',
        );
        if (selectedLocaleCode != 'fr') {
          failures.add(
            'Step 3 failed: the Add locale dialog did not keep the validated Locale code selection as "fr" before confirmation. '
            'Observed value: "${selectedLocaleCode ?? '<missing>'}". Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }

        final localeSaved = await screen.tapVisibleControl('Save');
        if (!localeSaved) {
          failures.add(
            'Step 3 failed: the Add locale dialog did not expose a tappable Save control.',
          );
        }
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final localeTextsAfterAdd = robot.visibleTexts();
        if (!localeTextsAfterAdd.contains('fr')) {
          failures.add(
            'Step 3 failed: confirming Add locale did not update Settings > Locales to show the new visible "fr" locale chip. '
            'Visible texts: ${_formatSnapshot(localeTextsAfterAdd)}.',
          );
        } else {
          await robot.selectLocaleChip('fr');
          final frenchStatusField = robot.localeEntryFieldScope(
            locale: 'fr',
            id: 'todo',
          );
          if (frenchStatusField.evaluate().isEmpty) {
            failures.add(
              'Step 3 failed: the new visible "fr" locale did not become available for translation editing after confirmation. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
            );
          }
        }

        final frenchFileExistsAfterAdd =
            await tester.runAsync(frenchLocaleFile.exists) ?? false;
        if (!frenchFileExistsAfterAdd) {
          failures.add(
            'Step 4 failed: confirming Add locale did not scaffold config/i18n/fr.json immediately. '
            'Observed file path: ${frenchLocaleFile.path}.',
          );
        }

        final projectJsonAfterAdd =
            jsonDecode(await tester.runAsync(projectFile.readAsString) ?? '{}')
                as Map<String, Object?>;
        final supportedLocalesAfterAdd = [
          for (final locale
              in (projectJsonAfterAdd['supportedLocales'] as List? ?? const []))
            '$locale',
        ];
        if (!supportedLocalesAfterAdd.contains('fr')) {
          failures.add(
            'Step 5 failed: project.json did not include "fr" in supportedLocales immediately after Add locale confirmation. '
            'Observed supportedLocales: $supportedLocalesAfterAdd.',
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
        screen.resetView();
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
