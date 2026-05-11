import 'package:flutter_test/flutter_test.dart';
import 'dart:typed_data';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('view model loads snapshot and default search results', () async {
    final viewModel = TrackerViewModel(
      repository: const DemoTrackStateRepository(),
    );

    await viewModel.load();

    expect(viewModel.project?.key, 'TRACK');
    expect(viewModel.selectedIssue?.key, 'TRACK-12');
    expect(viewModel.searchResults, isNotEmpty);
  });

  test(
    'view model routes hosted startup recovery into settings when reduced bootstrap succeeds',
    () async {
      final snapshot = await const DemoTrackStateRepository().loadSnapshot();
      final recoveryRepository = _StartupRecoveryRepository(
        loadResults: [_withStartupRecovery(snapshot)],
      );
      final viewModel = TrackerViewModel(repository: recoveryRepository);

      await viewModel.load();

      expect(viewModel.snapshot, isNotNull);
      expect(
        viewModel.startupRecovery?.kind,
        TrackerStartupRecoveryKind.githubRateLimit,
      );
      expect(viewModel.section, TrackerSection.settings);
      expect(recoveryRepository.loadCount, 1);
    },
  );

  test(
    'view model maps blocking hosted rate limits into recovery instead of generic data-load failure',
    () async {
      final viewModel = TrackerViewModel(
        repository: _StartupRecoveryRepository(
          loadResults: const [
            GitHubRateLimitException(
              message:
                  'GitHub API request failed for /repos/demo/contents/.trackstate/index/issues.json (403): {"message":"API rate limit exceeded"}',
              requestPath: '/repos/demo/contents/.trackstate/index/issues.json',
              statusCode: 403,
            ),
          ],
        ),
      );

      await viewModel.load();

      expect(viewModel.snapshot, isNull);
      expect(
        viewModel.startupRecovery?.kind,
        TrackerStartupRecoveryKind.githubRateLimit,
      );
      expect(viewModel.message?.kind, isNot(TrackerMessageKind.dataLoadFailed));
    },
  );

  test('view model appends the next search page through load more', () async {
    final viewModel = TrackerViewModel(
      repository: DemoTrackStateRepository(
        snapshot: _searchPaginationSnapshot(),
      ),
    );

    await viewModel.load();

    expect(viewModel.searchResults.length, 6);
    expect(viewModel.totalSearchResults, 8);
    expect(viewModel.hasMoreSearchResults, isTrue);

    await viewModel.loadMoreSearchResults();

    expect(viewModel.searchResults.length, 8);
    expect(viewModel.searchResults.last.key, 'TRACK-8');
    expect(viewModel.hasMoreSearchResults, isFalse);
  });

  test(
    'view model restores the last valid query after a search failure',
    () async {
      final viewModel = TrackerViewModel(
        repository: const _ThrowingSearchRepository(),
      );

      await viewModel.load();
      final previousQuery = viewModel.jql;
      final previousResults = viewModel.searchResults
          .map((issue) => issue.key)
          .toList();

      await viewModel.updateQuery('text = broken');

      expect(viewModel.jql, previousQuery);
      expect(
        viewModel.searchResults.map((issue) => issue.key),
        previousResults,
      );
      expect(viewModel.message?.kind, TrackerMessageKind.searchFailed);
    },
  );

  test('view model changes sections and toggles theme', () async {
    final viewModel = TrackerViewModel(
      repository: const DemoTrackStateRepository(),
    );
    await viewModel.load();

    viewModel.selectSection(TrackerSection.board);
    viewModel.toggleTheme();

    expect(viewModel.section, TrackerSection.board);
    expect(viewModel.themePreference, ThemePreference.dark);
  });

  test('view model restores remembered GitHub token', () async {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': 'stored-token',
    });
    final viewModel = TrackerViewModel(
      repository: const DemoTrackStateRepository(),
    );

    await viewModel.load();

    expect(viewModel.isConnected, isTrue);
    expect(viewModel.connectedUser?.initials, 'DU');
  });

  test(
    'view model resumes startup recovery once after GitHub authentication succeeds',
    () async {
      final snapshot = await const DemoTrackStateRepository().loadSnapshot();
      final repository = _StartupRecoveryRepository(
        loadResults: [_withStartupRecovery(snapshot), snapshot],
      );
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      await viewModel.connectGitHub('token');

      expect(repository.loadCount, 2);
      expect(repository.connectCount, 1);
      expect(viewModel.startupRecovery, isNull);
      expect(viewModel.section, TrackerSection.settings);
    },
  );

  test(
    'view model loads the local repository user for avatar details',
    () async {
      final viewModel = TrackerViewModel(
        repository: const _LocalRuntimeRepository(),
      );

      await viewModel.load();

      expect(viewModel.connectedUser?.displayName, 'Local User');
      expect(viewModel.connectedUser?.initials, 'LU');
    },
  );

  test(
    'view model keeps deferred detail failures scoped to the issue instead of failing the whole app',
    () async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'write-enabled-token',
      });
      final viewModel = TrackerViewModel(
        repository: ReactiveIssueDetailTrackStateRepository(
          failingTextPaths: {'TRACK-12/main.md'},
        ),
      );

      await viewModel.load();
      final issue = viewModel.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );

      await viewModel.ensureIssueDetailLoaded(issue);

      expect(
        viewModel.issueDeferredError(issue.key, IssueDeferredSection.detail),
        contains('Deferred read failed for TRACK-12/main.md'),
      );
      expect(
        viewModel.hasIssueDeferredError(issue.key, IssueDeferredSection.detail),
        isTrue,
      );
      expect(
        viewModel.message?.kind,
        isNot(TrackerMessageKind.issueSaveFailed),
      );
      expect(viewModel.snapshot, isNotNull);
    },
  );

  test(
    'view model reports local persistence after a successful move',
    () async {
      final viewModel = TrackerViewModel(
        repository: const _LocalRuntimeRepository(),
      );

      await viewModel.load();
      await viewModel.moveIssue(viewModel.selectedIssue!, IssueStatus.done);

      expect(viewModel.message?.kind, TrackerMessageKind.localGitMoveCommitted);
    },
  );

  test(
    'view model updates issue status without reloading the full snapshot',
    () async {
      final repository = _MutableEditRepository(
        snapshot: await const DemoTrackStateRepository().loadSnapshot(),
      );
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      final issue = viewModel.selectedIssue!;

      await viewModel.moveIssue(issue, IssueStatus.done);

      expect(repository.loadSnapshotCount, 1);
      expect(viewModel.selectedIssue?.statusId, 'done');
    },
  );

  test(
    'view model posts comments without reloading the full snapshot',
    () async {
      final repository = _MutableEditRepository(
        snapshot: await const DemoTrackStateRepository().loadSnapshot(),
      );
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      final issue = viewModel.selectedIssue!;

      final success = await viewModel.postIssueComment(
        issue,
        'Scoped comment refresh.',
      );

      expect(success, isTrue);
      expect(repository.loadSnapshotCount, 1);
      expect(
        viewModel.selectedIssue?.comments.any(
          (comment) => comment.body == 'Scoped comment refresh.',
        ),
        isTrue,
      );
    },
  );

  test(
    'view model uploads attachments without reloading the full snapshot',
    () async {
      final repository = _MutableEditRepository(
        snapshot: await const DemoTrackStateRepository().loadSnapshot(),
      );
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      final issue = viewModel.selectedIssue!;

      final success = await viewModel.uploadIssueAttachment(
        issue: issue,
        name: 'design spec.pdf',
        bytes: Uint8List.fromList(<int>[1, 2, 3]),
      );

      expect(success, isTrue);
      expect(repository.loadSnapshotCount, 1);
      expect(
        viewModel.selectedIssue?.attachments.any(
          (attachment) => attachment.name == 'design-spec.pdf',
        ),
        isTrue,
      );
    },
  );

  test(
    'view model reacts to live provider session capability downgrades',
    () async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'write-enabled-token',
      });
      final repository = ReactiveIssueDetailTrackStateRepository();
      final viewModel = TrackerViewModel(repository: repository);
      var notificationCount = 0;
      viewModel.addListener(() {
        notificationCount += 1;
      });

      await viewModel.load();

      expect(viewModel.hasReadOnlySession, isFalse);

      notificationCount = 0;
      repository.synchronizeSessionToReadOnly();

      expect(viewModel.hasReadOnlySession, isTrue);
      expect(
        notificationCount,
        greaterThan(0),
        reason:
            'Expected the view model to notify listeners when the active provider session becomes read-only.',
      );
      viewModel.dispose();
    },
  );

  test(
    'view model treats hosted browser mode as disconnected until GitHub auth is connected',
    () async {
      final viewModel = TrackerViewModel(
        repository: ReactiveIssueDetailTrackStateRepository(),
      );

      await viewModel.load();

      expect(
        viewModel.hostedRepositoryAccessMode,
        HostedRepositoryAccessMode.disconnected,
      );
      expect(viewModel.hasBlockedWriteAccess, isTrue);
    },
  );

  test(
    'view model reports attachment restrictions without blocking issue edits',
    () async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'limited-attachments',
      });
      const attachmentRestrictedPermission = RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: false,
        attachmentUploadMode: AttachmentUploadMode.noLfs,
        canCheckCollaborators: false,
      );
      final viewModel = TrackerViewModel(
        repository: ReactiveIssueDetailTrackStateRepository(
          permission: attachmentRestrictedPermission,
        ),
      );

      await viewModel.load();

      expect(
        viewModel.hostedRepositoryAccessMode,
        HostedRepositoryAccessMode.attachmentRestricted,
      );
      expect(viewModel.canUploadIssueAttachments, isFalse);
      expect(viewModel.hasBlockedWriteAccess, isFalse);
      expect(viewModel.hasAttachmentUploadRestriction, isTrue);
    },
  );

  test(
    'view model blocks hosted create mutations until GitHub write access is available',
    () async {
      final viewModel = TrackerViewModel(
        repository: ReactiveIssueDetailTrackStateRepository(),
      );

      await viewModel.load();
      final success = await viewModel.createIssue(summary: 'Blocked write');

      expect(success, isFalse);
      expect(viewModel.message?.kind, TrackerMessageKind.issueSaveFailed);
      expect(
        viewModel.message?.error,
        contains('Connect GitHub with repository Contents write access'),
      );
    },
  );

  test(
    'view model blocks hosted comments when the repository session is read-only',
    () async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'read-only-token',
      });
      const readOnlyPermission = RepositoryPermission(
        canRead: true,
        canWrite: false,
        isAdmin: false,
        canCreateBranch: false,
        canManageAttachments: false,
        canCheckCollaborators: false,
      );
      final repository = ReactiveIssueDetailTrackStateRepository(
        permission: readOnlyPermission,
      );
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      final success = await viewModel.postIssueComment(
        viewModel.selectedIssue!,
        'Blocked comment',
      );

      expect(success, isFalse);
      expect(
        viewModel.hostedRepositoryAccessMode,
        HostedRepositoryAccessMode.readOnly,
      );
      expect(viewModel.message?.kind, TrackerMessageKind.issueSaveFailed);
      expect(
        viewModel.message?.error,
        contains('This repository session is read-only'),
      );
    },
  );

  test(
    'view model inspects sanitized attachment collisions against existing files',
    () async {
      final viewModel = TrackerViewModel(
        repository: const DemoTrackStateRepository(),
      );

      await viewModel.load();
      final inspection = await viewModel.inspectIssueAttachmentUpload(
        viewModel.selectedIssue!,
        'sync sequence.svg',
      );

      expect(inspection.resolvedName, 'sync-sequence.svg');
      expect(
        inspection.existingAttachment?.storagePath,
        endsWith('sync-sequence.svg'),
      );
      expect(inspection.isLfsTracked, isFalse);
    },
  );

  test(
    'view model blocks attachment uploads when the session cannot manage attachments',
    () async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'limited-attachments',
      });
      const attachmentRestrictedPermission = RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: false,
        attachmentUploadMode: AttachmentUploadMode.noLfs,
        canCheckCollaborators: false,
      );
      final viewModel = TrackerViewModel(
        repository: ReactiveIssueDetailTrackStateRepository(
          permission: attachmentRestrictedPermission,
        ),
      );

      await viewModel.load();
      final issue = viewModel.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );
      final success = await viewModel.uploadIssueAttachment(
        issue: issue,
        name: 'release notes.pdf',
        bytes: Uint8List.fromList(<int>[1, 2, 3, 4]),
      );

      expect(viewModel.canUploadIssueAttachments, isFalse);
      expect(success, isFalse);
      expect(viewModel.message?.kind, TrackerMessageKind.issueSaveFailed);
      expect(
        viewModel.message?.error,
        contains('Attachment upload is unavailable in this repository session'),
      );
    },
  );

  test(
    'view model refreshes selected issue after uploading an attachment',
    () async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'write-enabled-token',
      });
      final viewModel = TrackerViewModel(
        repository: ReactiveIssueDetailTrackStateRepository(),
      );

      await viewModel.load();
      final issue = viewModel.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );

      final success = await viewModel.uploadIssueAttachment(
        issue: issue,
        name: 'release notes.pdf',
        bytes: Uint8List.fromList(<int>[1, 2, 3, 4]),
      );

      expect(success, isTrue);
      expect(viewModel.selectedIssue?.attachments, isNotEmpty);
      expect(
        viewModel.selectedIssue?.attachments.first.name,
        'release-notes.pdf',
      );
      expect(viewModel.selectedIssue?.attachments.first.sizeBytes, 4);
    },
  );

  test(
    'view model marks LFS-tracked attachment uploads for browser restriction checks',
    () async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'limited-attachments',
      });
      const attachmentRestrictedPermission = RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: true,
        attachmentUploadMode: AttachmentUploadMode.noLfs,
        canCheckCollaborators: false,
      );
      final viewModel = TrackerViewModel(
        repository: ReactiveIssueDetailTrackStateRepository(
          permission: attachmentRestrictedPermission,
          lfsTrackedPaths: {'TRACK-12/attachments/release-notes.pdf'},
        ),
      );

      await viewModel.load();
      final issue = viewModel.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );
      final inspection = await viewModel.inspectIssueAttachmentUpload(
        issue,
        'release notes.pdf',
      );

      expect(viewModel.canUploadIssueAttachments, isTrue);
      expect(viewModel.hasAttachmentUploadRestriction, isTrue);
      expect(inspection.isLfsTracked, isTrue);
      expect(inspection.resolvedName, 'release-notes.pdf');
    },
  );

  test(
    'view model preserves return context when opening an issue detail',
    () async {
      final viewModel = TrackerViewModel(
        repository: const DemoTrackStateRepository(),
      );
      await viewModel.load();

      final issue = viewModel.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );
      viewModel.selectIssue(issue, returnSection: TrackerSection.board);

      expect(viewModel.section, TrackerSection.search);
      expect(viewModel.issueDetailReturnSection, TrackerSection.board);

      viewModel.returnFromIssueDetail();

      expect(viewModel.section, TrackerSection.board);
      expect(viewModel.issueDetailReturnSection, isNull);
    },
  );

  test(
    'view model uses shared mutations and preserves the origin after create',
    () async {
      final repository = const DemoTrackStateRepository();
      final createdIssue = TrackStateIssue(
        key: 'TRACK-99',
        project: 'TRACK',
        issueType: IssueType.story,
        issueTypeId: 'story',
        status: IssueStatus.todo,
        statusId: 'todo',
        priority: IssuePriority.medium,
        priorityId: 'medium',
        summary: 'Created through view model',
        description: 'Uses shared mutation result.',
        assignee: 'demo-user',
        reporter: 'demo-user',
        labels: const ['ux'],
        components: const [],
        fixVersionIds: const [],
        watchers: const [],
        customFields: const {},
        parentKey: null,
        epicKey: 'TRACK-1',
        parentPath: null,
        epicPath: 'TRACK/TRACK-1',
        progress: 0,
        updatedLabel: 'just now',
        acceptanceCriteria: const [],
        comments: const [],
        links: const [],
        attachments: const [],
        isArchived: false,
        storagePath: 'TRACK/TRACK-1/TRACK-99/main.md',
        rawMarkdown: '',
      );
      final viewModel = TrackerViewModel(
        repository: repository,
        issueMutationService: _RecordingIssueMutationService(createdIssue),
      );

      await viewModel.load();

      final success = await viewModel.createIssue(
        summary: 'Created through view model',
        description: 'Uses shared mutation result.',
        issueTypeId: 'story',
        priorityId: 'medium',
        assignee: 'demo-user',
        epicKey: 'TRACK-1',
        labels: const ['ux'],
        returnSection: TrackerSection.hierarchy,
      );

      expect(success, isTrue);
      expect(viewModel.section, TrackerSection.search);
      expect(viewModel.issueDetailReturnSection, TrackerSection.hierarchy);
      expect(viewModel.selectedIssue?.key, 'TRACK-99');
    },
  );

  test(
    'view model saves project settings through the repository mutation',
    () async {
      final repository = _EditableSettingsRepository();
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      final initialSettings = viewModel.settingsCatalog!;

      final success = await viewModel.saveProjectSettings(
        initialSettings.copyWith(
          statusDefinitions: [
            ...initialSettings.statusDefinitions,
            const TrackStateConfigEntry(
              id: 'blocked',
              name: 'Blocked',
              category: 'indeterminate',
            ),
          ],
        ),
      );

      expect(success, isTrue);
      expect(
        viewModel.project?.statusDefinitions.map((status) => status.id),
        contains('blocked'),
      );
      expect(
        repository.savedSettings?.statusDefinitions.map((status) => status.id),
        contains('blocked'),
      );
    },
  );

  test(
    'view model saves issue edits through shared field, hierarchy, and workflow mutations',
    () async {
      final initialSnapshot = await const DemoTrackStateRepository()
          .loadSnapshot();
      final repository = _MutableEditRepository(
        snapshot: initialSnapshot,
        reloadReturnsSummaryOnly: true,
      );
      final service = _RecordingEditIssueMutationService(repository);
      final viewModel = TrackerViewModel(
        repository: repository,
        issueMutationService: service,
      );

      await viewModel.load();
      final issue = viewModel.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );

      final success = await viewModel.saveIssueEdits(
        issue,
        const IssueEditRequest(
          summary: 'Refine Git sync service',
          description: 'Syncs repository-backed tracker data safely.',
          priorityId: 'highest',
          assignee: 'Ana',
          labels: ['sync', 'repo-ui'],
          components: ['tracker-core', 'flutter-ui'],
          fixVersionIds: ['mvp'],
          epicKey: '',
          transitionStatusId: 'done',
          resolutionId: 'done',
        ),
      );

      expect(success, isTrue);
      expect(service.updatedFields['summary'], 'Refine Git sync service');
      expect(service.updatedFields['priority'], 'highest');
      expect(service.reassignedEpicKey, isNull);
      expect(service.transitionStatusId, 'done');
      expect(viewModel.selectedIssue?.summary, 'Refine Git sync service');
      expect(
        viewModel.selectedIssue?.description,
        'Syncs repository-backed tracker data safely.',
      );
      expect(viewModel.selectedIssue?.epicKey, isNull);
      expect(viewModel.selectedIssue?.statusId, 'done');
      expect(viewModel.selectedIssue?.resolutionId, 'done');
      expect(viewModel.selectedIssue?.hasDetailLoaded, isTrue);
      expect(
        viewModel.searchResults.where(
          (candidate) => candidate.key == 'TRACK-12',
        ),
        isEmpty,
      );
    },
  );

  test(
    'view model keeps the selected issue hydrated after hosted same-key status reloads',
    () async {
      final initialSnapshot = await const DemoTrackStateRepository()
          .loadSnapshot();
      final repository = _MutableEditRepository(
        snapshot: initialSnapshot,
        reloadReturnsSummaryOnly: true,
      );
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      final issue = viewModel.selectedIssue!;

      await viewModel.moveIssue(issue, IssueStatus.done);

      expect(viewModel.selectedIssue?.key, issue.key);
      expect(viewModel.selectedIssue?.statusId, 'done');
      expect(viewModel.selectedIssue?.description, issue.description);
      expect(viewModel.selectedIssue?.hasDetailLoaded, isTrue);
    },
  );

  test('view model preserves empty successful workflow transitions', () async {
    final initialSnapshot = await const DemoTrackStateRepository()
        .loadSnapshot();
    final repository = _MutableEditRepository(snapshot: initialSnapshot);
    final service = _RecordingEditIssueMutationService(
      repository,
      transitions: const [],
    );
    final viewModel = TrackerViewModel(
      repository: repository,
      issueMutationService: service,
    );

    await viewModel.load();
    final issue = viewModel.issues.firstWhere(
      (candidate) => candidate.key == 'TRACK-12',
    );

    final transitions = await viewModel.availableWorkflowTransitions(issue);

    expect(transitions, isEmpty);
  });

  test(
    'view model falls back to in-memory local edits when shared mutations are unavailable',
    () async {
      final initialSnapshot = await const DemoTrackStateRepository()
          .loadSnapshot();
      final repository = _MutableEditRepository(
        snapshot: initialSnapshot,
        usesLocalPersistence: true,
      );
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      final issue = viewModel.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );
      final nextEpicKey = issue.epicKey == null ? 'TRACK-1' : null;

      final success = await viewModel.saveIssueEdits(
        issue,
        IssueEditRequest(
          summary: 'Local fallback summary',
          description: 'Local fallback description.',
          priorityId: 'high',
          assignee: 'fresh-teammate',
          labels: const ['local-edit', 'browser'],
          components: const ['tracker-core'],
          fixVersionIds: const ['mvp'],
          parentKey: issue.parentKey,
          epicKey: nextEpicKey,
          transitionStatusId: 'in-review',
        ),
      );

      expect(success, isTrue);
      expect(viewModel.selectedIssue?.summary, 'Local fallback summary');
      expect(
        viewModel.selectedIssue?.description,
        'Local fallback description.',
      );
      expect(viewModel.selectedIssue?.priorityId, 'high');
      expect(viewModel.selectedIssue?.assignee, 'fresh-teammate');
      expect(viewModel.selectedIssue?.labels, ['local-edit', 'browser']);
      expect(viewModel.selectedIssue?.components, ['tracker-core']);
      expect(viewModel.selectedIssue?.fixVersionIds, ['mvp']);
      expect(viewModel.selectedIssue?.epicKey, nextEpicKey);
      expect(viewModel.selectedIssue?.statusId, 'in-review');
      expect(
        viewModel.searchResults.any(
          (candidate) =>
              candidate.key == 'TRACK-12' &&
              candidate.summary == 'Local fallback summary',
        ),
        isTrue,
      );
    },
  );

  test(
    'view model falls back to legacy description saves when shared mutations are unavailable',
    () async {
      final initialSnapshot = await const DemoTrackStateRepository()
          .loadSnapshot();
      final repository = _MutableEditRepository(
        snapshot: initialSnapshot,
        usesLocalPersistence: true,
      );
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      final issue = viewModel.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );

      final success = await viewModel.saveIssueEdits(
        issue,
        IssueEditRequest(
          summary: issue.summary,
          description: 'Legacy description save path.',
          priorityId: issue.priorityId,
          assignee: issue.assignee,
          labels: issue.labels,
          components: issue.components,
          fixVersionIds: issue.fixVersionIds,
          parentKey: issue.parentKey,
          epicKey: issue.epicKey,
        ),
      );

      expect(success, isTrue);
      expect(repository.lastSavedDescription, 'Legacy description save path.');
      expect(
        viewModel.selectedIssue?.description,
        'Legacy description save path.',
      );
    },
  );

  test(
    'view model blocks done fallback saves without a required resolution',
    () async {
      final initialSnapshot = await const DemoTrackStateRepository()
          .loadSnapshot();
      final repository = _MutableEditRepository(
        snapshot: _snapshotWithResolutions(initialSnapshot, const [
          TrackStateConfigEntry(id: 'done', name: 'Done'),
          TrackStateConfigEntry(id: 'wont-fix', name: "Won't Fix"),
        ]),
        usesLocalPersistence: true,
      );
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      final issue = viewModel.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );

      final success = await viewModel.saveIssueEdits(
        issue,
        IssueEditRequest(
          summary: 'Blocked resolution save',
          description: issue.description,
          priorityId: issue.priorityId,
          assignee: issue.assignee,
          labels: issue.labels,
          components: issue.components,
          fixVersionIds: issue.fixVersionIds,
          parentKey: issue.parentKey,
          epicKey: issue.epicKey,
          transitionStatusId: 'done',
        ),
      );

      expect(success, isFalse);
      expect(viewModel.message?.kind, TrackerMessageKind.issueSaveFailed);
      expect(
        viewModel.message?.error,
        contains('Done transitions require a resolution before saving.'),
      );
      expect(viewModel.selectedIssue?.summary, issue.summary);
      expect(viewModel.selectedIssue?.statusId, issue.statusId);
    },
  );

  test(
    'view model applies the single available resolution for done fallback saves',
    () async {
      final initialSnapshot = await const DemoTrackStateRepository()
          .loadSnapshot();
      final repository = _MutableEditRepository(
        snapshot: _snapshotWithResolutions(initialSnapshot, const [
          TrackStateConfigEntry(id: 'done', name: 'Done'),
        ]),
        usesLocalPersistence: true,
      );
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      final issue = viewModel.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );

      final success = await viewModel.saveIssueEdits(
        issue,
        IssueEditRequest(
          summary: 'Single resolution fallback',
          description: issue.description,
          priorityId: issue.priorityId,
          assignee: issue.assignee,
          labels: issue.labels,
          components: issue.components,
          fixVersionIds: issue.fixVersionIds,
          parentKey: issue.parentKey,
          epicKey: issue.epicKey,
          transitionStatusId: 'done',
        ),
      );

      expect(success, isTrue);
      expect(viewModel.selectedIssue?.summary, 'Single resolution fallback');
      expect(viewModel.selectedIssue?.statusId, 'done');
      expect(viewModel.selectedIssue?.resolutionId, 'done');
    },
  );
}

