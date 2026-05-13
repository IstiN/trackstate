import 'dart:convert';

import '../../domain/models/issue_mutation_models.dart';
import '../../domain/models/trackstate_models.dart';
import '../providers/trackstate_provider.dart';
import '../repositories/trackstate_repository.dart';

class IssueMutationService {
  IssueMutationService({required TrackStateRepository repository})
    : _repository = repository;

  final TrackStateRepository _repository;

  Future<IssueMutationResult<TrackStateIssue>> createIssue({
    required String summary,
    String description = '',
    String? issueTypeId,
    String? priorityId,
    String? assignee,
    String? reporter,
    String? parentKey,
    String? epicKey,
    Map<String, Object?> fields = const {},
  }) async {
    const operation = 'create';
    final normalizedSummary = summary.trim();
    if (normalizedSummary.isEmpty) {
      return _failure(
        operation: operation,
        issueKey: '',
        category: IssueMutationErrorCategory.validation,
        message: 'Issue summary is required before creating an issue.',
      );
    }

    final providerRepository = _providerRepository;
    if (providerRepository == null) {
      return _unsupported(operation: operation, issueKey: '');
    }

    try {
      final snapshot = await providerRepository.loadSnapshot();
      final provider = providerRepository.providerAdapter;
      final permission = await provider.getPermission();
      if (!permission.canWrite) {
        return _failure(
          operation: operation,
          issueKey: '',
          category: IssueMutationErrorCategory.permission,
          message: 'Connect a repository session with write access first.',
        );
      }
      await provider.ensureCleanWorktree();

      final key = _nextIssueKey(snapshot);
      final projectRoot = snapshot.project.key;
      final writeBranch = await provider.resolveWriteBranch();
      final blobPaths = await _blobPaths(provider, writeBranch);
      final issueTypeDefinition =
          _resolveConfigEntry(
            issueTypeId ?? fields['issueType']?.toString(),
            snapshot.project.issueTypeDefinitions,
          ) ??
          _resolveConfigEntry('story', snapshot.project.issueTypeDefinitions) ??
          snapshot.project.issueTypeDefinitions.firstOrNull;
      final priorityDefinition =
          _resolveConfigEntry(
            priorityId ?? fields['priority']?.toString(),
            snapshot.project.priorityDefinitions,
          ) ??
          _resolveConfigEntry('medium', snapshot.project.priorityDefinitions) ??
          snapshot.project.priorityDefinitions.firstOrNull;
      final statusDefinition =
          _defaultStatusDefinition(snapshot.project) ??
          snapshot.project.statusDefinitions.firstOrNull;
      if (issueTypeDefinition == null ||
          priorityDefinition == null ||
          statusDefinition == null) {
        return _failure(
          operation: operation,
          issueKey: key,
          category: IssueMutationErrorCategory.validation,
          message: 'Project configuration is missing required issue defaults.',
        );
      }

      final hierarchy = _resolveHierarchyForCreate(
        snapshot: snapshot,
        parentKey: parentKey,
        epicKey: epicKey,
        isEpicIssue: issueTypeDefinition.id == 'epic',
      );
      if (hierarchy.failure != null) {
        return _failure(
          operation: operation,
          issueKey: key,
          category: hierarchy.failure!.category,
          message: hierarchy.failure!.message,
          details: hierarchy.failure!.details,
        );
      }
      if (_canonicalConfigId(issueTypeDefinition.id) == 'subtask' &&
          hierarchy.parentKey == null) {
        return _failure(
          operation: operation,
          issueKey: key,
          category: IssueMutationErrorCategory.validation,
          message: 'Sub-task issues require a parent issue.',
        );
      }

      final issueRoot = hierarchy.issueRoot(projectRoot, key);
      final issuePath = '$issueRoot/main.md';
      if (blobPaths.contains(issuePath)) {
        return _failure(
          operation: operation,
          issueKey: key,
          category: IssueMutationErrorCategory.conflict,
          message: 'Issue path $issuePath already exists.',
        );
      }

      final timestamp = DateTime.now().toUtc().toIso8601String();
      final author =
          _normalizeNullableString(
            reporter ?? providerRepository.session?.resolvedUserIdentity,
          ) ??
          'unassigned';
      final normalizedAssignee = _normalizeNullableString(assignee) ?? author;
      final coreFields = _CreateIssueFields(
        issueTypeId: issueTypeDefinition.id,
        statusId: statusDefinition.id,
        priorityId: priorityDefinition.id,
        assignee: normalizedAssignee,
        reporter: author,
        parentKey: hierarchy.parentKey,
        epicKey: hierarchy.epicKey,
      );
      final createPayload = _CreateIssuePayload(
        summary: normalizedSummary,
        description: description.trim(),
        timestamp: timestamp,
        fields: fields,
        core: coreFields,
      );

      final markdown = _buildIssueMarkdown(
        key: key,
        projectKey: snapshot.project.key,
        payload: createPayload,
      );
      final updatedIssues = <_IssueIndexState>[
        for (final issue in snapshot.issues) _IssueIndexState.fromIssue(issue),
        _IssueIndexState(
          key: key,
          storagePath: issuePath,
          parentKey: hierarchy.parentKey,
          epicKey: hierarchy.epicKey,
          isArchived: false,
          summary: normalizedSummary,
          issueTypeId: issueTypeDefinition.id,
          statusId: statusDefinition.id,
          priorityId: priorityDefinition.id,
          assignee: normalizedAssignee,
          labels: _stringListValue(fields['labels']),
          updatedLabel: timestamp,
        ),
      ];
      final indexPath = '$projectRoot/.trackstate/index/issues.json';
      final changes = <RepositoryFileChange>[
        RepositoryTextFileChange(path: issuePath, content: markdown),
        RepositoryTextFileChange(
          path: indexPath,
          content: '${jsonEncode(_repositoryIndexJson(updatedIssues))}\n',
          expectedRevision: await _existingTextRevision(
            provider,
            path: indexPath,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
      ];

      final acceptanceCriteria = _normalizeAcceptanceCriteriaContent(
        fields['acceptanceCriteria'],
      );
      final acceptancePath = '$issueRoot/acceptance_criteria.md';
      if (acceptanceCriteria != null) {
        changes.add(
          RepositoryTextFileChange(
            path: acceptancePath,
            content: acceptanceCriteria,
          ),
        );
      }

      final commitResult = await _applyChanges(
        provider: provider,
        branch: writeBranch,
        message: 'Create $key',
        changes: changes,
      );
      final refreshed = await providerRepository.loadSnapshot();
      final createdIssue = refreshed.issues.firstWhere(
        (candidate) => candidate.key == key,
      );
      return IssueMutationResult.success(
        operation: operation,
        issueKey: key,
        value: createdIssue,
        revision: commitResult.revision,
      );
    } catch (error) {
      return _mapError<TrackStateIssue>(
        operation: operation,
        issueKey: '',
        error: error,
      );
    }
  }

  Future<IssueMutationResult<TrackStateIssue>> updateFields({
    required String issueKey,
    required Map<String, Object?> fields,
  }) async {
    const operation = 'update-fields';
    if (fields.isEmpty) {
      return _failure(
        operation: operation,
        issueKey: issueKey,
        category: IssueMutationErrorCategory.validation,
        message: 'Provide at least one field to update.',
      );
    }
    final prohibitedFields = [
      for (final key in fields.keys)
        if (key == 'status' ||
            key == 'issueType' ||
            key == 'parent' ||
            key == 'epic' ||
            key == 'archived')
          key,
    ];
    if (prohibitedFields.isNotEmpty) {
      return _failure(
        operation: operation,
        issueKey: issueKey,
        category: IssueMutationErrorCategory.validation,
        message:
            'Use dedicated lifecycle operations for ${prohibitedFields.join(', ')} changes.',
      );
    }

    final providerRepository = _providerRepository;
    if (providerRepository == null) {
      return _unsupported(operation: operation, issueKey: issueKey);
    }

    try {
      final resolution = await _resolveIssue(
        providerRepository,
        issueKey,
        operation,
      );
      if (resolution.failure != null) {
        return IssueMutationResult.failure(
          operation: operation,
          issueKey: issueKey,
          failure: resolution.failure!,
        );
      }
      final snapshot = resolution.snapshot!;
      final issue = resolution.issue!;
      final provider = providerRepository.providerAdapter;
      final writeBranch = await provider.resolveWriteBranch();
      final blobPaths = await _blobPaths(provider, writeBranch);
      final file = await provider.readTextFile(
        issue.storagePath,
        ref: writeBranch,
      );
      final document = _IssueDocument.parse(file.content);
      final frontmatter = {...document.frontmatter};
      final customFields = {
        ..._mapValue(frontmatter['customFields']),
        ..._extractCustomFields(frontmatter),
      };
      var body = document.body;

      for (final entry in fields.entries) {
        if (entry.key == 'summary') {
          final summary = _normalizeNullableString(entry.value);
          if (summary == null || summary.isEmpty) {
            return _failure(
              operation: operation,
              issueKey: issueKey,
              category: IssueMutationErrorCategory.validation,
              message: 'Summary cannot be empty.',
            );
          }
          frontmatter['summary'] = summary;
          body = _upsertSection(body, 'Summary', summary);
          continue;
        }
        if (entry.key == 'description') {
          final description = _normalizeNullableString(entry.value) ?? '';
          body = _upsertSection(body, 'Description', description);
          continue;
        }
        if (entry.key == 'priority') {
          final priorityDefinition = _resolveConfigEntry(
            entry.value?.toString(),
            snapshot.project.priorityDefinitions,
          );
          if (priorityDefinition == null) {
            return _failure(
              operation: operation,
              issueKey: issueKey,
              category: IssueMutationErrorCategory.validation,
              message: 'Unknown priority ${entry.value}.',
            );
          }
          frontmatter['priority'] = priorityDefinition.id;
          continue;
        }
        if (entry.key == 'assignee') {
          frontmatter['assignee'] = _normalizeNullableString(entry.value);
          continue;
        }
        if (entry.key == 'reporter') {
          frontmatter['reporter'] = _normalizeNullableString(entry.value);
          continue;
        }
        if (entry.key == 'labels') {
          frontmatter['labels'] = _stringListValue(entry.value);
          continue;
        }
        if (entry.key == 'components') {
          frontmatter['components'] = _stringListValue(entry.value);
          continue;
        }
        if (entry.key == 'fixVersions') {
          frontmatter['fixVersions'] = _stringListValue(entry.value);
          continue;
        }
        if (entry.key == 'watchers') {
          frontmatter['watchers'] = _stringListValue(entry.value);
          continue;
        }
        if (entry.key == 'resolution') {
          final resolutionDefinition = _resolveResolutionForUpdate(
            snapshot.project,
            issue,
            entry.value,
          );
          if (resolutionDefinition.failure != null) {
            return _failure(
              operation: operation,
              issueKey: issueKey,
              category: resolutionDefinition.failure!.category,
              message: resolutionDefinition.failure!.message,
            );
          }
          frontmatter['resolution'] = resolutionDefinition.value;
          continue;
        }
        if (entry.key == 'acceptanceCriteria') {
          continue;
        }
        if (entry.value == null) {
          customFields.remove(entry.key);
        } else {
          customFields[entry.key] = _normalizeStructuredValue(entry.value);
        }
      }

      frontmatter['customFields'] = customFields.isEmpty ? null : customFields;
      frontmatter['updated'] = DateTime.now().toUtc().toIso8601String();
      final markdown = _writeIssueMarkdown(
        frontmatter: frontmatter,
        body: body,
      );
      final changes = <RepositoryFileChange>[
        RepositoryTextFileChange(
          path: issue.storagePath,
          content: markdown,
          expectedRevision: file.revision,
        ),
      ];
      final updatedIndexState = _issueIndexStateFromFrontmatter(
        issue: issue,
        frontmatter: frontmatter,
        body: body,
        project: snapshot.project,
      );
      final indexPath = '${snapshot.project.key}/.trackstate/index/issues.json';
      changes.add(
        RepositoryTextFileChange(
          path: indexPath,
          content:
              '${jsonEncode(_repositoryIndexJson([for (final candidate in snapshot.issues)
                if (candidate.key == issue.key) updatedIndexState else _IssueIndexState.fromIssue(candidate)]))}\n',
          expectedRevision: await _existingTextRevision(
            provider,
            path: indexPath,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
      );
      final acceptancePath =
          '${_issueRoot(issue.storagePath)}/acceptance_criteria.md';
      if (fields.containsKey('acceptanceCriteria')) {
        final acceptanceCriteria = _normalizeAcceptanceCriteriaContent(
          fields['acceptanceCriteria'],
        );
        if (acceptanceCriteria == null) {
          changes.add(
            RepositoryDeleteFileChange(
              path: acceptancePath,
              expectedRevision: await _existingTextRevision(
                provider,
                path: acceptancePath,
                ref: writeBranch,
                blobPaths: blobPaths,
              ),
            ),
          );
        } else {
          changes.add(
            RepositoryTextFileChange(
              path: acceptancePath,
              content: acceptanceCriteria,
              expectedRevision: await _existingTextRevision(
                provider,
                path: acceptancePath,
                ref: writeBranch,
                blobPaths: blobPaths,
              ),
            ),
          );
        }
      }

      final commitResult = await _applyChanges(
        provider: provider,
        branch: writeBranch,
        message: 'Update $issueKey fields',
        changes: changes,
      );
      final refreshed = await providerRepository.hydrateIssue(
        issue,
        scopes: const {IssueHydrationScope.detail},
        force: true,
      );
      return IssueMutationResult.success(
        operation: operation,
        issueKey: issueKey,
        value: refreshed,
        revision: commitResult.revision,
      );
    } catch (error) {
      return _mapError<TrackStateIssue>(
        operation: operation,
        issueKey: issueKey,
        error: error,
      );
    }
  }

