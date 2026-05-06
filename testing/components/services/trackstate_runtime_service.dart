import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/runtime_startup_probe.dart';
import '../../core/interfaces/runtime_ui_probe.dart';
import '../../core/models/runtime_startup_observation.dart';
import '../../core/models/runtime_ui_observation.dart';

class TrackStateRuntimeService {
  const TrackStateRuntimeService({
    required this.startupProbe,
    required this.uiProbe,
  });

  final RuntimeStartupProbe startupProbe;
  final RuntimeUiProbe uiProbe;

  RuntimeStartupObservation inspectStartupResolution() {
    return startupProbe.inspectDefaultStartup();
  }

  RuntimeOverrideObservation inspectLocalGitOverrideAttempt() {
    return startupProbe.inspectLocalGitOverrideAttempt();
  }

  Future<RuntimeUiObservation> inspectHostedRuntimeExperience(
    WidgetTester tester,
  ) {
    return uiProbe.inspectHostedRuntimeExperience(tester);
  }
}
