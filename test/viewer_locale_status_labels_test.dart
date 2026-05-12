import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../testing/components/factories/testing_dependencies.dart';
import '../testing/core/interfaces/trackstate_app_component.dart';
import '../testing/fixtures/settings/local_git_settings_screen_context.dart';
import '../testing/tests/TS-467/support/ts467_locale_resolution_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'issue rows resolve status labels from viewer locale through canonical fallback and locale edits stay visible',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final settingsRobot = createLocalGitSettingsScreenRobot(tester);
      Ts467LocaleResolutionFixture? fixture;

      const query = 'project = DEMO';
      const locale = Ts467LocaleResolutionFixture.viewerLocale;
      const defaultLocale = Ts467LocaleResolutionFixture.defaultLocale;
      const initialStatus =
          Ts467LocaleResolutionFixture.viewerLocaleInProgressStatus;
      const editedStatus = 'WIP';
      const fallbackStatus =
          Ts467LocaleResolutionFixture.defaultLocaleInProgressStatus;
      const canonicalStatus =
          Ts467LocaleResolutionFixture.canonicalInProgressStatus;

      tester.binding.platformDispatcher.localeTestValue = const Locale(locale);
      tester.binding.platformDispatcher.localesTestValue = const <Locale>[
        Locale(locale),
      ];

      try {
        fixture = await tester.runAsync(Ts467LocaleResolutionFixture.create);

        await screen.pumpLocalGitApp(repositoryPath: fixture!.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('JQL Search');
        await screen.searchIssues(query);
        await screen.expectIssueSearchResultVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
        );
        expect(
          await screen.isIssueSearchResultTextVisible(
            Ts467LocaleResolutionFixture.issueKey,
            Ts467LocaleResolutionFixture.issueSummary,
            initialStatus,
          ),
          isTrue,
        );

        await screen.openSection('Settings');
        await settingsRobot.openLocalesTab();
        await settingsRobot.selectLocaleChip(locale);
        await settingsRobot.enterLocaleTranslation(
          locale: locale,
          id: 'in-progress',
          text: editedStatus,
        );
        expect(
          settingsRobot.localeTranslationFieldValue(
            locale: locale,
            id: 'in-progress',
          ),
          editedStatus,
        );
        await settingsRobot.tapSaveSettingsButton();
        await screen.waitWithoutInteraction(const Duration(milliseconds: 300));
        expect(
          await screen.isMessageBannerVisibleContaining('Save failed:'),
          isFalse,
          reason: screen.visibleTextsSnapshot().join(' | '),
        );
        final persistedDeCatalog =
            jsonDecode(
                  File(
                    '${fixture.repositoryPath}/DEMO/config/i18n/$locale.json',
                  ).readAsStringSync(),
                )
                as Map<String, Object?>;
        expect(
          ((persistedDeCatalog['statuses']
                  as Map<String, Object?>)['in-progress'])
              ?.toString(),
          editedStatus,
        );

        await screen.openSection('JQL Search');
        expect(
          await screen.isIssueSearchResultTextVisible(
            Ts467LocaleResolutionFixture.issueKey,
            Ts467LocaleResolutionFixture.issueSummary,
            editedStatus,
          ),
          isTrue,
        );

        await screen.openSection('Settings');
        await settingsRobot.openLocalesTab();
        await settingsRobot.selectLocaleChip(locale);
        expect(
          settingsRobot.localeTranslationFieldValue(
            locale: locale,
            id: 'in-progress',
          ),
          editedStatus,
        );

        await settingsRobot.enterLocaleTranslation(
          locale: locale,
          id: 'in-progress',
          text: '',
        );
        await settingsRobot.tapSaveSettingsButton();
        await screen.waitWithoutInteraction(const Duration(milliseconds: 300));

        await screen.openSection('JQL Search');
        expect(
          await screen.isIssueSearchResultTextVisible(
            Ts467LocaleResolutionFixture.issueKey,
            Ts467LocaleResolutionFixture.issueSummary,
            fallbackStatus,
          ),
          isTrue,
        );

        await screen.openSection('Settings');
        await settingsRobot.openLocalesTab();
        await settingsRobot.selectLocaleChip('$defaultLocale (default)');
        await settingsRobot.enterLocaleTranslation(
          locale: defaultLocale,
          id: 'in-progress',
          text: '',
        );
        await settingsRobot.tapSaveSettingsButton();
        await screen.waitWithoutInteraction(const Duration(milliseconds: 300));

        await screen.openSection('JQL Search');
        expect(
          await screen.isIssueSearchResultTextVisible(
            Ts467LocaleResolutionFixture.issueKey,
            Ts467LocaleResolutionFixture.issueSummary,
            canonicalStatus,
          ),
          isTrue,
        );
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
    timeout: const Timeout(Duration(seconds: 30)),
  );
}