TrackerSnapshot _snapshotWithResolutions(
  TrackerSnapshot snapshot,
  List<TrackStateConfigEntry> resolutionDefinitions,
) {
  return TrackerSnapshot(
    project: ProjectConfig(
      key: snapshot.project.key,
      name: snapshot.project.name,
      repository: snapshot.project.repository,
      branch: snapshot.project.branch,
      defaultLocale: snapshot.project.defaultLocale,
      issueTypeDefinitions: snapshot.project.issueTypeDefinitions,
      statusDefinitions: snapshot.project.statusDefinitions,
      fieldDefinitions: snapshot.project.fieldDefinitions,
      priorityDefinitions: snapshot.project.priorityDefinitions,
      versionDefinitions: snapshot.project.versionDefinitions,
      componentDefinitions: snapshot.project.componentDefinitions,
      resolutionDefinitions: resolutionDefinitions,
    ),
    issues: snapshot.issues,
    repositoryIndex: snapshot.repositoryIndex,
    loadWarnings: snapshot.loadWarnings,
  );
}

class _LocalRuntimeRepository implements TrackStateRepository {
  const _LocalRuntimeRepository();

  static const _demoRepository = DemoTrackStateRepository();

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'local-user', displayName: 'Local User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async =>
      _demoRepository.loadSnapshot();

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) => _demoRepository.searchIssuePage(
    jql,
    startAt: startAt,
    maxResults: maxResults,
    continuationToken: continuationToken,
  );

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      _demoRepository.searchIssues(jql);

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Local runtime view-model repository does not support issue archiving.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Local runtime view-model repository does not support issue deletion.',
      );

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    throw UnimplementedError('Issue creation is not implemented.');
  }

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async =>
      issue.copyWith(description: description.trim(), updatedLabel: 'just now');

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(status: status, updatedLabel: 'just now');

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async => issue.copyWith(
    comments: [
      ...issue.comments,
      IssueComment(
        id: (issue.comments.length + 1).toString().padLeft(4, '0'),
        author: 'local-user',
        body: body,
        updatedLabel: 'just now',
      ),
    ],
  );

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => const <IssueHistoryEntry>[];

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async => issue;
}

