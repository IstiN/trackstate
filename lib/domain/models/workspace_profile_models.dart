enum WorkspaceProfileTargetType { hosted, local }

enum HostedWorkspaceAccessMode {
  disconnected,
  readOnly,
  writable,
  attachmentRestricted,
}

class WorkspaceProfileInput {
  const WorkspaceProfileInput({
    required this.targetType,
    required this.target,
    required this.defaultBranch,
    String? writeBranch,
  }) : writeBranch = writeBranch ?? defaultBranch;

  final WorkspaceProfileTargetType targetType;
  final String target;
  final String defaultBranch;
  final String writeBranch;

  bool get isValid =>
      _normalizeTarget(targetType, target).isNotEmpty &&
      _normalizeBranch(defaultBranch).isNotEmpty &&
      _normalizeBranch(writeBranch).isNotEmpty;
}

class WorkspaceProfile {
  const WorkspaceProfile({
    required this.id,
    required this.displayName,
    required this.targetType,
    required this.target,
    required this.defaultBranch,
    required this.writeBranch,
    this.lastOpenedAt,
    this.hostedAccessMode,
  });

  final String id;
  final String displayName;
  final WorkspaceProfileTargetType targetType;
  final String target;
  final String defaultBranch;
  final String writeBranch;
  final DateTime? lastOpenedAt;
  final HostedWorkspaceAccessMode? hostedAccessMode;

  bool get isHosted => targetType == WorkspaceProfileTargetType.hosted;
  bool get isLocal => targetType == WorkspaceProfileTargetType.local;

  String get normalizedTarget => _normalizeTarget(targetType, target);
  String get normalizedDefaultBranch => _normalizeBranch(defaultBranch);
  String get normalizedWriteBranch => _normalizeBranch(writeBranch);

  String get baseDisplayName => switch (targetType) {
    WorkspaceProfileTargetType.hosted => normalizedTarget,
    WorkspaceProfileTargetType.local => _localBaseDisplayName(normalizedTarget),
  };

  WorkspaceProfile copyWith({
    String? id,
    String? displayName,
    WorkspaceProfileTargetType? targetType,
    String? target,
    String? defaultBranch,
    String? writeBranch,
    Object? lastOpenedAt = _workspaceProfileNoop,
    Object? hostedAccessMode = _workspaceProfileNoop,
  }) {
    return WorkspaceProfile(
      id: id ?? this.id,
      displayName: displayName ?? this.displayName,
      targetType: targetType ?? this.targetType,
      target: target ?? this.target,
      defaultBranch: defaultBranch ?? this.defaultBranch,
      writeBranch: writeBranch ?? this.writeBranch,
      lastOpenedAt: identical(lastOpenedAt, _workspaceProfileNoop)
          ? this.lastOpenedAt
          : lastOpenedAt as DateTime?,
      hostedAccessMode: identical(hostedAccessMode, _workspaceProfileNoop)
          ? this.hostedAccessMode
          : hostedAccessMode as HostedWorkspaceAccessMode?,
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'id': id,
      'displayName': displayName,
      'targetType': targetType.name,
      'target': target,
      'defaultBranch': defaultBranch,
      'writeBranch': writeBranch,
      'lastOpenedAt': lastOpenedAt?.toUtc().toIso8601String(),
      'hostedAccessMode': hostedAccessMode?.name,
    };
  }

  static WorkspaceProfile fromJson(Map<String, Object?> json) {
    final targetTypeName = json['targetType']?.toString().trim();
    final targetType = WorkspaceProfileTargetType.values.firstWhere(
      (candidate) => candidate.name == targetTypeName,
      orElse: () => WorkspaceProfileTargetType.hosted,
    );
    final hostedAccessModeName = json['hostedAccessMode']?.toString().trim();
    final hostedAccessMode = HostedWorkspaceAccessMode.values.where(
      (candidate) => candidate.name == hostedAccessModeName,
    );
    final lastOpenedAtValue = json['lastOpenedAt']?.toString().trim();
    return WorkspaceProfile(
      id: json['id']?.toString() ?? '',
      displayName: json['displayName']?.toString() ?? '',
      targetType: targetType,
      target: json['target']?.toString() ?? '',
      defaultBranch: json['defaultBranch']?.toString() ?? '',
      writeBranch:
          json['writeBranch']?.toString() ??
          json['defaultBranch']?.toString() ??
          '',
      lastOpenedAt: lastOpenedAtValue == null || lastOpenedAtValue.isEmpty
          ? null
          : DateTime.tryParse(lastOpenedAtValue)?.toUtc(),
      hostedAccessMode:
          targetType == WorkspaceProfileTargetType.hosted &&
              hostedAccessMode.isNotEmpty
          ? hostedAccessMode.first
          : null,
    );
  }

  static WorkspaceProfile create(
    WorkspaceProfileInput input, {
    DateTime? lastOpenedAt,
  }) {
    final normalizedTarget = _normalizeTarget(input.targetType, input.target);
    final normalizedDefaultBranch = _normalizeBranch(input.defaultBranch);
    final normalizedWriteBranch = _normalizeBranch(input.writeBranch);
    return WorkspaceProfile(
      id: workspaceProfileId(
        targetType: input.targetType,
        target: normalizedTarget,
        defaultBranch: normalizedDefaultBranch,
        writeBranch: normalizedWriteBranch,
      ),
      displayName: '',
      targetType: input.targetType,
      target: normalizedTarget,
      defaultBranch: normalizedDefaultBranch,
      writeBranch: normalizedWriteBranch,
      lastOpenedAt: lastOpenedAt?.toUtc(),
      hostedAccessMode: null,
    );
  }
}

