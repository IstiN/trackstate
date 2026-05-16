import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'startup restore skips an invalid workspace and opens the next valid saved workspace',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'local:/tmp/missing@main',
              displayName: 'broken',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/missing',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:stable/repo@main',
              displayName: 'stable/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'stable/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: 'local:/tmp/missing@main',
          migrationComplete: true,
        ),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: service,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async =>
                  throw StateError('Missing repository $repositoryPath'),
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repository),
              ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.textContaining('Skipped broken during restore.'),
        findsOneWidget,
      );
      expect(service.state.activeWorkspaceId, 'hosted:stable/repo@main');
      expect(find.text('stable/repo'), findsWidgets);
    },
  );

  testWidgets(
    'startup restore routes to settings recovery when every saved workspace is invalid',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'local:/tmp/missing@main',
              displayName: 'broken-local',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/missing',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:broken/repo@definitely-missing-branch',
              displayName: 'broken/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'broken/repo',
              defaultBranch: 'definitely-missing-branch',
              writeBranch: 'definitely-missing-branch',
            ),
          ],
          activeWorkspaceId: 'local:/tmp/missing@main',
          migrationComplete: true,
        ),
      );
      final snapshot = await const DemoTrackStateRepository().loadSnapshot();

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repositoryFactory: () => _QueuedLoadTrackStateRepository(
            loadResults: [_withStartupRecovery(snapshot)],
          ),
          workspaceProfileService: service,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async =>
                  throw StateError('Missing repository $repositoryPath'),
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => _QueuedLoadTrackStateRepository(
                loadResults: [
                  StateError(
                    'Hosted workspace broken/repo@definitely-missing-branch could not be opened.',
                  ),
                ],
              ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Project Settings'), findsOneWidget);
      expect(
        find.textContaining('No valid saved workspace could be restored.'),
        findsOneWidget,
      );
      expect(find.widgetWithText(OutlinedButton, 'Retry'), findsOneWidget);
    },
  );

  testWidgets(
    'saved workspace recovery keeps Retry visible and revalidates invalid workspaces',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'local:/tmp/missing@main',
              displayName: 'broken-local',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/missing',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:broken/repo@definitely-missing-branch',
              displayName: 'broken/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'broken/repo',
              defaultBranch: 'definitely-missing-branch',
              writeBranch: 'definitely-missing-branch',
            ),
          ],
          activeWorkspaceId: 'local:/tmp/missing@main',
          migrationComplete: true,
        ),
      );
      var hostedValidationAttempts = 0;

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repositoryFactory: DemoTrackStateRepository.new,
          workspaceProfileService: service,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async =>
                  throw StateError('Missing repository $repositoryPath'),
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async {
                hostedValidationAttempts += 1;
                return _QueuedLoadTrackStateRepository(
                  loadResults: [
                    StateError(
                      'Hosted workspace $repository@$defaultBranch could not be opened.',
                    ),
                  ],
                );
              },
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Project Settings'), findsOneWidget);
      expect(
        find.textContaining('No valid saved workspace could be restored.'),
        findsOneWidget,
      );
      expect(find.widgetWithText(OutlinedButton, 'Retry'), findsOneWidget);
      expect(hostedValidationAttempts, 1);

      await tester.tap(find.widgetWithText(OutlinedButton, 'Retry'));
      await tester.pumpAndSettle();

      expect(hostedValidationAttempts, 2);
      expect(find.text('Project Settings'), findsOneWidget);
      expect(
        find.textContaining('No valid saved workspace could be restored.'),
        findsOneWidget,
      );
      expect(find.widgetWithText(OutlinedButton, 'Retry'), findsOneWidget);
    },
  );

  testWidgets(
    'workspace switcher shows the last verified hosted access state for inactive saved workspaces',
    (tester) async {
      final authStore = _MemoryAuthStore()
        ..workspaceTokens['hosted:beta/repo@main'] = 'beta-token'
        ..workspaceTokens['hosted:gamma/repo@main'] = 'gamma-token';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:alpha/repo@main',
              displayName: 'alpha/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alpha/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
              hostedAccessMode: HostedWorkspaceAccessMode.writable,
            ),
            WorkspaceProfile(
              id: 'hosted:beta/repo@main',
              displayName: 'beta/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'beta/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
              hostedAccessMode: HostedWorkspaceAccessMode.readOnly,
            ),
            WorkspaceProfile(
              id: 'hosted:gamma/repo@main',
              displayName: 'gamma/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'gamma/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
              hostedAccessMode: HostedWorkspaceAccessMode.attachmentRestricted,
            ),
          ],
          activeWorkspaceId: 'hosted:alpha/repo@main',
          migrationComplete: true,
        ),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: service,
          authStore: authStore,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repository),
              ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      expect(find.text('Read-only'), findsOneWidget);
      expect(find.text('Attachments limited'), findsOneWidget);
    },
  );

  testWidgets(
    'workspace switcher keeps visible workspace details on compact layouts',
    (tester) async {
      const attachmentRestrictedPermission = RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: false,
        attachmentUploadMode: AttachmentUploadMode.noLfs,
        canCheckCollaborators: false,
      );
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:alpha/repo@main',
              displayName: 'alpha/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alpha/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: 'hosted:alpha/repo@main',
          migrationComplete: true,
        ),
      );

      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: service,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => ReactiveIssueDetailTrackStateRepository(
                permission: attachmentRestrictedPermission,
              ),
        ),
      );
      await tester.pumpAndSettle();

      final trigger = find.byKey(const ValueKey('workspace-switcher-trigger'));
      expect(trigger, findsOneWidget);
      expect(
        find.descendant(of: trigger, matching: find.text('alpha/repo')),
        findsOneWidget,
      );
      expect(
        find.descendant(
          of: trigger,
          matching: find.text('Hosted · Attachments limited'),
        ),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'workspace switcher keeps visible workspace details on condensed desktop layouts',
    (tester) async {
      const attachmentRestrictedPermission = RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: false,
        attachmentUploadMode: AttachmentUploadMode.noLfs,
        canCheckCollaborators: false,
      );
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:alpha/repo@main',
              displayName: 'alpha/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alpha/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: 'hosted:alpha/repo@main',
          migrationComplete: true,
        ),
      );

      tester.view.physicalSize = const Size(1180, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: service,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => ReactiveIssueDetailTrackStateRepository(
                permission: attachmentRestrictedPermission,
              ),
        ),
      );
      await tester.pumpAndSettle();

      final trigger = find.byKey(const ValueKey('workspace-switcher-trigger'));
      expect(trigger, findsOneWidget);
      expect(
        find.descendant(
          of: trigger,
          matching: find.text('alpha/repo · Hosted · Attachments limited'),
        ),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'workspace switcher keeps the current section while switching to another saved workspace',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:alpha/repo@main',
              displayName: 'alpha/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alpha/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'local:/tmp/demo@main',
              displayName: 'demo',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/demo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: 'hosted:alpha/repo@main',
          migrationComplete: true,
        ),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repository: const DemoTrackStateRepository(),
          workspaceProfileService: service,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repository),
              ),
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repositoryPath),
              ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.bySemanticsLabel(RegExp('Board')).first);
      await tester.pumpAndSettle();
      expect(find.bySemanticsLabel(RegExp('To Do column')), findsOneWidget);

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();
      expect(find.text('Saved workspaces'), findsOneWidget);

      await tester.tap(
        find.byKey(const ValueKey('workspace-open-local:/tmp/demo@main')),
      );
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel(RegExp('To Do column')), findsOneWidget);
      expect(service.state.activeWorkspaceId, 'local:/tmp/demo@main');
    },
  );

  testWidgets('workspace switcher confirms before deleting a saved workspace', (
    tester,
  ) async {
    final service = _MemoryWorkspaceProfileService(
      WorkspaceProfilesState(
        profiles: const [
          WorkspaceProfile(
            id: 'hosted:alpha/repo@main',
            displayName: 'alpha/repo',
            targetType: WorkspaceProfileTargetType.hosted,
            target: 'alpha/repo',
            defaultBranch: 'main',
            writeBranch: 'main',
          ),
          WorkspaceProfile(
            id: 'local:/tmp/demo@main',
            displayName: 'demo',
            targetType: WorkspaceProfileTargetType.local,
            target: '/tmp/demo',
            defaultBranch: 'main',
            writeBranch: 'main',
          ),
        ],
        activeWorkspaceId: 'hosted:alpha/repo@main',
        migrationComplete: true,
      ),
    );

    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      TrackStateApp(
        workspaceProfileService: service,
        openHostedRepository:
            ({
              required String repository,
              required String defaultBranch,
              required String writeBranch,
            }) async => DemoTrackStateRepository(
              snapshot: await _snapshotForRepository(repository),
            ),
        openLocalRepository:
            ({
              required String repositoryPath,
              required String defaultBranch,
              required String writeBranch,
            }) async => DemoTrackStateRepository(
              snapshot: await _snapshotForRepository(repositoryPath),
            ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.bySemanticsLabel(RegExp('Workspace switcher:')).last);
    await tester.pumpAndSettle();

    await tester.tap(
      find.byKey(const ValueKey('workspace-delete-local:/tmp/demo@main')),
    );
    await tester.pumpAndSettle();

    expect(find.text('Delete saved workspace'), findsOneWidget);
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();

    expect(find.text('Saved workspaces'), findsOneWidget);
    expect(
      service.state.profiles.any(
        (profile) => profile.id == 'local:/tmp/demo@main',
      ),
      isTrue,
    );

    await tester.tap(
      find.byKey(const ValueKey('workspace-delete-local:/tmp/demo@main')),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Delete'));
    await tester.pumpAndSettle();

    expect(
      service.state.profiles.any(
        (profile) => profile.id == 'local:/tmp/demo@main',
      ),
      isFalse,
    );
  });

  testWidgets(
    'workspace switcher can add a hosted workspace and switch to it',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        const WorkspaceProfilesState(migrationComplete: true),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repository: const DemoTrackStateRepository(),
          workspaceProfileService: service,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repository),
              ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Repository'),
        'new/repo',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Branch'),
        'main',
      );
      await tester.tap(find.byKey(const ValueKey('workspace-add-button')));
      await tester.pumpAndSettle();

      expect(service.state.activeWorkspaceId, 'hosted:new/repo@main');
      expect(find.textContaining('new/repo'), findsWidgets);
    },
  );
}