class _ThrowingSearchRepository extends _LocalRuntimeRepository {
  const _ThrowingSearchRepository();

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) {
    if (jql == 'text = broken') {
      throw const JqlSearchException('Unsupported JQL clause "text = broken".');
    }
    return super.searchIssuePage(
      jql,
      startAt: startAt,
      maxResults: maxResults,
      continuationToken: continuationToken,
    );
  }
}

class _EditableSettingsRepository extends _LocalRuntimeRepository
    implements ProjectSettingsRepository {
  _EditableSettingsRepository()
    : _snapshot = const DemoTrackStateRepository().loadSnapshot();

  Future<TrackerSnapshot> _snapshot;
  ProjectSettingsCatalog? savedSettings;

  @override
  Future<TrackerSnapshot> loadSnapshot() => _snapshot;

  @override
  Future<TrackerSnapshot> saveProjectSettings(
    ProjectSettingsCatalog settings,
  ) async {
    savedSettings = settings;
    final current = await _snapshot;
    final updated = TrackerSnapshot(
      project: ProjectConfig(
        key: current.project.key,
        name: current.project.name,
        repository: current.project.repository,
        branch: current.project.branch,
        defaultLocale: current.project.defaultLocale,
        issueTypeDefinitions: settings.issueTypeDefinitions,
        statusDefinitions: settings.statusDefinitions,
        fieldDefinitions: settings.fieldDefinitions,
        workflowDefinitions: settings.workflowDefinitions,
        priorityDefinitions: current.project.priorityDefinitions,
        versionDefinitions: current.project.versionDefinitions,
        componentDefinitions: current.project.componentDefinitions,
        resolutionDefinitions: current.project.resolutionDefinitions,
      ),
      issues: current.issues,
      repositoryIndex: current.repositoryIndex,
      loadWarnings: current.loadWarnings,
    );
    _snapshot = Future<TrackerSnapshot>.value(updated);
    return updated;
  }
}

