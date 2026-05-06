import 'package:trackstate/data/repositories/trackstate_runtime.dart';

class RuntimeStartupObservation {
  const RuntimeStartupObservation({
    required this.configuredRuntimeName,
    required this.configuredRuntime,
    required this.repositoryType,
    required this.usesLocalPersistence,
    required this.supportsGitHubAuth,
  });

  final String configuredRuntimeName;
  final TrackStateRuntime configuredRuntime;
  final String repositoryType;
  final bool usesLocalPersistence;
  final bool supportsGitHubAuth;

  bool get matchesHostedRuntime =>
      configuredRuntimeName == 'github' &&
      configuredRuntime == TrackStateRuntime.github &&
      repositoryType == 'SetupTrackStateRepository' &&
      usesLocalPersistence == false &&
      supportsGitHubAuth;
}

class RuntimeOverrideObservation {
  const RuntimeOverrideObservation({
    required this.isBlocked,
    this.configuredRuntimeName,
    this.repositoryType,
    this.usesLocalPersistence,
    this.supportsGitHubAuth,
    this.blockedReason,
  });

  final bool isBlocked;
  final String? configuredRuntimeName;
  final String? repositoryType;
  final bool? usesLocalPersistence;
  final bool? supportsGitHubAuth;
  final String? blockedReason;

  bool get matchesLocalRuntime =>
      isBlocked == false &&
      configuredRuntimeName == 'local-git' &&
      repositoryType == 'LocalTrackStateRepository' &&
      usesLocalPersistence == true &&
      supportsGitHubAuth == false;
}
