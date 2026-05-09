import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-139 keeps Create issue visible and reachable across sections while Local Git is dirty',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-139 fixture creation did not complete.');
        }

        await tester.runAsync(fixture.makeDirtyMainFileChange);
        final statusLines =
            await tester.runAsync(fixture.worktreeStatusLines) ??
            const <String>[];
        expect(
          statusLines,
          isNotEmpty,
          reason:
              'TS-139 requires a dirty Local Git repository before the app is opened.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        final failures = <String>[];
        for (final section in _sectionsUnderTest) {
          await screen.openSection(section.label);
          await screen.waitWithoutInteraction(
            const Duration(milliseconds: 150),
          );
          await _verifyCreateIssueEntryPointForSection(
            screen,
            section: section,
            failures: failures,
          );
        }

        await _verifyDirtyRecoveryGuidance(screen, failures: failures);

        if (failures.isNotEmpty) {
          fail(
            'Expected dirty Local Git mode to keep a user-reachable "Create issue" '
            'entry point in Dashboard, Board, JQL Search, Hierarchy, and Settings, '
            'and to surface recovery guidance after submission. ${failures.join(' ')}',
          );
        }
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
    timeout: const Timeout(Duration(seconds: 25)),
  );
}

const _sectionsUnderTest = <_SectionExpectation>[
  _SectionExpectation(label: 'Dashboard'),
  _SectionExpectation(label: 'Board'),
  _SectionExpectation(label: 'JQL Search'),
  _SectionExpectation(label: 'Hierarchy'),
  _SectionExpectation(label: 'Settings'),
];

Future<void> _verifyCreateIssueEntryPointForSection(
  TrackStateAppComponent screen, {
  required _SectionExpectation section,
  required List<String> failures,
}) async {
  final createIssueVisible =
      await screen.isSemanticsLabelVisible('Create issue') ||
      await screen.isTextVisible('Create issue');

  if (!createIssueVisible) {
    failures.add(
      'Step 2 failed in ${section.label}: no visible "Create issue" entry point '
      'was rendered after opening ${section.label} with dirty local changes. '
      'Top bar texts: ${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
      'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
      'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
    return;
  }

  final openedCreateFlow = await screen.tapVisibleControl('Create issue');
  if (!openedCreateFlow) {
    failures.add(
      'Step 3 failed in ${section.label}: the visible "Create issue" entry point '
      'could not be activated while the repository was dirty. Top bar texts: '
      '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible texts: '
      '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
    return;
  }

  final summaryVisible = await screen.isTextFieldVisible('Summary');
  final descriptionVisible = await screen.isTextFieldVisible('Description');
  final saveVisible =
      await screen.isSemanticsLabelVisible('Save') ||
      await screen.isTextVisible('Save');
  final cancelVisible =
      await screen.isSemanticsLabelVisible('Cancel') ||
      await screen.isTextVisible('Cancel');

  if (!summaryVisible ||
      !descriptionVisible ||
      !saveVisible ||
      !cancelVisible) {
    failures.add(
      'Step 3 failed in ${section.label}: opening "Create issue" did not render '
      'the expected user-facing create controls. Expected Summary='
      '${summaryVisible ? 'visible' : 'missing'}, Description='
      '${descriptionVisible ? 'visible' : 'missing'}, Save='
      '${saveVisible ? 'visible' : 'missing'}, Cancel='
      '${cancelVisible ? 'visible' : 'missing'}. Top bar texts: '
      '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible texts: '
      '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
    return;
  }

  final cancelled = await screen.tapVisibleControl('Cancel');
  if (!cancelled) {
    failures.add(
      'Step 3 failed in ${section.label}: the create flow opened, but no visible '
      '"Cancel" action was reachable to close it again. Top bar texts: '
      '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible texts: '
      '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
    return;
  }

  final summaryStillVisible = await screen.isTextFieldVisible('Summary');
  if (summaryStillVisible) {
    failures.add(
      'Step 3 failed in ${section.label}: tapping "Cancel" left the create form '
      'open with the Summary field still visible. Top bar texts: '
      '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible texts: '
      '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
  }
}

Future<void> _verifyDirtyRecoveryGuidance(
  TrackStateAppComponent screen, {
  required List<String> failures,
}) async {
  await screen.openSection('JQL Search');
  await screen.expectIssueSearchResultVisible(
    LocalTrackStateFixture.issueKey,
    LocalTrackStateFixture.issueSummary,
  );

  final createIssueVisible =
      await screen.isSemanticsLabelVisible('Create issue') ||
      await screen.isTextVisible('Create issue');
  if (!createIssueVisible) {
    failures.add(
      'Step 3 failed in JQL Search: the dirty-state recovery path could not be '
      'validated because no visible "Create issue" control was available. '
      'Top bar texts: ${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
      'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
      'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
    return;
  }

  final openedCreateFlow = await screen.tapVisibleControl('Create issue');
  if (!openedCreateFlow) {
    failures.add(
      'Step 3 failed in JQL Search: "Create issue" was visible but not '
      'interactive while the repository was dirty. Top bar texts: '
      '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible texts: '
      '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
    return;
  }

  await screen.expectCreateIssueFormVisible(createIssueSection: 'JQL Search');
  await screen.populateCreateIssueForm(
    summary: 'TS-139 dirty visibility candidate',
    description:
        'Dirty create visibility should still reach recovery guidance.',
  );
  await screen.submitCreateIssue(createIssueSection: 'JQL Search');

  for (final keyword in const ['commit', 'stash', 'clean']) {
    final bannerVisible = await screen.isMessageBannerVisibleContaining(
      keyword,
    );
    if (!bannerVisible) {
      failures.add(
        'Step 3 failed after submitting Create issue from JQL Search: expected '
        'dirty-state recovery guidance containing "$keyword", but it was not '
        'visible. Top bar texts: '
        '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible texts: '
        '${_formatSnapshot(screen.visibleTextsSnapshot())}. '
        'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
      );
      return;
    }
  }
}

class _SectionExpectation {
  const _SectionExpectation({required this.label});

  final String label;
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
