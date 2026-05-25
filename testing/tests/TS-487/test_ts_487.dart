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
    'TS-487 status labels fall back to the canonical name after viewer and default translations are cleared',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final settingsRobot = createLocalGitSettingsScreenRobot(tester);
      Ts467LocaleResolutionFixture? fixture;

      const query = 'project = DEMO';
      const locale = Ts467LocaleResolutionFixture.viewerLocale;
      const defaultLocale = Ts467LocaleResolutionFixture.defaultLocale;
      const defaultLocaleChipLabel = '$defaultLocale (default)';
      const viewerStatus =
          Ts467LocaleResolutionFixture.viewerLocaleInProgressStatus;
      const defaultStatus =
          Ts467LocaleResolutionFixture.defaultLocaleInProgressStatus;
      const canonicalStatus =
          Ts467LocaleResolutionFixture.canonicalInProgressStatus;

      tester.binding.platformDispatcher.localeTestValue = const Locale(locale);
      tester.binding.platformDispatcher.localesTestValue = const <Locale>[
        Locale(locale),
      ];

      try {
        fixture = await tester.runAsync(Ts467LocaleResolutionFixture.create);
        if (fixture == null) {
          throw StateError('TS-487 fixture creation did not complete.');
        }

        final failures = <String>[];

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('JQL Search');
        await screen.searchIssues(query);
        await screen.expectIssueSearchResultVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
        );

        final initialProjection = _formatSnapshot(
          screen.issueSearchResultTextsSnapshot(
            Ts467LocaleResolutionFixture.issueKey,
            Ts467LocaleResolutionFixture.issueSummary,
          ),
        );
        if (!await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          viewerStatus,
        )) {
          failures.add(
            'Precondition failed: the visible JQL Search row for ${Ts467LocaleResolutionFixture.issueKey} '
            'did not show the seeded de status "$viewerStatus" before the locale translations were cleared. '
            'Visible row texts: $initialProjection.',
          );
        }
        if (await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          canonicalStatus,
        )) {
          failures.add(
            'Precondition failed: the visible JQL Search row already showed the canonical status "$canonicalStatus" '
            'before the locale translations were cleared. Visible row texts: $initialProjection.',
          );
        }

        await screen.openSection('Settings');
        await settingsRobot.openLocalesTab();
        await settingsRobot.selectLocaleChip(locale);
        final seededViewerTranslation = settingsRobot
            .localeTranslationFieldValue(locale: locale, id: 'in-progress');
        if (seededViewerTranslation != viewerStatus) {
          failures.add(
            'Step 2 failed: Settings > Locales did not load the seeded de translation '
            '"$viewerStatus" for the in-progress status. Observed value: "$seededViewerTranslation".',
          );
        }
        await settingsRobot.enterLocaleTranslation(
          locale: locale,
          id: 'in-progress',
          text: '',
        );
        await settingsRobot.tapSaveSettingsButton();

        await settingsRobot.openLocalesTab();
        await settingsRobot.selectLocaleChip(locale);
        final clearedViewerTranslation = settingsRobot
            .localeTranslationFieldValue(locale: locale, id: 'in-progress');
        if (clearedViewerTranslation.isNotEmpty) {
          failures.add(
            'Step 2 failed: after saving, the de translation field for the in-progress status '
            'was not cleared. Observed value: "$clearedViewerTranslation".',
          );
        }

        await settingsRobot.selectLocaleChip(defaultLocaleChipLabel);
        final seededDefaultTranslation = settingsRobot
            .localeTranslationFieldValue(
              locale: defaultLocale,
              id: 'in-progress',
            );
        if (seededDefaultTranslation != defaultStatus) {
          failures.add(
            'Step 3 failed: Settings > Locales did not load the seeded en translation '
            '"$defaultStatus" for the in-progress status. Observed value: "$seededDefaultTranslation".',
          );
        }
        await settingsRobot.enterLocaleTranslation(
          locale: defaultLocale,
          id: 'in-progress',
          text: '',
        );
        await settingsRobot.tapSaveSettingsButton();

        await settingsRobot.openLocalesTab();
        await settingsRobot.selectLocaleChip(defaultLocaleChipLabel);
        final clearedDefaultTranslation = settingsRobot
            .localeTranslationFieldValue(
              locale: defaultLocale,
              id: 'in-progress',
            );
        if (clearedDefaultTranslation.isNotEmpty) {
          failures.add(
            'Step 3 failed: after saving, the en translation field for the in-progress status '
            'was not cleared. Observed value: "$clearedDefaultTranslation".',
          );
        }

        await screen.openSection('JQL Search');
        final visibleQuery = await screen.readJqlSearchFieldValue();
        if (visibleQuery != query) {
          failures.add(
            'Step 4 failed: returning to the issue list did not preserve the visible query. '
            'Observed query: "${visibleQuery ?? '<missing>'}". Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }
        await screen.expectIssueSearchResultVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
        );

        final canonicalProjection = _formatSnapshot(
          screen.issueSearchResultTextsSnapshot(
            Ts467LocaleResolutionFixture.issueKey,
            Ts467LocaleResolutionFixture.issueSummary,
          ),
        );
        if (!await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          canonicalStatus,
        )) {
          failures.add(
            'Step 4 failed: after clearing both locale translations, the visible JQL Search row '
            'did not show the canonical status "$canonicalStatus". Visible row texts: $canonicalProjection.',
          );
        }
        if (await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          viewerStatus,
        )) {
          failures.add(
            'Step 4 failed: after clearing both locale translations, the visible JQL Search row '
            'still showed the removed viewer-locale status "$viewerStatus". Visible row texts: $canonicalProjection.',
          );
        }
        if (await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          defaultStatus,
        )) {
          failures.add(
            'Step 4 failed: after clearing both locale translations, the visible JQL Search row '
            'still showed the removed default-locale status "$defaultStatus". Visible row texts: $canonicalProjection.',
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
    timeout: const Timeout(Duration(seconds: 90)),
  );
}

String _formatSnapshot(List<String> values, {int limit = 12}) {
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
