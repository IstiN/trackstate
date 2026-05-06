import 'package:flutter_test/flutter_test.dart';

import '../../core/utils/trackstate_test_harness.dart';

class SettingsProviderPage {
  SettingsProviderPage(this.tester);

  final WidgetTester tester;

  Finder get settingsNavigationButton => find.text('Settings');

  Finder get settingsHeading => find.text('Project Settings');
  Finder get localGitOption => find.text('Local Git');
  Finder get repositoryPathField => find.text('Repository Path');
  Finder get writeBranchField => find.text('Write Branch');
  Finder get githubTokenField => find.text('Fine-grained token');
  Finder get issueTypesCard => find.text('Issue Types');
  Finder get workflowCard => find.text('Workflow');
  Finder get fieldsCard => find.text('Fields');
  Finder get languageCard => find.text('Language');

  Future<void> open() async {
    await tester.tap(settingsNavigationButton.first);
    await tester.pumpAndSettle();
    await tester.ensureVisible(settingsHeading);
  }

  Future<void> tapLocalGitProvider() async {
    await tester.ensureVisible(localGitOption.first);
    await tester.tap(localGitOption.first);
    await tester.pumpAndSettle();
  }

  Future<void> scrollSettingsBody() async {
    await tester.drag(
      TrackStateTestHarness.scrollableBody(),
      const Offset(0, -400),
    );
    await tester.pumpAndSettle();
  }
}
