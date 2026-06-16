import 'core_enums.dart';

class TrackStateIssue {
  const TrackStateIssue({
    required this.key,
    required this.project,
    required this.issueType,
    required this.issueTypeId,
    required this.status,
    required this.statusId,
    required this.priority,
    required this.priorityId,
    required this.summary,
    required this.description,
    required this.assignee,
    required this.reporter,
    required this.labels,
    required this.components,
    required this.fixVersionIds,
    required this.watchers,
    required this.customFields,
    required this.parentKey,
    required this.epicKey,
    required this.parentPath,
    required this.epicPath,
    required this.progress,
    required this.updatedLabel,
    required this.acceptanceCriteria,
    required this.comments,
    required this.links,
    required this.attachments,
    required this.isArchived,
    this.hasDetailLoaded = true,
    this.hasCommentsLoaded = true,
    this.hasAttachmentsLoaded = true,
    this.resolutionId,
    this.storagePath = '',
    this.rawMarkdown = '',
  });

  final String key;
  final String project;
  final IssueType issueType;
  final String issueTypeId;
  final IssueStatus status;
  final String statusId;
  final IssuePriority priority;
  final String priorityId;
  final String summary;
  final String description;
  final String assignee;
  final String reporter;
  final List<String> labels;
  final List<String> components;
  final List<String> fixVersionIds;
  final List<String> watchers;
  final Map<String, Object?> customFields;
  final String? parentKey;
  final String? epicKey;
  final String? parentPath;
  final String? epicPath;
  final double progress;
  final String updatedLabel;
  final List<String> acceptanceCriteria;
  final List<IssueComment> comments;
  final List<IssueLink> links;
  final List<IssueAttachment> attachments;
  final bool isArchived;
  final bool hasDetailLoaded;
  final bool hasCommentsLoaded;
  final bool hasAttachmentsLoaded;
  final String? resolutionId;
  final String storagePath;
  final String rawMarkdown;

  bool get isEpic => issueType == IssueType.epic;

  TrackStateIssue copyWith({
    IssueStatus? status,
    String? statusId,
    String? description,
    String? rawMarkdown,
    String? updatedLabel,
    bool? isArchived,
    String? storagePath,
    bool? hasDetailLoaded,
    bool? hasCommentsLoaded,
    bool? hasAttachmentsLoaded,
    List<IssueComment>? comments,
    List<IssueLink>? links,
    List<IssueAttachment>? attachments,
  }) {
    return TrackStateIssue(
      key: key,
      project: project,
      issueType: issueType,
      issueTypeId: issueTypeId,
      status: status ?? this.status,
      statusId: statusId ?? this.statusId,
      priority: priority,
      priorityId: priorityId,
      summary: summary,
      description: description ?? this.description,
      assignee: assignee,
      reporter: reporter,
      labels: labels,
      components: components,
      fixVersionIds: fixVersionIds,
      watchers: watchers,
      customFields: customFields,
      parentKey: parentKey,
      epicKey: epicKey,
      parentPath: parentPath,
      epicPath: epicPath,
      progress: progress,
      updatedLabel: updatedLabel ?? this.updatedLabel,
      acceptanceCriteria: acceptanceCriteria,
      comments: comments ?? this.comments,
      links: links ?? this.links,
      attachments: attachments ?? this.attachments,
      isArchived: isArchived ?? this.isArchived,
      hasDetailLoaded: hasDetailLoaded ?? this.hasDetailLoaded,
      hasCommentsLoaded: hasCommentsLoaded ?? this.hasCommentsLoaded,
      hasAttachmentsLoaded: hasAttachmentsLoaded ?? this.hasAttachmentsLoaded,
      resolutionId: resolutionId,
      storagePath: storagePath ?? this.storagePath,
      rawMarkdown: rawMarkdown ?? this.rawMarkdown,
    );
  }

