import '../models/runtime_ui_observation.dart';

abstract class RuntimeUiProbe {
  Future<RuntimeUiObservation> inspectHostedRuntimeExperience();
}
