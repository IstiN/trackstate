import 'package:trackstate/domain/models/workspace_profile_models.dart';

class WorkspaceProfileDuplicateUpdateObservation {
  const WorkspaceProfileDuplicateUpdateObservation({
    required this.primaryProfile,
    required this.editableProfile,
    required this.initialState,
    required this.duplicateUpdateAttempt,
    required this.finalState,
  });

  final WorkspaceProfile primaryProfile;
  final WorkspaceProfile editableProfile;
  final WorkspaceProfilesState initialState;
  final WorkspaceProfileUpdateAttempt duplicateUpdateAttempt;
  final WorkspaceProfilesState finalState;
}

class WorkspaceProfileUpdateAttempt {
  const WorkspaceProfileUpdateAttempt({
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