Future<TrackerSnapshot> _snapshotForRepository(String repository) async {
  final base = await const DemoTrackStateRepository().loadSnapshot();
  return TrackerSnapshot(
    project: ProjectConfig(
      key: base.project.key,
      name: base.project.name,
      repository: repository,
      branch: base.project.branch,
      defaultLocale: base.project.defaultLocale,
      supportedLocales: base.project.supportedLocales,
      issueTypeDefinitions: base.project.issueTypeDefinitions,
      statusDefinitions: base.project.statusDefinitions,
      fieldDefinitions: base.project.fieldDefinitions,
      workflowDefinitions: base.project.workflowDefinitions,
      priorityDefinitions: base.project.priorityDefinitions,
      versionDefinitions: base.project.versionDefinitions,
      componentDefinitions: base.project.componentDefinitions,
      resolutionDefinitions: base.project.resolutionDefinitions,
      attachmentStorage: base.project.attachmentStorage,
    ),
    issues: base.issues,
    repositoryIndex: base.repositoryIndex,
    loadWarnings: base.loadWarnings,
    readiness: base.readiness,
    startupRecovery: base.startupRecovery,
  );
}

class _MemoryWorkspaceProfileService implements WorkspaceProfileService {
  _MemoryWorkspaceProfileService(this.state);

