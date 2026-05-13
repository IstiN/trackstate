import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/services/attachment_picker.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../testing/components/factories/testing_dependencies.dart';
import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';

const String _hostedReleaseProjectJson = '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config",
  "attachmentStorage": {
    "mode": "github-releases",
    "githubReleases": {
      "tagPrefix": "widget-test-assets-"
    }
  }
}
''';

const RepositoryPermission _hostedReleaseUploadPermission = RepositoryPermission(
  canRead: true,
  canWrite: true,
  isAdmin: false,
  canCreateBranch: true,
  canManageAttachments: true,
  attachmentUploadMode: AttachmentUploadMode.full,
  supportsReleaseAttachmentWrites: true,
  canCheckCollaborators: false,
);

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
    'first hosted load keeps the shell visible and shows bootstrap-backed placeholders',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      try {
        final snapshot = await const DemoTrackStateRepository().loadSnapshot();
        final repository = _BootstrapLoadingRepository(
          snapshot: _hostedBootstrapSnapshot(snapshot),
        );
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pump();
        await tester.pump();

        expect(find.bySemanticsLabel(RegExp('Dashboard')), findsWidgets);
        expect(
          find.bySemanticsLabel(RegExp('Dashboard\\s+Loading')),
          findsOneWidget,
        );

        await tester.tap(find.text('JQL Search').first);
        await tester.pump();

        expect(find.text('Loading...'), findsWidgets);
        expect(find.text('TRACK-12'), findsWidgets);
        expect(find.text('Implement Git sync service'), findsWidgets);
        expect(find.text('Description'), findsNothing);

        await tester.tap(find.text('Comments').first);
        await tester.pump();
        expect(find.text('Loading...'), findsWidgets);

        await tester.tap(find.text('Attachments').first);
        await tester.pump();
        expect(find.text('Loading...'), findsWidgets);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'hosted dashboard and board loading hints clear after initial search hydration completes',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      try {
        final snapshot = await const DemoTrackStateRepository().loadSnapshot();
        final repository = _BootstrapLoadingRepository(
          snapshot: _hostedBootstrapSnapshot(snapshot),
        );
        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pump();
        await tester.pump();

        expect(
          find.bySemanticsLabel(RegExp('Dashboard\\s+Loading')),
          findsOneWidget,
        );

        repository.completeInitialSearch();
        await tester.pumpAndSettle();

        expect(
          find.bySemanticsLabel(RegExp('Dashboard\\s+Loading')),
          findsNothing,
        );

        await tester.tap(find.bySemanticsLabel(RegExp('Board')).first);
        await tester.pumpAndSettle();

        expect(find.bySemanticsLabel(RegExp('Board\\s+Loading')), findsNothing);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'hosted search keeps bootstrap rows visible after the initial search fails',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      try {
        final snapshot = await const DemoTrackStateRepository().loadSnapshot();
        await tester.pumpWidget(
          TrackStateApp(
            repository: _FailingBootstrapSearchRepository(
              snapshot: _hostedBootstrapSnapshot(snapshot),
            ),
          ),
        );
        await tester.pump();
        await tester.pumpAndSettle();

        await tester.tap(find.text('JQL Search').first);
        await tester.pumpAndSettle();

        expect(
          find.bySemanticsLabel(RegExp('JQL Search\\s+Loading')),
          findsNothing,
        );
        expect(find.text('No issues match this query'), findsNothing);
        expect(find.text('TRACK-12'), findsWidgets);
        expect(find.text('Implement Git sync service'), findsWidgets);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

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

        await tester.tap(find.text('History').first);
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
    'issue detail keeps deferred load failures inside the active tab with a local retry action',
    (tester) async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'write-enabled-token',
      });
      final semantics = tester.ensureSemantics();
      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;
        await tester.pumpWidget(
          TrackStateApp(
            repository: ReactiveIssueDetailTrackStateRepository(
              failingTextPaths: {'TRACK-12/main.md'},
            ),
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('JQL Search')).first);
        await tester.pumpAndSettle();
        await tester.tap(
          find
              .bySemanticsLabel(
                RegExp('Open TRACK-12 Implement Git sync service'),
              )
              .first,
        );
        await tester.pumpAndSettle();

        expect(find.text('Detail'), findsWidgets);
        expect(
          find.textContaining('Deferred read failed for TRACK-12/main.md'),
          findsOneWidget,
        );
        expect(find.text('Retry'), findsOneWidget);
        expect(find.bySemanticsLabel('Comments'), findsWidgets);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'hosted issue detail keeps the header visible while tab hydration loads in place',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      try {
        await tester.pumpWidget(
          TrackStateApp(repository: _SlowHistoryReactiveRepository()),
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

        expect(find.text('Implement Git sync service'), findsWidgets);

        await tester.ensureVisible(find.text('History').first);
        await tester.tap(find.text('History').first);
        await tester.pump();

        expect(find.text('Loading...'), findsOneWidget);
        await tester.pump(const Duration(milliseconds: 20));
        await tester.pumpAndSettle();
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
        expect(await screen.isTextFieldVisible('Assignee'), isTrue);
        expect(await screen.isDropdownFieldVisible('Assignee'), isFalse);
        expect(await screen.isDropdownFieldVisible('Epic'), isTrue);
        expect(await screen.isDropdownFieldVisible('Status'), isTrue);
        await screen.expectTextVisible('Components');
        await screen.expectTextVisible('Fix versions');

        await screen.enterLabeledTextField('Assignee', text: 'fresh-teammate');
        await screen.selectDropdownOption('Status', optionText: 'Done');
        await screen.selectDropdownOption(
          'Resolution',
          optionText: "Won't Fix",
        );
        await screen.tapVisibleControl('Save');

        await screen.expectIssueDetailText('TRACK-12', 'fresh-teammate');
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'edit issue dialog blocks done transitions until a resolution is selected',
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

        await screen.selectDropdownOption('Status', optionText: 'Done');
        await screen.tapVisibleControl('Save');

        expect(
          find.text('Resolution is required for this transition.'),
          findsOneWidget,
        );
        expect(await screen.isDropdownFieldVisible('Resolution'), isTrue);
        expect(await screen.isTextFieldVisible('Summary'), isTrue);
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
  );

  testWidgets('edit issue dialog localizes component and fix version chips', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    final screen = defaultTestingDependencies.createTrackStateAppScreen(tester);
    try {
      await screen.pump(
        const _LocalizedEditIssueFieldsLocalRuntimeRepository(),
      );

      await screen.openSection('Search');
      await screen.openIssue('TRACK-12', 'Implement Git sync service');
      await screen.tapIssueDetailAction('TRACK-12', label: 'Edit');

      await screen.expectTextVisible('Tracker Core Localized');
      await screen.expectTextVisible('MVP Release');
    } finally {
      screen.resetView();
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
    'attachments tab lets users choose and upload files from issue detail',
    (tester) async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'write-enabled-token',
      });
      final semantics = tester.ensureSemantics();

      Future<PickedAttachment?> pickAttachment() async => PickedAttachment(
        name: 'release notes.pdf',
        bytes: Uint8List.fromList(<int>[1, 2, 3, 4]),
      );

      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;
        await tester.pumpWidget(
          TrackStateApp(
            repository: ReactiveIssueDetailTrackStateRepository(
              permission: _hostedReleaseUploadPermission,
              textFixtures: const <String, String>{
                'project.json': _hostedReleaseProjectJson,
              },
            ),
            attachmentPicker: pickAttachment,
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('JQL Search')).first);
        await tester.pumpAndSettle();
        await tester.tap(
          find
              .bySemanticsLabel(
                RegExp('Open TRACK-12 Implement Git sync service'),
              )
              .first,
        );
        await tester.pumpAndSettle();
        await tester.tap(find.bySemanticsLabel(RegExp('Attachments')).first);
        await tester.pumpAndSettle();

        final chooseAttachmentSemantics = find.bySemanticsLabel(
          'Choose attachment',
        );
        final uploadAttachmentSemantics = find.bySemanticsLabel(
          'Upload attachment',
        );
        final chooseAttachmentButton = find.widgetWithText(
          OutlinedButton,
          'Choose attachment',
        );
        final uploadAttachmentButton = find.widgetWithText(
          FilledButton,
          'Upload attachment',
        );

        expect(chooseAttachmentSemantics, findsOneWidget);
        expect(uploadAttachmentSemantics, findsOneWidget);
        expect(chooseAttachmentButton, findsOneWidget);
        expect(uploadAttachmentButton, findsOneWidget);
        expect(
          tester.widget<OutlinedButton>(chooseAttachmentButton).onPressed,
          isNotNull,
        );
        expect(
          tester.widget<FilledButton>(uploadAttachmentButton).onPressed,
          isNull,
        );

        await tester.tap(chooseAttachmentSemantics);
        await tester.pumpAndSettle();

        expect(find.text('release notes.pdf'), findsOneWidget);
        expect(find.text('4 B'), findsOneWidget);
        expect(
          tester.widget<FilledButton>(uploadAttachmentButton).onPressed,
          isNotNull,
        );

        await tester.tap(uploadAttachmentSemantics);
        await tester.pumpAndSettle();

        expect(find.text('release-notes.pdf'), findsOneWidget);
        expect(
          find.text('Choose a file to review its size before upload.'),
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
    'attachments tab confirms before replacing a sanitized name collision',
    (tester) async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'write-enabled-token',
      });
      final semantics = tester.ensureSemantics();

      Future<PickedAttachment?> pickAttachment() async => PickedAttachment(
        name: 'sync sequence.svg',
        bytes: Uint8List.fromList('<svg updated />'.codeUnits),
      );

      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;
        await tester.pumpWidget(
          TrackStateApp(
            repository: ReactiveIssueDetailTrackStateRepository(
              permission: _hostedReleaseUploadPermission,
              textFixtures: const <String, String>{
                'project.json': _hostedReleaseProjectJson,
              },
            ),
            attachmentPicker: pickAttachment,
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('JQL Search')).first);
        await tester.pumpAndSettle();
        await tester.tap(
          find
              .bySemanticsLabel(
                RegExp('Open TRACK-12 Implement Git sync service'),
              )
              .first,
        );
        await tester.pumpAndSettle();
        await tester.tap(find.bySemanticsLabel(RegExp('Attachments')).first);
        await tester.pumpAndSettle();

        await tester.tap(find.text('Choose attachment'));
        await tester.pumpAndSettle();
        await tester.tap(find.text('Upload attachment'));
        await tester.pumpAndSettle();

        expect(find.text('Replace attachment?'), findsOneWidget);
        expect(
          find.textContaining('stored as sync-sequence.svg'),
          findsOneWidget,
        );

        await tester.tap(find.text('Replace attachment'));
        await tester.pumpAndSettle();

        expect(find.text('Replace attachment?'), findsNothing);
        expect(find.text('sync-sequence.svg'), findsOneWidget);
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

class _LocalizedEditIssueFieldsLocalRuntimeRepository
    extends _EditIssueFieldsLocalRuntimeRepository {
  const _LocalizedEditIssueFieldsLocalRuntimeRepository();

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final snapshot = await super.loadSnapshot();
    return TrackerSnapshot(
      project: ProjectConfig(
        key: snapshot.project.key,
        name: snapshot.project.name,
        repository: snapshot.project.repository,
        branch: snapshot.project.branch,
        defaultLocale: 'en',
        supportedLocales: const ['en', 'fr'],
        issueTypeDefinitions: snapshot.project.issueTypeDefinitions,
        statusDefinitions: snapshot.project.statusDefinitions,
        fieldDefinitions: snapshot.project.fieldDefinitions,
        workflowDefinitions: snapshot.project.workflowDefinitions,
        priorityDefinitions: snapshot.project.priorityDefinitions,
        versionDefinitions: [
          for (final version in snapshot.project.versionDefinitions)
            if (version.id == 'mvp')
              version.copyWith(localizedLabels: const {'en': 'MVP Release'})
            else
              version,
        ],
        componentDefinitions: [
          for (final component in snapshot.project.componentDefinitions)
            if (component.id == 'tracker-core')
              component.copyWith(
                localizedLabels: const {'en': 'Tracker Core Localized'},
              )
            else
              component,
        ],
        resolutionDefinitions: snapshot.project.resolutionDefinitions,
      ),
      issues: snapshot.issues,
      repositoryIndex: snapshot.repositoryIndex,
      loadWarnings: snapshot.loadWarnings,
    );
  }
}

class _BootstrapLoadingRepository extends _LocalRuntimeRepository {
  _BootstrapLoadingRepository({required TrackerSnapshot snapshot})
    : _snapshot = snapshot;

  final TrackerSnapshot _snapshot;
  final JqlSearchService _searchService = const JqlSearchService();
  final Completer<TrackStateIssueSearchPage> _searchCompleter =
      Completer<TrackStateIssueSearchPage>();

  @override
  Future<TrackerSnapshot> loadSnapshot() async => _snapshot;

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) => _searchCompleter.future;

  void completeInitialSearch() {
    if (_searchCompleter.isCompleted) {
      return;
    }
    _searchCompleter.complete(
      _searchService.search(
        issues: _snapshot.issues,
        project: _snapshot.project,
        jql: 'project = TRACK AND status != Done ORDER BY priority DESC',
        maxResults: 6,
      ),
    );
  }
}

class _FailingBootstrapSearchRepository extends _LocalRuntimeRepository {
  _FailingBootstrapSearchRepository({required TrackerSnapshot snapshot})
    : _snapshot = snapshot;

  final TrackerSnapshot _snapshot;

  @override
  Future<TrackerSnapshot> loadSnapshot() async => _snapshot;

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    throw const JqlSearchException('Hosted bootstrap search failed.');
  }
}

class _SlowHistoryReactiveRepository
    extends ProviderBackedTrackStateRepository {
  _SlowHistoryReactiveRepository()
    : super(provider: MutableIssueDetailTrackStateProvider());

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async {
    await Future<void>.delayed(const Duration(milliseconds: 10));
    return super.loadIssueHistory(issue);
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

TrackerSnapshot _hostedBootstrapSnapshot(TrackerSnapshot snapshot) {
  return TrackerSnapshot(
    project: snapshot.project,
    issues: [for (final issue in snapshot.issues) _summaryOnlyIssue(issue)],
    repositoryIndex: snapshot.repositoryIndex,
    loadWarnings: snapshot.loadWarnings,
    readiness: const TrackerBootstrapReadiness(
      domainStates: {
        TrackerDataDomain.projectMeta: TrackerLoadState.ready,
        TrackerDataDomain.issueSummaries: TrackerLoadState.ready,
        TrackerDataDomain.repositoryIndex: TrackerLoadState.ready,
        TrackerDataDomain.issueDetails: TrackerLoadState.partial,
      },
      sectionStates: {
        TrackerSectionKey.dashboard: TrackerLoadState.ready,
        TrackerSectionKey.board: TrackerLoadState.ready,
        TrackerSectionKey.search: TrackerLoadState.partial,
        TrackerSectionKey.hierarchy: TrackerLoadState.ready,
        TrackerSectionKey.settings: TrackerLoadState.ready,
      },
    ),
  );
}

TrackStateIssue _summaryOnlyIssue(TrackStateIssue issue) => TrackStateIssue(
  key: issue.key,
  project: issue.project,
  issueType: issue.issueType,
  issueTypeId: issue.issueTypeId,
  status: issue.status,
  statusId: issue.statusId,
  priority: issue.priority,
  priorityId: issue.priorityId,
  summary: issue.summary,
  description: '',
  assignee: issue.assignee,
  reporter: issue.reporter,
  labels: issue.labels,
  components: const [],
  fixVersionIds: const [],
  watchers: const [],
  customFields: const {},
  parentKey: issue.parentKey,
  epicKey: issue.epicKey,
  parentPath: issue.parentPath,
  epicPath: issue.epicPath,
  progress: issue.progress,
  updatedLabel: issue.updatedLabel,
  acceptanceCriteria: const [],
  comments: const [],
  links: const [],
  attachments: const [],
  isArchived: issue.isArchived,
  hasDetailLoaded: false,
  hasCommentsLoaded: false,
  hasAttachmentsLoaded: false,
  resolutionId: issue.resolutionId,
  storagePath: issue.storagePath,
  rawMarkdown: issue.rawMarkdown,
);
