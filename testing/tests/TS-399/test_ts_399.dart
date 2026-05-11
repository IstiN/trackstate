import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts399_hierarchy_move_confirmation_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-399 requires confirmation with a subtree move summary before saving an epic change',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts399HierarchyMoveConfirmationFixture? fixture;

      try {
        fixture = await tester.runAsync(
          Ts399HierarchyMoveConfirmationFixture.create,
        );
        if (fixture == null) {
          throw StateError('TS-399 fixture creation did not complete.');
        }

        final beforeSave = await tester.runAsync(fixture.observeHierarchy);
        if (beforeSave == null) {
          throw StateError('TS-399 pre-save hierarchy observation failed.');
        }

        expect(
          beforeSave.storyStoragePath,
          Ts399HierarchyMoveConfirmationFixture.oldStoryPath,
          reason:
              'Precondition failed: Story-A must start under Epic-1 before the hierarchy move confirmation scenario begins.',
        );
        expect(
          beforeSave.storyEpicKey,
          Ts399HierarchyMoveConfirmationFixture.epic1Key,
          reason:
              'Precondition failed: Story-A must initially belong to Epic-1.',
        );
        expect(
          beforeSave.descendantKeys,
          [
            Ts399HierarchyMoveConfirmationFixture.subtask1Key,
            Ts399HierarchyMoveConfirmationFixture.subtask2Key,
            Ts399HierarchyMoveConfirmationFixture.subtask3Key,
          ],
          reason:
              'Precondition failed: Story-A must start with exactly three descendant sub-tasks.',
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('Search');
        await screen.openIssue(
          Ts399HierarchyMoveConfirmationFixture.storyAKey,
          Ts399HierarchyMoveConfirmationFixture.storyASummary,
        );
        await screen.expectIssueDetailText(
          Ts399HierarchyMoveConfirmationFixture.storyAKey,
          Ts399HierarchyMoveConfirmationFixture.storyASummary,
        );

        await screen.tapIssueDetailAction(
          Ts399HierarchyMoveConfirmationFixture.storyAKey,
          label: 'Edit',
        );

        expect(
          await screen.countDropdownFields('Epic'),
          1,
          reason:
              'Step 1 failed: opening Edit for Story-A did not render exactly one editable Epic field. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.readDropdownFieldValue('Epic'),
          Ts399HierarchyMoveConfirmationFixture.epic1OptionLabel,
          reason:
              'Step 1 failed: the visible Epic field did not start on Epic-1. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );

        await screen.selectDropdownOption(
          'Epic',
          optionText: Ts399HierarchyMoveConfirmationFixture.epic2OptionLabel,
        );
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        expect(
          await screen.readDropdownFieldValue('Epic'),
          Ts399HierarchyMoveConfirmationFixture.epic2OptionLabel,
          reason:
              'Step 2 failed: changing the Epic field did not update the visible selection to Epic-2. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );

        final saveTapped = await screen.tapVisibleControl('Save');
        expect(
          saveTapped,
          isTrue,
          reason:
              'Step 3 failed: the visible Save action could not be activated after selecting Epic-2.',
        );

        expect(
          await screen.isDialogTextVisible('Confirm hierarchy move'),
          isTrue,
          reason:
              'Step 4 failed: clicking Save did not open the hierarchy move confirmation prompt. '
              'Visible dialog texts: ${_formatSnapshot(screen.visibleDialogTextsSnapshot())}. '
              'Visible page texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );
        expect(
          await screen.isDialogTextVisible('Confirm move'),
          isTrue,
          reason:
              'Step 4 failed: the confirmation dialog did not expose a visible "Confirm move" action. '
              'Visible dialog texts: ${_formatSnapshot(screen.visibleDialogTextsSnapshot())}.',
        );
        expect(
          await screen.isDialogTextVisible('Cancel'),
          isTrue,
          reason:
              'Step 4 failed: the confirmation dialog did not expose a visible "Cancel" action. '
              'Visible dialog texts: ${_formatSnapshot(screen.visibleDialogTextsSnapshot())}.',
        );

        final dialogTexts = screen.visibleDialogTextsSnapshot();
        expect(
          _containsFragment(
                dialogTexts,
                Ts399HierarchyMoveConfirmationFixture.storyAKey,
              ) ||
              _containsFragment(
                dialogTexts,
                Ts399HierarchyMoveConfirmationFixture.storyASummary,
              ),
          isTrue,
          reason:
              'Step 5 failed: the confirmation summary did not identify Story-A as the moved issue. '
              'Visible dialog texts: ${_formatSnapshot(dialogTexts)}.',
        );
        expect(
          _containsFragment(dialogTexts, '3 descendants'),
          isTrue,
          reason:
              'Step 5 failed: the confirmation summary did not state that three descendants would move with Story-A. '
              'Visible dialog texts: ${_formatSnapshot(dialogTexts)}.',
        );
        expect(
          _containsFragment(
                dialogTexts,
                Ts399HierarchyMoveConfirmationFixture.epic2Key,
              ) ||
              _containsFragment(
                dialogTexts,
                Ts399HierarchyMoveConfirmationFixture.epic2Summary,
              ),
          isTrue,
          reason:
              'Expected result failed: the confirmation summary did not identify Epic-2 as the destination hierarchy owner. '
              'Visible dialog texts: ${_formatSnapshot(dialogTexts)}.',
        );

        final afterInitialSave = await tester.runAsync(
          fixture.observeHierarchy,
        );
        if (afterInitialSave == null) {
          throw StateError('TS-399 post-save hierarchy observation failed.');
        }
        expect(
          afterInitialSave.headRevision,
          beforeSave.headRevision,
          reason:
              'Expected result failed: clicking Save opened the prompt, but the repository head revision still changed before the move was confirmed.',
        );
        expect(
          afterInitialSave.storyStoragePath,
          Ts399HierarchyMoveConfirmationFixture.oldStoryPath,
          reason:
              'Expected result failed: Story-A moved to Epic-2 before the user confirmed the hierarchy change.',
        );
        expect(
          afterInitialSave.storyEpicKey,
          Ts399HierarchyMoveConfirmationFixture.epic1Key,
          reason:
              'Expected result failed: Story-A started reporting Epic-2 before the user confirmed the move.',
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

bool _containsFragment(List<String> texts, String expectedFragment) {
  for (final text in texts) {
    if (text.contains(expectedFragment)) {
      return true;
    }
  }
  return false;
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
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