  WorkspaceProfilesState state;

  @override
  Future<WorkspaceProfile> createProfile(
    WorkspaceProfileInput input, {
    bool select = true,
  }) async {
    final created = WorkspaceProfile.create(input);
    state = WorkspaceProfilesState(
      profiles: resolveWorkspaceDisplayNames([...state.profiles, created]),
      activeWorkspaceId: select ? created.id : state.activeWorkspaceId,
      migrationComplete: true,
    );
    return state.profiles.firstWhere((profile) => profile.id == created.id);
  }

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) async {
    final nextProfiles = state.profiles
        .where((profile) => profile.id != workspaceId)
        .toList(growable: false);
    state = WorkspaceProfilesState(
      profiles: nextProfiles,
      activeWorkspaceId: state.activeWorkspaceId == workspaceId
          ? nextProfiles.isEmpty
                ? null
                : nextProfiles.first.id
          : state.activeWorkspaceId,
      migrationComplete: true,
    );
    return state;
  }

  @override
  Future<WorkspaceProfilesState> saveHostedAccessMode(
    String workspaceId,
    HostedWorkspaceAccessMode? accessMode,
  ) async {
    state = WorkspaceProfilesState(
      profiles: [
        for (final profile in state.profiles)
          if (profile.id == workspaceId && profile.isHosted)
            profile.copyWith(hostedAccessMode: accessMode)
          else
            profile,
      ],
      activeWorkspaceId: state.activeWorkspaceId,
      migrationComplete: true,
    );
    return state;
  }

  @override
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  ) async => null;

  @override
  Future<WorkspaceProfilesState> loadState() async => state;

  @override
  Future<WorkspaceProfilesState> selectProfile(String workspaceId) async {
    state = state.copyWith(activeWorkspaceId: workspaceId);
    return state;
  }

  @override
  Future<WorkspaceProfile> updateProfile(
    String workspaceId,
    WorkspaceProfileInput input, {
    bool select = true,
  }) async {
    final updated = WorkspaceProfile.create(input);
    state = WorkspaceProfilesState(
      profiles: [
        for (final profile in state.profiles)
          if (profile.id == workspaceId) updated else profile,
      ],
      activeWorkspaceId: select ? updated.id : state.activeWorkspaceId,
      migrationComplete: true,
    );
    return updated;
  }
}

class _MemoryAuthStore implements TrackStateAuthStore {
  final Map<String, String> workspaceTokens = <String, String>{};

  @override
  Future<void> clearToken({String? repository, String? workspaceId}) async {
    if (workspaceId != null) {
      workspaceTokens.remove(workspaceId);
    }
  }

  @override
  Future<String?> migrateLegacyRepositoryToken({
    required String repository,
    required String workspaceId,
  }) async => null;

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
    return workspaceId == null ? null : workspaceTokens[workspaceId];
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
  }
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

class _QueuedLoadTrackStateRepository implements TrackStateRepository {
  _QueuedLoadTrackStateRepository({required List<Object> loadResults})
    : _loadResults = List<Object>.from(loadResults);

  final List<Object> _loadResults;
  final JqlSearchService _searchService = const JqlSearchService();
  TrackerSnapshot? _currentSnapshot;
  int _loadCount = 0;

  @override
  bool get supportsGitHubAuth => true;

  @override
  bool get usesLocalPersistence => false;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'demo-user', displayName: 'Demo User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final index = _loadCount < _loadResults.length
        ? _loadCount
        : _loadResults.length - 1;
    _loadCount += 1;
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
      throw UnimplementedError();

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw UnimplementedError();

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
