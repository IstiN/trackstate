import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/runtime_startup_probe.dart';
import '../../core/interfaces/runtime_ui_probe.dart';
import '../../core/models/runtime_startup_observation.dart';
import '../../core/models/runtime_ui_observation.dart';
import '../../frameworks/flutter/runtime_probes.dart';

class TrackStateRuntimeService {
  const TrackStateRuntimeService({
    required this.startupProbe,
    required this.uiProbe,
  });

  factory TrackStateRuntimeService.flutter() {
    return const TrackStateRuntimeService(
      startupProbe: FlutterRuntimeStartupProbe(),
      uiProbe: FlutterRuntimeUiProbe(),
    );
  }

  final RuntimeStartupProbe startupProbe;
  final RuntimeUiProbe uiProbe;

  RuntimeStartupObservation inspectStartupResolution() {
    return startupProbe.inspectDefaultStartup();
  }

  Future<RuntimeOverrideObservation> inspectLocalGitOverrideAttempt() {
    return startupProbe.inspectLocalGitOverrideAttempt();
  }

  Future<RuntimeUiObservation> inspectHostedRuntimeExperience(
    WidgetTester tester,
  ) {
    return uiProbe.inspectHostedRuntimeExperience(tester);
  }
}
