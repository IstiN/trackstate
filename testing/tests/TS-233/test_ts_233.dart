import 'dart:io';

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
    'TS-233 blocks issue creation when Summary is empty in Local Git mode',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;

      const descriptionValue = 'Mandatory field check';
      const expectedValidationMessage =
          'Issue summary is required before creating an issue.';
      const expectedCreatedIssuePath = 'DEMO/DEMO-2/main.md';

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-233 fixture creation did not complete.');
        }

        final initialHead = await tester.runAsync(fixture.headRevision) ?? '';
        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final initialIssueKeys = await tester.runAsync(
          () async => fixture!.repository.loadSnapshot().then(
            (snapshot) => snapshot.issues
                .map((issue) => issue.key)
                .toSet()
                .toList(growable: false),
          ),
        );
        if (initialIssueKeys == null) {
          throw StateError('TS-233 initial issue snapshot did not complete.');
        }

        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-233 requires a clean Local Git repository before opening '
              'Create issue, but `git status --short` returned '
              '${initialStatus.join(' | ')}.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));
        await screen.expectTextVisible(
          'Git-native. Jira-compatible. Team-proven.',
        );

        await _expectTopBarControlVisible(
          screen,
          label: 'Create issue',
          failingStep: 2,
          context: 'after opening Dashboard in Local Git mode',
        );

        final openedCreateFlow = await screen.tapTopBarControl('Create issue');
        expect(
          openedCreateFlow,
          isTrue,
          reason:
              'Step 2 failed: the visible top-bar "Create issue" control on '
              'Dashboard was not reachable. Top bar texts: '
              '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.expectCreateIssueFormVisible(
          createIssueSection: 'Dashboard',
        );
        expect(
          await screen.isTextFieldVisible('Description'),
          isTrue,
          reason:
              'Step 3 failed: opening Create issue from Dashboard did not '
              'render the visible Description field. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        await _expectVisibleControl(
          screen,
          label: 'Save',
          failingStep: 5,
          context: 'after opening Create issue from Dashboard',
        );

        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          isEmpty,
          reason:
              'Step 3 failed: Summary should start blank before the validation '
              'attempt.',
        );
        await screen.enterLabeledTextField(
          'Description',
          text: descriptionValue,
        );

        await screen.submitCreateIssue(createIssueSection: 'Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));

        final validationVisible =
            await screen.isMessageBannerVisibleContaining(
              expectedValidationMessage,
            ) ||
            _containsSummaryRequiredFeedback(
              texts: screen.visibleTextsSnapshot(),
              semantics: screen.visibleSemanticsLabelsSnapshot(),
            );
        expect(
          validationVisible,
          isTrue,
          reason:
              'Step 5 failed: saving with an empty Summary should show a visible '
              'summary-required validation error. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextFieldVisible('Summary'),
          isTrue,
          reason:
              'Step 5 failed: the Create issue form should remain visible after '
              'the blocked save attempt.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          isEmpty,
          reason:
              'Step 5 failed: Summary should remain empty after the blocked save '
              'attempt.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Description'),
          descriptionValue,
          reason:
              'Step 5 failed: Description should remain visible after the blocked '
              'save attempt.',
        );

        final latestHead = await tester.runAsync(fixture.headRevision) ?? '';
        final finalStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        final finalIssueKeys = await tester.runAsync(
          () async => fixture!.repository.loadSnapshot().then(
            (snapshot) => snapshot.issues
                .map((issue) => issue.key)
                .toSet()
                .toList(growable: false),
          ),
        );
        if (finalIssueKeys == null) {
          throw StateError('TS-233 final issue snapshot did not complete.');
        }
        final createdIssueExists = await tester.runAsync(
          () => File(
            '${fixture!.repositoryPath}/$expectedCreatedIssuePath',
          ).exists(),
        );

        expect(
          latestHead,
          initialHead,
          reason:
              'A blocked create attempt with an empty Summary must not add a '
              'new git commit.',
        );
        expect(
          finalStatus,
          isEmpty,
          reason:
              'A blocked create attempt with an empty Summary must leave the '
              'Local Git worktree clean, but `git status --short` returned '
              '${finalStatus.join(' | ')}.',
        );
        expect(
          finalIssueKeys.toSet(),
          initialIssueKeys.toSet(),
          reason:
              'A blocked create attempt with an empty Summary must not create a '
              'new issue in Local Git storage. Initial issue keys: '
              '${initialIssueKeys.join(', ')}. Final issue keys: '
              '${finalIssueKeys.join(', ')}.',
        );
        expect(
          createdIssueExists,
          isFalse,
          reason:
              'A blocked create attempt with an empty Summary must not create '
              'the new issue file at $expectedCreatedIssuePath.',
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
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Future<void> _expectVisibleControl(
  TrackStateAppComponent screen, {
  required String label,
  required int failingStep,
  required String context,
}) async {
  final isVisible =
      await screen.isSemanticsLabelVisible(label) ||
      await screen.isTextVisible(label);
  if (isVisible) {
    return;
  }

  fail(
    'Step $failingStep failed: no visible "$label" control was rendered '
    '$context. Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
    'Visible semantics: '
    '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
  );
}

Future<void> _expectTopBarControlVisible(
  TrackStateAppComponent screen, {
  required String label,
  required int failingStep,
  required String context,
}) async {
  final topBarTexts = screen.topBarVisibleTextsSnapshot();
  if (topBarTexts.any((value) => value.trim() == label)) {
    return;
  }

  fail(
    'Step $failingStep failed: no visible "$label" control was rendered in the '
    'top bar $context. Top bar texts: ${_formatSnapshot(topBarTexts)}. Visible '
    'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
    'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
  );
}

bool _containsSummaryRequiredFeedback({
  required List<String> texts,
  required List<String> semantics,
}) {
  for (final value in [...texts, ...semantics]) {
    final normalized = value.toLowerCase();
    if (normalized.contains('summary') && normalized.contains('required')) {
      return true;
    }
  }
  return false;
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
