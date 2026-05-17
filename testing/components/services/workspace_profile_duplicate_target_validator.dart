import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../core/interfaces/workspace_profile_duplicate_target_probe.dart';
import '../../core/models/workspace_profile_duplicate_target_observation.dart';

class WorkspaceProfileDuplicateTargetValidator
    implements WorkspaceProfileDuplicateTargetProbe {
  WorkspaceProfileDuplicateTargetValidator({
    required WorkspaceProfileService service,
    required Future<void> Function() resetState,
  }) : _service = service,
       _resetState = resetState;

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
  final Future<void> Function() _resetState;

  @override
  Future<WorkspaceProfileDuplicateTargetObservation> runScenario() async {
    await _resetState();

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