  TrackStateIssue withRepositoryIndex(RepositoryIssueIndexEntry? indexEntry) {
    if (indexEntry == null) return this;
    return TrackStateIssue(
      key: key,
      project: project,
      issueType: issueType,
      issueTypeId: issueTypeId,
      status: status,
      statusId: statusId,
      priority: priority,
      priorityId: priorityId,
      summary: summary,
      description: description,
      assignee: assignee,
      reporter: reporter,
      labels: labels,
      components: components,
      fixVersionIds: fixVersionIds,
      watchers: watchers,
      customFields: customFields,
      parentKey: parentKey,
      epicKey: epicKey,
      parentPath: indexEntry.parentPath,
      epicPath: indexEntry.epicPath,
      progress: progress,
      updatedLabel: updatedLabel,
      acceptanceCriteria: acceptanceCriteria,
      comments: comments,
      links: links,
      attachments: attachments,
      isArchived: indexEntry.isArchived || isArchived,
      hasDetailLoaded: hasDetailLoaded,
      hasCommentsLoaded: hasCommentsLoaded,
      hasAttachmentsLoaded: hasAttachmentsLoaded,
      resolutionId: resolutionId,
      storagePath: storagePath,
      rawMarkdown: rawMarkdown,
    );
  }
}

class IssueComment {
  const IssueComment({
    required this.id,
    required this.author,
    required this.body,
    required this.updatedLabel,
    this.createdAt,
    this.updatedAt,
    this.storagePath = '',
  });

  final String id;
  final String author;
  final String body;
  final String updatedLabel;
  final String? createdAt;
  final String? updatedAt;
  final String storagePath;
}

class IssueLink {
  const IssueLink({
    required this.type,
    required this.targetKey,
    this.direction = 'outward',
  });

  final String type;
  final String targetKey;
  final String direction;
}

const Object _issueAttachmentUnset = Object();

class IssueAttachment {
  const IssueAttachment({
    required this.id,
    required this.name,
    required this.mediaType,
    required this.sizeBytes,
    required this.author,
    required this.createdAt,
    required this.storagePath,
    required this.revisionOrOid,
    this.storageBackend = AttachmentStorageMode.repositoryPath,
    this.repositoryPath,
    this.githubReleaseTag,
    this.githubReleaseAssetName,
  });

  final String id;
  final String name;
  final String mediaType;
  final int sizeBytes;
  final String author;
  final String createdAt;
  final String storagePath;
  final String revisionOrOid;
  final AttachmentStorageMode storageBackend;
  final String? repositoryPath;
  final String? githubReleaseTag;
  final String? githubReleaseAssetName;

  IssueAttachment copyWith({
    String? id,
    String? name,
    String? mediaType,
    int? sizeBytes,
    String? author,
    String? createdAt,
    String? storagePath,
    String? revisionOrOid,
    AttachmentStorageMode? storageBackend,
    Object? repositoryPath = _issueAttachmentUnset,
    Object? githubReleaseTag = _issueAttachmentUnset,
    Object? githubReleaseAssetName = _issueAttachmentUnset,
  }) {
    return IssueAttachment(
      id: id ?? this.id,
      name: name ?? this.name,
      mediaType: mediaType ?? this.mediaType,
      sizeBytes: sizeBytes ?? this.sizeBytes,
      author: author ?? this.author,
      createdAt: createdAt ?? this.createdAt,
      storagePath: storagePath ?? this.storagePath,
      revisionOrOid: revisionOrOid ?? this.revisionOrOid,
      storageBackend: storageBackend ?? this.storageBackend,
      repositoryPath: identical(repositoryPath, _issueAttachmentUnset)
          ? this.repositoryPath
          : repositoryPath as String?,
      githubReleaseTag: identical(githubReleaseTag, _issueAttachmentUnset)
          ? this.githubReleaseTag
          : githubReleaseTag as String?,
      githubReleaseAssetName:
          identical(githubReleaseAssetName, _issueAttachmentUnset)
          ? this.githubReleaseAssetName
          : githubReleaseAssetName as String?,
    );
  }

  String get resolvedRepositoryPath => repositoryPath ?? storagePath;
}

enum AttachmentStorageMode {
  repositoryPath('repository-path'),
  githubReleases('github-releases');

  const AttachmentStorageMode(this.persistedValue);

  final String persistedValue;