class _RecordingIssueMutationService extends IssueMutationService {
  _RecordingIssueMutationService(this._created)
    : super(repository: const DemoTrackStateRepository());

  final TrackStateIssue _created;

  @override
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
  }) async => IssueMutationResult.success(
    operation: 'create',
    issueKey: _created.key,
    value: _created,
  );
}

class _MutableEditRepository implements TrackStateRepository {
  _MutableEditRepository({
    required TrackerSnapshot snapshot,
    this.usesLocalPersistence = false,
    this.reloadReturnsSummaryOnly = false,
  }) : _snapshot = snapshot;

  TrackerSnapshot _snapshot;
  final JqlSearchService _searchService = const JqlSearchService();
  String? lastSavedDescription;
  int loadSnapshotCount = 0;

  final bool reloadReturnsSummaryOnly;

  @override
  final bool usesLocalPersistence;

  @override
  bool get supportsGitHubAuth => !usesLocalPersistence;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'mutable-user', displayName: 'Mutable User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    loadSnapshotCount += 1;
    if (!reloadReturnsSummaryOnly) {
      return _snapshot;
    }
    return TrackerSnapshot(
      project: _snapshot.project,
      issues: [for (final issue in _snapshot.issues) _summaryOnlyIssue(issue)],
      repositoryIndex: _snapshot.repositoryIndex,
      loadWarnings: _snapshot.loadWarnings,
      readiness: _snapshot.readiness,
    );
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async => _searchService.search(
    issues: _snapshot.issues,
    project: _snapshot.project,
    jql: jql,
    startAt: startAt,
    maxResults: maxResults,
    continuationToken: continuationToken,
  );

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (await searchIssuePage(jql, maxResults: 2147483647)).issues;

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Archiving is not implemented.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException('Deletion is not implemented.');

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async => throw UnimplementedError('Issue creation is not implemented.');

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async {
    lastSavedDescription = description.trim();
    final updated = _copyIssue(issue, description: description.trim());
    applyIssue(updated);
    return updated;
  }

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async {
    final updated = _copyIssue(
      issue,
      status: status,
      statusId: status.id,
      resolutionId: status == IssueStatus.done ? 'done' : null,
    );
    applyIssue(updated);
    return updated;
  }

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async {
    final timestamp = DateTime.now().toUtc().toIso8601String();
    final updated = issue.copyWith(
      hasCommentsLoaded: true,
      comments: [
        ...issue.comments,
        IssueComment(
          id: (issue.comments.length + 1).toString().padLeft(4, '0'),
          author: 'mutable-user',
          body: body,
          updatedLabel: timestamp,
          createdAt: timestamp,
          updatedAt: timestamp,
          storagePath:
              '${issue.storagePath.substring(0, issue.storagePath.lastIndexOf('/'))}/comments/${(issue.comments.length + 1).toString().padLeft(4, '0')}.md',
        ),
      ],
    );
    applyIssue(updated);
    return updated;
  }

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => const <IssueHistoryEntry>[];

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async {
    final sanitizedName = sanitizeAttachmentName(name);
    final updated = issue.copyWith(
      hasAttachmentsLoaded: true,
      attachments: [
        ...issue.attachments,
        IssueAttachment(
          id: '${issue.storagePath}/$sanitizedName',
          name: sanitizedName,
          mediaType: 'application/pdf',
          sizeBytes: bytes.length,
          author: 'mutable-user',
          createdAt: 'just now',
          storagePath:
              '${issue.storagePath.substring(0, issue.storagePath.lastIndexOf('/'))}/attachments/$sanitizedName',
          revisionOrOid: 'mutable-revision',
        ),
      ],
    );
    applyIssue(updated);
    return updated;
  }

