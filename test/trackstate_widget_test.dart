import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../testing/components/factories/testing_dependencies.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('dashboard renders accessible navigation and actions', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      await tester.pumpWidget(
        const TrackStateApp(repository: DemoTrackStateRepository()),
      );
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel(RegExp('TrackState\\.AI')), findsWidgets);
      expect(find.bySemanticsLabel(RegExp('Dashboard')), findsWidgets);
      expect(find.bySemanticsLabel(RegExp('Connect GitHub')), findsWidgets);
      expect(find.bySemanticsLabel(RegExp('Synced with Git')), findsWidgets);
      expect(find.textContaining('Platform Foundation'), findsWidgets);
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      semantics.dispose();
    }
  });

  testWidgets('board navigation displays kanban columns and issue cards', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      await tester.pumpWidget(
        const TrackStateApp(repository: DemoTrackStateRepository()),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.bySemanticsLabel(RegExp('Board')).first);
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel(RegExp('To Do column')), findsOneWidget);
      expect(
        find.bySemanticsLabel(RegExp('In Progress column')),
        findsOneWidget,
      );
      expect(
        find.bySemanticsLabel(
          RegExp('Open TRACK-12 Implement Git sync service'),
        ),
        findsOneWidget,
      );
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      semantics.dispose();
    }
  });

  testWidgets('dragging a board card moves it to another status', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    try {
      await tester.pumpWidget(
        const TrackStateApp(repository: DemoTrackStateRepository()),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.bySemanticsLabel(RegExp('Board')).first);
      await tester.pumpAndSettle();

      final card = find.byWidgetPredicate(
        (widget) => widget is Draggable && widget.data is TrackStateIssue,
      );
      final doneColumn = find.bySemanticsLabel(RegExp('Done column'));

      await tester.timedDragFrom(
        tester.getCenter(card.at(1)),
        tester.getCenter(doneColumn) - tester.getCenter(card.at(1)),
        const Duration(milliseconds: 500),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('TRACK-12 moved locally'), findsOneWidget);
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    }
  });

  testWidgets('theme toggle switches to dark mode', (tester) async {
    final semantics = tester.ensureSemantics();
    try {
      await tester.pumpWidget(
        const TrackStateApp(repository: DemoTrackStateRepository()),
      );
      await tester.pumpAndSettle();

      final context = tester.element(find.byType(Scaffold).first);
      expect(Theme.of(context).brightness, Brightness.light);

      await tester.tap(find.bySemanticsLabel(RegExp('Dark theme')));
      await tester.pumpAndSettle();

      final darkContext = tester.element(find.byType(Scaffold).first);
      expect(Theme.of(darkContext).brightness, Brightness.dark);
    } finally {
      semantics.dispose();
    }
  });

  testWidgets('search screen appends results through the load more action', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      await tester.pumpWidget(
        TrackStateApp(
          repository: DemoTrackStateRepository(
            snapshot: _searchPaginationSnapshot(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.bySemanticsLabel(RegExp('JQL Search')).first);
      await tester.pumpAndSettle();

      expect(find.text('Showing 6 of 8 issues'), findsOneWidget);
      expect(find.bySemanticsLabel('Load more issues'), findsOneWidget);
      expect(find.text('Paged issue 8'), findsNothing);

      await tester.tap(find.bySemanticsLabel('Load more issues'));
      await tester.pumpAndSettle();

      expect(find.text('Paged issue 8'), findsOneWidget);
      expect(find.bySemanticsLabel('Load more issues'), findsNothing);
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      semantics.dispose();
    }
  });

  testWidgets(
    'issue detail exposes detail, comments, attachments, and history tabs',
    (tester) async {
      final semantics = tester.ensureSemantics();
      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;
        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Board')).first);
        await tester.pumpAndSettle();
        await tester.tap(
          find.bySemanticsLabel(
            RegExp('Open TRACK-12 Implement Git sync service'),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.bySemanticsLabel(RegExp('Detail')), findsWidgets);
        expect(find.bySemanticsLabel(RegExp('Comments')), findsWidgets);
        expect(find.bySemanticsLabel(RegExp('Attachments')), findsWidgets);
        expect(find.bySemanticsLabel(RegExp('History')), findsWidgets);
        expect(find.text('Description'), findsOneWidget);

        await tester.tap(find.bySemanticsLabel(RegExp('Attachments')).first);
        await tester.pumpAndSettle();
        expect(find.text('sync-sequence.svg'), findsOneWidget);

        await tester.tap(find.bySemanticsLabel(RegExp('History')).first);
        await tester.pumpAndSettle();
        expect(
          find.textContaining('Updated description on TRACK-12'),
          findsOneWidget,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'edit issue dialog exposes metadata, hierarchy, and workflow controls',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      try {
        await screen.pump(const _EditIssueFieldsLocalRuntimeRepository());

        await screen.openSection('Search');
        await screen.openIssue('TRACK-12', 'Implement Git sync service');
        await screen.tapIssueDetailAction('TRACK-12', label: 'Edit');

        expect(await screen.isTextFieldVisible('Summary'), isTrue);
        expect(await screen.isTextFieldVisible('Description'), isTrue);
        expect(await screen.isDropdownFieldVisible('Priority'), isTrue);
        expect(await screen.isDropdownFieldVisible('Assignee'), isTrue);
        expect(await screen.isDropdownFieldVisible('Epic'), isTrue);
        expect(await screen.isDropdownFieldVisible('Status'), isTrue);
        await screen.expectTextVisible('Components');
        await screen.expectTextVisible('Fix versions');

        await screen.selectDropdownOption('Status', optionText: 'Done');

        expect(await screen.isDropdownFieldVisible('Resolution'), isTrue);
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
  );

  testWidgets('local runtime shows repository access instead of GitHub auth', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    try {
      await tester.pumpWidget(
        TrackStateApp(repository: _LocalRuntimeRepository()),
      );
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel(RegExp('Local Git')), findsWidgets);
      expect(find.bySemanticsLabel(RegExp('Connect GitHub')), findsNothing);
      expect(find.text('LU'), findsOneWidget);

      await tester.tap(find.bySemanticsLabel(RegExp('Local Git')).first);
      await tester.pumpAndSettle();

      expect(find.text('Local Git runtime'), findsOneWidget);
      expect(
        find.textContaining('GitHub tokens are not used in this runtime'),
        findsOneWidget,
      );
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    }
  });

  testWidgets(
    'local runtime exposes a single dialog-based Create issue flow in expanded and compact layouts',
    (tester) async {
      final semantics = tester.ensureSemantics();
      RegExp exactLabel(String label) => RegExp('^${RegExp.escape(label)}\$');

      Finder byExactSemanticsLabel(String label) => find.byWidgetPredicate(
        (widget) =>
            widget is Semantics &&
            widget.properties.label != null &&
            exactLabel(label).hasMatch(widget.properties.label!),
      );
      Future<void> pumpLocalRuntime(Size size) async {
        tester.view.physicalSize = size;
        tester.view.devicePixelRatio = 1;
        await tester.pumpWidget(
          TrackStateApp(repository: _LocalRuntimeRepository()),
        );
        await tester.pumpAndSettle();
      }

      Future<void> expectCreateIssueFlowForSection(String sectionLabel) async {
        await tester.tap(byExactSemanticsLabel(sectionLabel).first);
        await tester.pumpAndSettle();

        final createIssue = byExactSemanticsLabel('Create issue');
        expect(
          createIssue,
          findsOneWidget,
          reason:
              'Expected $sectionLabel to expose exactly one reachable Create issue entry point in Local Git mode.',
        );
        expect(find.byType(Dialog), findsNothing);
        expect(byExactSemanticsLabel('Summary'), findsNothing);

        await tester.tap(createIssue);
        await tester.pumpAndSettle();

        expect(find.byType(Dialog), findsOneWidget);
        expect(byExactSemanticsLabel('Summary'), findsOneWidget);
        expect(byExactSemanticsLabel('Description'), findsOneWidget);
        expect(byExactSemanticsLabel('Assignee'), findsOneWidget);
        expect(byExactSemanticsLabel('Labels'), findsOneWidget);
        expect(byExactSemanticsLabel('Save'), findsOneWidget);
        expect(byExactSemanticsLabel('Cancel'), findsOneWidget);

        await tester.ensureVisible(byExactSemanticsLabel('Cancel'));
        await tester.tap(byExactSemanticsLabel('Cancel'), warnIfMissed: false);
        await tester.pumpAndSettle();
        expect(find.byType(Dialog), findsNothing);
        expect(byExactSemanticsLabel('Summary'), findsNothing);
      }

      try {
        for (final size in const [Size(1440, 960), Size(760, 960)]) {
          await pumpLocalRuntime(size);
          for (final section in const [
            'Dashboard',
            'Board',
            'JQL Search',
            'Hierarchy',
          ]) {
            await expectCreateIssueFlowForSection(section);
          }
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'contextual child-create entry points prefill hierarchy-aware fields',
    (tester) async {
      final semantics = tester.ensureSemantics();
      RegExp exactLabel(String label) => RegExp('^${RegExp.escape(label)}\$');

      Finder byExactSemanticsLabel(String label) => find.byWidgetPredicate(
        (widget) =>
            widget is Semantics &&
            widget.properties.label != null &&
            exactLabel(label).hasMatch(widget.properties.label!),
      );
      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;
        await tester.pumpWidget(
          TrackStateApp(repository: _LocalRuntimeRepository()),
        );
        await tester.pumpAndSettle();

        await tester.tap(byExactSemanticsLabel('JQL Search').first);
        await tester.pumpAndSettle();

        await tester.tap(byExactSemanticsLabel('Create child issue').first);
        await tester.pumpAndSettle();

        expect(find.byType(Dialog), findsOneWidget);
        expect(find.text('Sub-task'), findsWidgets);

        await tester.ensureVisible(byExactSemanticsLabel('Cancel').first);
        await tester.tap(
          byExactSemanticsLabel('Cancel').first,
          warnIfMissed: false,
        );
        await tester.pumpAndSettle();

        await tester.tap(byExactSemanticsLabel('Hierarchy').first);
        await tester.pumpAndSettle();
        await tester.tap(
          find.bySemanticsLabel(RegExp('^Create child issue for TRACK-')).first,
        );
        await tester.pumpAndSettle();

        expect(find.byType(Dialog), findsOneWidget);
        expect(find.text('Story'), findsWidgets);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'create issue overlay stays open and preserves draft while switching tracker sections',
    (tester) async {
      final semantics = tester.ensureSemantics();
      const preservedSummary = 'Refactor Persistence Verification';

      RegExp exactLabel(String label) => RegExp('^${RegExp.escape(label)}\$');

      Finder byExactSemanticsLabel(String label) => find.byWidgetPredicate(
        (widget) =>
            widget is Semantics &&
            widget.properties.label != null &&
            exactLabel(label).hasMatch(widget.properties.label!),
      );

      Finder summaryField() => find.byWidgetPredicate(
        (widget) =>
            widget is TextField && widget.decoration?.labelText == 'Summary',
      );

      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;
        await tester.pumpWidget(
          TrackStateApp(repository: _LocalRuntimeRepository()),
        );
        await tester.pumpAndSettle();

        await tester.tap(byExactSemanticsLabel('Create issue').first);
        await tester.pumpAndSettle();

        expect(find.byType(Dialog), findsOneWidget);
        expect(summaryField(), findsOneWidget);

        await tester.enterText(summaryField(), preservedSummary);
        await tester.pump();
        expect(
          tester.widget<TextField>(summaryField()).controller?.text,
          preservedSummary,
        );

        await tester.tap(byExactSemanticsLabel('Board').first);
        await tester.pumpAndSettle();

        expect(
          find.text('Drag-ready workflow columns backed by Git files'),
          findsOneWidget,
        );
        expect(find.byType(Dialog), findsOneWidget);
        expect(summaryField(), findsOneWidget);
        expect(
          tester.widget<TextField>(summaryField()).controller?.text,
          preservedSummary,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'create issue form renders configured custom fields in local mode',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      try {
        await screen.pump(const _CustomCreateFieldsLocalRuntimeRepository());

        final createIssueSection = await screen.openCreateIssueFlow();
        await screen.expectCreateIssueFormVisible(
          createIssueSection: createIssueSection,
        );

        expect(await screen.isTextFieldVisible('Solution'), isTrue);
        expect(await screen.isTextFieldVisible('Acceptance Criteria'), isTrue);
        expect(await screen.isTextFieldVisible('Diagrams'), isTrue);
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
  );

  testWidgets('save failure banner exposes a dismiss action in local mode', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    final screen = defaultTestingDependencies.createTrackStateAppScreen(tester);
    try {
      await screen.pump(const _FailingLocalRuntimeRepository());

      await screen.openSection('Search');
      await screen.openIssue('TRACK-12', 'Implement Git sync service');
      await screen.tapIssueDetailAction('TRACK-12', label: 'Edit');
      await screen.enterIssueDescription(
        'TRACK-12',
        label: 'Description',
        text: 'Updated description for dismiss regression coverage.',
      );
      await screen.tapIssueDetailAction('TRACK-12', label: 'Save');

      await screen.expectMessageBannerContains('Save failed:');
      await screen.expectMessageBannerContains('commit');
      await screen.expectMessageBannerContains('stash');
      await screen.expectMessageBannerContains('clean');

      expect(
        await screen.dismissMessageBannerContaining('Save failed:'),
        isTrue,
      );
    } finally {
      screen.resetView();
      semantics.dispose();
    }
  });
}

class _LocalRuntimeRepository implements TrackStateRepository {
  const _LocalRuntimeRepository();

  static const _demoRepository = DemoTrackStateRepository();

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'local-user', displayName: 'Local User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async =>
      _demoRepository.loadSnapshot();

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) => _demoRepository.searchIssuePage(
    jql,
    startAt: startAt,
    maxResults: maxResults,
    continuationToken: continuationToken,
  );

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      _demoRepository.searchIssues(jql);

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Local runtime widget repository does not support issue archiving.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Local runtime widget repository does not support issue deletion.',
      );

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    throw UnimplementedError('Issue creation is not implemented.');
  }

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async =>
      issue.copyWith(description: description.trim(), updatedLabel: 'just now');

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(status: status, updatedLabel: 'just now');

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async => issue;

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => const <IssueHistoryEntry>[];

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async => issue;
}

class _FailingLocalRuntimeRepository implements TrackStateRepository {
  const _FailingLocalRuntimeRepository();

  static const _demoRepository = DemoTrackStateRepository();

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'local-user', displayName: 'Local User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async =>
      _demoRepository.loadSnapshot();

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) => _demoRepository.searchIssuePage(
    jql,
    startAt: startAt,
    maxResults: maxResults,
    continuationToken: continuationToken,
  );

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      _demoRepository.searchIssues(jql);

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async {
    throw const TrackStateRepositoryException(
      'Cannot archive DEMO/DEMO-1/main.md because it has staged or unstaged local changes. '
      'commit, stash, or clean those local changes before trying again.',
    );
  }

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    throw const TrackStateRepositoryException(
      'Cannot save DEMO/DEMO-1/main.md because it has staged or unstaged local changes. '
      'commit, stash, or clean those local changes before trying again.',
    );
  }

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async {
    throw const TrackStateRepositoryException(
      'Cannot save DEMO/DEMO-1/main.md because it has staged or unstaged local changes. '
      'commit, stash, or clean those local changes before trying again.',
    );
  }

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async {
    throw const TrackStateRepositoryException(
      'Cannot delete DEMO/DEMO-1/main.md because it has staged or unstaged local changes. '
      'commit, stash, or clean those local changes before trying again.',
    );
  }

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(status: status, updatedLabel: 'just now');

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async {
    throw const TrackStateRepositoryException(
      'Cannot save DEMO/DEMO-1/main.md because it has staged or unstaged local changes. '
      'commit, stash, or clean those local changes before trying again.',
    );
  }

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => const <IssueHistoryEntry>[];

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async {
    throw const TrackStateRepositoryException(
      'Cannot save DEMO/DEMO-1/main.md because it has staged or unstaged local changes. '
      'commit, stash, or clean those local changes before trying again.',
    );
  }
}

class _CustomCreateFieldsLocalRuntimeRepository
    implements TrackStateRepository {
  const _CustomCreateFieldsLocalRuntimeRepository();

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'local-user', displayName: 'Local User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final snapshot = await const DemoTrackStateRepository().loadSnapshot();
    return TrackerSnapshot(
      project: ProjectConfig(
        key: snapshot.project.key,
        name: snapshot.project.name,
        repository: snapshot.project.repository,
        branch: snapshot.project.branch,
        defaultLocale: snapshot.project.defaultLocale,
        issueTypeDefinitions: snapshot.project.issueTypeDefinitions,
        statusDefinitions: snapshot.project.statusDefinitions,
        fieldDefinitions: const [
          TrackStateFieldDefinition(
            id: 'summary',
            name: 'Summary',
            type: 'string',
            required: true,
            localizedLabels: {'en': 'Summary'},
          ),
          TrackStateFieldDefinition(
            id: 'description',
            name: 'Description',
            type: 'markdown',
            required: false,
            localizedLabels: {'en': 'Description'},
          ),
          TrackStateFieldDefinition(
            id: 'solution',
            name: 'Solution',
            type: 'markdown',
            required: false,
            localizedLabels: {'en': 'Solution'},
          ),
          TrackStateFieldDefinition(
            id: 'acceptanceCriteria',
            name: 'Acceptance Criteria',
            type: 'markdown',
            required: false,
            localizedLabels: {'en': 'Acceptance Criteria'},
          ),
          TrackStateFieldDefinition(
            id: 'diagrams',
            name: 'Diagrams',
            type: 'markdown',
            required: false,
            localizedLabels: {'en': 'Diagrams'},
          ),
        ],
        priorityDefinitions: snapshot.project.priorityDefinitions,
        versionDefinitions: snapshot.project.versionDefinitions,
        componentDefinitions: snapshot.project.componentDefinitions,
        resolutionDefinitions: snapshot.project.resolutionDefinitions,
      ),
      issues: snapshot.issues,
      repositoryIndex: snapshot.repositoryIndex,
    );
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    final issues = (await loadSnapshot()).issues;
    final total = issues.length;
    final boundedStartAt = startAt.clamp(0, total);
    final endAt = (boundedStartAt + maxResults).clamp(0, total);
    return TrackStateIssueSearchPage(
      issues: issues.sublist(boundedStartAt, endAt),
      startAt: boundedStartAt,
      maxResults: maxResults,
      total: total,
      nextStartAt: endAt < total ? endAt : null,
      nextPageToken: endAt < total ? 'offset:$endAt' : null,
    );
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (await loadSnapshot()).issues;

  @override
  Future<TrackStateIssue> archiveIssue(
    TrackStateIssue issue,
  ) async => throw const TrackStateRepositoryException(
    'Custom create-field widget repository does not support issue archiving.',
  );

  @override
  Future<DeletedIssueTombstone> deleteIssue(
    TrackStateIssue issue,
  ) async => throw const TrackStateRepositoryException(
    'Custom create-field widget repository does not support issue deletion.',
  );

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    throw UnimplementedError('Issue creation is not implemented.');
  }

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async =>
      issue.copyWith(description: description.trim(), updatedLabel: 'just now');

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(status: status, updatedLabel: 'just now');

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async => issue;

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => const <IssueHistoryEntry>[];

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async => issue;
}

class _EditIssueFieldsLocalRuntimeRepository extends _LocalRuntimeRepository {
  const _EditIssueFieldsLocalRuntimeRepository();

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final snapshot = await super.loadSnapshot();
    return TrackerSnapshot(
      project: ProjectConfig(
        key: snapshot.project.key,
        name: snapshot.project.name,
        repository: snapshot.project.repository,
        branch: snapshot.project.branch,
        defaultLocale: snapshot.project.defaultLocale,
        issueTypeDefinitions: snapshot.project.issueTypeDefinitions,
        statusDefinitions: snapshot.project.statusDefinitions,
        fieldDefinitions: snapshot.project.fieldDefinitions,
        priorityDefinitions: snapshot.project.priorityDefinitions,
        versionDefinitions: snapshot.project.versionDefinitions,
        componentDefinitions: snapshot.project.componentDefinitions,
        resolutionDefinitions: const [
          TrackStateConfigEntry(id: 'done', name: 'Done'),
          TrackStateConfigEntry(id: 'wont-fix', name: "Won't Fix"),
        ],
      ),
      issues: snapshot.issues,
      repositoryIndex: snapshot.repositoryIndex,
      loadWarnings: snapshot.loadWarnings,
    );
  }
}

TrackerSnapshot _searchPaginationSnapshot() {
  final issues = [
    for (var index = 1; index <= 8; index += 1)
      TrackStateIssue(
        key: 'TRACK-$index',
        project: 'TRACK',
        issueType: IssueType.story,
        issueTypeId: 'story',
        status: IssueStatus.inProgress,
        statusId: 'in-progress',
        priority: IssuePriority.medium,
        priorityId: 'medium',
        summary: 'Paged issue $index',
        description: 'Search result $index',
        assignee: 'user-$index',
        reporter: 'demo-user',
        labels: const ['paged'],
        components: const [],
        fixVersionIds: const [],
        watchers: const [],
        customFields: const {},
        parentKey: null,
        epicKey: null,
        parentPath: null,
        epicPath: null,
        progress: 0,
        updatedLabel: 'just now',
        acceptanceCriteria: const ['Visible in search pagination'],
        comments: const [],
        links: const [],
        attachments: const [],
        isArchived: false,
        storagePath: 'TRACK/TRACK-$index/main.md',
        rawMarkdown: '',
      ),
  ];
  return TrackerSnapshot(
    project: const ProjectConfig(
      key: 'TRACK',
      name: 'TrackState',
      repository: 'trackstate/trackstate',
      branch: 'main',
      defaultLocale: 'en',
      issueTypeDefinitions: [TrackStateConfigEntry(id: 'story', name: 'Story')],
      statusDefinitions: [
        TrackStateConfigEntry(id: 'in-progress', name: 'In Progress'),
      ],
      fieldDefinitions: [
        TrackStateFieldDefinition(
          id: 'summary',
          name: 'Summary',
          type: 'string',
          required: true,
        ),
      ],
      priorityDefinitions: [
        TrackStateConfigEntry(id: 'medium', name: 'Medium'),
      ],
    ),
    issues: issues,
  );
}
