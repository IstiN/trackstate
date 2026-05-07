import '../../core/interfaces/runtime_startup_probe.dart';
import '../../core/interfaces/runtime_ui_probe.dart';
import '../../core/models/runtime_startup_observation.dart';
import '../../core/models/runtime_ui_observation.dart';

class TrackStateRuntimeService {
  const TrackStateRuntimeService({required this.startupProbe, this.uiProbe});

  final RuntimeStartupProbe startupProbe;
  final RuntimeUiProbe? uiProbe;

  RuntimeStartupObservation inspectStartupResolution() {
    return startupProbe.inspectDefaultStartup();
  }

  Future<RuntimeOverrideObservation> inspectLocalGitOverrideAttempt() {
    return startupProbe.inspectLocalGitOverrideAttempt();
  }

  Future<RuntimeUiObservation> inspectHostedRuntimeExperience() {
    final probe = uiProbe;
    if (probe == null) {
      throw StateError('Hosted runtime UI probe is not configured.');
    }
    return probe.inspectHostedRuntimeExperience();
  }
}