  TrackStateIssue issueForKey(String key) =>
      _snapshot.issues.firstWhere((issue) => issue.key == key);

  void applyIssue(TrackStateIssue issue) {
    _snapshot = TrackerSnapshot(
      project: _snapshot.project,
      issues: [
        for (final current in _snapshot.issues)
          if (current.key == issue.key) issue else current,
      ],
      repositoryIndex: _snapshot.repositoryIndex,
      loadWarnings: _snapshot.loadWarnings,
    );
  }
}

class _RecordingEditIssueMutationService extends IssueMutationService {
  _RecordingEditIssueMutationService(
    this._repository, {
    this.transitions = const [
      TrackStateConfigEntry(id: 'in-review', name: 'In Review'),
      TrackStateConfigEntry(id: 'done', name: 'Done'),
    ],
  }) : super(repository: const DemoTrackStateRepository());

  final _MutableEditRepository _repository;
  final List<TrackStateConfigEntry> transitions;
  Map<String, Object?> updatedFields = const {};
  String? reassignedParentKey;
  String? reassignedEpicKey;
  String? transitionStatusId;

  @override
  Future<IssueMutationResult<List<TrackStateConfigEntry>>>
  availableTransitions({required String issueKey}) async =>
      IssueMutationResult.success(
        operation: 'available-transitions',
        issueKey: issueKey,
        value: transitions,
      );