  Future<IssueMutationResult<List<TrackStateConfigEntry>>>
  availableTransitions({required String issueKey}) async {
    const operation = 'available-transitions';
    final providerRepository = _providerRepository;
    if (providerRepository == null) {
      return _unsupported(operation: operation, issueKey: issueKey);
    }

    try {
      final resolution = await _resolveIssue(
        providerRepository,
        issueKey,
        operation,
      );
      if (resolution.failure != null) {
        return IssueMutationResult.failure(
          operation: operation,
          issueKey: issueKey,
          failure: resolution.failure!,
        );
      }

      final snapshot = resolution.snapshot!;
      final issue = resolution.issue!;
      final provider = providerRepository.providerAdapter;
      final writeBranch = await provider.resolveWriteBranch();
      final workflow = await _loadWorkflow(
        provider: provider,
        issue: issue,
        project: snapshot.project,
        ref: writeBranch,
      );
      final transitions = snapshot.project.statusDefinitions
          .where(
            (status) =>
                _isTransitionAllowed(workflow, issue.statusId, status.id),
          )
          .toList(growable: false);
      return IssueMutationResult.success(
        operation: operation,
        issueKey: issueKey,
        value: transitions,
      );
    } catch (error) {
      return _mapError<List<TrackStateConfigEntry>>(
        operation: operation,
        issueKey: issueKey,
        error: error,
      );
    }
  }

