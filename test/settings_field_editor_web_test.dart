@TestOn('browser')
library;

import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'browser field editor keeps reserved and saved custom field values visible',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      final repository = _EditableSettingsBrowserRepository();

      try {
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        await tester.tap(_settingsTab('Fields'));
        await tester.pumpAndSettle();

        await tester.tap(_rowAction('Summary', 'Edit'));
        await tester.pumpAndSettle();

        expect(_labeledTextField('ID'), findsOneWidget);
        expect(_labeledTextField('Name'), findsOneWidget);
        expect(
          tester.widget<EditableText>(_labeledEditableText('ID')).controller.text,
          'summary',
        );
        expect(
          tester.widget<EditableText>(_labeledEditableText('Name')).controller.text,
          'Summary',
        );

        await tester.tap(find.widgetWithText(TextButton, 'Cancel'));
        await tester.pumpAndSettle();

        await tester.tap(find.text('Add field'));
        await tester.pumpAndSettle();

        await tester.enterText(_labeledEditableText('ID'), 'environment');
        await tester.enterText(_labeledEditableText('Name'), 'Environment');
        await tester.tap(find.byType(DropdownButtonFormField<String>));
        await tester.pumpAndSettle();
        await tester.tap(find.text('option').last);
        await tester.pumpAndSettle();
        await tester.enterText(
          _labeledEditableText('Options'),
          'Production, Staging, Development',
        );
        await tester.tap(find.widgetWithText(FilterChip, 'Bug'));
        await tester.pumpAndSettle();

        await tester.tap(find.widgetWithText(FilledButton, 'Save'));
        await tester.pumpAndSettle();

        expect(find.text('Environment'), findsOneWidget);

        await tester.tap(find.text('Save settings'));
        await tester.pumpAndSettle();

        final environmentEdit = _rowAction('Environment', 'Edit');
        await tester.ensureVisible(environmentEdit);
        await tester.tap(environmentEdit, warnIfMissed: false);
        await tester.pumpAndSettle();

        expect(_labeledTextField('ID'), findsOneWidget);
        expect(_labeledTextField('Name'), findsOneWidget);
        expect(_labeledTextField('Options'), findsOneWidget);
        expect(
          tester.widget<EditableText>(_labeledEditableText('ID')).controller.text,
          'environment',
        );
        expect(
          tester.widget<EditableText>(_labeledEditableText('Name')).controller.text,
          'Environment',
        );
        expect(
          tester.widget<EditableText>(_labeledEditableText('Options')).controller.text,
          'Production, Staging, Development',
        );
        expect(
          tester.widget<FilterChip>(find.widgetWithText(FilterChip, 'Bug')).selected,
          isTrue,
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

Finder _rowAction(String title, String actionLabel) => find.descendant(
  of: find.ancestor(of: find.text(title), matching: find.byType(ListTile)),
  matching: find.widgetWithText(TextButton, actionLabel),
);

Finder _labeledEditableText(String label) => find.descendant(
  of: find.byWidgetPredicate(
    (widget) => widget is InputDecorator && widget.decoration.labelText == label,
    description: 'input decorator labeled $label',
  ),
  matching: find.byType(EditableText),
);

Finder _labeledTextField(String label) => find.byWidgetPredicate(
  (widget) => widget is TextField && widget.decoration?.labelText == label,
  description: 'TextField labeled $label',
);

class _EditableSettingsBrowserRepository
    implements TrackStateRepository, ProjectSettingsRepository {
  _EditableSettingsBrowserRepository()
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
