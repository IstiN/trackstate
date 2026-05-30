import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../testing/components/factories/testing_dependencies.dart';
import '../testing/fixtures/settings/local_git_settings_screen_context.dart';
import '../testing/tests/TS-464/support/ts464_locale_addition_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'local git locale add flow scaffolds locale files after tapping Save',
    (tester) async {
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      final robot = createLocalGitSettingsScreenRobot(tester);
      final fixture = await tester.runAsync(Ts464LocaleAdditionFixture.create);

      expect(fixture, isNotNull);

      addTearDown(() async {
        await tester.runAsync(() => fixture!.dispose());
      });

      final projectFile = File('${fixture!.repositoryPath}/DEMO/project.json');
      final frenchLocaleFile = File(
        '${fixture.repositoryPath}/DEMO/config/i18n/fr.json',
      );

      await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
      await screen.openSection('Settings');
      await robot.openLocalesTab();

      expect(await screen.tapVisibleControl('Add locale'), isTrue);
      expect(await screen.isDropdownFieldVisible('Locale code'), isTrue);

      await screen.selectDropdownOption('Locale code', optionText: 'fr');
      expect(await screen.readDropdownFieldValue('Locale code'), 'fr');

      expect(await screen.tapVisibleControl('Save'), isTrue);
      await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

      final projectJson =
          jsonDecode(await tester.runAsync(projectFile.readAsString) ?? '{}')
              as Map<String, Object?>;
      final supportedLocales = [
        for (final locale in (projectJson['supportedLocales'] as List? ?? const []))
          '$locale',
      ];

      expect(robot.visibleTexts(), contains('fr'));
      expect(await tester.runAsync(frenchLocaleFile.exists), isTrue);
      expect(supportedLocales, contains('fr'));
    },
  );
}