  static AttachmentStorageMode? tryParse(Object? value) {
    final normalized = value?.toString().trim();
    if (normalized == null || normalized.isEmpty) {
      return null;
    }
    for (final mode in values) {
      if (mode.persistedValue == normalized) {
        return mode;
      }
    }
    return null;
  }
}

class GitHubReleasesAttachmentStorageSettings {
  const GitHubReleasesAttachmentStorageSettings({required this.tagPrefix});

  static const String defaultTagPrefix = 'trackstate-attachments-';

  final String tagPrefix;

  GitHubReleasesAttachmentStorageSettings copyWith({String? tagPrefix}) {
    return GitHubReleasesAttachmentStorageSettings(
      tagPrefix: tagPrefix ?? this.tagPrefix,
    );
  }

  String releaseTagForIssue(String issueKey) =>
      '$tagPrefix${issueKey.trim().toUpperCase()}';

  String releaseTitleForIssue(String issueKey) =>
      'Attachments for ${issueKey.trim().toUpperCase()}';
}

const Object _projectAttachmentStorageNoop = Object();

class ProjectAttachmentStorageSettings {
  const ProjectAttachmentStorageSettings({
    this.mode = AttachmentStorageMode.repositoryPath,
    this.githubReleases,
  });

  final AttachmentStorageMode mode;
  final GitHubReleasesAttachmentStorageSettings? githubReleases;

  ProjectAttachmentStorageSettings copyWith({
    AttachmentStorageMode? mode,
    Object? githubReleases = _projectAttachmentStorageNoop,
  }) {
    return ProjectAttachmentStorageSettings(
      mode: mode ?? this.mode,
      githubReleases: identical(githubReleases, _projectAttachmentStorageNoop)
          ? this.githubReleases
          : githubReleases as GitHubReleasesAttachmentStorageSettings?,
    );
  }
}

class RepositoryIssueIndexEntry {
  const RepositoryIssueIndexEntry({
    required this.key,
    required this.path,
    required this.childKeys,
    this.parentKey,
    this.epicKey,
    this.parentPath,
    this.epicPath,
    this.isArchived = false,
    this.summary,
    this.issueTypeId,
    this.statusId,
    this.priorityId,
    this.assignee,
    this.labels = const [],
    this.updatedLabel,
    this.progress,
    this.resolutionId,
    this.revision,
    this.links = const [],
  });

  final String key;
  final String path;
  final String? parentKey;
  final String? epicKey;
  final String? parentPath;
  final String? epicPath;
  final List<String> childKeys;
  final bool isArchived;
  final String? summary;
  final String? issueTypeId;
  final String? statusId;
  final String? priorityId;
  final String? assignee;
  final List<String> labels;
  final String? updatedLabel;
  final double? progress;
  final String? resolutionId;
  final String? revision;
  final List<IssueLink> links;

  RepositoryIssueIndexEntry copyWith({
    String? parentPath,
    String? epicPath,
    List<String>? childKeys,
    bool? isArchived,
    String? summary,
    String? issueTypeId,
    String? statusId,
    String? priorityId,
    String? assignee,
    List<String>? labels,
    String? updatedLabel,
    double? progress,
    String? resolutionId,
    String? revision,
    List<IssueLink>? links,
  }) {
    return RepositoryIssueIndexEntry(
      key: key,
      path: path,
      parentKey: parentKey,
      epicKey: epicKey,
      parentPath: parentPath ?? this.parentPath,
      epicPath: epicPath ?? this.epicPath,
      childKeys: childKeys ?? this.childKeys,
      isArchived: isArchived ?? this.isArchived,
      summary: summary ?? this.summary,
      issueTypeId: issueTypeId ?? this.issueTypeId,
      statusId: statusId ?? this.statusId,
      priorityId: priorityId ?? this.priorityId,
      assignee: assignee ?? this.assignee,
      labels: labels ?? this.labels,
      updatedLabel: updatedLabel ?? this.updatedLabel,
      progress: progress ?? this.progress,
      resolutionId: resolutionId ?? this.resolutionId,
      revision: revision ?? this.revision,
      links: links ?? this.links,
    );
  }
}
