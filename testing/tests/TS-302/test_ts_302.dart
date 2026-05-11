import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/create_issue_accessibility_robot.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts302_hierarchy_prefill_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-302 pre-fills hierarchy parent metadata when creating a child issue from Hierarchy',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final createIssueRobot = CreateIssueAccessibilityRobot(tester);
      Ts302HierarchyPrefillFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts302HierarchyPrefillFixture.create);
        if (fixture == null) {
          throw StateError('TS-302 fixture creation did not complete.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('Hierarchy');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final openedEpicChildCreate = await screen
            .openHierarchyChildCreateForIssue(
              Ts302HierarchyPrefillFixture.epicKey,
            );
        expect(
          openedEpicChildCreate,
          isTrue,
          reason:
              'Step 2 failed: the Hierarchy row for ${Ts302HierarchyPrefillFixture.epicKey} did not expose a visible contextual child-create action. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        await screen.expectCreateIssueFormVisible(
          createIssueSection: 'Hierarchy',
        );
        createIssueRobot.expectCreateIssueSurfaceVisible();
        _expectCreateIssueTexts(
          createIssueRobot,
          expectedTexts: <String>[
            'Create issue',
            'Issue Type',
            'Story',
            'Summary',
            'Description',
            'Epic',
            '${Ts302HierarchyPrefillFixture.epicKey} · ${Ts302HierarchyPrefillFixture.epicSummary}',
            'Save',
            'Cancel',
          ],
          failingStep: 3,
          verificationLabel:
              'opening the epic row action should create a story prefilled to the originating epic',
        );
        expect(
          createIssueRobot.showsText('Parent'),
          isFalse,
          reason:
              'Step 4 failed: creating a child from epic ${Ts302HierarchyPrefillFixture.epicKey} should open a Story form with Epic prefilled, not a Sub-task form with a Parent selector. '
              'Visible Create issue texts: ${_formatSnapshot(createIssueRobot.visibleTexts())}.',
        );

        final cancelledEpicFlow = await screen.tapVisibleControl('Cancel');
        expect(
          cancelledEpicFlow,
          isTrue,
          reason:
              'Step 3 failed: the visible "Cancel" action was not reachable after opening Create issue from epic ${Ts302HierarchyPrefillFixture.epicKey}.',
        );

        await screen.openSection('Hierarchy');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final openedStoryChildCreate = await screen
            .openHierarchyChildCreateForIssue(
              Ts302HierarchyPrefillFixture.storyKey,
            );
        expect(
          openedStoryChildCreate,
          isTrue,
          reason:
              'Step 2 failed: the Hierarchy row for ${Ts302HierarchyPrefillFixture.storyKey} did not expose a visible contextual child-create action. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        await screen.expectCreateIssueFormVisible(
          createIssueSection: 'Hierarchy',
        );
        createIssueRobot.expectCreateIssueSurfaceVisible();
        _expectCreateIssueTexts(
          createIssueRobot,
          expectedTexts: <String>[
            'Create issue',
            'Issue Type',
            'Sub-task',
            'Summary',
            'Description',
            'Parent',
            '${Ts302HierarchyPrefillFixture.storyKey} · ${Ts302HierarchyPrefillFixture.storySummary}',
            'Epic',
            '${Ts302HierarchyPrefillFixture.epicKey} · ${Ts302HierarchyPrefillFixture.epicSummary}',
            'Save',
            'Cancel',
          ],
          failingStep: 4,
          verificationLabel:
              'opening the story row action should create a sub-task with both Parent and derived Epic context visible to the user',
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

void _expectCreateIssueTexts(
  CreateIssueAccessibilityRobot robot, {
  required List<String> expectedTexts,
  required int failingStep,
  required String verificationLabel,
}) {
  for (final text in expectedTexts) {
    expect(
      robot.showsText(text),
      isTrue,
      reason:
          'Step $failingStep failed: $verificationLabel, but the visible Create issue form did not show "$text". '
          'Visible Create issue texts: ${_formatSnapshot(robot.visibleTexts())}.',
    );
  }
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
