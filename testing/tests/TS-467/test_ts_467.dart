import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../fixtures/settings/local_git_settings_screen_context.dart';
import 'support/ts467_locale_resolution_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-467 JQL Search status labels follow viewer locale, default-locale, and canonical fallback',
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
        if (fixture == null) {
          throw StateError('TS-467 fixture creation did not complete.');
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
          initialStatus,
        )) {
          failures.add(
            'Step 2 failed: the visible JQL Search row for ${Ts467LocaleResolutionFixture.issueKey} '
            'did not show the viewer-locale status "$initialStatus" with the forced de locale. '
            'Visible row texts: $initialProjection.',
          );
        }
        if (await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          canonicalStatus,
        )) {
          failures.add(
            'Step 2 failed: the visible JQL Search row skipped locale resolution and showed the canonical status "$canonicalStatus" '
            'instead of the viewer-locale translation "$initialStatus". '
            'Visible row texts: $initialProjection.',
          );
        }
        if (await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          fallbackStatus,
        )) {
          failures.add(
            'Step 2 failed: the visible JQL Search row still showed the default-locale status "$fallbackStatus" '
            'instead of the viewer-locale translation "$initialStatus". '
            'Visible row texts: $initialProjection.',
          );
        }

        await screen.openSection('Settings');
        await settingsRobot.openLocalesTab();
        await settingsRobot.selectLocaleChip(locale);
        final seededTranslation = settingsRobot.localeTranslationFieldValue(
          locale: locale,
          id: 'in-progress',
        );
        if (seededTranslation != initialStatus) {
          failures.add(
            'Precondition failed: Settings > Locales did not load the seeded de translation '
            '"$initialStatus" for the in-progress status. Observed value: "$seededTranslation".',
          );
        }

        await settingsRobot.enterLocaleTranslation(
          locale: locale,
          id: 'in-progress',
          text: editedStatus,
        );
        await settingsRobot.tapActionButton('Save settings');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 300));

        await screen.openSection('JQL Search');
        final queryAfterEdit = await screen.readJqlSearchFieldValue();
        if (queryAfterEdit != query) {
          failures.add(
            'Step 4 failed: returning from Settings required a manual reload because the visible JQL query did not persist. '
            'Observed query: "${queryAfterEdit ?? '<missing>'}". Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }
        await screen.expectIssueSearchResultVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
        );
        final editedProjection = _formatSnapshot(
          screen.issueSearchResultTextsSnapshot(
            Ts467LocaleResolutionFixture.issueKey,
            Ts467LocaleResolutionFixture.issueSummary,
          ),
        );
        if (!await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          editedStatus,
        )) {
          failures.add(
            'Step 4 failed: after saving the de translation edit, the visible JQL Search row did not refresh to "$editedStatus" '
            'without rerunning the query. Visible row texts: $editedProjection.',
          );
        }
        if (await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          fallbackStatus,
        )) {
          failures.add(
            'Step 4 failed: after saving the de translation edit, the visible JQL Search row fell back to the default-locale status "$fallbackStatus" '
            'instead of showing the edited viewer-locale value "$editedStatus". '
            'Visible row texts: $editedProjection.',
          );
        }
        if (await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          initialStatus,
        )) {
          failures.add(
            'Step 4 failed: after saving the de translation edit, the visible JQL Search row still showed the stale status "$initialStatus". '
            'Visible row texts: $editedProjection.',
          );
        }

        await screen.openSection('Settings');
        await settingsRobot.openLocalesTab();
        await settingsRobot.selectLocaleChip(locale);
        final persistedEditedTranslation = settingsRobot
            .localeTranslationFieldValue(locale: locale, id: 'in-progress');
        if (persistedEditedTranslation != editedStatus) {
          failures.add(
            'Step 5 precondition failed: reopening Settings > Locales did not persist the saved '
            '"$editedStatus" translation. Observed value: "$persistedEditedTranslation".',
          );
        }
        await settingsRobot.enterLocaleTranslation(
          locale: locale,
          id: 'in-progress',
          text: '',
        );
        await settingsRobot.tapActionButton('Save settings');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 300));

        await screen.openSection('JQL Search');
        final queryAfterFallback = await screen.readJqlSearchFieldValue();
        if (queryAfterFallback != query) {
          failures.add(
            'Step 5 failed: clearing the de translation forced the JQL Search field to lose the visible query, implying a manual reload. '
            'Observed query: "${queryAfterFallback ?? '<missing>'}". Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }
        await screen.expectIssueSearchResultVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
        );
        final fallbackProjection = _formatSnapshot(
          screen.issueSearchResultTextsSnapshot(
            Ts467LocaleResolutionFixture.issueKey,
            Ts467LocaleResolutionFixture.issueSummary,
          ),
        );
        if (!await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          fallbackStatus,
        )) {
          failures.add(
            'Step 5 failed: after removing the de translation, the visible JQL Search row did not fall back to the default-locale status "$fallbackStatus". '
            'Visible row texts: $fallbackProjection.',
          );
        }
        if (await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          canonicalStatus,
        )) {
          failures.add(
            'Step 5 failed: after removing the de translation, the visible JQL Search row skipped the default-locale branch and showed the canonical status "$canonicalStatus". '
            'Visible row texts: $fallbackProjection.',
          );
        }
        if (await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          editedStatus,
        )) {
          failures.add(
            'Step 5 failed: after removing the de translation, the visible JQL Search row still showed the removed status "$editedStatus". '
            'Visible row texts: $fallbackProjection.',
          );
        }

        await screen.openSection('Settings');
        await settingsRobot.openLocalesTab();
        await settingsRobot.selectLocaleChip(defaultLocaleChipLabel);
        final persistedDefaultTranslation = settingsRobot
            .localeTranslationFieldValue(
              locale: defaultLocale,
              id: 'in-progress',
            );
        if (persistedDefaultTranslation != fallbackStatus) {
          failures.add(
            'Step 6 precondition failed: Settings > Locales did not load the default-locale translation '
            '"$fallbackStatus" for the in-progress status before the canonical fallback check. '
            'Observed value: "$persistedDefaultTranslation".',
          );
        }
        await settingsRobot.enterLocaleTranslation(
          locale: defaultLocale,
          id: 'in-progress',
          text: '',
        );
        await settingsRobot.tapActionButton('Save settings');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 300));

        await screen.openSection('JQL Search');
        final queryAfterCanonicalFallback = await screen
            .readJqlSearchFieldValue();
        if (queryAfterCanonicalFallback != query) {
          failures.add(
            'Step 6 failed: clearing the default-locale translation forced the JQL Search field to lose the visible query, implying a manual reload. '
            'Observed query: "${queryAfterCanonicalFallback ?? '<missing>'}". Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
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
            'Step 6 failed: after removing both the de and en translations, the visible JQL Search row did not fall back to the canonical status "$canonicalStatus". '
            'Visible row texts: $canonicalProjection.',
          );
        }
        if (await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          fallbackStatus,
        )) {
          failures.add(
            'Step 6 failed: after removing both the de and en translations, the visible JQL Search row still showed the default-locale status "$fallbackStatus". '
            'Visible row texts: $canonicalProjection.',
          );
        }
        if (await screen.isIssueSearchResultTextVisible(
          Ts467LocaleResolutionFixture.issueKey,
          Ts467LocaleResolutionFixture.issueSummary,
          editedStatus,
        )) {
          failures.add(
            'Step 6 failed: after removing both the de and en translations, the visible JQL Search row still showed the removed viewer-locale status "$editedStatus". '
            'Visible row texts: $canonicalProjection.',
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
    timeout: const Timeout(Duration(seconds: 30)),
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