  Future<IssueMutationResult<TrackStateIssue>> transitionIssue({
    required String issueKey,
    required String status,
    String? resolution,
  }) async {
    const operation = 'transition';
    final providerRepository = _providerRepository;
    if (providerRepository == null) {
      return _unsupported(operation: operation, issueKey: issueKey);
    }

    try {
      final resolutionData = await _resolveIssue(
        providerRepository,
        issueKey,
        operation,
      );
      if (resolutionData.failure != null) {
        return IssueMutationResult.failure(
          operation: operation,
          issueKey: issueKey,
          failure: resolutionData.failure!,
        );
      }
      final snapshot = resolutionData.snapshot!;
      final issue = resolutionData.issue!;
      final provider = providerRepository.providerAdapter;
      final writeBranch = await provider.resolveWriteBranch();
      final file = await provider.readTextFile(
        issue.storagePath,
        ref: writeBranch,
      );
      final document = _IssueDocument.parse(file.content);
      final frontmatter = {...document.frontmatter};
      final targetStatus = _resolveConfigEntry(
        status,
        snapshot.project.statusDefinitions,
      );
      if (targetStatus == null) {
        return _failure(
          operation: operation,
          issueKey: issueKey,
          category: IssueMutationErrorCategory.validation,
          message: 'Unknown target status $status.',
        );
      }

      final workflow = await _loadWorkflow(
        provider: provider,
        issue: issue,
        project: snapshot.project,
        ref: writeBranch,
      );
      if (!_isTransitionAllowed(workflow, issue.statusId, targetStatus.id)) {
        return _failure(
          operation: operation,
          issueKey: issueKey,
          category: IssueMutationErrorCategory.validation,
          message:
              'Workflow does not allow moving $issueKey from ${issue.statusId} to ${targetStatus.id}.',
        );
      }

      final resolvedResolution = _resolveTransitionResolution(
        issue: issue,
        targetStatusId: targetStatus.id,
        requestedResolutionId: resolution,
        project: snapshot.project,
      );
      if (resolvedResolution.failure != null) {
        return _failure(
          operation: operation,
          issueKey: issueKey,
          category: resolvedResolution.failure!.category,
          message: resolvedResolution.failure!.message,
        );
      }

      frontmatter['status'] = targetStatus.id;
      frontmatter['resolution'] = resolvedResolution.value;
      frontmatter['updated'] = DateTime.now().toUtc().toIso8601String();
      final markdown = _writeIssueMarkdown(
        frontmatter: frontmatter,
        body: document.body,
      );
      final blobPaths = await _blobPaths(provider, writeBranch);
      final indexPath = '${snapshot.project.key}/.trackstate/index/issues.json';
      final writeResult = await _applyChanges(
        provider: provider,
        branch: writeBranch,
        message: 'Move $issueKey to ${targetStatus.name}',
        changes: [
          RepositoryTextFileChange(
            path: issue.storagePath,
            content: markdown,
            expectedRevision: file.revision,
          ),
          RepositoryTextFileChange(
            path: indexPath,
            content:
                '${jsonEncode(_repositoryIndexJson([for (final candidate in snapshot.issues)
                  if (candidate.key == issue.key) _issueIndexStateFromFrontmatter(issue: issue, frontmatter: frontmatter, body: document.body, project: snapshot.project) else _IssueIndexState.fromIssue(candidate)]))}\n',
            expectedRevision: await _existingTextRevision(
              provider,
              path: indexPath,
              ref: writeBranch,
              blobPaths: blobPaths,
            ),
          ),
        ],
      );
      final refreshed = await providerRepository.hydrateIssue(
        issue,
        scopes: const {IssueHydrationScope.detail},
        force: true,
      );
      return IssueMutationResult.success(
        operation: operation,
        issueKey: issueKey,
        value: refreshed,
        revision: writeResult.revision,
      );
    } catch (error) {
      return _mapError<TrackStateIssue>(
        operation: operation,
        issueKey: issueKey,
        error: error,
      );
    }
  }

  Future<IssueMutationResult<TrackStateIssue>> reassignIssue({
    required String issueKey,
    String? parentKey,
    String? epicKey,
  }) async {
    const operation = 'reassign';
    final providerRepository = _providerRepository;
    if (providerRepository == null) {
      return _unsupported(operation: operation, issueKey: issueKey);
    }

    try {
      final resolution = await _resolveIssue(
        providerRepository,
        issueKey,
        operation,
      );
      if (resolution.failure != null) {
        return IssueMutationResult.failure(
          operation: operation,
          issueKey: issueKey,
          failure: resolution.failure!,
        );
      }
      final snapshot = resolution.snapshot!;
      final issue = resolution.issue!;
      final provider = providerRepository.providerAdapter;
      final mutator = switch (provider) {
        final RepositoryFileMutator supported => supported,
        _ => null,
      };
      if (mutator == null) {
        return _unsupported(operation: operation, issueKey: issueKey);
      }

      final hierarchy = _resolveHierarchyForMove(
        snapshot: snapshot,
        issue: issue,
        parentKey: parentKey,
        epicKey: epicKey,
        isEpicIssue: issue.isEpic,
      );
      if (hierarchy.failure != null) {
        return _failure(
          operation: operation,
          issueKey: issueKey,
          category: hierarchy.failure!.category,
          message: hierarchy.failure!.message,
          details: hierarchy.failure!.details,
        );
      }
      if (hierarchy.parentKey == issue.parentKey &&
          hierarchy.epicKey == issue.epicKey) {
        return IssueMutationResult.success(
          operation: operation,
          issueKey: issueKey,
          value: issue,
        );
      }

      final writeBranch = await provider.resolveWriteBranch();
      final tree = await provider.listTree(ref: writeBranch);
      final blobPaths = tree
          .where((entry) => entry.type == 'blob')
          .map((entry) => entry.path)
          .toSet();
      final oldRoot = _issueRoot(issue.storagePath);
      final newRoot = hierarchy.issueRoot(snapshot.project.key, issueKey);
      final subtreeIssues =
          snapshot.issues
              .where(
                (candidate) =>
                    candidate.storagePath == issue.storagePath ||
                    candidate.storagePath.startsWith('$oldRoot/'),
              )
              .toList()
            ..sort(
              (left, right) => left.storagePath.compareTo(right.storagePath),
            );

      final subtreePaths =
          blobPaths
              .where(
                (path) =>
                    path == issue.storagePath || path.startsWith('$oldRoot/'),
              )
              .toList()
            ..sort();
      for (final path in subtreePaths) {
        final newPath = '$newRoot${path.substring(oldRoot.length)}';
        if (blobPaths.contains(newPath) && !subtreePaths.contains(newPath)) {
          return _failure(
            operation: operation,
            issueKey: issueKey,
            category: IssueMutationErrorCategory.conflict,
            message: 'Target path $newPath already exists.',
          );
        }
      }

      final movedStateByKey = <String, _IssueIndexState>{};
      final updatedMarkdownByKey = <String, String>{};
      final changes = <RepositoryFileChange>[];
      final newEpicForSubtree = issue.isEpic ? issue.key : hierarchy.epicKey;
      for (final path in subtreePaths) {
        final newPath = '$newRoot${path.substring(oldRoot.length)}';
        if (path.endsWith('/main.md')) {
          final file = await provider.readTextFile(path, ref: writeBranch);
          final document = _IssueDocument.parse(file.content);
          final frontmatter = {...document.frontmatter};
          final currentKey = frontmatter['key']?.toString() ?? '';
          final isMovedIssue = currentKey == issueKey;
          final descendantEpicKey = isMovedIssue
              ? hierarchy.epicKey
              : (issue.isEpic ? issue.key : newEpicForSubtree);
          if (isMovedIssue) {
            frontmatter['parent'] = hierarchy.parentKey;
          }
          if (currentKey != issueKey || !issue.isEpic) {
            frontmatter['epic'] = descendantEpicKey;
          } else {
            frontmatter['epic'] = null;
          }
          frontmatter['updated'] = DateTime.now().toUtc().toIso8601String();
          final updatedMarkdown = _writeIssueMarkdown(
            frontmatter: frontmatter,
            body: document.body,
          );
          updatedMarkdownByKey[currentKey] = updatedMarkdown;
          changes.add(
            RepositoryTextFileChange(
              path: newPath,
              content: updatedMarkdown,
              expectedRevision: await _existingTextRevision(
                provider,
                path: newPath,
                ref: writeBranch,
                blobPaths: blobPaths,
              ),
            ),
          );
          final snapshotIssue = subtreeIssues.firstWhere(
            (candidate) => candidate.key == currentKey,
          );
          movedStateByKey[currentKey] = _IssueIndexState(
            key: currentKey,
            storagePath: newPath,
            parentKey: isMovedIssue
                ? hierarchy.parentKey
                : snapshotIssue.parentKey,
            epicKey: currentKey == issueKey && issue.isEpic
                ? null
                : descendantEpicKey,
            isArchived: snapshotIssue.isArchived,
            summary: snapshotIssue.summary,
            issueTypeId: snapshotIssue.issueTypeId,
            statusId: snapshotIssue.statusId,
            priorityId: snapshotIssue.priorityId,
            assignee: snapshotIssue.assignee,
            labels: snapshotIssue.labels,
            updatedLabel:
                frontmatter['updated']?.toString() ??
                snapshotIssue.updatedLabel,
            resolutionId: snapshotIssue.resolutionId,
          );
        } else if (_isAttachmentMetadataPath(path)) {
          final file = await provider.readTextFile(path, ref: writeBranch);
          changes.add(
            RepositoryTextFileChange(
              path: newPath,
              content: _rebaseAttachmentMetadataContent(
                file.content,
                oldRoot: _issueRoot(path),
                newRoot: _issueRoot(newPath),
              ),
              expectedRevision: await _existingTextRevision(
                provider,
                path: newPath,
                ref: writeBranch,
                blobPaths: blobPaths,
              ),
            ),
          );
        } else if (_isTextArtifactPath(path)) {
          final file = await provider.readTextFile(path, ref: writeBranch);
          changes.add(
            RepositoryTextFileChange(
              path: newPath,
              content: file.content,
              expectedRevision: await _existingTextRevision(
                provider,
                path: newPath,
                ref: writeBranch,
                blobPaths: blobPaths,
              ),
            ),
          );
        } else {
          final attachment = await provider.readAttachment(
            path,
            ref: writeBranch,
          );
          changes.add(
            RepositoryBinaryFileChange(
              path: newPath,
              bytes: attachment.bytes,
              expectedRevision: await _existingBinaryRevision(
                provider,
                path: newPath,
                ref: writeBranch,
                blobPaths: blobPaths,
              ),
            ),
          );
        }
        changes.add(
          RepositoryDeleteFileChange(
            path: path,
            expectedRevision: await _existingRevisionForDelete(
              provider,
              path: path,
              ref: writeBranch,
              blobPaths: blobPaths,
            ),
          ),
        );
      }

      final indexPath = '${snapshot.project.key}/.trackstate/index/issues.json';
      final updatedIndexStates = [
        for (final candidate in snapshot.issues)
          movedStateByKey[candidate.key] ??
              _IssueIndexState.fromIssue(candidate),
      ];
      changes.add(
        RepositoryTextFileChange(
          path: indexPath,
          content: '${jsonEncode(_repositoryIndexJson(updatedIndexStates))}\n',
          expectedRevision: await _existingTextRevision(
            provider,
            path: indexPath,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
      );

      final commitResult = await mutator.applyFileChanges(
        RepositoryFileChangeRequest(
          branch: writeBranch,
          message: 'Move $issueKey to canonical hierarchy',
          changes: changes,
        ),
      );
      final pathByKey = {
        for (final state in updatedIndexStates) state.key: state.storagePath,
      };
      final updatedIssues = [
        for (final candidate in snapshot.issues)
          if (movedStateByKey.containsKey(candidate.key))
            _retargetIssueForHierarchyMove(
              candidate,
              state: movedStateByKey[candidate.key]!,
              pathByKey: pathByKey,
              rawMarkdown: updatedMarkdownByKey[candidate.key],
            )
          else
            candidate,
      ]..sort((left, right) => left.key.compareTo(right.key));
      providerRepository.replaceCachedState(
        snapshot: TrackerSnapshot(
          project: snapshot.project,
          issues: updatedIssues,
          repositoryIndex: _deriveRepositoryIndex(
            updatedIssues,
            snapshot.repositoryIndex.deleted,
          ),
          loadWarnings: snapshot.loadWarnings,
          readiness: snapshot.readiness,
          startupRecovery: snapshot.startupRecovery,
        ),
        tree: await provider.listTree(ref: writeBranch),
      );
      return IssueMutationResult.success(
        operation: operation,
        issueKey: issueKey,
        value: updatedIssues.firstWhere(
          (candidate) => candidate.key == issueKey,
        ),
        revision: commitResult.revision,
      );
    } catch (error) {
      return _mapError<TrackStateIssue>(
        operation: operation,
        issueKey: issueKey,
        error: error,
      );
    }
  }

  Future<IssueMutationResult<TrackStateIssue>> addComment({
    required String issueKey,
    required String body,
  }) async {
    const operation = 'comment';
    if (body.trim().isEmpty) {
      return _failure(
        operation: operation,
        issueKey: issueKey,
        category: IssueMutationErrorCategory.validation,
        message: 'Comment body is required before posting.',
      );
    }

    final providerRepository = _providerRepository;
    if (providerRepository == null) {
      return _unsupported(operation: operation, issueKey: issueKey);
    }

    try {
      final resolution = await _resolveIssue(
        providerRepository,
        issueKey,
        operation,
      );
      if (resolution.failure != null) {
        return IssueMutationResult.failure(
          operation: operation,
          issueKey: issueKey,
          failure: resolution.failure!,
        );
      }

      final updatedIssue = await providerRepository.addIssueComment(
        resolution.issue!,
        body,
      );
      return IssueMutationResult.success(
        operation: operation,
        issueKey: issueKey,
        value: updatedIssue,
      );
    } catch (error) {
      return _mapError<TrackStateIssue>(
        operation: operation,
        issueKey: issueKey,
        error: error,
      );
    }
  }

  Future<IssueMutationResult<TrackStateIssue>> createLink({
    required String issueKey,
    required String targetKey,
    required String type,
  }) async {
    const operation = 'link';
    final providerRepository = _providerRepository;
    if (providerRepository == null) {
      return _unsupported(operation: operation, issueKey: issueKey);
    }

    try {
      final resolution = await _resolveIssue(
        providerRepository,
        issueKey,
        operation,
      );
      if (resolution.failure != null) {
        return IssueMutationResult.failure(
          operation: operation,
          issueKey: issueKey,
          failure: resolution.failure!,
        );
      }
      final snapshot = resolution.snapshot!;
      final issue = resolution.issue!;
      final target = snapshot.issues.where(
        (candidate) => candidate.key == targetKey,
      );
      if (target.isEmpty) {
        return _failure(
          operation: operation,
          issueKey: issueKey,
          category: IssueMutationErrorCategory.notFound,
          message: 'Could not find linked issue $targetKey.',
        );
      }

      final normalizedLink = _normalizeLinkType(type);
      if (normalizedLink == null) {
        return _failure(
          operation: operation,
          issueKey: issueKey,
          category: IssueMutationErrorCategory.validation,
          message: 'Unsupported link type $type.',
        );
      }

      final provider = providerRepository.providerAdapter;
      final writeBranch = await provider.resolveWriteBranch();
      final targetIssue = target.first;
      final storesCanonicalOutwardLink = normalizedLink.direction == 'inward';
      final issueRoot = _issueRoot(
        storesCanonicalOutwardLink
            ? targetIssue.storagePath
            : issue.storagePath,
      );
      final linksPath = '$issueRoot/links.json';
      final blobPaths = await _blobPaths(provider, writeBranch);
      final existingRevision = await _existingTextRevision(
        provider,
        path: linksPath,
        ref: writeBranch,
        blobPaths: blobPaths,
      );
      final existingLinks = blobPaths.contains(linksPath)
          ? _parseLinksJson(
              (await provider.readTextFile(
                linksPath,
                ref: writeBranch,
              )).content,
            )
          : <IssueLink>[];
      final duplicate = existingLinks.any(
        (entry) =>
            entry.type == normalizedLink.type &&
            entry.targetKey ==
                (storesCanonicalOutwardLink ? issueKey : targetKey) &&
            entry.direction == 'outward',
      );
      if (!duplicate) {
        existingLinks.add(
          IssueLink(
            type: normalizedLink.type,
            targetKey: storesCanonicalOutwardLink ? issueKey : targetKey,
            direction: 'outward',
          ),
        );
      }
      final writeResult = await provider.writeTextFile(
        RepositoryWriteRequest(
          path: linksPath,
          content: '${jsonEncode(_linksJson(existingLinks))}\n',
          message: 'Link $issueKey to $targetKey',
          branch: writeBranch,
          expectedRevision: existingRevision,
        ),
      );
      final refreshed = await providerRepository.loadSnapshot();
      return IssueMutationResult.success(
        operation: operation,
        issueKey: issueKey,
        value: refreshed.issues.firstWhere(
          (candidate) => candidate.key == issueKey,
        ),
        revision: writeResult.revision,
      );
    } catch (error) {
      return _mapError<TrackStateIssue>(
        operation: operation,
        issueKey: issueKey,
        error: error,
      );
    }
  }

  Future<IssueMutationResult<TrackStateIssue>> archiveIssue(
    String issueKey,
  ) async {
    const operation = 'archive';
    final providerRepository = _providerRepository;
    if (providerRepository == null) {
      return _unsupported(operation: operation, issueKey: issueKey);
    }

    try {
      final resolution = await _resolveIssue(
        providerRepository,
        issueKey,
        operation,
      );
      if (resolution.failure != null) {
        return IssueMutationResult.failure(
          operation: operation,
          issueKey: issueKey,
          failure: resolution.failure!,
        );
      }
      final archived = await providerRepository.archiveIssue(resolution.issue!);
      return IssueMutationResult.success(
        operation: operation,
        issueKey: issueKey,
        value: archived,
      );
    } catch (error) {
      return _mapError<TrackStateIssue>(
        operation: operation,
        issueKey: issueKey,
        error: error,
      );
    }
  }

  Future<IssueMutationResult<DeletedIssueTombstone>> deleteIssue(
    String issueKey,
  ) async {
    const operation = 'delete';
    final providerRepository = _providerRepository;
    if (providerRepository == null) {
      return _unsupported(operation: operation, issueKey: issueKey);
    }

    try {
      final resolution = await _resolveIssue(
        providerRepository,
        issueKey,
        operation,
      );
      if (resolution.failure != null) {
        return IssueMutationResult.failure(
          operation: operation,
          issueKey: issueKey,
          failure: resolution.failure!,
        );
      }
      final tombstone = await providerRepository.deleteIssue(resolution.issue!);
      return IssueMutationResult.success(
        operation: operation,
        issueKey: issueKey,
        value: tombstone,
      );
    } catch (error) {
      return _mapError<DeletedIssueTombstone>(
        operation: operation,
        issueKey: issueKey,
        error: error,
      );
    }
  }

  ProviderBackedTrackStateRepository? get _providerRepository =>
      switch (_repository) {
        final ProviderBackedTrackStateRepository repository => repository,
        _ => null,
      };

  IssueMutationResult<T> _unsupported<T>({
    required String operation,
    required String issueKey,
  }) => _failure(
    operation: operation,
    issueKey: issueKey,
    category: IssueMutationErrorCategory.providerFailure,
    message: 'This repository implementation does not expose shared mutations.',
  );

  IssueMutationResult<T> _failure<T>({
    required String operation,
    required String issueKey,
    required IssueMutationErrorCategory category,
    required String message,
    Map<String, Object?> details = const {},
  }) => IssueMutationResult.failure(
    operation: operation,
    issueKey: issueKey,
    failure: IssueMutationFailure(
      category: category,
      message: message,
      details: details,
    ),
  );

  Future<_ResolvedIssue> _resolveIssue(
    ProviderBackedTrackStateRepository repository,
    String issueKey,
    String operation,
  ) async {
    final snapshot =
        repository.cachedSnapshot ?? await repository.loadSnapshot();
    final matches = snapshot.issues.where(
      (candidate) => candidate.key == issueKey,
    );
    if (matches.isEmpty) {
      return _ResolvedIssue(
        failure: IssueMutationFailure(
          category: IssueMutationErrorCategory.notFound,
          message: 'Could not find issue $issueKey for $operation.',
        ),
      );
    }
    return _ResolvedIssue(snapshot: snapshot, issue: matches.single);
  }

  IssueMutationResult<T> _mapError<T>({
    required String operation,
    required String issueKey,
    required Object error,
  }) {
    if (error is IssueMutationResult<T>) return error;
    final normalized = error is TrackStateProviderException
        ? error.message
        : '$error';
    final lower = normalized.toLowerCase();
    late final IssueMutationErrorCategory category;
    if (lower.contains('write access')) {
      category = IssueMutationErrorCategory.permission;
    } else if (lower.contains('not find')) {
      category = IssueMutationErrorCategory.notFound;
    } else if (lower.contains('staged or unstaged') ||
        (lower.contains('commit') &&
            lower.contains('stash') &&
            lower.contains('clean'))) {
      category = IssueMutationErrorCategory.dirtyWorktree;
    } else if (lower.contains('changed in the current branch') ||
        lower.contains('already exists')) {
      category = IssueMutationErrorCategory.conflict;
    } else if (lower.contains('workflow') ||
        lower.contains('unknown') ||
        lower.contains('still has child issues')) {
      category = IssueMutationErrorCategory.validation;
    } else {
      category = IssueMutationErrorCategory.providerFailure;
    }
    return _failure(
      operation: operation,
      issueKey: issueKey,
      category: category,
      message: normalized,
    );
  }
}

class _ResolvedIssue {
  const _ResolvedIssue({this.snapshot, this.issue, this.failure});

  final TrackerSnapshot? snapshot;
  final TrackStateIssue? issue;
  final IssueMutationFailure? failure;
}

class _HierarchyResolution {
  const _HierarchyResolution({
    this.parentKey,
    this.epicKey,
    this.parentIssue,
    this.epicIssue,
    this.failure,
  });

  final String? parentKey;
  final String? epicKey;
  final TrackStateIssue? parentIssue;
  final TrackStateIssue? epicIssue;
  final IssueMutationFailure? failure;

  String issueRoot(String projectRoot, String issueKey) {
    if (parentIssue != null) {
      return '${_issueRoot(parentIssue!.storagePath)}/$issueKey';
    }
    if (epicIssue != null) {
      return '${_issueRoot(epicIssue!.storagePath)}/$issueKey';
    }
    return '$projectRoot/$issueKey';
  }
}

class _NormalizedLink {
  const _NormalizedLink({required this.type, required this.direction});

  final String type;
  final String direction;
}

class _IssueDocument {
  const _IssueDocument({required this.frontmatter, required this.body});

  factory _IssueDocument.parse(String markdown) {
    final lines = const LineSplitter().convert(markdown);
    if (lines.isEmpty || lines.first.trim() != '---') {
      return _IssueDocument(frontmatter: const {}, body: markdown.trim());
    }
    final endIndex = lines.indexWhere((line) => line.trim() == '---', 1);
    if (endIndex == -1) {
      return _IssueDocument(frontmatter: const {}, body: markdown.trim());
    }
    return _IssueDocument(
      frontmatter: _parseFrontmatter(lines.sublist(1, endIndex)),
      body: lines.skip(endIndex + 1).join('\n').trim(),
    );
  }

  final Map<String, Object?> frontmatter;
  final String body;
}

class _WorkflowDefinition {
  const _WorkflowDefinition({required this.transitions});

  final List<_WorkflowTransition> transitions;
}

class _WorkflowTransition {
  const _WorkflowTransition({required this.fromId, required this.toId});

  final String fromId;
  final String toId;
}

class _IssueIndexState {
  const _IssueIndexState({
    required this.key,
    required this.storagePath,
    required this.parentKey,
    required this.epicKey,
    required this.isArchived,
    required this.summary,
    required this.issueTypeId,
    required this.statusId,
    required this.priorityId,
    required this.assignee,
    required this.labels,
    required this.updatedLabel,
    this.resolutionId,
  });

  factory _IssueIndexState.fromIssue(TrackStateIssue issue) => _IssueIndexState(
    key: issue.key,
    storagePath: issue.storagePath,
    parentKey: issue.parentKey,
    epicKey: issue.epicKey,
    isArchived: issue.isArchived,
    summary: issue.summary,
    issueTypeId: issue.issueTypeId,
    statusId: issue.statusId,
    priorityId: issue.priorityId,
    assignee: issue.assignee,
    labels: issue.labels,
    updatedLabel: issue.updatedLabel,
    resolutionId: issue.resolutionId,
  );

  final String key;
  final String storagePath;
  final String? parentKey;
  final String? epicKey;
  final bool isArchived;
  final String summary;
  final String issueTypeId;
  final String priorityId;
  final String statusId;
  final String assignee;
  final List<String> labels;
  final String updatedLabel;
  final String? resolutionId;
}

TrackStateIssue _retargetIssueForHierarchyMove(
  TrackStateIssue issue, {
  required _IssueIndexState state,
  required Map<String, String> pathByKey,
  String? rawMarkdown,
}) {
  final oldRoot = _issueRoot(issue.storagePath);
  final newRoot = _issueRoot(state.storagePath);

  String rebaseArtifactPath(String path) {
    if (path.isEmpty || !path.startsWith(oldRoot)) {
      return path;
    }
    return '$newRoot${path.substring(oldRoot.length)}';
  }

  return TrackStateIssue(
    key: issue.key,
    project: issue.project,
    issueType: issue.issueType,
    issueTypeId: issue.issueTypeId,
    status: issue.status,
    statusId: issue.statusId,
    priority: issue.priority,
    priorityId: issue.priorityId,
    summary: issue.summary,
    description: issue.description,
    assignee: issue.assignee,
    reporter: issue.reporter,
    labels: issue.labels,
    components: issue.components,
    fixVersionIds: issue.fixVersionIds,
    watchers: issue.watchers,
    customFields: issue.customFields,
    parentKey: state.parentKey,
    epicKey: state.epicKey,
    parentPath: state.parentKey == null ? null : pathByKey[state.parentKey!],
    epicPath: state.epicKey == null ? null : pathByKey[state.epicKey!],
    progress: issue.progress,
    updatedLabel: state.updatedLabel,
    acceptanceCriteria: issue.acceptanceCriteria,
    comments: [
      for (final comment in issue.comments)
        IssueComment(
          id: comment.id,
          author: comment.author,
          body: comment.body,
          updatedLabel: comment.updatedLabel,
          createdAt: comment.createdAt,
          updatedAt: comment.updatedAt,
          storagePath: rebaseArtifactPath(comment.storagePath),
        ),
    ],
    links: issue.links,
    attachments: [
      for (final attachment in issue.attachments)
        attachment.copyWith(
          id: rebaseArtifactPath(attachment.id),
          storagePath: rebaseArtifactPath(attachment.storagePath),
          repositoryPath: attachment.repositoryPath == null
              ? null
              : rebaseArtifactPath(attachment.repositoryPath!),
        ),
    ],
    isArchived: issue.isArchived,
    hasDetailLoaded: issue.hasDetailLoaded,
    hasCommentsLoaded: issue.hasCommentsLoaded,
    hasAttachmentsLoaded: issue.hasAttachmentsLoaded,
    resolutionId: issue.resolutionId,
    storagePath: state.storagePath,
    rawMarkdown: rawMarkdown ?? issue.rawMarkdown,
  );
}

RepositoryIndex _deriveRepositoryIndex(
  List<TrackStateIssue> issues,
  List<DeletedIssueTombstone> deleted,
) {
  final pathByKey = {for (final issue in issues) issue.key: issue.storagePath};
  final childrenByKey = <String, List<String>>{};
  for (final issue in issues) {
    final relationshipParent = issue.parentKey ?? issue.epicKey;
    if (relationshipParent == null) {
      continue;
    }
    childrenByKey
        .putIfAbsent(relationshipParent, () => <String>[])
        .add(issue.key);
  }
  final entries = [
    for (final issue in issues)
      RepositoryIssueIndexEntry(
        key: issue.key,
        path: issue.storagePath,
        parentKey: issue.parentKey,
        epicKey: issue.epicKey,
        parentPath: issue.parentKey == null
            ? null
            : pathByKey[issue.parentKey!],
        epicPath: issue.epicKey == null ? null : pathByKey[issue.epicKey!],
        childKeys: [...(childrenByKey[issue.key] ?? const <String>[])]..sort(),
        isArchived: issue.isArchived,
        summary: issue.summary,
        issueTypeId: issue.issueTypeId,
        statusId: issue.statusId,
        priorityId: issue.priorityId,
        assignee: _normalizeNullableString(issue.assignee),
        labels: issue.labels,
        updatedLabel: issue.updatedLabel,
        progress: issue.progress,
        resolutionId: issue.resolutionId,
        revision: null,
      ),
  ]..sort((left, right) => left.key.compareTo(right.key));
  return RepositoryIndex(entries: entries, deleted: deleted);
}

class _CreateIssueFields {
  const _CreateIssueFields({
    required this.issueTypeId,
    required this.statusId,
    required this.priorityId,
    required this.assignee,
    required this.reporter,
    required this.parentKey,
    required this.epicKey,
  });

  final String issueTypeId;
  final String statusId;
  final String priorityId;
  final String assignee;
  final String reporter;
  final String? parentKey;
  final String? epicKey;
}

class _CreateIssuePayload {
  const _CreateIssuePayload({
    required this.summary,
    required this.description,
    required this.timestamp,
    required this.fields,
    required this.core,
  });

  final String summary;
  final String description;
  final String timestamp;
  final Map<String, Object?> fields;
  final _CreateIssueFields core;
}

_HierarchyResolution _resolveHierarchyForCreate({
  required TrackerSnapshot snapshot,
  String? parentKey,
  String? epicKey,
  bool isEpicIssue = false,
}) {
  final normalizedParentKey = _normalizeNullableString(parentKey);
  final normalizedEpicKey = _normalizeNullableString(epicKey);
  if (isEpicIssue &&
      (normalizedParentKey != null || normalizedEpicKey != null)) {
    return const _HierarchyResolution(
      failure: IssueMutationFailure(
        category: IssueMutationErrorCategory.validation,
        message: 'Epic issues cannot belong to a parent issue or another epic.',
      ),
    );
  }
  if (normalizedParentKey != null) {
    final parent = snapshot.issues.where(
      (candidate) => candidate.key == normalizedParentKey,
    );
    if (parent.isEmpty) {
      return const _HierarchyResolution(
        failure: IssueMutationFailure(
          category: IssueMutationErrorCategory.notFound,
          message: 'Could not find parent issue.',
        ),
      );
    }
    final parentIssue = parent.single;
    if (parentIssue.isEpic) {
      return _HierarchyResolution(
        parentKey: null,
        epicKey: parentIssue.key,
        epicIssue: parentIssue,
      );
    }
    final inheritedEpic = parentIssue.epicKey;
    if (normalizedEpicKey != null && normalizedEpicKey != inheritedEpic) {
      return const _HierarchyResolution(
        failure: IssueMutationFailure(
          category: IssueMutationErrorCategory.validation,
          message:
              'Explicit epic does not match the selected parent hierarchy.',
        ),
      );
    }
    TrackStateIssue? epicIssue;
    if (inheritedEpic != null) {
      final inheritedEpicMatches = snapshot.issues.where(
        (candidate) => candidate.key == inheritedEpic,
      );
      if (inheritedEpicMatches.isEmpty) {
        return const _HierarchyResolution(
          failure: IssueMutationFailure(
            category: IssueMutationErrorCategory.notFound,
            message: 'Could not find epic issue.',
          ),
        );
      }
      epicIssue = inheritedEpicMatches.single;
      if (!epicIssue.isEpic) {
        return const _HierarchyResolution(
          failure: IssueMutationFailure(
            category: IssueMutationErrorCategory.validation,
            message: 'Explicit epic target must reference an epic issue.',
          ),
        );
      }
    }
    return _HierarchyResolution(
      parentKey: parentIssue.key,
      epicKey: inheritedEpic,
      parentIssue: parentIssue,
      epicIssue: epicIssue,
    );
  }
  if (normalizedEpicKey == null) {
    return const _HierarchyResolution();
  }
  final epic = snapshot.issues.where(
    (candidate) => candidate.key == normalizedEpicKey,
  );
  if (epic.isEmpty) {
    return const _HierarchyResolution(
      failure: IssueMutationFailure(
        category: IssueMutationErrorCategory.notFound,
        message: 'Could not find epic issue.',
      ),
    );
  }
  final epicIssue = epic.single;
  if (!epicIssue.isEpic) {
    return const _HierarchyResolution(
      failure: IssueMutationFailure(
        category: IssueMutationErrorCategory.validation,
        message: 'Explicit epic target must reference an epic issue.',
      ),
    );
  }
  return _HierarchyResolution(epicKey: normalizedEpicKey, epicIssue: epicIssue);
}

_HierarchyResolution _resolveHierarchyForMove({
  required TrackerSnapshot snapshot,
  required TrackStateIssue issue,
  String? parentKey,
  String? epicKey,
  required bool isEpicIssue,
}) {
  final normalizedParentKey = _normalizeNullableString(parentKey);
  final normalizedEpicKey = _normalizeNullableString(epicKey);
  if (normalizedParentKey == issue.key || normalizedEpicKey == issue.key) {
    return const _HierarchyResolution(
      failure: IssueMutationFailure(
        category: IssueMutationErrorCategory.validation,
        message: 'An issue cannot become its own parent or epic.',
      ),
    );
  }
  if (normalizedParentKey == null) {
    return _resolveHierarchyForCreate(
      snapshot: snapshot,
      parentKey: null,
      epicKey: normalizedEpicKey,
      isEpicIssue: isEpicIssue,
    );
  }
  final parent = snapshot.issues.where(
    (candidate) => candidate.key == normalizedParentKey,
  );
  if (parent.isEmpty) {
    return const _HierarchyResolution(
      failure: IssueMutationFailure(
        category: IssueMutationErrorCategory.notFound,
        message: 'Could not find parent issue.',
      ),
    );
  }
  final parentIssue = parent.single;
  final issueRoot = _issueRoot(issue.storagePath);
  if (parentIssue.storagePath.startsWith('$issueRoot/')) {
    return const _HierarchyResolution(
      failure: IssueMutationFailure(
        category: IssueMutationErrorCategory.validation,
        message: 'Cannot move an issue under one of its descendants.',
      ),
    );
  }
  return _resolveHierarchyForCreate(
    snapshot: snapshot,
    parentKey: normalizedParentKey,
    epicKey: normalizedEpicKey,
    isEpicIssue: isEpicIssue,
  );
}

Future<RepositoryCommitResult> _applyChanges({
  required TrackStateProviderAdapter provider,
  required String branch,
  required String message,
  required List<RepositoryFileChange> changes,
}) async {
  final singleChange = changes.length == 1 ? changes.single : null;
  if (singleChange is RepositoryTextFileChange) {
    final result = await provider.writeTextFile(
      RepositoryWriteRequest(
        path: singleChange.path,
        content: singleChange.content,
        message: message,
        branch: branch,
        expectedRevision: singleChange.expectedRevision,
      ),
    );
    return RepositoryCommitResult(
      branch: result.branch,
      message: message,
      revision: result.revision,
    );
  }

  final mutator = switch (provider) {
    final RepositoryFileMutator supported => supported,
    _ => null,
  };
  if (mutator == null) {
    throw const TrackStateRepositoryException(
      'This repository provider does not support multi-file issue mutations yet.',
    );
  }
  return mutator.applyFileChanges(
    RepositoryFileChangeRequest(
      branch: branch,
      message: message,
      changes: changes,
    ),
  );
}

Future<Set<String>> _blobPaths(
  TrackStateProviderAdapter provider,
  String ref,
) async => (await provider.listTree(
  ref: ref,
)).where((entry) => entry.type == 'blob').map((entry) => entry.path).toSet();

bool _isTextArtifactPath(String path) {
  final normalized = path.toLowerCase();
  return normalized.endsWith('.md') ||
      normalized.endsWith('.json') ||
      normalized.endsWith('.txt') ||
      normalized.endsWith('.yaml') ||
      normalized.endsWith('.yml');
}

bool _isAttachmentMetadataPath(String path) =>
    path.toLowerCase().endsWith('/attachments.json');

String _rebaseAttachmentMetadataContent(
  String content, {
  required String oldRoot,
  required String newRoot,
}) {
  final json = jsonDecode(content);
  if (json is! List) {
    return content;
  }

  String rebasePathValue(Object? value) {
    final path = value?.toString() ?? '';
    if (path.isEmpty || !path.startsWith(oldRoot)) {
      return path;
    }
    return '$newRoot${path.substring(oldRoot.length)}';
  }

  return '${jsonEncode([
    for (final entry in json)
      if (entry is Map) {for (final mapEntry in entry.entries) mapEntry.key.toString(): switch (mapEntry.key.toString()) {
            'id' || 'storagePath' || 'repositoryPath' => rebasePathValue(mapEntry.value),
            _ => mapEntry.value,
          }} else entry,
  ])}\n';
}

