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
        expect(byExactSemanticsLabel('Save'), findsOneWidget);
        expect(byExactSemanticsLabel('Cancel'), findsOneWidget);

        await tester.tap(byExactSemanticsLabel('Cancel'));
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
}
