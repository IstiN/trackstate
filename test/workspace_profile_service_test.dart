import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'createProfile allows distinct write branches and rejects exact duplicates',
    () async {
      final service = SharedPreferencesWorkspaceProfileService(
        authStore: _MemoryAuthStore(),
      );

      final featureA = await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate',
          defaultBranch: 'main',
          writeBranch: 'feature/ts-632',
        ),
      );
      final featureB = await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate',
          defaultBranch: 'main',
          writeBranch: 'other-branch',
        ),
        select: false,
      );

      expect(featureA.id, 'local:/tmp/trackstate@main:feature/ts-632');
      expect(featureB.id, 'local:/tmp/trackstate@main:other-branch');

      expect(
        () => service.createProfile(
          const WorkspaceProfileInput(
            targetType: WorkspaceProfileTargetType.local,
            target: '/tmp/trackstate',
            defaultBranch: 'main',
            writeBranch: 'feature/ts-632',
          ),
        ),
        throwsA(isA<WorkspaceProfileException>()),
      );
    },
  );

  test(
    'updateProfile moves workspace-scoped credentials when the workspace id changes',
    () async {
      final authStore = _MemoryAuthStore()
        ..workspaceTokens['hosted:trackstate/trackstate@main'] = 'token';
      final service = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
        now: () => DateTime.utc(2026, 5, 13, 12),
      );

      await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'trackstate/trackstate',
          defaultBranch: 'main',
        ),
      );

      final updated = await service.updateProfile(
        'hosted:trackstate/trackstate@main',
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'trackstate/trackstate',
          defaultBranch: 'main',
          writeBranch: 'release',
        ),
      );

      expect(updated.id, 'hosted:trackstate/trackstate@main:release');
      expect(
        authStore.workspaceTokens['hosted:trackstate/trackstate@main:release'],
        'token',
      );
      expect(
        authStore.workspaceTokens.containsKey(
          'hosted:trackstate/trackstate@main',
        ),
        isFalse,
      );
    },
  );

  test(
    'deleteProfile clears scoped credentials and falls back to the most recently opened workspace',
    () async {
      final authStore = _MemoryAuthStore()
        ..workspaceTokens['local:/tmp/alpha@main'] = 'alpha-token'
        ..workspaceTokens['local:/tmp/beta@main'] = 'beta-token';
      final service = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
        now: () => DateTime.utc(2026, 5, 13, 18),
      );

      await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/alpha',
          defaultBranch: 'main',
        ),
      );
      await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/beta',
          defaultBranch: 'main',
        ),
      );

      final nextState = await service.deleteProfile('local:/tmp/beta@main');

      expect(nextState.activeWorkspaceId, 'local:/tmp/alpha@main');
      expect(authStore.clearedWorkspaceIds, contains('local:/tmp/beta@main'));
    },
  );

  test(
    'ensureLegacyContextMigrated seeds one workspace and migrates the active legacy token only once',
    () async {
      final authStore = _MemoryAuthStore()
        ..legacyTokens['trackstate/trackstate'] = 'legacy-token';
      final service = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
        now: () => DateTime.utc(2026, 5, 13, 18, 39),
      );

      final seededWorkspace = await service.ensureLegacyContextMigrated(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'trackstate/trackstate',
          defaultBranch: 'main',
        ),
      );
      final secondAttempt = await service.ensureLegacyContextMigrated(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'other/repository',
          defaultBranch: 'main',
        ),
      );
      final state = await service.loadState();

      expect(seededWorkspace?.id, 'hosted:trackstate/trackstate@main');
      expect(secondAttempt?.id, 'hosted:trackstate/trackstate@main');
      expect(state.profiles, hasLength(1));
      expect(
        authStore.workspaceTokens['hosted:trackstate/trackstate@main'],
        'legacy-token',
      );
      expect(
        authStore.legacyTokens.containsKey('trackstate/trackstate'),
        isFalse,
      );
    },
  );

  test(
    'display names include the branch only when needed to distinguish saved workspaces',
    () async {
      final service = SharedPreferencesWorkspaceProfileService(
        authStore: _MemoryAuthStore(),
      );

      final mainWorkspace = await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'trackstate/trackstate',
          defaultBranch: 'main',
        ),
      );
      final releaseWorkspace = await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'trackstate/trackstate',
          defaultBranch: 'release',
        ),
        select: false,
      );
      final state = await service.loadState();

      expect(
        state.profiles
            .firstWhere((profile) => profile.id == mainWorkspace.id)
            .displayName,
        'trackstate/trackstate (main)',
      );
      expect(
        state.profiles
            .firstWhere((profile) => profile.id == releaseWorkspace.id)
            .displayName,
        'trackstate/trackstate (release)',
      );
    },
  );

  test(
    'display names include the write branch when the default branch is shared',
    () async {
      final service = SharedPreferencesWorkspaceProfileService(
        authStore: _MemoryAuthStore(),
      );

      final mainWorkspace = await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'trackstate/trackstate',
          defaultBranch: 'main',
        ),
      );
      final featureWorkspace = await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'trackstate/trackstate',
          defaultBranch: 'main',
          writeBranch: 'feature/ts-632',
        ),
        select: false,
      );
      final state = await service.loadState();

      expect(
        state.profiles
            .firstWhere((profile) => profile.id == mainWorkspace.id)
            .displayName,
        'trackstate/trackstate (main)',
      );
      expect(
        state.profiles
            .firstWhere((profile) => profile.id == featureWorkspace.id)
            .displayName,
        'trackstate/trackstate (main -> feature/ts-632)',
      );
    },
  );
}

class _MemoryAuthStore implements TrackStateAuthStore {
  final Map<String, String> legacyTokens = <String, String>{};
  final Map<String, String> workspaceTokens = <String, String>{};
  final List<String> clearedWorkspaceIds = <String>[];

  @override
  Future<void> clearToken({String? repository, String? workspaceId}) async {
    if (workspaceId != null) {
      clearedWorkspaceIds.add(workspaceId);
      workspaceTokens.remove(workspaceId);
    }
    if (repository != null) {
      legacyTokens.remove(repository);
    }
  }

  @override
  Future<String?> migrateLegacyRepositoryToken({
    required String repository,
    required String workspaceId,
  }) async {
    final token = legacyTokens.remove(repository);
    if (token != null) {
      workspaceTokens[workspaceId] = token;
    }
    return token;
  }

  @override
  Future<void> moveToken({
    required String fromWorkspaceId,
    required String toWorkspaceId,
  }) async {
    final token = workspaceTokens.remove(fromWorkspaceId);
    if (token != null) {
      workspaceTokens[toWorkspaceId] = token;
    }
  }

  @override
  Future<String?> readToken({String? repository, String? workspaceId}) async {
    if (workspaceId != null && workspaceTokens.containsKey(workspaceId)) {
      return workspaceTokens[workspaceId];
    }
    return repository == null ? null : legacyTokens[repository];
  }

  @override
  Future<void> saveToken(
    String token, {
    String? repository,
    String? workspaceId,
  }) async {
    if (workspaceId != null) {
      workspaceTokens[workspaceId] = token;
    }
    if (repository != null) {
      legacyTokens[repository] = token;
    }
  }
}
