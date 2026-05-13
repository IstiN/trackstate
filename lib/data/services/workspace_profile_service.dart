import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../../domain/models/workspace_profile_models.dart';
import 'trackstate_auth_store.dart';

abstract interface class WorkspaceProfileService {
  Future<WorkspaceProfilesState> loadState();
  Future<WorkspaceProfile> createProfile(
    WorkspaceProfileInput input, {
    bool select = true,
  });
  Future<WorkspaceProfile> updateProfile(
    String workspaceId,
    WorkspaceProfileInput input, {
    bool select = true,
  });
  Future<WorkspaceProfilesState> selectProfile(String workspaceId);
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId);
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  );
}

class SharedPreferencesWorkspaceProfileService
    implements WorkspaceProfileService {
  const SharedPreferencesWorkspaceProfileService({
    TrackStateAuthStore authStore = const SharedPreferencesTrackStateAuthStore(),
    DateTime Function()? now,
  }) : _authStore = authStore,
       _now = now;

  static const _stateKey = 'trackstate.workspaceProfiles.state';

  final TrackStateAuthStore _authStore;
  final DateTime Function()? _now;

  DateTime get _clock => (_now ?? DateTime.now)().toUtc();

  @override
  Future<WorkspaceProfilesState> loadState() async {
    final preferences = await SharedPreferences.getInstance();
    final state = _readState(preferences);
    final normalizedState = _normalizeState(state);
    if (!_statesEqual(state, normalizedState)) {
      await _writeState(preferences, normalizedState);
    }
    return normalizedState;
  }

  @override
  Future<WorkspaceProfile> createProfile(
    WorkspaceProfileInput input, {
    bool select = true,
  }) async {
    _validateInput(input);
    final preferences = await SharedPreferences.getInstance();
    final state = _normalizeState(_readState(preferences));
    final nextProfile = WorkspaceProfile.create(
      input,
      lastOpenedAt: select ? _clock : null,
    );
    _throwIfDuplicate(state.profiles, nextProfile, ignoredWorkspaceId: null);

    final nextProfiles = resolveWorkspaceDisplayNames([
      ...state.profiles,
      nextProfile,
    ])..sort(compareWorkspaceProfileRecency);
    final nextState = WorkspaceProfilesState(
      profiles: nextProfiles,
      activeWorkspaceId: select ? nextProfile.id : state.activeWorkspaceId,
      migrationComplete: true,
    );
    await _writeState(preferences, nextState);
    return nextState.profiles.firstWhere((profile) => profile.id == nextProfile.id);
  }

  @override
  Future<WorkspaceProfile> updateProfile(
    String workspaceId,
    WorkspaceProfileInput input, {
    bool select = true,
  }) async {
    _validateInput(input);
    final preferences = await SharedPreferences.getInstance();
    final state = _normalizeState(_readState(preferences));
    final existingProfile = state.profiles.where((profile) => profile.id == workspaceId);
    if (existingProfile.isEmpty) {
      throw WorkspaceProfileException('Saved workspace $workspaceId was not found.');
    }

    final currentProfile = existingProfile.first;
    final updatedProfile = WorkspaceProfile.create(
      input,
      lastOpenedAt:
          select ? _clock : (currentProfile.lastOpenedAt?.toUtc()),
    );
    _throwIfDuplicate(
      state.profiles,
      updatedProfile,
      ignoredWorkspaceId: workspaceId,
    );

    final nextProfiles = resolveWorkspaceDisplayNames([
      for (final profile in state.profiles)
        if (profile.id == workspaceId) updatedProfile else profile,
    ])..sort(compareWorkspaceProfileRecency);
    final nextActiveWorkspaceId =
        state.activeWorkspaceId == workspaceId || select
        ? updatedProfile.id
        : state.activeWorkspaceId;
    final nextState = WorkspaceProfilesState(
      profiles: nextProfiles,
      activeWorkspaceId: nextActiveWorkspaceId,
      migrationComplete: true,
    );
    await _writeState(preferences, nextState);
    if (workspaceId != updatedProfile.id) {
      await _authStore.moveToken(
        fromWorkspaceId: workspaceId,
        toWorkspaceId: updatedProfile.id,
      );
    }
    return nextState.profiles.firstWhere(
      (profile) => profile.id == updatedProfile.id,
    );
  }

  @override
  Future<WorkspaceProfilesState> selectProfile(String workspaceId) async {
    final preferences = await SharedPreferences.getInstance();
    final state = _normalizeState(_readState(preferences));
    WorkspaceProfile? selectedProfile;
    final nextProfiles = [
      for (final profile in state.profiles)
        if (profile.id == workspaceId)
          selectedProfile = profile.copyWith(lastOpenedAt: _clock)
        else
          profile,
    ];
    if (selectedProfile == null) {
      throw WorkspaceProfileException('Saved workspace $workspaceId was not found.');
    }
    final nextState = WorkspaceProfilesState(
      profiles: resolveWorkspaceDisplayNames(nextProfiles)
        ..sort(compareWorkspaceProfileRecency),
      activeWorkspaceId: workspaceId,
      migrationComplete: true,
    );
    await _writeState(preferences, nextState);
    return nextState;
  }

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) async {
    final preferences = await SharedPreferences.getInstance();
    final state = _normalizeState(_readState(preferences));
    final nextProfiles = resolveWorkspaceDisplayNames(
      state.profiles.where((profile) => profile.id != workspaceId),
    )..sort(compareWorkspaceProfileRecency);
    final fallbackWorkspace = nextProfiles.isEmpty ? null : nextProfiles.first;
    final nextActiveWorkspaceId =
        state.activeWorkspaceId == workspaceId ? fallbackWorkspace?.id : state.activeWorkspaceId;
    final nextState = WorkspaceProfilesState(
      profiles: nextProfiles,
      activeWorkspaceId: nextActiveWorkspaceId,
      migrationComplete: true,
    );
    await _writeState(preferences, nextState);
    await _authStore.clearToken(workspaceId: workspaceId);
    return nextState;
  }

  @override
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  ) async {
    final preferences = await SharedPreferences.getInstance();
    final state = _normalizeState(_readState(preferences));
    if (state.migrationComplete) {
      return state.activeWorkspace;
    }
    if (state.profiles.isNotEmpty) {
      final nextState = state.copyWith(migrationComplete: true);
      await _writeState(preferences, nextState);
      return nextState.activeWorkspace;
    }
    if (input == null || !input.isValid) {
      final nextState = state.copyWith(migrationComplete: true);
      await _writeState(preferences, nextState);
      return null;
    }

    final seededProfile = WorkspaceProfile.create(input, lastOpenedAt: _clock);
    final nextState = WorkspaceProfilesState(
      profiles: resolveWorkspaceDisplayNames([seededProfile]),
      activeWorkspaceId: seededProfile.id,
      migrationComplete: true,
    );
    await _writeState(preferences, nextState);
    if (seededProfile.isHosted) {
      await _authStore.migrateLegacyRepositoryToken(
        repository: seededProfile.target,
        workspaceId: seededProfile.id,
      );
    }
    return nextState.activeWorkspace;
  }

  WorkspaceProfilesState _readState(SharedPreferences preferences) {
    final rawState = preferences.getString(_stateKey);
    if (rawState == null || rawState.trim().isEmpty) {
      return const WorkspaceProfilesState();
    }
    final decoded = jsonDecode(rawState);
    if (decoded is! Map<String, Object?>) {
      return const WorkspaceProfilesState();
    }
    final rawProfiles = decoded['profiles'];
    final profiles = rawProfiles is List<Object?>
        ? rawProfiles
              .whereType<Map<String, Object?>>()
              .map(WorkspaceProfile.fromJson)
              .toList(growable: false)
        : const <WorkspaceProfile>[];
    return WorkspaceProfilesState(
      profiles: profiles,
      activeWorkspaceId: decoded['activeWorkspaceId']?.toString(),
      migrationComplete: decoded['migrationComplete'] == true,
    );
  }

  WorkspaceProfilesState _normalizeState(WorkspaceProfilesState state) {
    final normalizedProfiles = resolveWorkspaceDisplayNames([
      for (final profile in state.profiles)
        WorkspaceProfile(
          id: workspaceProfileId(
            targetType: profile.targetType,
            target: profile.target,
            defaultBranch: profile.defaultBranch,
          ),
          displayName: profile.displayName,
          targetType: profile.targetType,
          target: normalizeWorkspaceTarget(profile.targetType, profile.target),
          defaultBranch: normalizeWorkspaceBranch(profile.defaultBranch),
          writeBranch: normalizeWorkspaceBranch(profile.writeBranch),
          lastOpenedAt: profile.lastOpenedAt?.toUtc(),
        ),
    ])..sort(compareWorkspaceProfileRecency);
    final activeWorkspaceId = normalizedProfiles.any(
          (profile) => profile.id == state.activeWorkspaceId,
        )
        ? state.activeWorkspaceId
        : normalizedProfiles.isEmpty
        ? null
        : normalizedProfiles.first.id;
    return WorkspaceProfilesState(
      profiles: normalizedProfiles,
      activeWorkspaceId: activeWorkspaceId,
      migrationComplete: state.migrationComplete,
    );
  }

  Future<void> _writeState(
    SharedPreferences preferences,
    WorkspaceProfilesState state,
  ) async {
    await preferences.setString(
      _stateKey,
      jsonEncode({
        'activeWorkspaceId': state.activeWorkspaceId,
        'migrationComplete': state.migrationComplete,
        'profiles': [
          for (final profile in state.profiles) profile.toJson(),
        ],
      }),
    );
  }

  void _validateInput(WorkspaceProfileInput input) {
    if (!input.isValid) {
      throw const WorkspaceProfileException(
        'Saved workspace target and branches are required.',
      );
    }
  }

  void _throwIfDuplicate(
    List<WorkspaceProfile> existingProfiles,
    WorkspaceProfile candidate, {
    required String? ignoredWorkspaceId,
  }) {
    for (final profile in existingProfiles) {
      if (profile.id == ignoredWorkspaceId) {
        continue;
      }
      if (profile.targetType == candidate.targetType &&
          profile.normalizedTarget == candidate.normalizedTarget &&
          profile.normalizedDefaultBranch == candidate.normalizedDefaultBranch) {
        throw WorkspaceProfileException(
          'A saved workspace already exists for ${candidate.target} on ${candidate.defaultBranch}.',
        );
      }
    }
  }

  bool _statesEqual(WorkspaceProfilesState left, WorkspaceProfilesState right) {
    if (left.activeWorkspaceId != right.activeWorkspaceId ||
        left.migrationComplete != right.migrationComplete ||
        left.profiles.length != right.profiles.length) {
      return false;
    }
    for (var index = 0; index < left.profiles.length; index += 1) {
      final leftProfile = left.profiles[index];
      final rightProfile = right.profiles[index];
      if (leftProfile.id != rightProfile.id ||
          leftProfile.displayName != rightProfile.displayName ||
          leftProfile.targetType != rightProfile.targetType ||
          leftProfile.target != rightProfile.target ||
          leftProfile.defaultBranch != rightProfile.defaultBranch ||
          leftProfile.writeBranch != rightProfile.writeBranch ||
          leftProfile.lastOpenedAt != rightProfile.lastOpenedAt) {
        return false;
      }
    }
    return true;
  }
}
