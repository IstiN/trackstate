import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../core/interfaces/workspace_profile_duplicate_update_probe.dart';
import '../../core/models/workspace_profile_duplicate_update_observation.dart';

class WorkspaceProfileDuplicateUpdateValidator
    implements WorkspaceProfileDuplicateUpdateProbe {
  WorkspaceProfileDuplicateUpdateValidator({
    required WorkspaceProfileService service,
    required Future<void> Function() resetState,
  }) : _service = service,
       _resetState = resetState;

  static const WorkspaceProfileInput primaryProfileInput =
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: '/user/projects/app',
        defaultBranch: 'main',
      );

  static const WorkspaceProfileInput editableProfileInput =
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: '/user/projects/temp',
        defaultBranch: 'main',
      );

  static const WorkspaceProfileInput duplicateUpdateInput =
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.local,
        target: '/user/projects/app',
        defaultBranch: 'main',
      );

  final WorkspaceProfileService _service;
  final Future<void> Function() _resetState;

  @override
  Future<WorkspaceProfileDuplicateUpdateObservation> runScenario() async {
    await _resetState();

    final primaryProfile = await _service.createProfile(
      primaryProfileInput,
      select: false,
    );
    final editableProfile = await _service.createProfile(editableProfileInput);
    final initialState = await _service.loadState();

    final duplicateUpdateAttempt = await _attemptUpdate(
      editableProfile.id,
      duplicateUpdateInput,
      select: true,
    );
    final finalState = await _service.loadState();

    return WorkspaceProfileDuplicateUpdateObservation(
      primaryProfile: primaryProfile,
      editableProfile: editableProfile,
      initialState: initialState,
      duplicateUpdateAttempt: duplicateUpdateAttempt,
      finalState: finalState,
    );
  }

  Future<WorkspaceProfileUpdateAttempt> _attemptUpdate(
    String workspaceId,
    WorkspaceProfileInput input, {
    required bool select,
  }) async {
    try {
      final profile = await _service.updateProfile(
        workspaceId,
        input,
        select: select,
      );
      return WorkspaceProfileUpdateAttempt(profile: profile);
    } catch (error, stackTrace) {
      return WorkspaceProfileUpdateAttempt(
        error: error,
        stackTrace: stackTrace,
      );
    }
  }
}