  @override
  Future<IssueMutationResult<TrackStateIssue>> updateFields({
    required String issueKey,
    required Map<String, Object?> fields,
  }) async {
    updatedFields = Map<String, Object?>.from(fields);
    final issue = _repository.issueForKey(issueKey);
    final updated = _copyIssue(
      issue,
      summary: fields['summary'] as String? ?? issue.summary,
      description: fields['description'] as String? ?? issue.description,
      priorityId: fields['priority'] as String? ?? issue.priorityId,
      assignee: (fields['assignee'] as String?) ?? issue.assignee,
      labels: (fields['labels'] as List<String>?) ?? issue.labels,
      components: (fields['components'] as List<String>?) ?? issue.components,
      fixVersionIds:
          (fields['fixVersions'] as List<String>?) ?? issue.fixVersionIds,
    );
    _repository.applyIssue(updated);
    return IssueMutationResult.success(
      operation: 'update-fields',
      issueKey: issueKey,
      value: updated,
    );
  }

  @override
  Future<IssueMutationResult<TrackStateIssue>> reassignIssue({
    required String issueKey,
    String? parentKey,
    String? epicKey,
  }) async {
    reassignedParentKey = parentKey;
    reassignedEpicKey = epicKey;
    final issue = _repository.issueForKey(issueKey);
    final updated = _copyIssue(issue, parentKey: parentKey, epicKey: epicKey);
    _repository.applyIssue(updated);
    return IssueMutationResult.success(
      operation: 'reassign',
      issueKey: issueKey,
      value: updated,
    );
  }