class WorkspaceProfilesState {
  const WorkspaceProfilesState({
    this.profiles = const <WorkspaceProfile>[],
    this.activeWorkspaceId,
    this.migrationComplete = false,
  });

  final List<WorkspaceProfile> profiles;
  final String? activeWorkspaceId;
  final bool migrationComplete;

  bool get hasProfiles => profiles.isNotEmpty;

  WorkspaceProfile? get activeWorkspace {
    final activeWorkspaceId = this.activeWorkspaceId;
    if (activeWorkspaceId == null || activeWorkspaceId.isEmpty) {
      return mostRecentlyOpenedWorkspace;
    }
    for (final profile in profiles) {
      if (profile.id == activeWorkspaceId) {
        return profile;
      }
    }
    return mostRecentlyOpenedWorkspace;
  }

  WorkspaceProfile? get mostRecentlyOpenedWorkspace {
    if (profiles.isEmpty) {
      return null;
    }
    final sortedProfiles = List<WorkspaceProfile>.of(profiles)
      ..sort(_workspaceProfileRecencyCompare);
    return sortedProfiles.first;
  }

  WorkspaceProfilesState copyWith({
    List<WorkspaceProfile>? profiles,
    Object? activeWorkspaceId = _workspaceProfileNoop,
    bool? migrationComplete,
  }) {
    return WorkspaceProfilesState(
      profiles: profiles ?? this.profiles,
      activeWorkspaceId: identical(activeWorkspaceId, _workspaceProfileNoop)
          ? this.activeWorkspaceId
          : activeWorkspaceId as String?,
      migrationComplete: migrationComplete ?? this.migrationComplete,
    );
  }
}

class WorkspaceProfileException implements Exception {
  const WorkspaceProfileException(this.message);

  final String message;

  @override
  String toString() => message;
}

String workspaceProfileId({
  required WorkspaceProfileTargetType targetType,
  required String target,
  required String defaultBranch,
  required String writeBranch,
}) {
  final prefix = switch (targetType) {
    WorkspaceProfileTargetType.hosted => 'hosted',
    WorkspaceProfileTargetType.local => 'local',
  };
  final normalizedTarget = _normalizeTarget(targetType, target);
  final normalizedDefaultBranch = _normalizeBranch(defaultBranch);
  final normalizedWriteBranch = _normalizeBranch(writeBranch);
  final baseId = '$prefix:$normalizedTarget@$normalizedDefaultBranch';
  return normalizedWriteBranch == normalizedDefaultBranch
      ? baseId
      : '$baseId:$normalizedWriteBranch';
}

List<WorkspaceProfile> resolveWorkspaceDisplayNames(
  Iterable<WorkspaceProfile> profiles,
) {
  final baseNameCounts = <String, int>{};
  for (final profile in profiles) {
    final baseName = profile.baseDisplayName;
    baseNameCounts.update(baseName, (count) => count + 1, ifAbsent: () => 1);
  }

  return [
    for (final profile in profiles)
      profile.copyWith(
        displayName: () {
          if ((baseNameCounts[profile.baseDisplayName] ?? 0) <= 1) {
            return profile.baseDisplayName;
          }
          final branchScopedCount = profiles
              .where(
                (candidate) =>
                    candidate.baseDisplayName == profile.baseDisplayName &&
                    candidate.normalizedDefaultBranch ==
                        profile.normalizedDefaultBranch,
              )
              .length;
          if (branchScopedCount <= 1 ||
              profile.normalizedWriteBranch ==
                  profile.normalizedDefaultBranch) {
            return '${profile.baseDisplayName} (${profile.defaultBranch})';
          }
          return '${profile.baseDisplayName} (${profile.defaultBranch} -> ${profile.writeBranch})';
        }(),
      ),
  ];
}

int _workspaceProfileRecencyCompare(
  WorkspaceProfile left,
  WorkspaceProfile right,
) {
  final leftTime = left.lastOpenedAt;
  final rightTime = right.lastOpenedAt;
  if (leftTime == null && rightTime == null) {
    return left.displayName.compareTo(right.displayName);
  }
  if (leftTime == null) {
    return 1;
  }
  if (rightTime == null) {
    return -1;
  }
  final timeComparison = rightTime.compareTo(leftTime);
  if (timeComparison != 0) {
    return timeComparison;
  }
  return left.displayName.compareTo(right.displayName);
}

int compareWorkspaceProfileRecency(
  WorkspaceProfile left,
  WorkspaceProfile right,
) => _workspaceProfileRecencyCompare(left, right);

String normalizeWorkspaceTarget(
  WorkspaceProfileTargetType targetType,
  String target,
) => _normalizeTarget(targetType, target);

String normalizeWorkspaceBranch(String branch) => _normalizeBranch(branch);

String _normalizeTarget(WorkspaceProfileTargetType targetType, String target) {
  final trimmed = target.trim();
  if (trimmed.isEmpty) {
    return '';
  }
  return switch (targetType) {
    WorkspaceProfileTargetType.hosted => trimmed.toLowerCase(),
    WorkspaceProfileTargetType.local => _normalizeLocalPath(trimmed),
  };
}

String _normalizeBranch(String branch) => branch.trim();

String _normalizeLocalPath(String path) {
  var normalized = path.replaceAll('\\', '/').trim();
  while (normalized.length > 1 && normalized.endsWith('/')) {
    normalized = normalized.substring(0, normalized.length - 1);
  }
  return normalized;
}

String _localBaseDisplayName(String target) {
  final lastSeparator = target.lastIndexOf('/');
  if (lastSeparator == -1 || lastSeparator == target.length - 1) {
    return target;
  }
  return target.substring(lastSeparator + 1);
}

const Object _workspaceProfileNoop = Object();
