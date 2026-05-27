import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

void main() {
  test(
    'saved workspace state falls back to the most recently opened profile',
    () {
      final state = WorkspaceProfilesState(
        profiles: const [
          WorkspaceProfile(
            id: 'hosted:trackstate/trackstate@main',
            displayName: 'trackstate/trackstate',
            targetType: WorkspaceProfileTargetType.hosted,
            target: 'trackstate/trackstate',
            defaultBranch: 'main',
            writeBranch: 'main',
            lastOpenedAt: null,
          ),
          WorkspaceProfile(
            id: 'local:/tmp/demo@main',
            displayName: 'demo',
            targetType: WorkspaceProfileTargetType.local,
            target: '/tmp/demo',
            defaultBranch: 'main',
            writeBranch: 'main',
            lastOpenedAt: null,
          ),
        ],
        activeWorkspaceId: 'missing-workspace',
        migrationComplete: true,
      );

      expect(state.activeWorkspace?.displayName, 'demo');
    },
  );
}
