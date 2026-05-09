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
    'TS-122 renders a reachable Create issue entry point in core Local Git sections',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-122 fixture creation did not complete.');
        }

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

        if (failures.isNotEmpty) {
          fail(
            'Expected Local Git mode to render a user-reachable "Create issue" '
            'entry point in Dashboard, Board, JQL Search, and Hierarchy. '
            '${failures.join(' ')}',
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
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

const _sectionsUnderTest = <_SectionExpectation>[
  _SectionExpectation(
    label: 'Dashboard',
    visibilityStep: 2,
    reachabilityStep: 2,
  ),
  _SectionExpectation(label: 'Board', visibilityStep: 4, reachabilityStep: 4),
  _SectionExpectation(
    label: 'JQL Search',
    visibilityStep: 6,
    reachabilityStep: 6,
  ),
  _SectionExpectation(
    label: 'Hierarchy',
    visibilityStep: 8,
    reachabilityStep: 8,
  ),
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
      'Step ${section.visibilityStep} failed in ${section.label}: no visible '
      '"Create issue" entry point was rendered after opening ${section.label}. '
      'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
      'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
    return;
  }

  final openedCreateFlow = await screen.tapVisibleControl('Create issue');
  if (!openedCreateFlow) {
    failures.add(
      'Step ${section.reachabilityStep} failed in ${section.label}: '
      'the visible "Create issue" entry point could not be activated. '
      'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
      'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
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
      'Step ${section.reachabilityStep} failed in ${section.label}: '
      'opening "Create issue" did not render the expected user-facing create '
      'controls. Expected Summary=${summaryVisible ? 'visible' : 'missing'}, '
      'Description=${descriptionVisible ? 'visible' : 'missing'}, '
      'Save=${saveVisible ? 'visible' : 'missing'}, '
      'Cancel=${cancelVisible ? 'visible' : 'missing'}. Visible texts: '
      '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
    return;
  }

  final cancelled = await screen.tapVisibleControl('Cancel');
  if (!cancelled) {
    failures.add(
      'Step ${section.reachabilityStep} failed in ${section.label}: '
      'the create flow opened, but no visible "Cancel" action was reachable '
      'to close it again. Visible texts: '
      '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
      '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
    return;
  }

  final summaryStillVisible = await screen.isTextFieldVisible('Summary');
  if (summaryStillVisible) {
    failures.add(
      'Step ${section.reachabilityStep} failed in ${section.label}: tapping '
      '"Cancel" left the create form open with the Summary field still '
      'visible, so the create surface was not cleanly dismissible. Visible '
      'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
      'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
    );
  }
}

class _SectionExpectation {
  const _SectionExpectation({
    required this.label,
    required this.visibilityStep,
    required this.reachabilityStep,
  });

  final String label;
  final int visibilityStep;
  final int reachabilityStep;
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
