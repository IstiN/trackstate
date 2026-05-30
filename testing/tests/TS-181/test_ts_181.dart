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
    'TS-181 keeps the top-bar Create issue entry point visible while switching from hosted to Local Git',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;
      final failures = <String>[];

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-181 fixture creation did not complete.');
        }

        await screen.pump(const DemoTrackStateRepository());
        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final hostedRuntimeVisible = await _isAnyTopBarLabelVisible(
          screen,
          const ['Connect GitHub', 'Connected'],
        );
        if (!hostedRuntimeVisible) {
          failures.add(
            'Step 1 failed: the app did not expose a hosted repository-access '
            'state in the top bar before the storage switch. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final hostedCreateIssueFailure =
            await _verifyTopBarCreateIssueVisibility(
              screen,
              step: 2,
              stateDescription: 'hosted Dashboard',
            );
        if (hostedCreateIssueFailure != null) {
          failures.add(hostedCreateIssueFailure);
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
          failures.add(
            'Step 3 failed: the Local Git settings form did not retain the '
            'values the user entered before returning to Dashboard. Expected '
            'Repository Path="${fixture.repositoryPath}" but saw '
            '"${repositoryPathValue ?? '<missing>'}", and expected Write '
            'Branch="main" but saw "${writeBranchValue ?? '<missing>'}". '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: '
            '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }
        await screen.openSection('Dashboard');
        await _waitForTopBarLabelVisible(
          screen,
          'Local Git',
          timeout: const Duration(seconds: 5),
        );

        final localGitVisible = await _isTopBarLabelVisible(
          screen,
          'Local Git',
        );
        if (!localGitVisible) {
          failures.add(
            'Step 3 failed: selecting Local Git in Settings and providing the '
            'repository path did not switch the top bar to the Local Git mode '
            'without a manual refresh. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final hostedLabelsHidden = await _waitForAnyTopBarLabelHidden(
          screen,
          const ['Connect GitHub', 'Connected'],
        );
        if (!hostedLabelsHidden) {
          failures.add(
            'Step 3 failed: the hosted repository-access label remained visible '
            'in the top bar after switching to Local Git. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final localGitCreateIssueFailure =
            await _verifyTopBarCreateIssueVisibility(
              screen,
              step: 5,
              stateDescription: 'Local Git Dashboard after the settings switch',
            );
        if (localGitCreateIssueFailure != null) {
          failures.add(localGitCreateIssueFailure);
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n\n'));
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

Future<String?> _verifyTopBarCreateIssueVisibility(
  TrackStateAppComponent screen, {
  required int step,
  required String stateDescription,
}) async {
  final failures = <String>[];
  final createIssueVisible = await _isTopBarLabelVisible(
    screen,
    'Create issue',
  );
  if (!createIssueVisible) {
    failures.add(
      'Step $step failed: no visible "Create issue" control was rendered in the '
      'top bar while the user was on $stateDescription. Top bar texts: '
      '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible texts: '
      '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
    return failures.join('\n\n');
  }

  final openedCreateFlow = await screen.tapVisibleControl('Create issue');
  if (!openedCreateFlow) {
    failures.add(
      'Step $step failed: the visible top-bar "Create issue" control on '
      '$stateDescription could not be activated. Top bar texts: '
      '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible texts: '
      '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
    return failures.join('\n\n');
  }

  final summaryVisible = await screen.isTextFieldVisible('Summary');
  final descriptionVisible = await screen.isTextFieldVisible('Description');
  final saveVisible = await _isAnyLabelVisible(screen, const ['Save']);
  final cancelVisible = await _isAnyLabelVisible(screen, const ['Cancel']);
  if (!summaryVisible ||
      !descriptionVisible ||
      !saveVisible ||
      !cancelVisible) {
    failures.add(
      'Step $step failed: opening the top-bar "Create issue" control on '
      '$stateDescription did not render the expected user-facing create form. '
      'Expected Summary=${summaryVisible ? 'visible' : 'missing'}, '
      'Description=${descriptionVisible ? 'visible' : 'missing'}, '
      'Save=${saveVisible ? 'visible' : 'missing'}, '
      'Cancel=${cancelVisible ? 'visible' : 'missing'}. Top bar texts: '
      '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible texts: '
      '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
  }

  if (cancelVisible) {
    final cancelled = await screen.tapVisibleControl('Cancel');
    if (!cancelled) {
      failures.add(
        'Step $step failed: the create flow opened from the top bar on '
        '$stateDescription, but the visible "Cancel" action was not reachable. '
        'Top bar texts: ${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
        'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
        'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
      );
    }
  }

  if (cancelVisible) {
    final summaryStillVisible = await screen.isTextFieldVisible('Summary');
    if (summaryStillVisible) {
      failures.add(
        'Step $step failed: tapping "Cancel" after opening "Create issue" on '
        '$stateDescription left the create form open with the Summary field still '
        'visible. Top bar texts: ${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
        'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
        'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
      );
    }
  }

  if (failures.isEmpty) {
    return null;
  }
  return failures.join('\n\n');
}

Future<bool> _isTopBarLabelVisible(
  TrackStateAppComponent screen,
  String label,
) async {
  return await screen.isTopBarSemanticsLabelVisible(label) ||
      await screen.isTopBarTextVisible(label);
}

Future<bool> _isAnyTopBarLabelVisible(
  TrackStateAppComponent screen,
  List<String> labels,
) async {
  for (final label in labels) {
    if (await _isTopBarLabelVisible(screen, label)) {
      return true;
    }
  }
  return false;
}

Future<void> _waitForTopBarLabelVisible(
  TrackStateAppComponent screen,
  String label, {
  Duration timeout = const Duration(seconds: 2),
  Duration step = const Duration(milliseconds: 100),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (await _isTopBarLabelVisible(screen, label)) {
      return;
    }
    await screen.waitWithoutInteraction(step);
  }
}

Future<bool> _waitForAnyTopBarLabelHidden(
  TrackStateAppComponent screen,
  List<String> labels, {
  Duration timeout = const Duration(seconds: 2),
  Duration step = const Duration(milliseconds: 100),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (!await _isAnyTopBarLabelVisible(screen, labels)) {
      return true;
    }
    await screen.waitWithoutInteraction(step);
  }
  return !await _isAnyTopBarLabelVisible(screen, labels);
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
