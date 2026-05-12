import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

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
        expect(capturedError, isA<StateError>());
        expect(openAttempts, 1);

        await tester.tap(field('Repository Path'));
        await tester.pump();
        FocusManager.instance.primaryFocus?.unfocus();
        await tester.pumpAndSettle();

        expect(openAttempts, 2);
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
        expect(find.widgetWithText(Tab, 'Statuses'), findsOneWidget);
        expect(find.widgetWithText(Tab, 'Workflows'), findsOneWidget);
        expect(find.widgetWithText(Tab, 'Issue Types'), findsOneWidget);
        expect(find.widgetWithText(Tab, 'Fields'), findsOneWidget);
        expect(find.widgetWithText(Tab, 'Priorities'), findsOneWidget);
        expect(find.widgetWithText(Tab, 'Components'), findsOneWidget);
        expect(find.widgetWithText(Tab, 'Versions'), findsOneWidget);
        expect(find.widgetWithText(Tab, 'Locales'), findsOneWidget);

        await tester.tap(find.widgetWithText(Tab, 'Fields'));
        await tester.pumpAndSettle();
        expect(find.bySemanticsLabel('Delete field Summary'), findsNothing);

        await tester.tap(find.widgetWithText(Tab, 'Statuses'));
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

        final localesTab = find.widgetWithText(Tab, 'Locales');
        await tester.ensureVisible(localesTab);
        await tester.tap(localesTab);
        await tester.pumpAndSettle();
        await tester.tap(find.text('Add locale'));
        await tester.pumpAndSettle();
        await tester.enterText(
          find.widgetWithText(TextFormField, 'Locale code'),
          'fr',
        );
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

        final localesTab = find.widgetWithText(Tab, 'Locales');
        await tester.ensureVisible(localesTab);
        await tester.tap(localesTab);
        await tester.pumpAndSettle();
        await tester.tap(find.text('Add locale'));
        await tester.pumpAndSettle();
        await tester.enterText(
          find.widgetWithText(TextFormField, 'Locale code'),
          'fr',
        );
        await tester.tap(find.widgetWithText(FilledButton, 'Save'));
        await tester.pumpAndSettle();

        final viewportHeight =
            tester.view.physicalSize.height / tester.view.devicePixelRatio;
        final versionsSummary = find.bySemanticsLabel('Versions Locales\nsummary');
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

class _EditableSettingsWidgetRepository
    implements TrackStateRepository, ProjectSettingsRepository {
  _EditableSettingsWidgetRepository()
    : _snapshot = const DemoTrackStateRepository().loadSnapshot();

  Future<TrackerSnapshot> _snapshot;
  ProjectSettingsCatalog? savedSettings;

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
      ),
      issues: current.issues,
      repositoryIndex: current.repositoryIndex,
      loadWarnings: current.loadWarnings,
    );
    _snapshot = Future<TrackerSnapshot>.value(updated);
    return updated;
  }
}