  @override
  Future<IssueMutationResult<TrackStateIssue>> transitionIssue({
    required String issueKey,
    required String status,
    String? resolution,
  }) async {
    transitionStatusId = status;
    final issue = _repository.issueForKey(issueKey);
    final nextStatus = switch (status) {
      'in-review' => IssueStatus.inReview,
      'done' => IssueStatus.done,
      _ => IssueStatus.inProgress,
    };
    final updated = _copyIssue(
      issue,
      status: nextStatus,
      statusId: status,
      resolutionId: resolution,
    );
    _repository.applyIssue(updated);
    return IssueMutationResult.success(
      operation: 'transition',
      issueKey: issueKey,
      value: updated,
    );
  }
}

TrackStateIssue _copyIssue(
  TrackStateIssue issue, {
  String? summary,
  String? description,
  String? priorityId,
  String? assignee,
  List<String>? labels,
  List<String>? components,
  List<String>? fixVersionIds,
  Object? parentKey = _unsetEditValue,
  Object? epicKey = _unsetEditValue,
  IssueStatus? status,
  String? statusId,
  Object? resolutionId = _unsetEditValue,
}) {
  final nextPriorityId = priorityId ?? issue.priorityId;
  final nextStatus = status ?? issue.status;
  final nextStatusId = statusId ?? issue.statusId;
  return TrackStateIssue(
    key: issue.key,
    project: issue.project,
    issueType: issue.issueType,
    issueTypeId: issue.issueTypeId,
    status: nextStatus,
    statusId: nextStatusId,
    priority: _priorityForId(nextPriorityId),
    priorityId: nextPriorityId,
    summary: summary ?? issue.summary,
    description: description ?? issue.description,
    assignee: assignee ?? issue.assignee,
    reporter: issue.reporter,
    labels: labels ?? issue.labels,
    components: components ?? issue.components,
    fixVersionIds: fixVersionIds ?? issue.fixVersionIds,
    watchers: issue.watchers,
    customFields: issue.customFields,
    parentKey: identical(parentKey, _unsetEditValue)
        ? issue.parentKey
        : parentKey as String?,
    epicKey: identical(epicKey, _unsetEditValue)
        ? issue.epicKey
        : epicKey as String?,
    parentPath: issue.parentPath,
    epicPath: issue.epicPath,
    progress: issue.progress,
    updatedLabel: 'just now',
    acceptanceCriteria: issue.acceptanceCriteria,
    comments: issue.comments,
    links: issue.links,
    attachments: issue.attachments,
    isArchived: issue.isArchived,
    resolutionId: identical(resolutionId, _unsetEditValue)
        ? issue.resolutionId
        : resolutionId as String?,
    storagePath: issue.storagePath,
    rawMarkdown: issue.rawMarkdown,
  );
}

