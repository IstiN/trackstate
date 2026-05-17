import 'package:trackstate/domain/models/workspace_profile_models.dart';

class WorkspaceProfileDuplicateTargetObservation {
  const WorkspaceProfileDuplicateTargetObservation({
    required this.seededProfile,
    required this.seededState,
    required this.duplicateAttempt,
    required this.afterDuplicateState,
    required this.differentDefaultBranchAttempt,
    required this.finalState,
  });

  final WorkspaceProfile seededProfile;
  final WorkspaceProfilesState seededState;
  final WorkspaceProfileCreateAttempt duplicateAttempt;
  final WorkspaceProfilesState afterDuplicateState;
  final WorkspaceProfileCreateAttempt differentDefaultBranchAttempt;
  final WorkspaceProfilesState finalState;
}

class WorkspaceProfileCreateAttempt {
  const WorkspaceProfileCreateAttempt({
    this.profile,
    this.error,
    this.stackTrace,
  });

  final WorkspaceProfile? profile;
  final Object? error;
  final StackTrace? stackTrace;

  bool get succeeded => profile != null;
  String get errorType => error?.runtimeType.toString() ?? '<none>';
  String get errorMessage => error?.toString() ?? '<none>';
}
