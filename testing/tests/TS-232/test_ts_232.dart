import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../frameworks/flutter/trackstate_test_runtime.dart';
import 'support/ts232_delayed_trackstate_repository.dart';
import 'support/ts232_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-232 gates Create issue access until Local Git configuration loading completes',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts232LocalGitFixture? fixture;

      const initialLoadDelay = Duration(seconds: 2);

      try {
        fixture = await tester.runAsync(Ts232LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-232 fixture creation did not complete.');
        }

        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-232 requires a clean Local Git repository before observing '
              'the delayed configuration load, but `git status --short` '
              'returned ${initialStatus.join(' | ')}.',
        );

        final repository = await createLocalGitTestRepository(
          tester: tester,
          repositoryPath: fixture.repositoryPath,
        );
        await _pumpTrackStateApp(
          tester,
          repository: Ts232DelayedTrackStateRepository(
            repository,
            initialLoadDelay: initialLoadDelay,
          ),
        );

        await tester.pump(const Duration(milliseconds: 400));

        expect(
          find.byType(CircularProgressIndicator),
          findsOneWidget,
          reason:
              'Step 3 failed: the app did not expose a visible loading state '
              'while the delayed Local Git configuration load was still in '
              'progress.',
        );

        final createIssueVisibleWhileLoading = await _isCreateIssueEntryVisible(
          screen,
        );
        expect(
          createIssueVisibleWhileLoading,
          isFalse,
          reason:
              'Step 3 failed: Create issue became visible before the delayed '
              'ProjectConfig load completed. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextFieldVisible('Summary'),
          isFalse,
          reason:
              'Step 3 failed: the default Summary field rendered before the '
              'delayed ProjectConfig load completed. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await tester.pump(initialLoadDelay + const Duration(milliseconds: 400));
        await tester.pumpAndSettle();

        screen.expectLocalRuntimeChrome();
        expect(
          await _waitForCreateIssueEntry(screen, tester),
          isTrue,
          reason:
              'Step 5 failed: Create issue never became visible after the '
              'delayed configuration load finished. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        final createIssueSection = await screen.openCreateIssueFlow();
        await screen.expectCreateIssueFormVisible(
          createIssueSection: createIssueSection,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Solution',
          createIssueSection: createIssueSection,
          failingStep: 6,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Acceptance Criteria',
          createIssueSection: createIssueSection,
          failingStep: 6,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Diagrams',
          createIssueSection: createIssueSection,
          failingStep: 6,
        );
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

Future<void> _pumpTrackStateApp(
  WidgetTester tester, {
  required Ts232DelayedTrackStateRepository repository,
}) async {
  tester.view.physicalSize = const Size(1440, 960);
  tester.view.devicePixelRatio = 1;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });

  await tester.pumpWidget(
    TrackStateApp(key: UniqueKey(), repository: repository),
  );
  await tester.pump();
}

Future<bool> _isCreateIssueEntryVisible(TrackStateAppComponent screen) async {
  return await screen.isTextVisible('Create issue') ||
      await screen.isSemanticsLabelVisible('Create issue') ||
      await screen.isTopBarTextVisible('Create issue') ||
      await screen.isTopBarSemanticsLabelVisible('Create issue');
}

Future<bool> _waitForCreateIssueEntry(
  TrackStateAppComponent screen,
  WidgetTester tester,
) async {
  final deadline = DateTime.now().add(const Duration(seconds: 5));
  while (DateTime.now().isBefore(deadline)) {
    if (await _isCreateIssueEntryVisible(screen)) {
      return true;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
  return _isCreateIssueEntryVisible(screen);
}

Future<void> _expectCreateFieldVisible(
  TrackStateAppComponent screen, {
  required String label,
  required String createIssueSection,
  required int failingStep,
}) async {
  if (await screen.isTextFieldVisible(label)) {
    return;
  }
  fail(
    'Step $failingStep failed: the Local Git Create issue form opened from '
    '$createIssueSection did not render the visible "$label" field after '
    'configuration loading completed. Visible texts: '
    '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
    '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
  );
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
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