Future<String?> _existingTextRevision(
  TrackStateProviderAdapter provider, {
  required String path,
  required String ref,
  required Set<String> blobPaths,
}) async {
  if (!blobPaths.contains(path)) {
    return null;
  }
  return (await provider.readTextFile(path, ref: ref)).revision;
}

Future<String?> _existingBinaryRevision(
  TrackStateProviderAdapter provider, {
  required String path,
  required String ref,
  required Set<String> blobPaths,
}) async {
  if (!blobPaths.contains(path)) {
    return null;
  }
  return (await provider.readAttachment(path, ref: ref)).revision;
}

Future<String?> _existingRevisionForDelete(
  TrackStateProviderAdapter provider, {
  required String path,
  required String ref,
  required Set<String> blobPaths,
}) async {
  if (!blobPaths.contains(path)) {
    return null;
  }
  if (path.endsWith('.md') || path.endsWith('.json') || path.endsWith('.txt')) {
    return _existingTextRevision(
      provider,
      path: path,
      ref: ref,
      blobPaths: blobPaths,
    );
  }
  return _existingBinaryRevision(
    provider,
    path: path,
    ref: ref,
    blobPaths: blobPaths,
  );
}

String _nextIssueKey(TrackerSnapshot snapshot) {
  var highest = 0;
  final pattern = RegExp('^${RegExp.escape(snapshot.project.key)}-(\\d+)\$');
  for (final issue in snapshot.issues) {
    final match = pattern.firstMatch(issue.key);
    final value = int.tryParse(match?.group(1) ?? '');
    if (value != null && value > highest) {
      highest = value;
    }
  }
  for (final tombstone in snapshot.repositoryIndex.deleted) {
    final match = pattern.firstMatch(tombstone.key);
    final value = int.tryParse(match?.group(1) ?? '');
    if (value != null && value > highest) {
      highest = value;
    }
  }
  return '${snapshot.project.key}-${highest + 1}';
}

