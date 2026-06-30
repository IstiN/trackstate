part of 'trackstate_repository.dart';

mixin _TrackStateRepositoryMutations {
  TrackStateProviderAdapter get _provider;
  ProviderSession get _session;
  http.Client? get _githubClient;
  TrackerSnapshot? get _snapshot;
  set _snapshot(TrackerSnapshot? value);
  Set<String> get _knownTombstoneKeys;
  Map<String, DeletedIssueTombstone> get _knownTombstonesByKey;
  Map<String, String?> get _snapshotArtifactRevisions;
  Set<String> get _snapshotBlobPaths;
  set _snapshotBlobPaths(Set<String> value);
  TrackStateRepository get _repository;
  Future<TrackerSnapshot> loadSnapshot();
  Future<TrackStateIssue> hydrateIssue(
    TrackStateIssue issue, {
    Set<IssueHydrationScope> scopes = const {IssueHydrationScope.detail},
  });
  Future<void> _acquireDeleteMutationLock();
  void _releaseDeleteMutationLock();
  void _replaceCachedIssue(TrackStateIssue updatedIssue);
  Future<String> _resolveStatusIdForUpdate({
    required TrackStateIssue issue,
    required IssueStatus status,
    required String writeBranch,
  });
  Future<List<IssueHistoryEntry>> _normalizeIssueHistory({
    required TrackStateIssue issue,
    required List<RepositoryHistoryCommit> commits,
  });

  Future<TrackerSnapshot> _loadSnapshotAfterWrite() {
    _repository.markHostedTreeStale();
    return loadSnapshot();
  }
  Future<String?> _existingArtifactRevision({
    required String path,
    required String ref,
    required Set<String> blobPaths,
  });
  Future<String?> _existingRevision({
    required String path,
    required String ref,
    required Set<String> blobPaths,
    // ignore: unused_element_parameter
    Map<String, String?>? blobRevisions,
  });

  /// Returns the revision of an existing attachment stored in the repository
  /// (i.e. not release-backed), or null when the attachment is release-backed.
  Future<String?> _existingRepositoryAttachmentRevision({
    required IssueAttachment existingAttachment,
    required String attachmentPath,
    required String writeBranch,
  }) async {
    if (existingAttachment.storageBackend ==
        AttachmentStorageMode.githubReleases) {
      return null;
    }
    return (await _provider.readAttachment(
      attachmentPath,
      ref: writeBranch,
    )).revision;
  }

  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    final normalizedSummary = summary.trim();
    if (normalizedSummary.isEmpty) {
      throw const TrackStateRepositoryException(
        'Issue summary is required before creating an issue.',
      );
    }
    final permission = await _provider.getPermission();
    if (!permission.canWrite) {
      throw const TrackStateRepositoryException(
        'Connect a repository session with write access first.',
      );
    }

    final snapshot = _snapshot ?? await loadSnapshot();
    await _provider.ensureCleanWorktree();

    final project = snapshot.project;
    final key = _nextIssueKey(snapshot);
    final writeBranch = await _provider.resolveWriteBranch();
    final issuePath = _nextIssuePath(snapshot, key);
    final createdAt = DateTime.now().toUtc().toIso8601String();
    final issueTypeId = _defaultIssueTypeId(project);
    final statusId = _defaultStatusId(project);
    final priorityId = _defaultPriorityId(project);
    final author = _defaultAuthor(_session.resolvedUserIdentity);
    final markdown = _buildIssueMarkdown(
      key: key,
      projectKey: project.key,
      summary: normalizedSummary,
      description: description.trim(),
      customFields: customFields,
      issueTypeId: issueTypeId,
      statusId: statusId,
      priorityId: priorityId,
      assignee: author,
      reporter: author,
      createdAt: createdAt,
    );

    await _provider.writeTextFile(
      RepositoryWriteRequest(
        path: issuePath,
        content: markdown,
        message: 'Create $key',
        branch: writeBranch,
      ),
    );

    final refreshed = await _loadSnapshotAfterWrite();
    return refreshed.issues.firstWhere(
      (issue) => issue.key == key,
      orElse: () => _parseIssue(
        storagePath: issuePath,
        markdown: markdown,
        comments: const [],
        links: const [],
        attachments: const [],
        repositoryIndexEntry: RepositoryIssueIndexEntry(
          key: key,
          path: issuePath,
          childKeys: const [],
        ),
        issueTypeDefinitions: project.issueTypeDefinitions,
        statusDefinitions: project.statusDefinitions,
        priorityDefinitions: project.priorityDefinitions,
        resolutionDefinitions: project.resolutionDefinitions,
      ),
    );
  }

  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async {
    if (issue.storagePath.isEmpty) {
      throw const TrackStateRepositoryException(
        'This issue has no repository file path and cannot be saved.',
      );
    }
    final permission = await _provider.getPermission();
    if (!permission.canWrite) {
      throw const TrackStateRepositoryException(
        'Connect a repository session with write access first.',
      );
    }

    final normalizedDescription = description.trim();
    final snapshot = _snapshot ?? await loadSnapshot();
    final currentIssue = snapshot.issues.firstWhere(
      (candidate) => candidate.key == issue.key,
      orElse: () => issue,
    );
    final writeBranch = await _provider.resolveWriteBranch();
    final blobPaths = (await _provider.listTree(ref: writeBranch))
        .where((entry) => entry.type == 'blob')
        .map((entry) => entry.path)
        .toSet();
    if (!blobPaths.contains(currentIssue.storagePath)) {
      throw TrackStateRepositoryException(
        'Could not find repository artifacts for ${currentIssue.key}.',
      );
    }
    final file = await _provider.readTextFile(
      currentIssue.storagePath,
      ref: writeBranch,
    );
    final updatedMarkdown = _replaceSection(
      file.content,
      'Description',
      normalizedDescription,
    );
    await _provider.writeTextFile(
      RepositoryWriteRequest(
        path: currentIssue.storagePath,
        content: updatedMarkdown,
        message: 'Update ${currentIssue.key} description',
        branch: writeBranch,
        expectedRevision: file.revision,
      ),
    );
    _repository.markHostedTreeStale();

    final updatedIssue = currentIssue.copyWith(
      description: normalizedDescription,
      rawMarkdown: updatedMarkdown,
      updatedLabel: 'just now',
    );
    _replaceCachedIssue(updatedIssue);
    return updatedIssue;
  }

  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async {
    if (issue.storagePath.isEmpty) {
      throw const TrackStateRepositoryException(
        'This issue has no repository file path and cannot be saved.',
      );
    }
    final permission = await _provider.getPermission();
    if (!permission.canWrite) {
      throw const TrackStateRepositoryException(
        'Connect a repository session with write access first.',
      );
    }

    final writeBranch = await _provider.resolveWriteBranch();
    final file = await _provider.readTextFile(
      issue.storagePath,
      ref: writeBranch,
    );
    final statusId = await _resolveStatusIdForUpdate(
      issue: issue,
      status: status,
      writeBranch: writeBranch,
    );
    final updatedMarkdown = _replaceFrontmatterValue(
      file.content,
      'status',
      statusId,
    );
    await _provider.writeTextFile(
      RepositoryWriteRequest(
        path: issue.storagePath,
        content: updatedMarkdown,
        message: 'Move ${issue.key} to ${status.label}',
        branch: writeBranch,
        expectedRevision: file.revision,
      ),
    );
    _repository.markHostedTreeStale();

    final updatedIssue = issue.copyWith(
      status: status,
      statusId: statusId,
      rawMarkdown: updatedMarkdown,
      updatedLabel: 'just now',
    );
    _replaceCachedIssue(updatedIssue);
    return updatedIssue;
  }

  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async {
    if (issue.storagePath.isEmpty) {
      throw const TrackStateRepositoryException(
        'This issue has no repository file path and cannot receive comments.',
      );
    }
    final permission = await _provider.getPermission();
    if (!permission.canWrite) {
      throw const TrackStateRepositoryException(
        'Connect a repository session with write access first.',
      );
    }

    final persistedBody = body.trimRight();
    if (persistedBody.trim().isEmpty) {
      throw const TrackStateRepositoryException(
        'Comment body is required before saving.',
      );
    }

    final snapshot = _snapshot ?? await loadSnapshot();
    final currentIssue = snapshot.issues.firstWhere(
      (candidate) => candidate.key == issue.key,
      orElse: () => issue,
    );
    final writeBranch = await _provider.resolveWriteBranch();
    final blobPaths = (await _provider.listTree(ref: writeBranch))
        .where((entry) => entry.type == 'blob')
        .map((entry) => entry.path)
        .toSet();
    final issueRoot = _issueRoot(currentIssue.storagePath);
    final nextCommentId = _nextCommentId(
      blobPaths: blobPaths,
      issueRoot: issueRoot,
    );
    final commentPath = _joinPath(issueRoot, 'comments/$nextCommentId.md');
    final timestamp = DateTime.now().toUtc().toIso8601String();
    final author = _defaultAuthor(_session.resolvedUserIdentity);
    final markdown = _buildCommentMarkdown(
      author: author,
      createdAt: timestamp,
      body: persistedBody,
    );
    final result = await _provider.writeTextFile(
      RepositoryWriteRequest(
        path: commentPath,
        content: markdown,
        message: 'Add comment to ${currentIssue.key}',
        branch: writeBranch,
      ),
    );
    _repository.markHostedTreeStale();

    final updatedIssue = currentIssue.copyWith(
      hasCommentsLoaded: true,
      comments: [
        ...currentIssue.comments,
        IssueComment(
          id: nextCommentId,
          author: author,
          body: persistedBody,
          updatedLabel: timestamp,
          createdAt: timestamp,
          updatedAt: timestamp,
          storagePath: commentPath,
        ),
      ]..sort((left, right) => left.id.compareTo(right.id)),
    );
    _snapshotArtifactRevisions[commentPath] = result.revision;
    _replaceCachedIssue(updatedIssue);
    return updatedIssue;
  }

  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
    String? sourceName,
  }) async {
    if (issue.storagePath.isEmpty) {
      throw const TrackStateRepositoryException(
        'This issue has no repository file path and cannot receive attachments.',
      );
    }
    final snapshot = _snapshot ?? await loadSnapshot();
    final permission = await _provider.getPermission();
    final attachmentStorage = snapshot.project.attachmentStorage;
    if (attachmentStorage.mode == AttachmentStorageMode.githubReleases) {
      final githubReleases = attachmentStorage.githubReleases;
      if (githubReleases == null || githubReleases.tagPrefix.trim().isEmpty) {
        throw const TrackStateRepositoryException(
          'GitHub Releases attachment storage requires a non-empty tag prefix.',
        );
      }
      if (!permission.supportsReleaseAttachmentWrites &&
          !(permission.canManageAttachments &&
              _provider.providerType == ProviderType.github)) {
        throw TrackStateRepositoryException(
          permission.releaseAttachmentWriteFailureReason?.trim().isNotEmpty ==
                  true
              ? permission.releaseAttachmentWriteFailureReason!.trim()
              : 'GitHub Releases attachment storage requires GitHub '
                    'authentication/configuration that supports release '
                    'uploads. This repository session cannot upload '
                    'release-backed attachments.',
        );
      }
    } else if (!permission.canManageAttachments) {
      throw const TrackStateRepositoryException(
        'This repository session does not allow attachment uploads.',
      );
    }
    final normalizedName = name.trim();
    if (normalizedName.isEmpty) {
      throw const TrackStateRepositoryException(
        'Attachment name is required before uploading.',
      );
    }
    if (bytes.isEmpty) {
      throw const TrackStateRepositoryException(
        'Attachment bytes are required before uploading.',
      );
    }

    var currentIssue = snapshot.issues.firstWhere(
      (candidate) => candidate.key == issue.key,
      orElse: () => issue,
    );
    if (!currentIssue.hasAttachmentsLoaded) {
      currentIssue = await hydrateIssue(
        currentIssue,
        scopes: const {IssueHydrationScope.attachments},
      );
    }
    final attachmentPath = _repository.resolveIssueAttachmentPath(
      currentIssue,
      normalizedName,
      sourceName: sourceName,
    );
    final existingAttachment = currentIssue.attachments
        .where((candidate) => candidate.storagePath == attachmentPath)
        .firstOrNull;
    final replacesRepositoryPathAttachment =
        attachmentStorage.mode == AttachmentStorageMode.repositoryPath &&
        existingAttachment?.storageBackend ==
            AttachmentStorageMode.repositoryPath;
    final preserveRepositoryPathReplacement =
        attachmentStorage.mode == AttachmentStorageMode.githubReleases &&
        !permission.supportsReleaseAttachmentWrites &&
        existingAttachment?.storageBackend ==
            AttachmentStorageMode.repositoryPath;
    final writeBranch = await _provider.resolveWriteBranch();
    final attachmentMetadataPath = _attachmentMetadataPath(
      _issueRoot(currentIssue.storagePath),
    );
    final existingRevision = existingAttachment == null
        ? await _existingArtifactRevision(
            path: attachmentPath,
            ref: writeBranch,
            blobPaths: _snapshotBlobPaths,
          )
        : await _existingRepositoryAttachmentRevision(
            existingAttachment: existingAttachment,
            attachmentPath: attachmentPath,
            writeBranch: writeBranch,
          );
    final metadataRevision = await _existingRevision(
      path: attachmentMetadataPath,
      ref: writeBranch,
      blobPaths: _snapshotBlobPaths,
    );
    final lfsTracked = await _provider.isLfsTracked(attachmentPath);
    final shouldMigrateHostedLfsReplacementToReleaseStorage =
        attachmentStorage.mode == AttachmentStorageMode.repositoryPath &&
        existingAttachment?.storageBackend ==
            AttachmentStorageMode.repositoryPath &&
        lfsTracked &&
        !replacesRepositoryPathAttachment &&
        permission.attachmentUploadMode == AttachmentUploadMode.noLfs &&
        permission.supportsReleaseAttachmentWrites;
    final prefersReleaseStorage =
        !preserveRepositoryPathReplacement &&
        (attachmentStorage.mode == AttachmentStorageMode.githubReleases ||
            existingAttachment?.storageBackend ==
                AttachmentStorageMode.githubReleases ||
            shouldMigrateHostedLfsReplacementToReleaseStorage);
    final githubReleases =
        attachmentStorage.githubReleases ??
        (prefersReleaseStorage
            ? const GitHubReleasesAttachmentStorageSettings(
                tagPrefix:
                    GitHubReleasesAttachmentStorageSettings.defaultTagPrefix,
              )
            : null);
    if (prefersReleaseStorage && githubReleases != null) {
      if (!permission.supportsReleaseAttachmentWrites) {
        if (attachmentStorage.mode != AttachmentStorageMode.githubReleases) {
          throw TrackStateRepositoryException(
            'This repository session cannot replace ${existingAttachment?.name ?? normalizedName} '
            'because hosted GitHub Releases attachment writes are unavailable.',
          );
        }
        final inboxPath = _releaseAttachmentInboxPath(
          issue: currentIssue,
          fileName: resolveAttachmentStorageName(
            normalizedName,
            sourceName: sourceName,
          ),
        );
        final existingInboxRevision = await _existingRevision(
          path: inboxPath,
          ref: writeBranch,
          blobPaths: _snapshotBlobPaths,
        );
        final inboxWriteResult = await _provider.writeAttachment(
          RepositoryAttachmentWriteRequest(
            path: inboxPath,
            bytes: bytes,
            message: 'Queue release attachment upload for ${currentIssue.key}',
            branch: writeBranch,
            expectedRevision: existingInboxRevision,
          ),
        );
        _snapshotArtifactRevisions[inboxPath] = inboxWriteResult.revision;
        _snapshotBlobPaths = {..._snapshotBlobPaths, inboxPath};
        final updatedIssue = currentIssue.copyWith(hasAttachmentsLoaded: true);
        _replaceCachedIssue(updatedIssue);
        return updatedIssue;
      }
      final releaseStore = switch (_provider) {
        final RepositoryReleaseAttachmentStore supported => supported,
        _ => throw const TrackStateRepositoryException(
          'This repository provider does not support GitHub Releases '
          'attachment uploads.',
        ),
      };
      final timestamp = DateTime.now().toUtc().toIso8601String();
      final author = _defaultAuthor(_session.resolvedUserIdentity);
      final existingReleaseAttachment =
          existingAttachment?.storageBackend ==
              AttachmentStorageMode.githubReleases
          ? existingAttachment
          : null;
      final releaseTag =
          existingReleaseAttachment?.githubReleaseTag ??
          githubReleases.releaseTagForIssue(currentIssue.key);
      final assetName =
          existingReleaseAttachment?.githubReleaseAssetName ??
          attachmentPath.split('/').last;
      final releaseAssetNames = {
        for (final attachment in currentIssue.attachments)
          if (attachment.storageBackend ==
                  AttachmentStorageMode.githubReleases &&
              attachment.githubReleaseTag == releaseTag)
            attachment.githubReleaseAssetName ?? attachment.name,
      };
      final previousReleaseAttachment = currentIssue.attachments
          .where(
            (attachment) =>
                attachment.storagePath == attachmentPath &&
                attachment.storageBackend ==
                    AttachmentStorageMode.githubReleases &&
                attachment.githubReleaseTag == releaseTag,
          )
          .firstOrNull;
      final rollbackAttachment = previousReleaseAttachment == null
          ? null
          : await releaseStore.readReleaseAttachment(
              RepositoryReleaseAttachmentReadRequest(
                releaseTag: previousReleaseAttachment.githubReleaseTag!,
                assetName:
                    previousReleaseAttachment.githubReleaseAssetName ??
                    previousReleaseAttachment.name,
                assetId: previousReleaseAttachment.revisionOrOid,
              ),
            );
      final releaseWriteResult = await releaseStore.writeReleaseAttachment(
        RepositoryReleaseAttachmentWriteRequest(
          issueKey: currentIssue.key,
          releaseTag: releaseTag,
          releaseTitle: githubReleases.releaseTitleForIssue(currentIssue.key),
          assetName: assetName,
          bytes: bytes,
          mediaType: _mediaTypeForPath(assetName),
          branch: writeBranch,
          allowedAssetNames: releaseAssetNames,
        ),
      );
      final updatedAttachment = IssueAttachment(
        id: attachmentPath,
        name: normalizedName,
        mediaType: _mediaTypeForPath(attachmentPath),
        sizeBytes: bytes.length,
        author: author,
        createdAt: timestamp,
        storagePath: attachmentPath,
        revisionOrOid: releaseWriteResult.assetId,
        storageBackend: AttachmentStorageMode.githubReleases,
        githubReleaseTag: releaseWriteResult.releaseTag,
        githubReleaseAssetName: releaseWriteResult.assetName,
      );
      final updatedAttachments = [
        for (final candidate in currentIssue.attachments)
          if (candidate.storagePath == attachmentPath)
            updatedAttachment
          else
            candidate,
        if (!currentIssue.attachments.any(
          (candidate) => candidate.storagePath == attachmentPath,
        ))
          updatedAttachment,
      ]..sort(_sortAttachmentsNewestFirst);
      final metadataWriteResult = await () async {
        try {
          return await _provider.writeTextFile(
            RepositoryWriteRequest(
              path: attachmentMetadataPath,
              content:
                  '${jsonEncode(_attachmentMetadataJson(updatedAttachments))}\n',
              message: 'Update attachment metadata for ${currentIssue.key}',
              branch: writeBranch,
              expectedRevision: metadataRevision,
            ),
          );
        } catch (error, stackTrace) {
          try {
            await releaseStore.deleteReleaseAttachment(
              RepositoryReleaseAttachmentDeleteRequest(
                releaseTag: releaseWriteResult.releaseTag,
                assetId: releaseWriteResult.assetId,
                assetName: releaseWriteResult.assetName,
              ),
            );
            if (previousReleaseAttachment != null &&
                rollbackAttachment != null) {
              await releaseStore.writeReleaseAttachment(
                RepositoryReleaseAttachmentWriteRequest(
                  issueKey: currentIssue.key,
                  releaseTag: previousReleaseAttachment.githubReleaseTag!,
                  releaseTitle: githubReleases.releaseTitleForIssue(
                    currentIssue.key,
                  ),
                  assetName:
                      previousReleaseAttachment.githubReleaseAssetName ??
                      previousReleaseAttachment.name,
                  bytes: rollbackAttachment.bytes,
                  mediaType: previousReleaseAttachment.mediaType,
                  branch: writeBranch,
                  allowedAssetNames: releaseAssetNames,
                ),
              );
            }
          } catch (rollbackError) {
            throw TrackStateRepositoryException(
              'Could not update attachment metadata for ${currentIssue.key} '
              'after uploading GitHub release asset $assetName. '
              'Rollback also failed: $rollbackError',
            );
          }
          Error.throwWithStackTrace(error, stackTrace);
        }
      }();
      _snapshotArtifactRevisions[attachmentMetadataPath] =
          metadataWriteResult.revision;
      _snapshotBlobPaths = {..._snapshotBlobPaths, attachmentMetadataPath};
      final updatedIssue = currentIssue.copyWith(
        hasAttachmentsLoaded: true,
        attachments: updatedAttachments,
      );
      _replaceCachedIssue(updatedIssue);
      _repository.markHostedTreeStale();
      return updatedIssue;
    }
    if (lfsTracked &&
        permission.attachmentUploadMode == AttachmentUploadMode.noLfs &&
        !replacesRepositoryPathAttachment) {
      throw const TrackStateRepositoryException(
        'This repository session is download-only for Git LFS attachments.',
      );
    }

    final timestamp = DateTime.now().toUtc().toIso8601String();
    final author = _defaultAuthor(_session.resolvedUserIdentity);
    final attachmentWriteResult = await _provider.writeAttachment(
      RepositoryAttachmentWriteRequest(
        path: attachmentPath,
        bytes: bytes,
        message: 'Upload attachment to ${currentIssue.key}',
        branch: writeBranch,
        expectedRevision: existingRevision,
        allowLfsTrackedWrite: replacesRepositoryPathAttachment,
      ),
    );
    RepositoryAttachment persistedAttachmentArtifact;
    const maxReadAttempts = 5;
    for (var readAttempt = 0; ; readAttempt++) {
      persistedAttachmentArtifact = await _provider.readAttachment(
        attachmentPath,
        ref: writeBranch,
      );
      if (persistedAttachmentArtifact.bytes.length == bytes.length) {
        break;
      }
      if (readAttempt >= maxReadAttempts - 1) {
        throw TrackStateRepositoryException(
          'Stored attachment size ${persistedAttachmentArtifact.bytes.length} bytes '
          'does not match uploaded size ${bytes.length} bytes for $attachmentPath.',
        );
      }
      await Future.delayed(const Duration(milliseconds: 400));
    }
    _snapshotArtifactRevisions[attachmentPath] = attachmentWriteResult.revision;
    final updatedAttachment = IssueAttachment(
      id: attachmentPath,
      name: normalizedName,
      mediaType: _mediaTypeForPath(attachmentPath),
      sizeBytes: persistedAttachmentArtifact.bytes.length,
      author: author,
      createdAt: timestamp,
      storagePath: attachmentPath,
      revisionOrOid: _attachmentRevisionOrOid(
        attachment: persistedAttachmentArtifact,
        isLfsTracked: lfsTracked,
      ),
      storageBackend: AttachmentStorageMode.repositoryPath,
      repositoryPath: attachmentPath,
    );
    final updatedAttachments = [
      for (final candidate in currentIssue.attachments)
        if (candidate.storagePath == attachmentPath)
          updatedAttachment
        else
          candidate,
      if (!currentIssue.attachments.any(
        (candidate) => candidate.storagePath == attachmentPath,
      ))
        updatedAttachment,
    ]..sort(_sortAttachmentsNewestFirst);
    final metadataWriteResult = await _provider.writeTextFile(
      RepositoryWriteRequest(
        path: attachmentMetadataPath,
        content: '${jsonEncode(_attachmentMetadataJson(updatedAttachments))}\n',
        message: 'Update attachment metadata for ${currentIssue.key}',
        branch: writeBranch,
        expectedRevision: metadataRevision,
      ),
    );
    _snapshotArtifactRevisions[attachmentMetadataPath] =
        metadataWriteResult.revision;
    _snapshotBlobPaths = {
      ..._snapshotBlobPaths,
      attachmentPath,
      attachmentMetadataPath,
    };
    final updatedIssue = currentIssue.copyWith(
      hasAttachmentsLoaded: true,
      attachments: updatedAttachments,
    );
    _replaceCachedIssue(updatedIssue);
    _repository.markHostedTreeStale();
    return updatedIssue;
  }

  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async {
    if (attachment.storageBackend == AttachmentStorageMode.githubReleases) {
      final releaseTag = attachment.githubReleaseTag?.trim() ?? '';
      final assetName = attachment.githubReleaseAssetName?.trim() ?? '';
      if (releaseTag.isEmpty || assetName.isEmpty) {
        throw TrackStateRepositoryException(
          'GitHub Releases attachment metadata is incomplete for '
          '${attachment.name}.',
        );
      }
      final request = RepositoryReleaseAttachmentReadRequest(
        releaseTag: releaseTag,
        assetName: assetName,
        assetId: attachment.revisionOrOid,
      );
      final artifact = switch (_provider) {
        final RepositoryReleaseAttachmentStore supported =>
          await supported.readReleaseAttachment(request),
        final RepositoryGitHubIdentityResolver identityResolver =>
          await () async {
            final failureReason = await identityResolver
                .releaseAttachmentIdentityFailureReason();
            if (failureReason?.trim().isNotEmpty == true) {
              throw TrackStateRepositoryException(failureReason!.trim());
            }
            final repository = await identityResolver
                .resolveGitHubRepositoryIdentity();
            if (repository == null || repository.trim().isEmpty) {
              final reason = await identityResolver
                  .releaseAttachmentIdentityFailureReason();
              throw TrackStateRepositoryException(
                reason?.trim().isNotEmpty == true
                    ? reason!.trim()
                    : 'This repository provider does not support GitHub Releases '
                          'attachment downloads.',
              );
            }
            return GitHubTrackStateProvider(
              client: _githubClient,
              repositoryName: repository,
            ).readReleaseAttachmentForRepository(
              repository: repository,
              request: request,
            );
          }(),
        _ => throw const TrackStateRepositoryException(
          'This repository provider does not support GitHub Releases '
          'attachment downloads.',
        ),
      };
      return artifact.bytes;
    }
    final artifact = await _provider.readAttachment(
      attachment.resolvedRepositoryPath,
      ref: _provider.dataRef,
    );
    return artifact.bytes;
  }

  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async {
    final historyReader = switch (_provider) {
      final RepositoryHistoryReader supported => supported,
      _ => null,
    };
    if (historyReader == null) {
      return const <IssueHistoryEntry>[];
    }
    final issueRoot = _issueRoot(issue.storagePath);
    final commits = await historyReader.listHistory(
      ref: _provider.dataRef,
      path: issueRoot,
    );
    return _normalizeIssueHistory(issue: issue, commits: commits);
  }

  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async {
    if (issue.storagePath.isEmpty) {
      throw const TrackStateRepositoryException(
        'This issue has no repository file path and cannot be archived.',
      );
    }
    final permission = await _provider.getPermission();
    if (!permission.canWrite) {
      throw const TrackStateRepositoryException(
        'Connect a repository session with write access first.',
      );
    }
    final mutator = switch (_provider) {
      final RepositoryFileMutator supported => supported,
      _ => throw const TrackStateRepositoryException(
        'This repository provider does not support archiving issues yet.',
      ),
    };
    final snapshot = _snapshot ?? await loadSnapshot();
    final currentIssue = snapshot.issues.firstWhere(
      (candidate) => candidate.key == issue.key,
      orElse: () => issue,
    );

    try {
      final writeBranch = await _provider.resolveWriteBranch();
      final tree = await _provider.listTree(ref: writeBranch);
      final blobPaths = tree
          .where((entry) => entry.type == 'blob')
          .map((entry) => entry.path)
          .toSet();
      final projectRoot = currentIssue.storagePath.split('/').first;
      if (projectRoot.isEmpty) {
        throw const TrackStateRepositoryException(
          'Could not resolve the project root for the issue being archived.',
        );
      }
      if (!blobPaths.contains(currentIssue.storagePath)) {
        throw TrackStateRepositoryException(
          'Could not find repository artifacts for ${currentIssue.key}.',
        );
      }

      final issueFile = await _provider.readTextFile(
        currentIssue.storagePath,
        ref: writeBranch,
      );
      final updatedMarkdown = _replaceFrontmatterValue(
        issueFile.content,
        'archived',
        'true',
      );
      final updatedIssues = [
        for (final candidate in snapshot.issues)
          if (candidate.key == currentIssue.key)
            candidate.copyWith(
              rawMarkdown: updatedMarkdown,
              updatedLabel: 'just now',
              isArchived: true,
            )
          else
            candidate,
      ]..sort((a, b) => a.key.compareTo(b.key));
      final repositoryIndex = _deriveRepositoryIndex(
        updatedIssues,
        snapshot.repositoryIndex.deleted,
      );
      final issuesIndexPath = _joinPath(
        projectRoot,
        '.trackstate/index/issues.json',
      );
      final changes = <RepositoryFileChange>[];
      changes.add(
        RepositoryTextFileChange(
          path: currentIssue.storagePath,
          content: updatedMarkdown,
          expectedRevision: issueFile.revision,
        ),
      );
      changes.add(
        RepositoryTextFileChange(
          path: issuesIndexPath,
          content:
              '${jsonEncode(_repositoryIndexEntriesJson(repositoryIndex.entries))}\n',
          expectedRevision: await _existingRevision(
            path: issuesIndexPath,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
      );

      await mutator.applyFileChanges(
        RepositoryFileChangeRequest(
          branch: writeBranch,
          message: 'Archive ${currentIssue.key}',
          changes: changes,
        ),
      );
      _repository.markHostedTreeStale();

      final indexedUpdatedIssues = [
        for (final updatedIssue in updatedIssues)
          updatedIssue.withRepositoryIndex(
            repositoryIndex.entryForKey(updatedIssue.key),
          ),
      ]..sort((a, b) => a.key.compareTo(b.key));
      _snapshot = TrackerSnapshot(
        project: snapshot.project,
        repositoryIndex: repositoryIndex,
        issues: indexedUpdatedIssues,
      );
      return indexedUpdatedIssues.singleWhere(
        (candidate) => candidate.key == currentIssue.key,
      );
    } on TrackStateProviderException catch (error) {
      if (error is TrackStateRepositoryException) {
        rethrow;
      }
      throw TrackStateRepositoryException(
        'Could not archive ${currentIssue.key} because the repository provider '
        'failed while applying the archive change.',
      );
    }
  }

  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async {
    await _acquireDeleteMutationLock();
    try {
      if (issue.storagePath.isEmpty) {
        throw const TrackStateRepositoryException(
          'This issue has no repository file path and cannot be deleted.',
        );
      }
      final permission = await _provider.getPermission();
      if (!permission.canWrite) {
        throw const TrackStateRepositoryException(
          'Connect a repository session with write access first.',
        );
      }
      final mutator = switch (_provider) {
        final RepositoryFileMutator supported => supported,
        _ => throw const TrackStateRepositoryException(
          'This repository provider does not support deleting issues yet.',
        ),
      };
      final snapshot = _snapshot ?? await loadSnapshot();
      final currentIssue = snapshot.issues.firstWhere(
        (candidate) => candidate.key == issue.key,
        orElse: () => issue,
      );
      final indexEntry = snapshot.repositoryIndex.entryForKey(currentIssue.key);
      if (indexEntry != null && indexEntry.childKeys.isNotEmpty) {
        throw TrackStateRepositoryException(
          'Cannot delete ${currentIssue.key} because it still has child issues: '
          '${indexEntry.childKeys.join(', ')}.',
        );
      }

      final writeBranch = await _provider.resolveWriteBranch();
      final tree = await _provider.listTree(ref: writeBranch);
      final blobPaths = tree
          .where((entry) => entry.type == 'blob')
          .map((entry) => entry.path)
          .toSet();
      final projectRoot = currentIssue.storagePath.split('/').first;
      if (projectRoot.isEmpty) {
        throw const TrackStateRepositoryException(
          'Could not resolve the project root for the issue being deleted.',
        );
      }
      final issueArtifactPaths =
          blobPaths
              .where(
                (path) => _isIssueArtifactPath(
                  issueStoragePath: currentIssue.storagePath,
                  candidatePath: path,
                ),
              )
              .toList()
            ..sort();
      if (issueArtifactPaths.isEmpty) {
        throw TrackStateRepositoryException(
          'Could not find repository artifacts for ${currentIssue.key}.',
        );
      }
      final tombstone = DeletedIssueTombstone(
        key: currentIssue.key,
        project: currentIssue.project,
        formerPath: currentIssue.storagePath,
        deletedAt: DateTime.now().toUtc().toIso8601String(),
        summary: currentIssue.summary,
        issueTypeId: currentIssue.issueTypeId.isEmpty
            ? null
            : currentIssue.issueTypeId,
        parentKey: currentIssue.parentKey,
        epicKey: currentIssue.epicKey,
      );
      _knownTombstoneKeys.add(tombstone.key);
      _knownTombstonesByKey[tombstone.key] = tombstone;
      final latestSnapshot = _snapshot ?? snapshot;
      final snapshotDeletedByKey = {
        for (final entry in latestSnapshot.repositoryIndex.deleted)
          entry.key: entry,
        ..._knownTombstonesByKey,
        tombstone.key: tombstone,
      };
      final snapshotDeletedTombstones = snapshotDeletedByKey.values.toList()
        ..sort((a, b) => a.key.compareTo(b.key));
      final remainingIssues = latestSnapshot.issues
          .where((candidate) => candidate.key != currentIssue.key)
          .toList(growable: false);
      final repositoryIndex = _deriveRepositoryIndex(
        remainingIssues,
        snapshotDeletedTombstones,
      );
      final indexedRemainingIssues = [
        for (final remainingIssue in remainingIssues)
          remainingIssue.withRepositoryIndex(
            repositoryIndex.entryForKey(remainingIssue.key),
          ),
      ]..sort((a, b) => a.key.compareTo(b.key));
      final updatedSnapshot = TrackerSnapshot(
        project: latestSnapshot.project,
        repositoryIndex: repositoryIndex,
        issues: indexedRemainingIssues,
      );

      final tombstoneArtifactPrefix = _joinPath(
        projectRoot,
        '.trackstate/tombstones/',
      );
      final tombstoneKeysInArtifacts = blobPaths
          .where(
            (path) =>
                path.startsWith(tombstoneArtifactPrefix) &&
                path.endsWith('.json'),
          )
          .map((path) => path.split('/').last.replaceAll('.json', ''))
          .toSet();
      final tombstoneKeysForIndex = <String>{
        ..._knownTombstoneKeys,
        ...tombstoneKeysInArtifacts,
      };
      final tombstoneIndexTombstones =
          snapshotDeletedTombstones
              .where((entry) => tombstoneKeysForIndex.contains(entry.key))
              .toList(growable: false)
            ..sort((a, b) => a.key.compareTo(b.key));

      final tombstoneIndexPath = _joinPath(
        projectRoot,
        '.trackstate/index/tombstones.json',
      );
      final issuesIndexPath = _joinPath(
        projectRoot,
        '.trackstate/index/issues.json',
      );
      final tombstoneArtifactPath = _tombstoneArtifactPath(
        projectRoot,
        tombstone.key,
      );
      final changes = <RepositoryFileChange>[
        for (final path in issueArtifactPaths)
          RepositoryDeleteFileChange(
            path: path,
            expectedRevision:
                _snapshotArtifactRevisions[path] ??
                await _existingArtifactRevision(
                  path: path,
                  ref: writeBranch,
                  blobPaths: blobPaths,
                ),
          ),
        RepositoryTextFileChange(
          path: issuesIndexPath,
          content:
              '${jsonEncode(_repositoryIndexEntriesJson(repositoryIndex.entries))}\n',
          expectedRevision: await _existingRevision(
            path: issuesIndexPath,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
        RepositoryTextFileChange(
          path: tombstoneIndexPath,
          content:
              '${jsonEncode(_tombstoneIndexEntriesJson(projectRoot, tombstoneIndexTombstones))}\n',
          expectedRevision: await _existingRevision(
            path: tombstoneIndexPath,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
        RepositoryTextFileChange(
          path: tombstoneArtifactPath,
          content: '${jsonEncode(_deletedIssueTombstoneJson(tombstone))}\n',
          expectedRevision: await _existingRevision(
            path: tombstoneArtifactPath,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
      ];

      try {
        await mutator.applyFileChanges(
          RepositoryFileChangeRequest(
            branch: writeBranch,
            message: 'Delete ${currentIssue.key} and reserve tombstone',
            changes: changes,
          ),
        );
        _repository.markHostedTreeStale();
        _snapshot = updatedSnapshot;
        return tombstone;
      } catch (_) {
        _knownTombstoneKeys.remove(tombstone.key);
        _knownTombstonesByKey.remove(tombstone.key);
        rethrow;
      }
    } finally {
      _releaseDeleteMutationLock();
    }
  }
}
