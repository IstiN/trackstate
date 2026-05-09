import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts239_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-239 falls back to system create fields when the config directory is missing',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts239LocalGitFixture? fixture;

      const summaryValue = 'TS-239 fallback summary';
      const descriptionValue =
          'TS-239 verifies the missing config directory fallback keeps the create form usable.';

      try {
        fixture = await tester.runAsync(Ts239LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-239 fixture creation did not complete.');
        }

        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-239 requires a clean Local Git repository before launching '
              'the missing DEMO/config scenario, but `git status --short` '
              'returned ${initialStatus.join(' | ')}.',
        );

        final configDirectoryExists =
            await tester.runAsync(fixture.configDirectoryExists) ?? true;
        expect(
          configDirectoryExists,
          isFalse,
          reason:
              'TS-239 must exercise a fixture where the DEMO/config directory '
              'is absent from the Local Git repository.',
        );

        final startupError = await _launchSupportedLocalGitApp(
          screen,
          repositoryPath: fixture.repositoryPath,
        );
        await screen.waitWithoutInteraction(const Duration(seconds: 2));

        final startupObservation = await _observeMissingConfigStartup(
          screen,
          tester,
        );
        final frameworkException = tester.takeException();
        final localGitChromeVisible =
            await screen.isSemanticsLabelVisible('Local Git') ||
            await screen.isTextVisible('Local Git');
        if (startupError != null ||
            !startupObservation.fallbackWarningVisible ||
            startupObservation.dataLoadFailureVisible ||
            frameworkException != null ||
            !localGitChromeVisible) {
          fail(
            'Step 4 failed: launching the app with the missing DEMO/config '
            'directory did not preserve the required fallback behavior. '
            'startup error=${startupError ?? '<none>'}, fallback warning '
            'visible=${startupObservation.fallbackWarningVisible ? 'yes' : 'no'}, '
            'data load failure visible='
            '${startupObservation.dataLoadFailureVisible ? 'yes' : 'no'}, '
            'framework exception=${frameworkException ?? '<none>'}, '
            'Local Git visible=${localGitChromeVisible ? 'yes' : 'no'}. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: '
            '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final createIssueSection = await screen.openCreateIssueFlow();
        await screen.expectCreateIssueFormVisible(
          createIssueSection: createIssueSection,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Description',
          createIssueSection: createIssueSection,
          failingStep: 5,
        );
        await _expectVisibleText(
          screen,
          label: 'Save',
          createIssueSection: createIssueSection,
          failingStep: 5,
        );
        await _expectVisibleText(
          screen,
          label: 'Cancel',
          createIssueSection: createIssueSection,
          failingStep: 5,
        );

        await screen.populateCreateIssueForm(
          summary: summaryValue,
          description: descriptionValue,
        );

        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          summaryValue,
          reason:
              'Expected result failed: the fallback Summary field did not keep '
              'the entered value "$summaryValue". Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Description'),
          descriptionValue,
          reason:
              'Expected result failed: the fallback Description field did not '
              'keep the entered value "$descriptionValue". Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Expected result failed: interacting with the fallback Create '
              'issue form surfaced a framework exception instead of keeping the '
              'UI stable.',
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

Future<Object?> _launchSupportedLocalGitApp(
  TrackStateAppComponent screen, {
  required String repositoryPath,
}) async {
  try {
    await screen.pumpLocalGitApp(repositoryPath: repositoryPath);
    return null;
  } catch (error) {
    return error;
  }
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
    '$createIssueSection did not render a visible "$label" field after '
    'loading with the missing DEMO/config directory. Visible texts: '
    '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
    '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
  );
}

Future<void> _expectVisibleText(
  TrackStateAppComponent screen, {
  required String label,
  required String createIssueSection,
  required int failingStep,
}) async {
  if (await screen.isTextVisible(label)) {
    return;
  }
  fail(
    'Step $failingStep failed: the Local Git Create issue form opened from '
    '$createIssueSection did not show the visible "$label" action after '
    'loading with the missing DEMO/config directory. Visible texts: '
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

Future<_MissingConfigStartupObservation> _observeMissingConfigStartup(
  TrackStateAppComponent screen,
  WidgetTester tester,
) async {
  final deadline = DateTime.now().add(const Duration(seconds: 8));
  while (DateTime.now().isBefore(deadline)) {
    final observation = await _readMissingConfigStartupObservation(screen);
    if (observation.fallbackWarningVisible ||
        observation.dataLoadFailureVisible) {
      return observation;
    }
    await tester.pump(const Duration(milliseconds: 200));
  }
  return _readMissingConfigStartupObservation(screen);
}

Future<_MissingConfigStartupObservation> _readMissingConfigStartupObservation(
  TrackStateAppComponent screen,
) async {
  final fallbackBannerVisible =
      await screen.isMessageBannerVisibleContaining('built-in defaults') ||
      await screen.isMessageBannerVisibleContaining('built-in fields') ||
      await screen.isMessageBannerVisibleContaining('fell back') ||
      await screen.isMessageBannerVisibleContaining('falling back');
  final dataLoadFailureVisible =
      await screen.isMessageBannerVisibleContaining(
        'TrackState data was not found',
      ) ||
      await screen.isMessageBannerVisibleContaining('Git command failed:');

  final visibleTexts = screen.visibleTextsSnapshot();
  final visibleSemantics = screen.visibleSemanticsLabelsSnapshot();

  return _MissingConfigStartupObservation(
    fallbackWarningVisible:
        (fallbackBannerVisible &&
            (_snapshotContainsConfigFallbackPath(visibleTexts) ||
                _snapshotContainsConfigFallbackPath(visibleSemantics))) ||
        _snapshotContainsMissingConfigFallback(visibleTexts) ||
        _snapshotContainsMissingConfigFallback(visibleSemantics),
    dataLoadFailureVisible:
        dataLoadFailureVisible ||
        _snapshotContainsDataLoadFailure(visibleTexts) ||
        _snapshotContainsDataLoadFailure(visibleSemantics),
  );
}

bool _snapshotContainsMissingConfigFallback(List<String> values) {
  return values.any((value) {
    final normalized = value.toLowerCase();
    final mentionsFallback =
        normalized.contains('built-in defaults') ||
        normalized.contains('built-in fields') ||
        normalized.contains('fell back') ||
        normalized.contains('falling back') ||
        normalized.contains('system fields');
    return mentionsFallback &&
        (normalized.contains('demo/config') ||
            normalized.contains('fields.json'));
  });
}

bool _snapshotContainsConfigFallbackPath(List<String> values) {
  return values.any(
    (value) =>
        value.toLowerCase().contains('demo/config') ||
        value.toLowerCase().contains('fields.json'),
  );
}

bool _snapshotContainsDataLoadFailure(List<String> values) {
  return values.any((value) {
    final normalized = value.toLowerCase();
    return normalized.contains('trackstate data was not found') ||
        normalized.contains('git command failed:') ||
        ((normalized.contains('demo/config') ||
                normalized.contains('fields.json')) &&
            normalized.contains("does not exist in 'head'"));
  });
}

class _MissingConfigStartupObservation {
  const _MissingConfigStartupObservation({
    required this.fallbackWarningVisible,
    required this.dataLoadFailureVisible,
  });

  final bool fallbackWarningVisible;
  final bool dataLoadFailureVisible;
}
