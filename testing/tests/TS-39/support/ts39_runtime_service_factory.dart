import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';

import '../../../components/services/trackstate_runtime_service.dart';
import '../../../frameworks/flutter/runtime_probes.dart';
import 'ts39_hosted_runtime_fixture.dart';

TrackStateRuntimeService createTrackStateRuntimeService() {
  return TrackStateRuntimeService(
    startupProbe: const FlutterRuntimeStartupProbe(),
    uiProbe: FlutterRuntimeUiProbe(
      createRepository: () =>
          createTrackStateRepository(client: createHostedSetupClient()),
    ),
  );
}
