import '../models/runtime_startup_observation.dart';

abstract class RuntimeStartupProbe {
  RuntimeStartupObservation inspectDefaultStartup();

  Future<RuntimeOverrideObservation> inspectLocalGitOverrideAttempt();
}