TrackStateConfigEntry? _resolveConfigEntry(
  String? value,
  List<TrackStateConfigEntry> definitions,
) {
  final normalized = _canonicalConfigId(value);
  if (normalized.isEmpty) {
    return null;
  }
  for (final definition in definitions) {
    if (_canonicalConfigId(definition.id) == normalized ||
        _canonicalConfigId(definition.name) == normalized ||
        definition.localizedLabels.values.any(
          (label) => _canonicalConfigId(label) == normalized,
        )) {
      return definition;
    }
  }
  return null;
}

TrackStateConfigEntry? _defaultStatusDefinition(ProjectConfig project) =>
    _resolveConfigEntry('todo', project.statusDefinitions) ??
    project.statusDefinitions.firstOrNull;

IssueMutationResult<String?> _resolveResolutionForUpdate(
  ProjectConfig project,
  TrackStateIssue issue,
  Object? value,
) {
  if (value == null || value.toString().trim().isEmpty) {
    return const IssueMutationResult.success(
      operation: 'resolution',
      issueKey: '',
      value: null,
    );
  }
  if (issue.status != IssueStatus.done) {
    return const IssueMutationResult.failure(
      operation: 'resolution',
      issueKey: '',
      failure: IssueMutationFailure(
        category: IssueMutationErrorCategory.validation,
        message: 'Only done issues can keep a resolution.',
      ),
    );
  }
  final definition = _resolveConfigEntry(
    value.toString(),
    project.resolutionDefinitions,
  );
  if (definition == null) {
    return IssueMutationResult.failure(
      operation: 'resolution',
      issueKey: '',
      failure: IssueMutationFailure(
        category: IssueMutationErrorCategory.validation,
        message: 'Unknown resolution $value.',
      ),
    );
  }
  return IssueMutationResult.success(
    operation: 'resolution',
    issueKey: '',
    value: definition.id,
  );
}

