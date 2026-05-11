import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts400_subtask_edit_hierarchy_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-400 keeps Epic derived and read-only when editing a sub-task hierarchy',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts400SubtaskEditHierarchyFixture? fixture;

      try {
        fixture = await tester.runAsync(
          Ts400SubtaskEditHierarchyFixture.create,
        );
        if (fixture == null) {
          throw StateError('TS-400 fixture creation did not complete.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('Search');
        await screen.openIssue(
          Ts400SubtaskEditHierarchyFixture.subtaskKey,
          Ts400SubtaskEditHierarchyFixture.subtaskSummary,
        );
        await screen.expectIssueDetailText(
          Ts400SubtaskEditHierarchyFixture.subtaskKey,
          Ts400SubtaskEditHierarchyFixture.subtaskSummary,
        );

        await screen.tapIssueDetailAction(
          Ts400SubtaskEditHierarchyFixture.subtaskKey,
          label: 'Edit',
        );

        expect(
          await screen.countDropdownFields('Parent'),
          1,
          reason:
              'Step 1 failed: opening Edit for ${Ts400SubtaskEditHierarchyFixture.subtaskKey} did not render exactly one editable Parent field. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.readDropdownFieldValue('Parent'),
          Ts400SubtaskEditHierarchyFixture.storyAOptionLabel,
          reason:
              'Step 1 failed: the Parent field did not show Story-A as the initial parent for ${Ts400SubtaskEditHierarchyFixture.subtaskKey}. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );
        expect(
          await screen.countDropdownFields('Epic'),
          0,
          reason:
              'Steps 2 and 3 failed: the sub-task Edit surface exposed an editable Epic dropdown even though Epic should be derived from Parent. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.countReadOnlyFields('Epic'),
          1,
          reason:
              'Steps 2 and 3 failed: the sub-task Edit surface did not render a single read-only Epic field. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.readReadOnlyFieldValue('Epic'),
          Ts400SubtaskEditHierarchyFixture.epic1OptionLabel,
          reason:
              'Steps 2 and 3 failed: the read-only Epic field did not show Epic-1 derived from Story-A before the parent changed. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible(
            'Epic is derived from the selected parent issue.',
          ),
          isTrue,
          reason:
              'Steps 2 and 3 failed: the Edit surface did not explain that Epic is derived from Parent. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.selectDropdownOption(
          'Parent',
          optionText: Ts400SubtaskEditHierarchyFixture.storyBOptionLabel,
        );
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        expect(
          await screen.readDropdownFieldValue('Parent'),
          Ts400SubtaskEditHierarchyFixture.storyBOptionLabel,
          reason:
              'Step 4 failed: selecting Story-B did not update the visible Parent field. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );
        expect(
          await screen.readReadOnlyFieldValue('Epic'),
          Ts400SubtaskEditHierarchyFixture.epic2OptionLabel,
          reason:
              'Step 5 failed: after changing Parent to Story-B, the read-only Epic field did not automatically update to Epic-2. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.countDropdownFields('Epic'),
          0,
          reason:
              'Expected Result failed: Epic became directly editable after Parent changed to Story-B. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );

        await screen.tapIssueDetailAction(
          Ts400SubtaskEditHierarchyFixture.subtaskKey,
          label: 'Save',
        );
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final updatedSubtask = await tester.runAsync(fixture.loadSubtask);
        final repositoryIssues =
            await tester.runAsync(fixture.describeIssues) ?? const <String>[];
        if (updatedSubtask == null) {
          throw StateError('TS-400 updated sub-task reload did not complete.');
        }

        final postSaveFailures = <String>[];

        if (updatedSubtask.parentKey !=
            Ts400SubtaskEditHierarchyFixture.storyBKey) {
          postSaveFailures.add(
            'Expected Result failed: saving the edited sub-task should persist '
            'Parent=${Ts400SubtaskEditHierarchyFixture.storyBKey}, but the '
            'repository still reports Parent=${updatedSubtask.parentKey ?? 'null'}. '
            'Repository issues: ${repositoryIssues.join(' | ')}.',
          );
        }
        if (updatedSubtask.epicKey !=
            Ts400SubtaskEditHierarchyFixture.epic2Key) {
          postSaveFailures.add(
            'Expected Result failed: saving the edited sub-task should persist '
            'Epic=${Ts400SubtaskEditHierarchyFixture.epic2Key}, but the '
            'repository still reports Epic=${updatedSubtask.epicKey ?? 'null'}. '
            'Repository issues: ${repositoryIssues.join(' | ')}.',
          );
        }

        final parentFieldCountAfterSave = await screen.countDropdownFields(
          'Parent',
        );
        if (parentFieldCountAfterSave == 0) {
          await screen.tapIssueDetailAction(
            Ts400SubtaskEditHierarchyFixture.subtaskKey,
            label: 'Edit',
          );
        }

        final reopenedParentValue = await screen.readDropdownFieldValue(
          'Parent',
        );
        final reopenedEpicValue = await screen.readReadOnlyFieldValue('Epic');
        final reopenedEpicDropdownCount = await screen.countDropdownFields(
          'Epic',
        );

        if (reopenedParentValue !=
            Ts400SubtaskEditHierarchyFixture.storyBOptionLabel) {
          postSaveFailures.add(
            'Human-style verification failed: after saving, the visible Edit '
            'surface should show Parent='
            '${Ts400SubtaskEditHierarchyFixture.storyBOptionLabel}, but '
            'rendered Parent=${reopenedParentValue ?? 'null'}. Visible texts: '
            '${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }
        if (reopenedEpicDropdownCount != 0) {
          postSaveFailures.add(
            'Human-style verification failed: after saving, the visible Edit '
            'surface should keep Epic non-editable for a sub-task, but '
            '$reopenedEpicDropdownCount editable Epic dropdown(s) were rendered. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }
        if (reopenedEpicValue !=
            Ts400SubtaskEditHierarchyFixture.epic2OptionLabel) {
          postSaveFailures.add(
            'Human-style verification failed: after saving, the visible Edit '
            'surface should show Epic='
            '${Ts400SubtaskEditHierarchyFixture.epic2OptionLabel}, but rendered '
            'Epic=${reopenedEpicValue ?? 'null'}. Visible texts: '
            '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        if (postSaveFailures.isNotEmpty) {
          fail(postSaveFailures.join('\n'));
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
