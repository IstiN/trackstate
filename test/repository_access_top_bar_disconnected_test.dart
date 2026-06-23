import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../testing/components/factories/testing_dependencies.dart';
import '../testing/tests/TS-1239/support/ts1239_repository_access_golden_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'disconnected hosted workspace keeps Connect GitHub CTA in top bar after initial search completes',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final app = defaultTestingDependencies.createTrackStateAppScreen(tester);
      final fixture = Ts1239RepositoryAccessGoldenFixture();

      await app.pump(fixture.createRepository());
      await tester.pumpAndSettle();

      expect(
        app.topBarVisibleTextsSnapshot(),
        contains(Ts1239RepositoryAccessGoldenFixture.disconnectedLabel),
        reason: 'The top bar should expose the Connect GitHub action for a '
            'disconnected hosted workspace once the initial search has completed.',
      );

      expect(
        await app.isRepositoryAccessBannerVisible(
          title: Ts1239RepositoryAccessGoldenFixture.disconnectedTitle,
          message: Ts1239RepositoryAccessGoldenFixture.disconnectedMessage,
        ),
        isTrue,
        reason: 'The global repository-access banner should remain visible.',
      );

      final errors = <String>[];
      while (true) {
        final error = tester.takeException();
        if (error == null) break;
        errors.add(error.toString());
      }
      expect(errors, isEmpty, reason: 'No framework overflow/layout errors');

      semantics.dispose();
    },
  );
}