IssueMutationResult<String?> _resolveTransitionResolution({
  required TrackStateIssue issue,
  required String targetStatusId,
  required String? requestedResolutionId,
  required ProjectConfig project,
}) {
  final targetStatusIsDone = _canonicalConfigId(targetStatusId) == 'done';
  if (!targetStatusIsDone) {
    return const IssueMutationResult.success(
      operation: 'resolution',
      issueKey: '',
      value: null,
    );
  }
  final resolved = _normalizeNullableString(requestedResolutionId);
  if (resolved != null) {
    final definition = _resolveConfigEntry(
      resolved,
      project.resolutionDefinitions,
    );
    if (definition == null) {
      return IssueMutationResult.failure(
        operation: 'resolution',
        issueKey: issue.key,
        failure: IssueMutationFailure(
          category: IssueMutationErrorCategory.validation,
          message: 'Unknown resolution $requestedResolutionId.',
        ),
      );
    }
    return IssueMutationResult.success(
      operation: 'resolution',
      issueKey: issue.key,
      value: definition.id,
    );
  }
  final resolutionDefinitions = project.resolutionDefinitions;
  if (resolutionDefinitions.length == 1) {
    return IssueMutationResult.success(
      operation: 'resolution',
      issueKey: issue.key,
      value: resolutionDefinitions.single.id,
    );
  }
  return IssueMutationResult.failure(
    operation: 'resolution',
    issueKey: issue.key,
    failure: const IssueMutationFailure(
      category: IssueMutationErrorCategory.validation,
      message: 'Done transitions must include a resolution.',
    ),
  );
}

