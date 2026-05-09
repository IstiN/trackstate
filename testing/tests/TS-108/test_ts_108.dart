import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';

void main() {
  testWidgets('TS-108 guest mode renders the unauthenticated profile surface', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    final TrackStateAppComponent screen = defaultTestingDependencies
        .createTrackStateAppScreen(tester);

    try {
      await screen.pump(const DemoTrackStateRepository());

      screen.expectGuestProfileSurface(
        repositoryAccessLabel: 'Connect GitHub',
        initials: 'CG',
      );

      await screen.openRepositoryAccess();
      await screen.expectTextVisible('Connect GitHub');
      await screen.expectTextVisible('Fine-grained token');
      await screen.expectTextVisible('Remember on this browser');
      await screen.closeDialog('Cancel');
    } finally {
      screen.resetView();
      semantics.dispose();
    }
  });
}
