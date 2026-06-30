part of 'tracker_view_model.dart';

extension TrackerViewModelWorkspaceSync on TrackerViewModel {
  Future<void> _handleWorkspaceSyncRefresh(WorkspaceSyncRefresh refresh) async {
    if (_disposed) {
      return;
    }
    if (_shouldDeferWorkspaceSyncRefresh) {
      _pendingWorkspaceSyncRefresh = refresh;
      _workspaceSyncStatus = _workspaceSyncStatus.copyWith(
        hasPendingRefresh: true,
        health: WorkspaceSyncHealth.attentionNeeded,
        lastResult: refresh.result,
      );
      notifyListeners();
      return;
    }
    await _applyWorkspaceSyncRefresh(refresh);
  }

  Future<void> _applyPendingWorkspaceSyncRefresh() async {
    if (_disposed) {
      return;
    }
    final refresh = _pendingWorkspaceSyncRefresh;
    if (refresh == null || _shouldDeferWorkspaceSyncRefresh) {
      return;
    }
    _pendingWorkspaceSyncRefresh = null;
    await _applyWorkspaceSyncRefresh(refresh);
  }

  Future<void> _applyWorkspaceSyncRefresh(WorkspaceSyncRefresh refresh) async {
    if (_disposed) {
      return;
    }
    final snapshot = refresh.snapshot;
    final changedDomains = refresh.result.changedDomains;
    final shouldRefreshProjectMetadata =
        snapshot == null &&
        changedDomains.contains(WorkspaceSyncDomain.projectMeta);
    final shouldClearMissingSelection =
        changedDomains.contains(WorkspaceSyncDomain.issueSummaries) ||
        changedDomains.contains(WorkspaceSyncDomain.repositoryIndex);
    final previousSelectedIssueKey = _selectedIssue?.key;
    final selectedIssueRemovedFromWorkspace =
        shouldClearMissingSelection &&
        previousSelectedIssueKey != null &&
        snapshot != null &&
        !snapshot.issues.any((issue) => issue.key == previousSelectedIssueKey);
    if (snapshot != null) {
      await _applyReloadedSnapshot(
        snapshot,
        previousSelectedIssue: _selectedIssue,
        preferredSelectedIssueKey: _selectedIssue?.key,
        fallbackWhenMissing: !shouldClearMissingSelection,
      );
      if (changedDomains.contains(WorkspaceSyncDomain.projectMeta) ||
          changedDomains.contains(WorkspaceSyncDomain.issueSummaries) ||
          changedDomains.contains(WorkspaceSyncDomain.repositoryIndex)) {
        await _refreshSearchResultsAfterMutation(
          preferLoadedSnapshot: true,
          retainSelectionWhenMissing: false,
        );
        if (selectedIssueRemovedFromWorkspace) {
          _message = TrackerMessage.selectedIssueUnavailable(
            issueKey: previousSelectedIssueKey,
          );
        }
      }
    } else {
      if (shouldRefreshProjectMetadata) {
        await _refreshProjectMetadataForWorkspaceSync();
        await _refreshSearchResultsAfterMutation(preferLoadedSnapshot: true);
      }
      await _hydrateSelectedIssueForWorkspaceSync(refresh.result);
    }
    final refreshedIssueKeys = <String>{
      for (final domain in refresh.result.domains.values) ...domain.issueKeys,
    };
    for (final issueKey in refreshedIssueKeys) {
      _issueHistoryByKey.remove(issueKey);
    }
    _workspaceSyncStatus = _workspaceSyncStatus.copyWith(
      hasPendingRefresh: false,
      lastResult: refresh.result,
      latestError: null,
      health: WorkspaceSyncHealth.synced,
    );
    notifyListeners();
  }

  Future<void> _hydrateSelectedIssueForWorkspaceSync(
    WorkspaceSyncResult result,
  ) async {
    final currentIssue = _selectedIssue;
    final repository = _repository;
    if (currentIssue == null ||
        repository is! ProviderBackedTrackStateRepository) {
      return;
    }
    final scopes = <IssueHydrationScope>{};
    if (_syncChangeAppliesToIssue(
      result.domains[WorkspaceSyncDomain.comments],
      currentIssue.key,
    )) {
      scopes.add(IssueHydrationScope.comments);
    }
    if (_syncChangeAppliesToIssue(
      result.domains[WorkspaceSyncDomain.attachments],
      currentIssue.key,
    )) {
      scopes.add(IssueHydrationScope.attachments);
    }
    if (scopes.isEmpty) {
      return;
    }
    final hydrationContextToken = _captureIssueHydrationContext();
    for (final scope in scopes) {
      _clearIssueDeferredError(
        currentIssue.key,
        _deferredSectionForScope(scope),
      );
    }
    try {
      final hydrated = await repository.hydrateIssue(
        currentIssue,
        scopes: scopes,
        force: true,
      );
      if (!_shouldApplyHydratedIssueRefresh(
        hydrationContextToken: hydrationContextToken,
        issueKey: currentIssue.key,
      )) {
        return;
      }
      _applyTargetedIssueRefresh(hydrated);
      _refreshSearchResultsFromLoadedSnapshot(_snapshot!);
    } on TrackStatePartialHydrationException catch (error) {
      if (!_shouldApplyHydratedIssueRefresh(
        hydrationContextToken: hydrationContextToken,
        issueKey: currentIssue.key,
      )) {
        return;
      }
      _applyTargetedIssueRefresh(error.partialIssue);
      _refreshSearchResultsFromLoadedSnapshot(_snapshot!);
      for (final failedScope in error.failedScopes) {
        _setIssueDeferredError(
          currentIssue.key,
          _deferredSectionForScope(failedScope),
          '$error',
        );
      }
    } on Object catch (error) {
      for (final scope in scopes) {
        _setIssueDeferredError(
          currentIssue.key,
          _deferredSectionForScope(scope),
          '$error',
        );
      }
    }
  }

