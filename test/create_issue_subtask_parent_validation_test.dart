import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../testing/components/factories/testing_dependencies.dart';
import '../testing/core/interfaces/trackstate_app_component.dart';
import '../testing/tests/TS-303/support/ts303_issue_hierarchy_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'create issue blocks sub-task creation until a parent is selected',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts303IssueHierarchyFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts303IssueHierarchyFixture.create);
        if (fixture == null) {
          throw StateError('TS-1065 fixture creation did not complete.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));
        final openedCreateFlow = await screen.tapTopBarControl('Create issue');
        expect(openedCreateFlow, isTrue);

        await screen.expectCreateIssueFormVisible(
          createIssueSection: 'Dashboard',
        );
        await screen.selectDropdownOption('Issue Type', optionText: 'Sub-task');
        await screen.enterLabeledTextField(
          'Summary',
          text: 'TS-1065 regression issue',
        );

        await screen.submitCreateIssue(createIssueSection: 'Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final repositoryIssues =
            await tester.runAsync(fixture.describeIssues) ?? const <String>[];
        expect(
          await screen.isTextVisible('Sub-tasks require a parent issue.'),
          isTrue,
        );
        expect(await screen.isTextFieldVisible('Summary'), isTrue);
        expect(
          repositoryIssues.any(
            (issue) => issue.contains('TS-1065 regression issue'),
          ),
          isFalse,
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
  );
}
