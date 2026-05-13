import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

class WorkspaceProfileDuplicateTargetValidator {
  WorkspaceProfileDuplicateTargetValidator({WorkspaceProfileService? service})
    : _service =
          service ??
          SharedPreferencesWorkspaceProfileService(
            authStore: _MemoryAuthStore(),
          );

  static const WorkspaceProfileInput existingProfileInput =
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: '/user/projects/ts',
        defaultBranch: 'main',
      );

  static const WorkspaceProfileInput duplicateWriteBranchInput =
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: '/user/projects/ts',
        defaultBranch: 'main',
        writeBranch: 'feature-x',
      );

  static const WorkspaceProfileInput differentDefaultBranchInput =
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: '/user/projects/ts',
        defaultBranch: 'develop',
      );

  final WorkspaceProfileService _service;

  Future<WorkspaceProfileDuplicateTargetObservation> runScenario() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});

    final seededProfile = await _service.createProfile(existingProfileInput);
    final seededState = await _service.loadState();

    final duplicateAttempt = await _attemptCreate(
      duplicateWriteBranchInput,
      select: false,
    );
    final afterDuplicateState = await _service.loadState();

    final differentDefaultBranchAttempt = await _attemptCreate(
      differentDefaultBranchInput,
      select: false,
    );
    final finalState = await _service.loadState();

    return WorkspaceProfileDuplicateTargetObservation(
      seededProfile: seededProfile,
      seededState: seededState,
      duplicateAttempt: duplicateAttempt,
      afterDuplicateState: afterDuplicateState,
      differentDefaultBranchAttempt: differentDefaultBranchAttempt,
      finalState: finalState,
    );
  }

  Future<WorkspaceProfileCreateAttempt> _attemptCreate(
    WorkspaceProfileInput input, {
    required bool select,
  }) async {
    try {
      final profile = await _service.createProfile(input, select: select);
      return WorkspaceProfileCreateAttempt(profile: profile);
    } catch (error, stackTrace) {
      return WorkspaceProfileCreateAttempt(
        error: error,
        stackTrace: stackTrace,
      );
    }
  }
}

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

class _MemoryAuthStore implements TrackStateAuthStore {
  @override
  Future<void> clearToken({String? repository, String? workspaceId}) async {}

  @override
  Future<String?> migrateLegacyRepositoryToken({
    required String repository,
    required String workspaceId,
  }) async => null;

  @override
  Future<void> moveToken({
    required String fromWorkspaceId,
    required String toWorkspaceId,
  }) async {}

  @override
  Future<String?> readToken({String? repository, String? workspaceId}) async =>
      null;

  @override
  Future<void> saveToken(
    String token, {
    String? repository,
    String? workspaceId,
  }) async {}
}
