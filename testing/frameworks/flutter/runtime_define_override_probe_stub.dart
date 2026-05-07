import '../../core/models/runtime_startup_observation.dart';

Future<RuntimeOverrideObservation> inspectLocalGitOverrideAttempt() async {
  return const RuntimeOverrideObservation(
    isBlocked: true,
    blockedReason:
        'Runtime define overrides can only be exercised from an IO test subprocess.',
  );
}
