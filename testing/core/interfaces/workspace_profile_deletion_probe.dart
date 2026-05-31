import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../models/workspace_profile_deletion_observation.dart';

abstract interface class WorkspaceProfileDeletionProbe {
  Future<WorkspaceProfileDeletionObservation> inspectActiveWorkspaceDeletion({
    required WorkspaceProfileInput remainingProfileInput,
    required WorkspaceProfileInput deletedActiveProfileInput,
    required String deletedActiveProfileToken,
  });
}
