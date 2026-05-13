import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../fixtures/repositories/ts467_locale_resolution_fixture.dart';
import '../../fixtures/settings/local_git_settings_screen_context.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-486 saved locale edits persist in Settings after navigating away and back',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final settingsRobot = createLocalGitSettingsScreenRobot(tester);
      Ts467LocaleResolutionFixture? fixture;

      const locale = Ts467LocaleResolutionFixture.viewerLocale;
      const initialStatus =
          Ts467LocaleResolutionFixture.viewerLocaleInProgressStatus;
      const editedStatus = 'WIP';

      tester.binding.platformDispatcher.localeTestValue = const Locale(locale);
      tester.binding.platformDispatcher.localesTestValue = const <Locale>[
        Locale(locale),
      ];

      try {
        fixture = await tester.runAsync(Ts467LocaleResolutionFixture.create);
        if (fixture == null) {
          throw StateError('TS-486 fixture creation did not complete.');
        }

        final failures = <String>[];

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('Settings');
        await settingsRobot.openLocalesTab();
        await settingsRobot.selectLocaleChip(locale);

        final initialVisibleTexts = _formatSnapshot(
          settingsRobot.visibleTexts(),
        );
        for (final requiredText in const [
          'Project Settings',
          'Project settings administration',
          'Locales',
          'en (default)',
          'de',
          'Default locale',
          'Remove locale',
        ]) {
          if (!settingsRobot.visibleTexts().contains(requiredText)) {
            failures.add(
              'Step 1 failed: navigating to Settings > Locales did not keep the visible "$requiredText" text on screen. '
              'Visible texts: $initialVisibleTexts.',
            );
          }
        }

        final seededTranslation = settingsRobot.localeTranslationFieldValue(
          locale: locale,
          id: 'in-progress',
        );
        if (seededTranslation != initialStatus) {
          failures.add(
            'Step 2 failed: the visible de translation field for the in-progress status did not start with "$initialStatus". '
            'Observed value: "$seededTranslation".',
          );
        }

        await settingsRobot.enterLocaleTranslation(
          locale: locale,
          id: 'in-progress',
          text: editedStatus,
        );
        final editedFieldValue = settingsRobot.localeTranslationFieldValue(
          locale: locale,
          id: 'in-progress',
        );
        if (editedFieldValue != editedStatus) {
          failures.add(
            'Step 2 failed: editing the visible de translation field did not keep the typed value "$editedStatus" before save. '
            'Observed value: "$editedFieldValue".',
          );
        }

        await settingsRobot.tapSaveSettingsButton();
        await screen.waitWithoutInteraction(const Duration(milliseconds: 300));

        if (await screen.isMessageBannerVisibleContaining('Save failed:')) {
          failures.add(
            'Step 3 failed: saving the locale translation surfaced a visible save failure banner. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }

        final persistedDeCatalog =
            jsonDecode(
                  File(
                    '${fixture.repositoryPath}/DEMO/config/i18n/$locale.json',
                  ).readAsStringSync(),
                )
                as Map<String, Object?>;
        final persistedStatus =
            ((persistedDeCatalog['statuses']
                    as Map<String, Object?>)['in-progress'])
                ?.toString();
        if (persistedStatus != editedStatus) {
          failures.add(
            'Step 3 failed: the saved de locale catalog did not persist the in-progress translation as "$editedStatus". '
            'Observed value in config/i18n/$locale.json: "${persistedStatus ?? '<missing>'}".',
          );
        }

        await screen.openSection('Board');
        final boardSemantics = _formatSnapshot(
          screen.visibleSemanticsLabelsSnapshot(),
        );
        if (!screen.visibleSemanticsLabelsSnapshot().contains(
          '$editedStatus column',
        )) {
          failures.add(
            'Step 4 failed: after navigating away to Board, the visible status column did not update to "$editedStatus". '
            'Visible semantics: $boardSemantics.',
          );
        }
        if (screen.visibleSemanticsLabelsSnapshot().contains(
          '$initialStatus column',
        )) {
          failures.add(
            'Step 4 failed: after navigating away to Board, the stale status column "$initialStatus" remained visible instead of the saved "$editedStatus". '
            'Visible semantics: $boardSemantics.',
          );
        }

        await screen.openSection('Settings');
        await settingsRobot.openLocalesTab();
        await settingsRobot.selectLocaleChip(locale);
        final reopenedTranslation = settingsRobot.localeTranslationFieldValue(
          locale: locale,
          id: 'in-progress',
        );
        if (reopenedTranslation != editedStatus) {
          failures.add(
            'Step 5 failed: returning to Settings > Locales did not keep the visible de translation field at "$editedStatus". '
            'Observed value: "$reopenedTranslation". Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        tester.binding.platformDispatcher.clearLocaleTestValue();
        tester.binding.platformDispatcher.clearLocalesTestValue();
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 60)),
  );
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
