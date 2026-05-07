import 'package:flutter_test/flutter_test.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/utils/local_git_repository_fixture.dart';

void main() {
  testWidgets(
    'TS-72 repository issue-type customization appears on the Settings discovery surface',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);

      try {
        final fixture = (await tester.runAsync(
          LocalGitRepositoryFixture.create,
        ))!;
        addTearDown(fixture.dispose);

        await tester.runAsync(() async {
          await fixture.replaceIssueTypes(const ['Story', 'Requirement']);
          await fixture.commitChanges('Add Requirement issue type');
        });

        await robot.pumpLocalGitApp(repositoryPath: fixture.directory.path);
        await robot.openSettings();
        robot.expectVisibleSettingsContent();

        final visibleIssueTypes = robot.visibleConfigItems('Issue Types');
        final workflowItems = robot.visibleConfigItems('Workflow');

        print('OBSERVE|Issue Types|${visibleIssueTypes.join(' | ')}');
        print('OBSERVE|Workflow|${workflowItems.join(' | ')}');

        expect(
          robot.configCard('Issue Types'),
          findsOneWidget,
          reason:
              'The Settings screen should render the Issue Types configuration card for discovery.',
        );
        expect(
          robot.configCardItem('Issue Types', 'Story'),
          findsOneWidget,
          reason:
              'The Issue Types card should continue to show the existing Story type after repository-backed customization.',
        );
        expect(
          robot.configCardItem('Issue Types', 'Requirement'),
          findsOneWidget,
          reason:
              'After committing DEMO/config/issue-types.json with Requirement, the Settings UI should show Requirement inside the Issue Types card.',
        );
        expect(
          visibleIssueTypes,
          containsAllInOrder(const ['Story', 'Requirement']),
          reason:
              'The visible Issue Types chips should reflect the repository file ordering so users can discover the new Requirement type.',
        );
        expect(
          visibleIssueTypes.where((item) => item == 'Requirement'),
          hasLength(1),
          reason:
              'The Settings UI should render the new Requirement type exactly once rather than duplicating it elsewhere on the page.',
        );
        expect(
          workflowItems,
          isNot(contains('Requirement')),
          reason:
              'Requirement should appear as an issue type chip, not as unrelated text in the Workflow settings card.',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
