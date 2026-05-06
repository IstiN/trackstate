import 'package:flutter_test/flutter_test.dart';

import '../../components/pages/settings_provider_page.dart';
import '../../core/utils/trackstate_test_harness.dart';

void main() {
  testWidgets('TS-45: Settings provider selector shows Local Git stacked config fields', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      await TrackStateTestHarness.pumpApp(tester);
      final settingsPage = SettingsProviderPage(tester);

      await settingsPage.open();

      expect(
        settingsPage.settingsHeading,
        findsOneWidget,
        reason:
            'The Settings screen should open with the Project Settings heading.',
      );
      expect(
        settingsPage.localGitOption,
        findsAtLeastNWidgets(1),
        reason:
            'The Settings screen should show a Local Git provider row inside the provider selector.',
      );

      await settingsPage.tapLocalGitProvider();
      await settingsPage.scrollSettingsBody();

      expect(
        settingsPage.repositoryPathField,
        findsOneWidget,
        reason:
            'Selecting Local Git should reveal the Repository Path field below the provider row.',
      );
      expect(
        settingsPage.writeBranchField,
        findsOneWidget,
        reason:
            'Selecting Local Git should reveal the Write Branch field below the provider row.',
      );
      expect(
        settingsPage.githubTokenField,
        findsNothing,
        reason:
            'Selecting Local Git should clear any previously active hosted-provider configuration.',
      );

      final localGitRect = tester.getRect(settingsPage.localGitOption.first);
      final repositoryPathRect = tester.getRect(
        settingsPage.repositoryPathField,
      );
      final writeBranchRect = tester.getRect(settingsPage.writeBranchField);

      expect(
        repositoryPathRect.top,
        greaterThan(localGitRect.bottom),
        reason:
            'Repository Path should be rendered below the selected Local Git option.',
      );
      expect(
        writeBranchRect.top,
        greaterThan(repositoryPathRect.bottom),
        reason:
            'Write Branch should be stacked below Repository Path in the active Local Git configuration.',
      );
      expect(
        (repositoryPathRect.left - writeBranchRect.left).abs(),
        lessThan(24),
        reason:
            'Repository Path and Write Branch should align as stacked fields in a single column.',
      );
    } finally {
      TrackStateTestHarness.resetView(tester);
      semantics.dispose();
    }
  });
}
