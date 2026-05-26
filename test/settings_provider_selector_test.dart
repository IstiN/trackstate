import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../testing/components/screens/settings_screen_robot.dart';
import '../testing/core/utils/color_contrast.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'settings provider selector reveals Local Git fields and clears hosted config',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        final providerSelector = find.bySemanticsLabel(
          RegExp('Repository access'),
        );
        final hostedProvider = find.descendant(
          of: providerSelector,
          matching: find.bySemanticsLabel(RegExp('Connect GitHub')),
        );
        final localGitProvider = find.descendant(
          of: providerSelector,
          matching: find.bySemanticsLabel(RegExp('Local Git')),
        );

        expect(providerSelector, findsOneWidget);
        expect(hostedProvider, findsOneWidget);
        expect(localGitProvider, findsOneWidget);

        await tester.tap(hostedProvider);
        await tester.pumpAndSettle();
        expect(find.text('Fine-grained token'), findsOneWidget);

        await tester.tap(localGitProvider);
        await tester.pumpAndSettle();

        expect(find.text('Repository Path'), findsOneWidget);
        expect(find.text('Write Branch'), findsOneWidget);
        expect(find.text('Fine-grained token'), findsNothing);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'local git configuration fields are editable and reset after provider switch',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      Finder field(String label) => find.widgetWithText(TextFormField, label);

      try {
        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        final providerSelector = find.bySemanticsLabel(
          RegExp('Repository access'),
        );
        final hostedProvider = find.descendant(
          of: providerSelector,
          matching: find.bySemanticsLabel(RegExp('Connect GitHub')),
        );
        final localGitProvider = find.descendant(
          of: providerSelector,
          matching: find.bySemanticsLabel(RegExp('Local Git')),
        );

        await tester.tap(localGitProvider);
        await tester.pumpAndSettle();

        final repositoryPathEditableText = tester.widget<EditableText>(
          find.descendant(
            of: field('Repository Path'),
            matching: find.byType(EditableText),
          ),
        );
        final writeBranchEditableText = tester.widget<EditableText>(
          find.descendant(
            of: field('Write Branch'),
            matching: find.byType(EditableText),
          ),
        );

        expect(repositoryPathEditableText.readOnly, isFalse);
        expect(writeBranchEditableText.readOnly, isFalse);
        expect(repositoryPathEditableText.controller.text, isEmpty);
        expect(writeBranchEditableText.controller.text, isEmpty);

        await tester.enterText(
          field('Repository Path'),
          '/tmp/trackstate-demo.git',
        );
        await tester.enterText(field('Write Branch'), 'feature/ts-54');
        await tester.pumpAndSettle();

        expect(
          tester
              .widget<EditableText>(
                find.descendant(
                  of: field('Repository Path'),
                  matching: find.byType(EditableText),
                ),
              )
              .controller
              .text,
          '/tmp/trackstate-demo.git',
        );
        expect(
          tester
              .widget<EditableText>(
                find.descendant(
                  of: field('Write Branch'),
                  matching: find.byType(EditableText),
                ),
              )
              .controller
              .text,
          'feature/ts-54',
        );

        await tester.tap(hostedProvider);
        await tester.pumpAndSettle();
        await tester.tap(localGitProvider);
        await tester.pumpAndSettle();

        expect(
          tester
              .widget<EditableText>(
                find.descendant(
                  of: field('Repository Path'),
                  matching: find.byType(EditableText),
                ),
              )
              .controller
              .text,
          isEmpty,
        );
        expect(
          tester
              .widget<EditableText>(
                find.descendant(
                  of: field('Write Branch'),
                  matching: find.byType(EditableText),
                ),
              )
              .controller
              .text,
          isEmpty,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'failed Local Git auto-apply can retry the same configuration without edits',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      Finder field(String label) => find.widgetWithText(TextFormField, label);

      var openAttempts = 0;
      Object? capturedError;

      try {
        await tester.pumpWidget(
          TrackStateApp(
            repository: const DemoTrackStateRepository(),
            openLocalRepository:
                ({
                  required String repositoryPath,
                  required String defaultBranch,
                  required String writeBranch,
                }) async {
                  openAttempts += 1;
                  if (openAttempts == 1) {
                    throw StateError(
                      'Simulated Local Git open failure for $repositoryPath',
                    );
                  }
                  return const DemoTrackStateRepository();
                },
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();
        await tester.tap(find.bySemanticsLabel(RegExp('Local Git')).first);
        await tester.pumpAndSettle();

        await tester.enterText(field('Repository Path'), '/tmp/retryable-repo');
        await tester.enterText(field('Write Branch'), 'main');
        await runZonedGuarded(
          () async {
            FocusManager.instance.primaryFocus?.unfocus();
            await tester.pump();
          },
          (error, _) {
            capturedError = error;
          },
        );
        expect(capturedError, isNull);
        expect(openAttempts, 1);

        await tester.tap(field('Repository Path'));
        await tester.pump();
        FocusManager.instance.primaryFocus?.unfocus();
        await tester.pumpAndSettle();

        expect(openAttempts, 1);
        expect(find.bySemanticsLabel(RegExp('Local Git')), findsWidgets);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'settings admin tabs can add a status and keep reserved fields undeletable',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      final repository = _EditableSettingsWidgetRepository();

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        expect(find.text('Project settings administration'), findsOneWidget);
        expect(_settingsTab('Statuses'), findsOneWidget);
        expect(_settingsTab('Workflows'), findsOneWidget);
        expect(_settingsTab('Issue Types'), findsOneWidget);
        expect(_settingsTab('Fields'), findsOneWidget);
        expect(_settingsTab('Priorities'), findsOneWidget);
        expect(_settingsTab('Components'), findsOneWidget);
        expect(_settingsTab('Versions'), findsOneWidget);
        expect(_settingsTab('Attachments'), findsOneWidget);
        expect(_settingsTab('Locales'), findsOneWidget);

        await tester.tap(_settingsTab('Fields'));
        await tester.pumpAndSettle();
        expect(find.bySemanticsLabel('Delete field Summary'), findsNothing);

        await tester.tap(_settingsTab('Statuses'));
        await tester.pumpAndSettle();
        await tester.tap(find.text('Add status'));
        await tester.pumpAndSettle();
        await tester.enterText(
          find.widgetWithText(TextFormField, 'ID'),
          'blocked',
        );
        await tester.enterText(
          find.widgetWithText(TextFormField, 'Name'),
          'Blocked',
        );
        await tester.tap(find.widgetWithText(FilledButton, 'Save'));
        await tester.pumpAndSettle();

        expect(find.text('Blocked'), findsOneWidget);

        await tester.tap(find.text('Save settings'));
        await tester.pumpAndSettle();

        expect(
          repository.savedSettings?.statusDefinitions.map(
            (status) => status.id,
          ),
          contains('blocked'),
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'fields editor keeps Summary immutable and saves a Bug-only Environment select field',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      final repository = _EditableSettingsWidgetRepository();

      Finder fieldInput(String label) => find.descendant(
        of: find.widgetWithText(TextFormField, label),
        matching: find.byType(EditableText),
      );
      Finder rowAction(String title, String actionLabel) => find.descendant(
        of: find.ancestor(
          of: find.text(title),
          matching: find.byType(ListTile),
        ),
        matching: find.widgetWithText(TextButton, actionLabel),
      );

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        await tester.tap(_settingsTab('Fields'));
        await tester.pumpAndSettle();

        expect(find.bySemanticsLabel('Delete field Summary'), findsNothing);

        await tester.tap(rowAction('Summary', 'Edit'));
        await tester.pumpAndSettle();

        final summaryIdField = tester.widget<TextFormField>(
          find.widgetWithText(TextFormField, 'ID'),
        );
        expect(summaryIdField.controller?.text, 'summary');
        expect(summaryIdField.enabled, isFalse);

        final summaryTypeButton = tester.widget<TextButton>(
          find.widgetWithText(TextButton, 'Type string'),
        );
        expect(summaryTypeButton.onPressed, isNull);

        await tester.tap(find.widgetWithText(TextButton, 'Cancel'));
        await tester.pumpAndSettle();

        await tester.tap(find.text('Add field'));
        await tester.pumpAndSettle();

        await tester.enterText(fieldInput('ID'), 'environment');
        await tester.enterText(fieldInput('Name'), 'Environment');
        await tester.tap(find.byType(DropdownButtonFormField<String>));
        await tester.pumpAndSettle();
        await tester.tap(find.text('option').last);
        await tester.pumpAndSettle();
        await tester.enterText(
          fieldInput('Options'),
          'Production, Staging, Development',
        );
        await tester.tap(find.widgetWithText(FilterChip, 'Bug'));
        await tester.pumpAndSettle();

        await tester.tap(find.widgetWithText(FilledButton, 'Save'));
        await tester.pumpAndSettle();

        expect(find.text('Environment'), findsOneWidget);

        await tester.tap(find.text('Save settings'));
        await tester.pumpAndSettle();

        final environmentField = repository.savedSettings?.fieldDefinitions
            .where((field) => field.id == 'environment')
            .single;
        expect(environmentField, isNotNull);
        expect(environmentField!.name, 'Environment');
        expect(environmentField.type, 'option');
        expect(environmentField.options.map((option) => option.name).toList(), [
          'Production',
          'Staging',
          'Development',
        ]);
        expect(environmentField.applicableIssueTypeIds, ['bug']);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'simple catalog editor preloads selected component after adding a priority',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      final repository = _EditableSettingsWidgetRepository();

      Finder fieldInput(String label) => find.descendant(
        of: find.widgetWithText(TextFormField, label),
        matching: find.byType(EditableText),
      );

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        await tester.tap(_settingsTab('Priorities'));
        await tester.pumpAndSettle();
        await tester.tap(find.text('Add priority'));
        await tester.pumpAndSettle();
        await tester.enterText(fieldInput('ID'), 'ultra');
        await tester.enterText(fieldInput('Name'), 'Ultra High');
        await tester.tap(find.widgetWithText(FilledButton, 'Save'));
        await tester.pumpAndSettle();

        await tester.tap(_settingsTab('Components'));
        await tester.pumpAndSettle();
        final editAutomation = find.bySemanticsLabel(
          'Edit component Automation',
        );
        await tester.ensureVisible(editAutomation);
        await tester.tap(editAutomation, warnIfMissed: false);
        await tester.pumpAndSettle();

        expect(
          tester.widget<EditableText>(fieldInput('ID')).controller.text,
          'automation',
        );
        expect(
          tester.widget<EditableText>(fieldInput('Name')).controller.text,
          'Automation',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets('settings locale editor exposes a validated locale selector', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    final repository = _EditableSettingsWidgetRepository();

    try {
      await tester.pumpWidget(TrackStateApp(repository: repository));
      await tester.pumpAndSettle();

      await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
      await tester.pumpAndSettle();

      final localesTab = _settingsTab('Locales');
      await tester.ensureVisible(localesTab);
      await tester.tap(localesTab);
      await tester.pumpAndSettle();

      await tester.tap(find.text('Add locale'));
      await tester.pumpAndSettle();

      expect(_localeCodeDropdown(), findsOneWidget);
      expect(find.widgetWithText(TextFormField, 'Locale code'), findsNothing);

      await tester.tap(_localeCodeDropdown());
      await tester.pumpAndSettle();

      expect(find.text('fr').last, findsOneWidget);
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    }
  });

  testWidgets(
    'settings locale admin adds a locale and persists supported locales',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      final repository = _EditableSettingsWidgetRepository();

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        final localesTab = _settingsTab('Locales');
        await tester.ensureVisible(localesTab);
        await tester.tap(localesTab);
        await tester.pumpAndSettle();
        await tester.tap(find.text('Add locale'));
        await tester.pumpAndSettle();
        await _selectLocaleCode(tester, 'fr');
        await tester.tap(find.widgetWithText(FilledButton, 'Save'));
        await tester.pumpAndSettle();

        expect(find.text('fr'), findsWidgets);
        expect(find.textContaining('Missing translation.'), findsWidgets);

        await tester.tap(find.text('Save settings'));
        await tester.pumpAndSettle();

        expect(repository.savedSettings?.defaultLocale, 'en');
        expect(repository.savedSettings?.effectiveSupportedLocales, [
          'en',
          'fr',
        ]);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets('settings locale add persists immediately after dialog save', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    final repository = _EditableSettingsWidgetRepository();

    try {
      await tester.pumpWidget(TrackStateApp(repository: repository));
      await tester.pumpAndSettle();

      await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
      await tester.pumpAndSettle();

      final localesTab = _settingsTab('Locales');
      await tester.ensureVisible(localesTab);
      await tester.tap(localesTab);
      await tester.pumpAndSettle();

      expect(repository.saveProjectSettingsCalls, 0);

      await tester.tap(find.text('Add locale'));
      await tester.pumpAndSettle();
      await _selectLocaleCode(tester, 'fr');
      await tester.tap(find.widgetWithText(FilledButton, 'Save'));
      await tester.pumpAndSettle();

      expect(repository.saveProjectSettingsCalls, 1);
      expect(repository.savedSettings?.effectiveSupportedLocales, ['en', 'fr']);
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    }
  });

  testWidgets(
    'settings locale warnings stay accessible and focus in catalog order',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      final repository = _EditableSettingsWidgetRepository();
      final robot = SettingsScreenRobot(tester);

      const locale = 'fr';
      const warningText =
          'Missing translation. Using fallback "Description" from en.';

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        await robot.openSettings();
        await robot.openLocalesTab();
        await tester.tap(find.text('Add locale'));
        await tester.pumpAndSettle();
        await _selectLocaleCode(tester, locale);
        await tester.tap(find.widgetWithText(FilledButton, 'Save'));
        await tester.pumpAndSettle();

        final warningIcon = robot.localeWarningIcon(warningText);
        expect(warningIcon, findsOneWidget);
        expect(tester.getSemantics(warningIcon).label.trim(), isNotEmpty);

        final warningBackground = robot.localeWarningBackgroundColor(
          warningText,
        );
        expect(warningBackground, isNotNull);
        expect(
          contrastRatio(
            robot.localeWarningTextColor(warningText),
            warningBackground!,
          ),
          greaterThanOrEqualTo(4.5),
        );

        final focusCandidates = <String, Finder>{
          'Status To Do': robot.localeEntryFieldScope(
            locale: locale,
            id: 'todo',
            section: 'status',
          ),
          'Status Done': robot.localeEntryFieldScope(
            locale: locale,
            id: 'done',
            section: 'status',
          ),
          'Issue type Story': robot.localeEntryFieldScope(
            locale: locale,
            id: 'story',
            section: 'issueType',
          ),
          'Field Summary': robot.localeEntryFieldScope(
            locale: locale,
            id: 'summary',
            section: 'field',
          ),
          'Field Description': robot.localeEntryFieldScope(
            locale: locale,
            id: 'description',
            section: 'field',
          ),
          'Priority High': robot.localeEntryFieldScope(
            locale: locale,
            id: 'high',
            section: 'priority',
          ),
          'Component Tracker Core': robot.localeEntryFieldScope(
            locale: locale,
            id: 'tracker-core',
            section: 'component',
          ),
          'Version MVP': robot.localeEntryFieldScope(
            locale: locale,
            id: 'mvp',
            section: 'version',
          ),
          'Resolution Done': robot.localeEntryFieldScope(
            locale: locale,
            id: 'done',
            section: 'resolution',
          ),
        };

        await robot.clearFocus();
        await robot.focusLocaleTranslationField(
          locale: locale,
          id: 'todo',
          section: 'status',
        );
        final focusedOrder = <String>[];
        final firstFocused = robot.focusedLabel(focusCandidates);
        if (firstFocused != null) {
          focusedOrder.add(firstFocused);
        }
        focusedOrder.addAll(
          await robot.collectFocusOrder(candidates: focusCandidates, tabs: 24),
        );

        expect(
          focusedOrder,
          containsAllInOrder([
            'Status To Do',
            'Status Done',
            'Issue type Story',
            'Field Summary',
            'Field Description',
            'Priority High',
            'Component Tracker Core',
            'Version MVP',
            'Resolution Done',
          ]),
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'settings attachments tab persists github releases attachment storage',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      final repository = _EditableSettingsWidgetRepository();

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        final attachmentsTab = _settingsTab('Attachments');
        await tester.ensureVisible(attachmentsTab);
        await tester.tap(attachmentsTab);
        await tester.pumpAndSettle();

        await tester.tap(
          find.byKey(const ValueKey('attachment-storage-mode-field')),
        );
        await tester.pumpAndSettle();
        await tester.tap(find.text('GitHub Releases').last);
        await tester.pumpAndSettle();
        await tester.enterText(
          find.byKey(const ValueKey('attachment-release-tag-prefix-field')),
          'custom-prefix-',
        );

        await tester.tap(find.text('Save settings'));
        await tester.pumpAndSettle();

        expect(
          repository.savedSettings?.attachmentStorage.mode,
          AttachmentStorageMode.githubReleases,
        );
        expect(
          repository.savedSettings?.attachmentStorage.githubReleases?.tagPrefix,
          'custom-prefix-',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'settings locales keeps versions and resolutions visible after adding a locale',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1280, 720);
      tester.view.devicePixelRatio = 1;
      final repository = _EditableSettingsWidgetRepository();

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        final localesTab = _settingsTab('Locales');
        await tester.ensureVisible(localesTab);
        await tester.tap(localesTab);
        await tester.pumpAndSettle();
        await tester.tap(find.text('Add locale'));
        await tester.pumpAndSettle();
        await _selectLocaleCode(tester, 'fr');
        await tester.tap(find.widgetWithText(FilledButton, 'Save'));
        await tester.pumpAndSettle();

        final viewportHeight =
            tester.view.physicalSize.height / tester.view.devicePixelRatio;
        final versionsSummary = find.bySemanticsLabel(
          'Versions Locales\nsummary',
        );
        final resolutionsSummary = find.bySemanticsLabel(
          'Resolutions Locales\nsummary',
        );

        expect(versionsSummary, findsOneWidget);
        expect(resolutionsSummary, findsOneWidget);
        expect(tester.getRect(versionsSummary).top, lessThan(viewportHeight));
        expect(
          tester.getRect(resolutionsSummary).top,
          lessThan(viewportHeight),
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}

Finder _settingsTab(String label) =>
    find.bySemanticsLabel(RegExp(RegExp.escape(label))).first;

Finder _localeCodeDropdown() => find.byWidgetPredicate(
  (widget) =>
      widget is DropdownButtonFormField<String> &&
      widget.decoration.labelText == 'Locale code',
  description: 'Locale code dropdown',
);

Future<void> _selectLocaleCode(WidgetTester tester, String locale) async {
  await tester.tap(_localeCodeDropdown());
  await tester.pumpAndSettle();
  await tester.tap(find.text(locale).last);
  await tester.pumpAndSettle();
}

class _EditableSettingsWidgetRepository
    implements TrackStateRepository, ProjectSettingsRepository {
  _EditableSettingsWidgetRepository()
    : _snapshot = const DemoTrackStateRepository().loadSnapshot();

  Future<TrackerSnapshot> _snapshot;
  ProjectSettingsCatalog? savedSettings;
  int saveProjectSettingsCalls = 0;

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'local-user', displayName: 'Local User');

  @override
  Future<TrackerSnapshot> loadSnapshot() => _snapshot;

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async => const DemoTrackStateRepository().searchIssuePage(
    jql,
    startAt: startAt,
    maxResults: maxResults,
    continuationToken: continuationToken,
  );

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      const DemoTrackStateRepository().searchIssues(jql);

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Not implemented in test repository.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Not implemented in test repository.',
      );

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async => throw const TrackStateRepositoryException(
    'Not implemented in test repository.',
  );

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async => issue;

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue;

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async => issue;

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
    String? sourceName,
  }) async => issue;

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => const <IssueHistoryEntry>[];

  @override
  Future<TrackerSnapshot> saveProjectSettings(
    ProjectSettingsCatalog settings,
  ) async {
    saveProjectSettingsCalls += 1;
    savedSettings = settings;
    final current = await _snapshot;
    final updated = TrackerSnapshot(
      project: ProjectConfig(
        key: current.project.key,
        name: current.project.name,
        repository: current.project.repository,
        branch: current.project.branch,
        defaultLocale: settings.defaultLocale,
        supportedLocales: settings.effectiveSupportedLocales,
        issueTypeDefinitions: settings.issueTypeDefinitions,
        statusDefinitions: settings.statusDefinitions,
        fieldDefinitions: settings.fieldDefinitions,
        workflowDefinitions: settings.workflowDefinitions,
        priorityDefinitions: settings.priorityDefinitions,
        versionDefinitions: settings.versionDefinitions,
        componentDefinitions: settings.componentDefinitions,
        resolutionDefinitions: settings.resolutionDefinitions,
        attachmentStorage: settings.attachmentStorage,
      ),
      issues: current.issues,
      repositoryIndex: current.repositoryIndex,
      loadWarnings: current.loadWarnings,
    );
    _snapshot = Future<TrackerSnapshot>.value(updated);
    return updated;
  }
}