Future<_WorkflowDefinition> _loadWorkflow({
  required TrackStateProviderAdapter provider,
  required TrackStateIssue issue,
  required ProjectConfig project,
  required String ref,
}) async {
  if (project.workflowDefinitions.isNotEmpty) {
    final issueTypeDefinition = project.issueTypeDefinitions.where(
      (definition) => definition.id == issue.issueTypeId,
    );
    final workflowId = issueTypeDefinition.isNotEmpty
        ? issueTypeDefinition.first.workflowId
        : null;
    final selectedWorkflow = project.workflowDefinitions
        .where(
          (workflow) =>
              workflow.id == workflowId ||
              (workflowId == null && workflow.id == 'default'),
        )
        .toList();
    final workflow = selectedWorkflow.isNotEmpty
        ? selectedWorkflow.first
        : project.workflowDefinitions.first;
    return _WorkflowDefinition(
      transitions: [
        for (final transition in workflow.transitions)
          _WorkflowTransition(
            fromId: transition.fromStatusId,
            toId: transition.toStatusId,
          ),
      ],
    );
  }
  final path = '${issue.project}/config/workflows.json';
  try {
    final file = await provider.readTextFile(path, ref: ref);
    final json = jsonDecode(file.content);
    if (json is! Map<String, Object?>) {
      throw const TrackStateRepositoryException(
        'config/workflows.json must contain an object.',
      );
    }
    final workflowJson = json['default'];
    if (workflowJson is! Map<String, Object?>) {
      throw const TrackStateRepositoryException(
        'config/workflows.json must contain a default workflow.',
      );
    }
    final transitions = workflowJson['transitions'];
    if (transitions is! List) {
      throw const TrackStateRepositoryException(
        'config/workflows.json must contain transitions.',
      );
    }
    return _WorkflowDefinition(
      transitions: [
        for (final entry in transitions.whereType<Map>())
          _WorkflowTransition(
            fromId:
                _resolveConfigEntry(
                  entry['from']?.toString(),
                  project.statusDefinitions,
                )?.id ??
                _canonicalConfigId(entry['from']?.toString()),
            toId:
                _resolveConfigEntry(
                  entry['to']?.toString(),
                  project.statusDefinitions,
                )?.id ??
                _canonicalConfigId(entry['to']?.toString()),
          ),
      ],
    );
  } on TrackStateProviderException {
    throw const TrackStateRepositoryException(
      'Workflow rules are required for status transitions but config/workflows.json was not found.',
    );
  }
}

bool _isTransitionAllowed(
  _WorkflowDefinition workflow,
  String currentStatusId,
  String targetStatusId,
) {
  final normalizedCurrent = _canonicalConfigId(currentStatusId);
  final normalizedTarget = _canonicalConfigId(targetStatusId);
  return workflow.transitions.any(
    (transition) =>
        _canonicalConfigId(transition.fromId) == normalizedCurrent &&
        _canonicalConfigId(transition.toId) == normalizedTarget,
  );
}

_NormalizedLink? _normalizeLinkType(String value) {
  final normalized = _canonicalConfigId(value);
  return switch (normalized) {
    'blocks' => const _NormalizedLink(type: 'blocks', direction: 'outward'),
    'is-blocked-by' => const _NormalizedLink(
      type: 'blocks',
      direction: 'inward',
    ),
    'relates' || 'relates-to' => const _NormalizedLink(
      type: 'relates-to',
      direction: 'outward',
    ),
    'duplicates' => const _NormalizedLink(
      type: 'duplicates',
      direction: 'outward',
    ),
    'is-duplicated-by' => const _NormalizedLink(
      type: 'duplicates',
      direction: 'inward',
    ),
    'clones' => const _NormalizedLink(type: 'clones', direction: 'outward'),
    'is-cloned-by' => const _NormalizedLink(
      type: 'clones',
      direction: 'inward',
    ),
    _ => null,
  };
}

List<IssueLink> _parseLinksJson(String content) {
  final json = jsonDecode(content);
  if (json is! List) {
    return const [];
  }
  return json
      .whereType<Map>()
      .map(
        (entry) => IssueLink(
          type: entry['type']?.toString() ?? 'relates-to',
          targetKey:
              entry['target']?.toString() ??
              entry['targetKey']?.toString() ??
              '',
          direction: entry['direction']?.toString() ?? 'outward',
        ),
      )
      .where((entry) => entry.targetKey.isNotEmpty)
      .toList();
}

List<Map<String, Object?>> _linksJson(List<IssueLink> links) => [
  for (final link in links)
    {'type': link.type, 'target': link.targetKey, 'direction': link.direction},
];

Map<String, Object?> _parseFrontmatter(List<String> lines) {
  final result = <String, Object?>{};
  String? pendingRootKey;
  String? activeRootListKey;
  String? activeMapKey;
  String? pendingMapListKey;

  for (final rawLine in lines) {
    if (rawLine.trim().isEmpty) {
      continue;
    }
    final indent = rawLine.length - rawLine.trimLeft().length;
    final line = rawLine.trimRight();
    final trimmed = line.trimLeft();
    final listItem = RegExp(r'^-\s+(.+)$').firstMatch(trimmed);
    final keyValue = RegExp(r'^([A-Za-z0-9_-]+):\s*(.*)$').firstMatch(trimmed);

    if (indent == 0) {
      pendingRootKey = null;
      activeRootListKey = null;
      activeMapKey = null;
      pendingMapListKey = null;
      if (keyValue == null) continue;
      final key = keyValue.group(1)!;
      final rawValue = keyValue.group(2)!.trim();
      if (rawValue.isEmpty) {
        pendingRootKey = key;
        result[key] = null;
      } else {
        result[key] = _parseScalar(rawValue);
      }
      continue;
    }

    if (indent == 2) {
      if (pendingRootKey != null) {
        if (listItem != null) {
          final list = <Object?>[];
          result[pendingRootKey] = list;
          activeRootListKey = pendingRootKey;
          pendingRootKey = null;
          list.add(_parseScalar(listItem.group(1)!));
          continue;
        }
        if (keyValue != null) {
          final map = <String, Object?>{};
          result[pendingRootKey] = map;
          activeMapKey = pendingRootKey;
          pendingRootKey = null;
          final nestedKey = keyValue.group(1)!;
          final nestedValue = keyValue.group(2)!.trim();
          if (nestedValue.isEmpty) {
            pendingMapListKey = nestedKey;
            map[nestedKey] = null;
          } else {
            map[nestedKey] = _parseScalar(nestedValue);
          }
          continue;
        }
      }
      if (activeRootListKey != null && listItem != null) {
        (result[activeRootListKey] as List<Object?>).add(
          _parseScalar(listItem.group(1)!),
        );
        continue;
      }
      if (activeMapKey != null && keyValue != null) {
        final map = result[activeMapKey] as Map<String, Object?>;
        final nestedKey = keyValue.group(1)!;
        final nestedValue = keyValue.group(2)!.trim();
        if (nestedValue.isEmpty) {
          pendingMapListKey = nestedKey;
          map[nestedKey] = null;
        } else {
          pendingMapListKey = null;
          map[nestedKey] = _parseScalar(nestedValue);
        }
      }
    }

    if (indent == 4 && activeMapKey != null && pendingMapListKey != null) {
      final map = result[activeMapKey] as Map<String, Object?>;
      if (listItem == null) continue;
      final list = (map[pendingMapListKey] as List<Object?>?) ?? <Object?>[];
      map[pendingMapListKey] = list;
      list.add(_parseScalar(listItem.group(1)!));
    }
  }

  return result;
}

Object? _parseScalar(String value) {
  final trimmed = value.trim();
  if (trimmed == 'null') return null;
  if (trimmed == 'true') return true;
  if (trimmed == 'false') return false;
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    try {
      return _normalizeStructuredValue(jsonDecode(trimmed));
    } on FormatException {
      return trimmed;
    }
  }
  if ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
      (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return trimmed.substring(1, trimmed.length - 1);
  }
  final intValue = int.tryParse(trimmed);
  if (intValue != null) return intValue;
  final doubleValue = double.tryParse(trimmed);
  if (doubleValue != null) return doubleValue;
  return trimmed;
}

String _buildIssueMarkdown({
  required String key,
  required String projectKey,
  required _CreateIssuePayload payload,
}) {
  final frontmatter = <String, Object?>{
    'key': key,
    'project': projectKey,
    'issueType': payload.core.issueTypeId,
    'status': payload.core.statusId,
    'priority': payload.core.priorityId,
    'summary': payload.summary,
    'assignee': payload.core.assignee,
    'reporter': payload.core.reporter,
    'labels': _stringListValue(payload.fields['labels']),
    'components': _stringListValue(payload.fields['components']),
    'fixVersions': _stringListValue(payload.fields['fixVersions']),
    'watchers': _stringListValue(payload.fields['watchers']),
    'parent': payload.core.parentKey,
    'epic': payload.core.epicKey,
    'created': payload.timestamp,
    'updated': payload.timestamp,
  };
  final customFields = {
    for (final entry in payload.fields.entries)
      if (!_reservedCreateFieldKeys.contains(entry.key) && entry.value != null)
        entry.key: _normalizeStructuredValue(entry.value),
  };
  if (customFields.isNotEmpty) {
    frontmatter['customFields'] = customFields;
  }
  final body = _upsertSection(
    _upsertSection('', 'Summary', payload.summary),
    'Description',
    payload.description,
  );
  return _writeIssueMarkdown(frontmatter: frontmatter, body: body);
}

