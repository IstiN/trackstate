import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../testing/components/factories/testing_dependencies.dart';
import '../testing/core/interfaces/trackstate_app_component.dart';
import '../testing/tests/TS-399/support/ts399_hierarchy_move_confirmation_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'edit issue confirmation summary names the moved issue and destination epic',
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
          throw StateError('Hierarchy move confirmation fixture failed.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        await screen.openSection('Search');
        await screen.openIssue(
          Ts399HierarchyMoveConfirmationFixture.storyAKey,
          Ts399HierarchyMoveConfirmationFixture.storyASummary,
        );
        await screen.tapIssueDetailAction(
          Ts399HierarchyMoveConfirmationFixture.storyAKey,
          label: 'Edit',
        );
        await screen.selectDropdownOption(
          'Epic',
          optionText: Ts399HierarchyMoveConfirmationFixture.epic2OptionLabel,
        );
        await screen.tapVisibleControl('Save');

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
        );
        expect(_containsFragment(dialogTexts, '3 descendants'), isTrue);
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
        );
      } finally {
        await tester.runAsync(() async {
          await fixture?.dispose();
        });
        screen.resetView();
        semantics.dispose();
      }
    },
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
