import '../models/runtime_ui_observation.dart';
import '../models/runtime_ui_stability_observation.dart';

abstract class RuntimeUiProbe {
  Future<RuntimeUiObservation> inspectHostedRuntimeExperience();

  Future<RuntimeUiStabilityObservation> inspectHostedRuntimeStability();
}
