import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-222 re-initializes the top-bar hosted UI after switching from Local Git back to Remote',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-222 fixture creation did not complete.');
        }

        await screen.pump(const DemoTrackStateRepository());
        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final initialHostedVisible = await _isTopBarLabelVisible(
          screen,
          'Connect GitHub',
        );
        if (!initialHostedVisible) {
          fail(
            'Precondition failed: the hosted Dashboard did not expose the '
            '"Connect GitHub" top-bar control before establishing the Local Git '
            'state required by TS-222. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await screen.switchToLocalGitInSettings(
          repositoryPath: fixture.repositoryPath,
          writeBranch: 'main',
        );

        final repositoryPathValue = await screen.readLabeledTextFieldValue(
          'Repository Path',
        );
        final writeBranchValue = await screen.readLabeledTextFieldValue(
          'Write Branch',
        );
        if (repositoryPathValue != fixture.repositoryPath ||
            writeBranchValue != 'main') {
          fail(
            'Precondition failed: the Local Git settings form did not retain '
            'the values entered while establishing the starting state for '
            'TS-222. Expected Repository Path="${fixture.repositoryPath}" but '
            'saw "${repositoryPathValue ?? '<missing>'}", and expected Write '
            'Branch="main" but saw "${writeBranchValue ?? '<missing>'}". '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: '
            '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final localGitVisible = await _isTopBarLabelVisible(
          screen,
          'Local Git',
        );
        if (!localGitVisible) {
          fail(
            'Precondition failed: the app did not reach the required Local Git '
            'Dashboard state before attempting the reverse switch to Remote. '
            'Top bar texts: ${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await screen.openSection('Settings');

        final hostedSelectorVisible =
            await screen.isSemanticsLabelVisible('Connect GitHub') ||
            await screen.isTextVisible('Connect GitHub');
        if (!hostedSelectorVisible) {
          fail(
            'Step 2 failed: after opening Settings from the Local Git state, '
            'the UI did not expose a visible "Connect GitHub" option to switch '
            'back to the Remote/Hosted mode. Visible texts: '
            '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final switchedToHosted = await screen.tapVisibleControl(
          'Connect GitHub',
        );
        if (!switchedToHosted) {
          fail(
            'Step 2 failed: the visible "Connect GitHub" control in Settings '
            'could not be activated to switch the storage mode back to Remote. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await _saveSettingsIfPresent(screen);
        await screen.openSection('Dashboard');
        await _waitForTopBarStatePropagation(screen);

        final hostedTopBarVisible = await _isTopBarLabelVisible(
          screen,
          'Connect GitHub',
        );
        if (!hostedTopBarVisible) {
          fail(
            'Step 5 failed: returning to Dashboard after switching back to '
            'Remote did not restore the hosted-mode "Connect GitHub" control in '
            'the top bar without a manual refresh. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final localGitStillVisible = await _isTopBarLabelVisible(
          screen,
          'Local Git',
        );
        if (localGitStillVisible) {
          fail(
            'Step 6 failed: the Dashboard top bar still showed "Local Git" '
            'after switching the storage mode back to Remote. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final openedConnectDialog = await screen.tapTopBarControl(
          'Connect GitHub',
        );
        if (!openedConnectDialog) {
          fail(
            'Human-style verification failed: the hosted-mode "Connect GitHub" '
            'control was visible in the top bar after the reverse switch, but '
            'the user could not activate it. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final fineGrainedTokenVisible = await screen.isTextFieldVisible(
          'Fine-grained token',
        );
        final connectTokenVisible = await _isAnyLabelVisible(screen, const [
          'Connect token',
        ]);
        if (!fineGrainedTokenVisible || !connectTokenVisible) {
          fail(
            'Human-style verification failed: activating the hosted-mode '
            '"Connect GitHub" control did not render the expected hosted '
            'connection dialog. Fine-grained token visible='
            '${fineGrainedTokenVisible ? 'yes' : 'no'}, Connect token visible='
            '${connectTokenVisible ? 'yes' : 'no'}. Visible texts: '
            '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final cancelledDialog = await screen.tapVisibleControl('Cancel');
        if (!cancelledDialog) {
          fail(
            'Human-style verification failed: the hosted connection dialog '
            'opened, but the visible "Cancel" action could not be activated. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final tokenFieldStillVisible = await screen.isTextFieldVisible(
          'Fine-grained token',
        );
        if (tokenFieldStillVisible) {
          fail(
            'Human-style verification failed: dismissing the hosted connection '
            'dialog left the "Fine-grained token" field visible on screen. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
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
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Future<void> _saveSettingsIfPresent(TrackStateAppComponent screen) async {
  for (final label in const ['Save', 'Apply']) {
    final visible =
        await screen.isSemanticsLabelVisible(label) ||
        await screen.isTextVisible(label);
    if (!visible) {
      continue;
    }
    await screen.tapVisibleControl(label);
    await screen.waitWithoutInteraction(const Duration(milliseconds: 150));
    return;
  }
}

Future<void> _waitForTopBarStatePropagation(
  TrackStateAppComponent screen,
) async {
  const timeout = Duration(seconds: 5);
  const tick = Duration(milliseconds: 100);
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (await _isTopBarLabelVisible(screen, 'Connect GitHub')) {
      return;
    }
    await screen.waitWithoutInteraction(tick);
  }
}

Future<bool> _isTopBarLabelVisible(
  TrackStateAppComponent screen,
  String label,
) async {
  return await screen.isTopBarSemanticsLabelVisible(label) ||
      await screen.isTopBarTextVisible(label);
}

Future<bool> _isAnyLabelVisible(
  TrackStateAppComponent screen,
  List<String> labels,
) async {
  for (final label in labels) {
    if (await screen.isSemanticsLabelVisible(label) ||
        await screen.isTextVisible(label)) {
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