  Future<void> _refreshProjectMetadataForWorkspaceSync() async {
    final snapshot = _snapshot;
    final repository = _repository;
    if (snapshot == null) {
      return;
    }
    if (repository is! ProjectMetadataRepository) {
      return;
    }
    final refresh = await (repository as ProjectMetadataRepository)
        .loadProjectMetadata();
    _snapshot = TrackerSnapshot(
      project: refresh.project,
      issues: snapshot.issues,
      repositoryIndex: snapshot.repositoryIndex,
      loadWarnings: refresh.loadWarnings,
      readiness: snapshot.readiness,
      startupRecovery: snapshot.startupRecovery,
    );
    _updateWorkspaceSyncBaseline();
  }

  bool _syncChangeAppliesToIssue(
    WorkspaceSyncDomainChange? change,
    String issueKey,
  ) {
    if (change == null) {
      return false;
    }
    return change.isGlobal || change.issueKeys.contains(issueKey);
  }

  void _updateWorkspaceSyncBaseline() {
    final snapshot = _snapshot;
    if (snapshot == null) {
      return;
    }
    _workspaceSyncService?.updateBaselineSnapshot(snapshot);
  }

  bool get _shouldDeferWorkspaceSyncRefresh =>
      _isSaving ||
      _editSessionDepth > 0 ||
      _isUpdatingQuery ||
      _isLoadingMoreSearchResults;

  Future<void> _applyReloadedSnapshot(
    TrackerSnapshot snapshot, {
    required TrackStateIssue? previousSelectedIssue,
    required String? preferredSelectedIssueKey,
    bool fallbackWhenMissing = true,
    bool preserveStartupRecovery = false,
  }) async {
    final previousSelectedIssueKey = _selectedIssue?.key;
    _snapshot = snapshot;
    if (!preserveStartupRecovery || snapshot.startupRecovery != null) {
      _startupRecovery = snapshot.startupRecovery;
    }
    if (_jql.contains('project = TRACK') && snapshot.project.key != 'TRACK') {
      _jql = _jql.replaceFirst(
        'project = TRACK',
        'project = ${snapshot.project.key}',
      );
    }
    _selectedIssue = _resolveSelectedIssue(
      preferredSelectedIssueKey,
      snapshot.issues,
      fallbackWhenMissing,
    );
    if (_selectedIssue?.key != previousSelectedIssueKey) {
      _invalidateIssueHydrationContext();
    }
    _updateWorkspaceSyncBaseline();
    await _restoreSelectedIssueScopes(previousSelectedIssue);
  }

  Future<void> _restoreSelectedIssueScopes(
    TrackStateIssue? previousSelectedIssue,
  ) async {
    final currentIssue = _selectedIssue;
    final repository = _repository;
    if (previousSelectedIssue == null ||
        currentIssue == null ||
        previousSelectedIssue.key != currentIssue.key ||
        repository is! ProviderBackedTrackStateRepository) {
      return;
    }
    final scopes = <IssueHydrationScope>{
      for (final scope in IssueHydrationScope.values)
        if (_isScopeLoaded(previousSelectedIssue, scope) &&
            !_isScopeLoaded(currentIssue, scope))
          scope,
    };
    if (scopes.isEmpty) {
      return;
    }
    final hydrationContextToken = _captureIssueHydrationContext();
    for (final scope in scopes) {
      _clearIssueDeferredError(
        currentIssue.key,
        _deferredSectionForScope(scope),
      );
    }
    try {
      final hydrated = await repository.hydrateIssue(
        currentIssue,
        scopes: scopes,
      );
      if (!_shouldApplyHydratedIssueRefresh(
        hydrationContextToken: hydrationContextToken,
        issueKey: currentIssue.key,
      )) {
        return;
      }
      _applyTargetedIssueRefresh(hydrated);
      _refreshSearchResultsFromLoadedSnapshot(_snapshot!);
    } on TrackStatePartialHydrationException catch (error) {
      if (!_shouldApplyHydratedIssueRefresh(
        hydrationContextToken: hydrationContextToken,
        issueKey: currentIssue.key,
      )) {
        return;
      }
      _applyTargetedIssueRefresh(error.partialIssue);
      _refreshSearchResultsFromLoadedSnapshot(_snapshot!);
      for (final failedScope in error.failedScopes) {
        _setIssueDeferredError(
          currentIssue.key,
          _deferredSectionForScope(failedScope),
          '$error',
        );
      }
    } on Object catch (error) {
      for (final scope in scopes) {
        _setIssueDeferredError(
          currentIssue.key,
          _deferredSectionForScope(scope),
          '$error',
        );
      }
    }
  }
}
