import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';

import '../../fixtures/hosted_runtime_client_fixture.dart';
import '../services/trackstate_runtime_service.dart';
import '../../frameworks/flutter/runtime_probes.dart';

TrackStateRuntimeService createTrackStateStartupService() {
  return TrackStateRuntimeService(
    startupProbe: const FlutterRuntimeStartupProbe(),
  );
}

TrackStateRuntimeService createTrackStateRuntimeUiService(WidgetTester tester) {
  return TrackStateRuntimeService(
    startupProbe: const FlutterRuntimeStartupProbe(),
    uiProbe: FlutterRuntimeUiProbe(
      tester: tester,
      createRepository: () =>
          createTrackStateRepository(client: createHostedSetupClient()),
    ),
  );
}