const Object _unsetEditValue = Object();

IssuePriority _priorityForId(String id) {
  return switch (id) {
    'highest' => IssuePriority.highest,
    'high' => IssuePriority.high,
    'low' => IssuePriority.low,
    _ => IssuePriority.medium,
  };
}

TrackStateIssue _summaryOnlyIssue(TrackStateIssue issue) => TrackStateIssue(
  key: issue.key,
  project: issue.project,
  issueType: issue.issueType,
  issueTypeId: issue.issueTypeId,
  status: issue.status,
  statusId: issue.statusId,
  priority: issue.priority,
  priorityId: issue.priorityId,
  summary: issue.summary,
  description: '',
  assignee: issue.assignee,
  reporter: issue.reporter,
  labels: issue.labels,
  components: const [],
  fixVersionIds: const [],
  watchers: const [],
  customFields: const {},
  parentKey: issue.parentKey,
  epicKey: issue.epicKey,
  parentPath: issue.parentPath,
  epicPath: issue.epicPath,
  progress: issue.progress,
  updatedLabel: issue.updatedLabel,
  acceptanceCriteria: const [],
  comments: const [],
  links: const [],
  attachments: const [],
  isArchived: issue.isArchived,
  hasDetailLoaded: false,
  hasCommentsLoaded: false,
  hasAttachmentsLoaded: false,
  resolutionId: issue.resolutionId,
  storagePath: issue.storagePath,
  rawMarkdown: issue.rawMarkdown,
);

TrackerSnapshot _searchPaginationSnapshot() {
  final issues = [
    for (var index = 1; index <= 8; index += 1)
      TrackStateIssue(
        key: 'TRACK-$index',
        project: 'TRACK',
        issueType: IssueType.story,
        issueTypeId: 'story',
        status: IssueStatus.inProgress,
        statusId: 'in-progress',
        priority: IssuePriority.medium,
        priorityId: 'medium',
        summary: 'Paged issue $index',
        description: 'Search result $index',
        assignee: 'user-$index',
        reporter: 'demo-user',
        labels: const ['paged'],
        components: const [],
        fixVersionIds: const [],
        watchers: const [],
        customFields: const {},
        parentKey: null,
        epicKey: null,
        parentPath: null,
        epicPath: null,
        progress: 0,
        updatedLabel: 'just now',
        acceptanceCriteria: const ['Visible in search pagination'],
        comments: const [],
        links: const [],
        attachments: const [],
        isArchived: false,
        storagePath: 'TRACK/TRACK-$index/main.md',
        rawMarkdown: '',
      ),
  ];
  return TrackerSnapshot(
    project: const ProjectConfig(
      key: 'TRACK',
      name: 'TrackState',
      repository: 'trackstate/trackstate',
      branch: 'main',
      defaultLocale: 'en',
      issueTypeDefinitions: [TrackStateConfigEntry(id: 'story', name: 'Story')],
      statusDefinitions: [
        TrackStateConfigEntry(id: 'in-progress', name: 'In Progress'),
      ],
      fieldDefinitions: [
        TrackStateFieldDefinition(
          id: 'summary',
          name: 'Summary',
          type: 'string',
          required: true,
        ),
      ],
      priorityDefinitions: [
        TrackStateConfigEntry(id: 'medium', name: 'Medium'),
      ],
    ),
    issues: issues,
  );
}

TrackerSnapshot _withStartupRecovery(TrackerSnapshot snapshot) {
  return TrackerSnapshot(
    project: snapshot.project,
    issues: snapshot.issues,
    repositoryIndex: snapshot.repositoryIndex,
    loadWarnings: snapshot.loadWarnings,
    readiness: snapshot.readiness,
    startupRecovery: const TrackerStartupRecovery(
      kind: TrackerStartupRecoveryKind.githubRateLimit,
      failedPath:
          '/repos/trackstate/trackstate/contents/.trackstate/index/tombstones.json',
    ),
  );
}

class _StartupRecoveryRepository implements TrackStateRepository {
  _StartupRecoveryRepository({required List<Object> loadResults})
    : _loadResults = List<Object>.from(loadResults);

  final List<Object> _loadResults;
  final JqlSearchService _searchService = const JqlSearchService();
  int loadCount = 0;
  int connectCount = 0;
  TrackerSnapshot? _currentSnapshot;

  @override
  bool get supportsGitHubAuth => true;

  @override
  bool get usesLocalPersistence => false;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async {
    connectCount += 1;
    return const RepositoryUser(login: 'demo-user', displayName: 'Demo User');
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final index = loadCount < _loadResults.length
        ? loadCount
        : _loadResults.length - 1;
    loadCount += 1;
    final result = _loadResults[index];
    if (result is TrackerSnapshot) {
      _currentSnapshot = result;
      return result;
    }
    throw result;
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    final snapshot =
        _currentSnapshot ??
        await const DemoTrackStateRepository().loadSnapshot();
    return _searchService.search(
      issues: snapshot.issues,
      project: snapshot.project,
      jql: jql,
      startAt: startAt,
      maxResults: maxResults,
      continuationToken: continuationToken,
    );
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (await searchIssuePage(jql, maxResults: 500)).issues;

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Startup recovery test repository does not support archiving.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Startup recovery test repository does not support deletion.',
      );

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async => throw UnimplementedError();

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async => issue;

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue;

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async => issue;

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => const <IssueHistoryEntry>[];

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async => issue;
}
