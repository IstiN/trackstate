import 'dart:async';
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  goldenFileComparator = _TolerantGoldenFileComparator(
    Uri.parse('test/trackstate_golden_test.dart'),
    precisionTolerance: 0.04,
  );

  testWidgets('dashboard light desktop golden', (tester) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      const TrackStateApp(repository: DemoTrackStateRepository()),
    );
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(TrackStateApp),
      matchesGoldenFile('goldens/dashboard_light_desktop.png'),
    );
  });

  testWidgets('dashboard dark desktop golden', (tester) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      const TrackStateApp(repository: DemoTrackStateRepository()),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsLabel('Dark theme'));
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(TrackStateApp),
      matchesGoldenFile('goldens/dashboard_dark_desktop.png'),
    );
  });

  testWidgets('mobile board golden', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      const TrackStateApp(repository: DemoTrackStateRepository()),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Board').first);
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(TrackStateApp),
      matchesGoldenFile('goldens/mobile_board.png'),
    );
  });

  testWidgets('desktop search pagination golden', (tester) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      TrackStateApp(
        repository: DemoTrackStateRepository(
          snapshot: _searchPaginationSnapshot(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('JQL Search').first);
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(TrackStateApp),
      matchesGoldenFile('goldens/search_pagination_desktop.png'),
    );
  });

  testWidgets('hosted search loading desktop golden', (tester) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final snapshot = await const DemoTrackStateRepository().loadSnapshot();
    await tester.pumpWidget(
      TrackStateApp(
        repository: _BootstrapLoadingRepository(
          snapshot: _hostedBootstrapSnapshot(snapshot),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
    await tester.tap(find.text('JQL Search').first);
    await tester.pump();

    await expectLater(
      find.byType(TrackStateApp),
      matchesGoldenFile('goldens/hosted_search_loading_desktop.png'),
    );
  });

  testWidgets('desktop settings admin golden', (tester) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      const TrackStateApp(repository: DemoTrackStateRepository()),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Settings').first);
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(TrackStateApp),
      matchesGoldenFile('goldens/settings_admin_desktop.png'),
    );
  });

  testWidgets('local onboarding desktop golden', (tester) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const TrackStateApp());
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(TrackStateApp),
      matchesGoldenFile('goldens/local_onboarding_desktop.png'),
    );
  });
}

class _TolerantGoldenFileComparator extends LocalFileComparator {
  _TolerantGoldenFileComparator(
    super.testFile, {
    required double precisionTolerance,
  }) : assert(
         precisionTolerance >= 0 && precisionTolerance <= 1,
         'precisionTolerance must be between 0 and 1',
       ),
       _precisionTolerance = precisionTolerance;

  final double _precisionTolerance;

  @override
  Future<bool> compare(Uint8List imageBytes, Uri golden) async {
    final result = await GoldenFileComparator.compareLists(
      imageBytes,
      await getGoldenBytes(golden),
    );
    final passed = result.passed || result.diffPercent <= _precisionTolerance;
    if (passed) {
      result.dispose();
      return true;
    }

    final error = await generateFailureOutput(result, golden, basedir);
    result.dispose();
    throw FlutterError(error);
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

class _BootstrapLoadingRepository extends DemoTrackStateRepository {
  _BootstrapLoadingRepository({required TrackerSnapshot snapshot})
    : _snapshot = snapshot;

  final TrackerSnapshot _snapshot;
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
