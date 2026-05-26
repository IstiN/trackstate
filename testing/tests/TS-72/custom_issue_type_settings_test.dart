import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/settings/local_git_settings_screen_context.dart';
import '../../core/utils/local_git_repository_fixture.dart';

void main() {
  testWidgets(
    'TS-72 repository issue-type customization appears on the Settings discovery surface',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = createLocalGitSettingsScreenRobot(tester);

      try {
        final fixture = (await tester.runAsync(
          LocalGitRepositoryFixture.create,
        ))!;
        addTearDown(fixture.dispose);

        await tester.runAsync(() async {
          await fixture.writeFile(
            'DEMO/config/issue-types.json',
            '${jsonEncode([
              {'name': 'Story'},
              {'name': 'Requirement'},
            ])}\n',
          );
          await fixture.stageAll();
          await fixture.commit('Add Requirement issue type');
        });

        await robot.pumpLocalGitApp(repositoryPath: fixture.directory.path);
        await robot.openSettings();
        robot.expectVisibleSettingsContent();
        await tester.tap(robot.issueTypesCard);
        await tester.pumpAndSettle();

        final visibleIssueTypes = robot.visibleConfigItems('Issue Types');

        print('OBSERVE|Issue Types|${visibleIssueTypes.join(' | ')}');

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
              'The visible Issue Types list should reflect the repository file ordering so users can discover the new Requirement type.',
        );
        expect(
          visibleIssueTypes.where((item) => item == 'Requirement'),
          hasLength(1),
          reason:
              'The Settings UI should render the new Requirement type exactly once rather than duplicating it elsewhere on the page.',
        );
        await tester.tap(robot.workflowCard);
        await tester.pumpAndSettle();
        final workflowItems = robot.visibleConfigItems('Workflows');
        print('OBSERVE|Workflow|${workflowItems.join(' | ')}');
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