const _reservedCreateFieldKeys = {
  'summary',
  'description',
  'issueType',
  'status',
  'priority',
  'assignee',
  'reporter',
  'labels',
  'components',
  'fixVersions',
  'watchers',
  'parent',
  'epic',
  'acceptanceCriteria',
};

String _writeIssueMarkdown({
  required Map<String, Object?> frontmatter,
  required String body,
}) {
  final orderedKeys = <String>[
    'key',
    'project',
    'issueType',
    'status',
    'priority',
    'summary',
    'assignee',
    'reporter',
    'labels',
    'components',
    'fixVersions',
    'watchers',
    'customFields',
    'parent',
    'epic',
    'created',
    'updated',
    'archived',
    'resolution',
    ...(() {
      final extraKeys =
          frontmatter.keys
              .where((key) => !_defaultFrontmatterOrder.contains(key))
              .toList()
            ..sort();
      return extraKeys;
    })(),
  ];
  final buffer = StringBuffer()..writeln('---');
  for (final key in orderedKeys) {
    if (!frontmatter.containsKey(key)) continue;
    _writeFrontmatterEntry(buffer, key, frontmatter[key]);
  }
  buffer
    ..writeln('---')
    ..writeln();
  final normalizedBody = body.trim();
  if (normalizedBody.isNotEmpty) {
    buffer.writeln(normalizedBody);
  }
  return '${buffer.toString().trimRight()}\n';
}

const _defaultFrontmatterOrder = {
  'key',
  'project',
  'issueType',
  'status',
  'priority',
  'summary',
  'assignee',
  'reporter',
  'labels',
  'components',
  'fixVersions',
  'watchers',
  'customFields',
  'parent',
  'epic',
  'created',
  'updated',
  'archived',
  'resolution',
};

void _writeFrontmatterEntry(StringBuffer buffer, String key, Object? value) {
  if (value == null) {
    buffer.writeln('$key: null');
    return;
  }
  if (value is bool || value is num) {
    buffer.writeln('$key: $value');
    return;
  }
  if (value is List || value is Map) {
    buffer.writeln('$key: ${jsonEncode(_normalizeStructuredValue(value))}');
    return;
  }
  final text = value.toString();
  if (RegExp(r'^[A-Za-z0-9._/\-]+$').hasMatch(text)) {
    buffer.writeln('$key: $text');
    return;
  }
  final escaped = text.replaceAll('\\', '\\\\').replaceAll('"', '\\"');
  buffer.writeln('$key: "$escaped"');
}

String _upsertSection(String markdown, String title, String content) {
  final normalizedContent = content.trim().isEmpty && title == 'Description'
      ? 'Describe the issue.'
      : content.trim();
  final header = '# $title';
  final start = markdown.indexOf(header);
  if (start != -1) {
    final nextHeaderStart = markdown.indexOf('\n# ', start + header.length);
    final prefix = markdown.substring(0, start);
    final replacement = '$header\n\n$normalizedContent';
    if (nextHeaderStart == -1) {
      return '$prefix$replacement';
    }
    final suffix = markdown.substring(nextHeaderStart + 1);
    return '$prefix$replacement\n\n$suffix';
  }
  final trimmed = markdown.trimRight();
  final separator = trimmed.isEmpty ? '' : '\n\n';
  return '$trimmed$separator# $title\n\n$normalizedContent';
}

String _issueRoot(String storagePath) =>
    storagePath.substring(0, storagePath.lastIndexOf('/'));

bool? _boolValue(Object? value) {
  if (value is bool) {
    return value;
  }
  final text = value?.toString().trim().toLowerCase();
  return switch (text) {
    'true' => true,
    'false' => false,
    _ => null,
  };
}

String? _normalizeNullableString(Object? value) {
  final text = value?.toString().trim();
  if (text == null || text.isEmpty || text == 'null') {
    return null;
  }
  return text;
}

String? _readSection(String body, String title) {
  final pattern = RegExp(
    '^#\\s+$title\\s*\$([\\s\\S]*?)(?=^#\\s+|\\z)',
    multiLine: true,
    caseSensitive: false,
  );
  final match = pattern.firstMatch(body);
  return match?.group(1)?.trim();
}

String _canonicalConfigId(String? value) {
  final normalized = (value ?? '').trim().toLowerCase();
  if (normalized.isEmpty) {
    return '';
  }
  return normalized
      .replaceAll('&', 'and')
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'-+'), '-')
      .replaceAll(RegExp(r'^-|-$'), '');
}

List<String> _stringListValue(Object? value) {
  if (value is List) {
    return value
        .map((entry) => entry.toString().trim())
        .where((entry) => entry.isNotEmpty)
        .toList(growable: false);
  }
  final text = _normalizeNullableString(value);
  if (text == null) {
    return const [];
  }
  return text
      .split(',')
      .map((entry) => entry.trim())
      .where((entry) => entry.isNotEmpty)
      .toList(growable: false);
}

Map<String, Object?> _mapValue(Object? value) {
  if (value is! Map) {
    return <String, Object?>{};
  }
  return {
    for (final entry in value.entries)
      entry.key.toString(): _normalizeStructuredValue(entry.value),
  };
}

Map<String, Object?> _extractCustomFields(Map<String, Object?> frontmatter) {
  final result = <String, Object?>{};
  for (final entry in frontmatter.entries) {
    if (_defaultFrontmatterOrder.contains(entry.key)) {
      continue;
    }
    result[entry.key] = _normalizeStructuredValue(entry.value);
  }
  return result;
}

Object? _normalizeStructuredValue(Object? value) {
  if (value is List) {
    return value
        .map<Object?>((entry) => _normalizeStructuredValue(entry))
        .toList(growable: false);
  }
  if (value is Map) {
    return {
      for (final entry in value.entries)
        entry.key.toString(): _normalizeStructuredValue(entry.value),
    };
  }
  return value;
}

String? _normalizeAcceptanceCriteriaContent(Object? value) {
  if (value == null) {
    return null;
  }
  final lines = switch (value) {
    final List entries =>
      entries
          .map((entry) => entry.toString().trim())
          .where((entry) => entry.isNotEmpty)
          .toList(growable: false),
    _ =>
      const LineSplitter()
          .convert(value.toString())
          .map((line) {
            final trimmed = line.trim();
            if (trimmed.startsWith('- ')) {
              return trimmed.substring(2).trim();
            }
            return trimmed;
          })
          .where((line) => line.isNotEmpty)
          .toList(growable: false),
  };
  if (lines.isEmpty) {
    return null;
  }
  return '${lines.map((line) => '- $line').join('\n')}\n';
}

_IssueIndexState _issueIndexStateFromFrontmatter({
  required TrackStateIssue issue,
  required Map<String, Object?> frontmatter,
  required String body,
  required ProjectConfig project,
}) {
  final issueTypeId =
      _resolveConfigEntry(
        frontmatter['issueType']?.toString(),
        project.issueTypeDefinitions,
      )?.id ??
      issue.issueTypeId;
  final statusId =
      _resolveConfigEntry(
        frontmatter['status']?.toString(),
        project.statusDefinitions,
      )?.id ??
      issue.statusId;
  final priorityId =
      _resolveConfigEntry(
        frontmatter['priority']?.toString(),
        project.priorityDefinitions,
      )?.id ??
      issue.priorityId;
  final resolutionId =
      _resolveConfigEntry(
        frontmatter['resolution']?.toString(),
        project.resolutionDefinitions,
      )?.id ??
      _normalizeNullableString(frontmatter['resolution']) ??
      issue.resolutionId;
  final summary =
      _normalizeNullableString(frontmatter['summary']) ??
      _readSection(body, 'Summary') ??
      issue.summary;
  return _IssueIndexState(
    key: issue.key,
    storagePath: issue.storagePath,
    parentKey: issue.parentKey,
    epicKey: issue.epicKey,
    isArchived: _boolValue(frontmatter['archived']) ?? issue.isArchived,
    summary: summary,
    issueTypeId: issueTypeId,
    statusId: statusId,
    priorityId: priorityId,
    assignee:
        _normalizeNullableString(frontmatter['assignee']) ?? issue.assignee,
    labels: _stringListValue(frontmatter['labels']),
    updatedLabel: frontmatter['updated']?.toString() ?? issue.updatedLabel,
    resolutionId: resolutionId,
  );
}

List<Map<String, Object?>> _repositoryIndexJson(List<_IssueIndexState> issues) {
  final pathByKey = {for (final issue in issues) issue.key: issue.storagePath};
  final childrenByKey = <String, List<String>>{};
  for (final issue in issues) {
    final relationshipParent = issue.parentKey ?? issue.epicKey;
    if (relationshipParent == null) {
      continue;
    }
    childrenByKey
        .putIfAbsent(relationshipParent, () => <String>[])
        .add(issue.key);
  }
  return [
    for (final issue in [
      ...issues,
    ]..sort((left, right) => left.key.compareTo(right.key)))
      {
        'key': issue.key,
        'path': issue.storagePath,
        'parent': issue.parentKey,
        'epic': issue.epicKey,
        'parentPath': issue.parentKey == null
            ? null
            : pathByKey[issue.parentKey!],
        'epicPath': issue.epicKey == null ? null : pathByKey[issue.epicKey!],
        'summary': issue.summary,
        'issueType': issue.issueTypeId,
        'status': issue.statusId,
        'priority': issue.priorityId,
        'assignee': issue.assignee,
        'labels': issue.labels,
        'updated': issue.updatedLabel,
        'resolution': issue.resolutionId,
        'children': [...(childrenByKey[issue.key] ?? const <String>[])]..sort(),
        'archived': issue.isArchived,
      },
  ];
}
