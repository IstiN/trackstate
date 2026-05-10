import 'package:flutter/material.dart' show CircularProgressIndicator;
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../TS-141/support/ts141_local_git_fixture.dart';

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
      Ts141LocalGitFixture? fixture;

      const initialLoadDelay = Duration(seconds: 2);

      try {
        fixture = await tester.runAsync(Ts141LocalGitFixture.create);
        if (fixture == null) {
          throw StateError(
            'TS-232 fixture creation did not complete from the TS-141 dependency.',
          );
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

        await screen.pumpLocalGitApp(
          repositoryPath: fixture.repositoryPath,
          initialLoadDelay: initialLoadDelay,
        );

        await screen.waitWithoutInteraction(const Duration(milliseconds: 400));

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

        await screen.waitWithoutInteraction(
          initialLoadDelay + const Duration(milliseconds: 400),
        );
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
