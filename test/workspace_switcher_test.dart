import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../testing/core/utils/color_contrast.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'startup restore clears an unavailable active local workspace before delayed auth completes',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: activeLocalWorkspaceId,
              displayName: 'Active local workspace',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/trackstate-demo',
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
          activeWorkspaceId: activeLocalWorkspaceId,
          migrationComplete: true,
        ),
      );
      final authStore = _MemoryAuthStore()
        ..workspaceTokens[activeLocalWorkspaceId] = 'github-token';
      final delayedRepository = _DelayedConnectTrackStateRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repositoryFactory: () => delayedRepository,
          workspaceProfileService: service,
          authStore: authStore,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => _QueuedLoadTrackStateRepository(
                loadResults: [
                  UnsupportedError(
                    'Unsupported operation: Process.run is not supported on the web.',
                  ),
                ],
              ),
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
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(service.state.activeWorkspaceId, isNull);
      expect(
        service.state.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
      expect(
        _findExplicitWorkspaceSwitcherSemantics(
          'Workspace switcher: Active local workspace, Local, Local Git',
        ),
        findsNothing,
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsNothing,
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      final activeLocalRow = find.byKey(
        const ValueKey('workspace-local:/tmp/trackstate-demo@main'),
      );
      expect(activeLocalRow, findsOneWidget);
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Active')),
        findsNothing,
      );

      delayedRepository.completeConnect();
      await tester.pump();
      await tester.pumpAndSettle();
    },
  );

  testWidgets(
    'shared-preferences startup restore clears an unavailable active local workspace after delayed auth',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const hostedWorkspaceId = 'hosted:stable/repo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final service = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'stable/repo',
        ),
        select: false,
      );
      await authStore.saveToken(
        'github-token',
        workspaceId: activeLocalWorkspaceId,
      );

      final delayedRepository = _DelayedConnectTrackStateRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repositoryFactory: () => delayedRepository,
          workspaceProfileService: service,
          authStore: authStore,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => _QueuedLoadTrackStateRepository(
                loadResults: [
                  UnsupportedError(
                    'Unsupported operation: Process.run is not supported on the web.',
                  ),
                ],
              ),
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
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect((await service.loadState()).activeWorkspaceId, isNull);
      expect(
        (await authStore.readToken(workspaceId: activeLocalWorkspaceId)),
        'github-token',
      );
      expect(
        _findExplicitWorkspaceSwitcherSemantics(
          'Workspace switcher: Active local workspace, Local, Local Git',
        ),
        findsNothing,
      );
      expect(find.text('Dashboard'), findsNothing);
      expect(
        find.text('Git-native. Jira-compatible. Team-proven.'),
        findsNothing,
      );
      expect(find.text('Add workspace'), findsOneWidget);

      delayedRepository.completeConnect();
      await tester.pump();
      await tester.pumpAndSettle();

      final savedState = await service.loadState();
      expect(savedState.activeWorkspaceId, isNull);
      expect(
        savedState.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
      expect(
        (await authStore.readToken(workspaceId: hostedWorkspaceId)),
        isNull,
      );
      expect(
        _findExplicitWorkspaceSwitcherSemantics(
          'Workspace switcher: Active local workspace, Local, Local Git',
        ),
        findsNothing,
      );
      expect(find.text('Dashboard'), findsNothing);
      expect(find.text('Add workspace'), findsOneWidget);
    },
  );

  testWidgets(
    'startup restore clears the active workspace when the saved local repository is missing',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/missing@main';
      const hostedWorkspaceId = 'hosted:stable/repo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: activeLocalWorkspaceId,
              displayName: 'broken',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/missing',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: hostedWorkspaceId,
              displayName: 'stable/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'stable/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: activeLocalWorkspaceId,
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
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repository),
              ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(service.state.activeWorkspaceId, isNull);
      expect(
        service.state.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsNothing,
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      final activeLocalRow = find.byKey(
        const ValueKey('workspace-local:/tmp/missing@main'),
      );
      expect(activeLocalRow, findsOneWidget);
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Active')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'refresh preserves the saved local unavailable state until onboarding reopens it manually',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/guarded@main';
      const hostedWorkspaceId = 'hosted:stable/repo@main';
      final service = SharedPreferencesWorkspaceProfileService(
        authStore: _MemoryAuthStore(),
      );
      await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/guarded',
          defaultBranch: 'main',
        ),
      );
      await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
        ),
        select: false,
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      var localWorkspaceAvailable = false;
      final openedLocalRepositories = <String>[];
      var directoryPickerCalls = 0;

      Future<void> openWorkspaceSwitcher() async {
        final switcherSheet = find.byKey(
          const ValueKey('workspace-switcher-sheet'),
        );
        if (switcherSheet.evaluate().isNotEmpty) {
          return;
        }
        await tester.tap(
          find.byKey(const ValueKey('workspace-switcher-trigger')),
        );
        await tester.pumpAndSettle();
      }

      Future<void> expectUnavailableLocalWorkspace({
        bool expectHostedActive = false,
      }) async {
        await openWorkspaceSwitcher();
        final localRow = find.byKey(
          const ValueKey('workspace-local:/tmp/guarded@main'),
        );
        final hostedRow = find.byKey(
          const ValueKey('workspace-$hostedWorkspaceId'),
        );
        expect(localRow, findsOneWidget);
        expect(hostedRow, findsOneWidget);
        expect(
          find.descendant(of: localRow, matching: find.text('Active')),
          findsNothing,
        );
        expect(
          find.descendant(of: localRow, matching: find.text('Unavailable')),
          findsOneWidget,
        );
        expect(
          find.descendant(of: localRow, matching: find.text('Local Git')),
          findsNothing,
        );
        expect(
          find.descendant(of: hostedRow, matching: find.text('Active')),
          expectHostedActive ? findsOneWidget : findsNothing,
        );
      }

      Future<void> expectAvailableLocalWorkspace() async {
        await openWorkspaceSwitcher();
        final activeRow = find.byKey(
          const ValueKey('workspace-local:/tmp/guarded@main'),
        );
        expect(activeRow, findsOneWidget);
        expect(
          find.descendant(of: activeRow, matching: find.text('Active')),
          findsOneWidget,
        );
        expect(
          find.descendant(of: activeRow, matching: find.text('Local Git')),
          findsOneWidget,
        );
        expect(
          find.descendant(of: activeRow, matching: find.text('Unavailable')),
          findsNothing,
        );
      }

      Future<void> pumpApp() async {
        await tester.pumpWidget(
          TrackStateApp(
            repositoryFactory: DemoTrackStateRepository.new,
            workspaceProfileService: service,
            workspaceDirectoryPicker:
                ({String? confirmButtonText, String? initialDirectory}) async {
                  directoryPickerCalls += 1;
                  expect(initialDirectory, '/tmp/guarded');
                  return '/tmp/guarded';
                },
            openLocalRepository:
                ({
                  required String repositoryPath,
                  required String defaultBranch,
                  required String writeBranch,
                }) async {
                  openedLocalRepositories.add(repositoryPath);
                  if (!localWorkspaceAvailable) {
                    throw StateError('Missing repository $repositoryPath');
                  }
                  return DemoTrackStateRepository(
                    snapshot: await _snapshotForRepository(repositoryPath),
                  );
                },
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
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 300));
      }

      await pumpApp();
      expect((await service.loadState()).activeWorkspaceId, isNull);
      expect(
        (await service.loadState()).unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      await expectUnavailableLocalWorkspace();

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();

      openedLocalRepositories.clear();
      localWorkspaceAvailable = true;
      await pumpApp();
      expect((await service.loadState()).activeWorkspaceId, hostedWorkspaceId);
      expect(openedLocalRepositories, isEmpty);
      await expectUnavailableLocalWorkspace(expectHostedActive: true);
      await tester.tap(
        find.byKey(
          const ValueKey('workspace-primary-action-local:/tmp/guarded@main'),
        ),
      );
      await tester.pumpAndSettle();

      expect(openedLocalRepositories, ['/tmp/guarded']);
      expect(directoryPickerCalls, 1);
      expect(
        (await service.loadState()).unavailableLocalWorkspaceIds,
        isNot(contains(activeLocalWorkspaceId)),
      );
      await expectAvailableLocalWorkspace();
    },
  );

  testWidgets(
    'startup restore clears the saved active local workspace when local startup access is unavailable',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: activeLocalWorkspaceId,
              displayName: 'Active local workspace',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/trackstate-demo',
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
          activeWorkspaceId: activeLocalWorkspaceId,
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
          repositoryFactory: DemoTrackStateRepository.new,
          workspaceProfileService: service,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => throw UnsupportedError(
                'Local Git startup access is unavailable.',
              ),
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
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(service.state.activeWorkspaceId, isNull);
      expect(
        service.state.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsNothing,
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      final activeLocalRow = find.byKey(
        const ValueKey('workspace-local:/tmp/trackstate-demo@main'),
      );
      expect(activeLocalRow, findsOneWidget);
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Active')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'startup restore clears the saved active local workspace when snapshot loading reports unsupported startup access',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: activeLocalWorkspaceId,
              displayName: 'Active local workspace',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/trackstate-demo',
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
          activeWorkspaceId: activeLocalWorkspaceId,
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
          repositoryFactory: DemoTrackStateRepository.new,
          workspaceProfileService: service,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => _QueuedLoadTrackStateRepository(
                loadResults: [
                  UnsupportedError('Local Git startup access is unavailable.'),
                ],
              ),
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
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(service.state.activeWorkspaceId, isNull);
      expect(
        service.state.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsNothing,
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      final activeLocalRow = find.byKey(
        const ValueKey('workspace-local:/tmp/trackstate-demo@main'),
      );
      expect(activeLocalRow, findsOneWidget);
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Active')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'startup restore clears the saved active local workspace when web startup reports unsupported Process.run access',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: activeLocalWorkspaceId,
              displayName: 'Active local workspace',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/trackstate-demo',
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
          activeWorkspaceId: activeLocalWorkspaceId,
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
          repositoryFactory: DemoTrackStateRepository.new,
          workspaceProfileService: service,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => _QueuedLoadTrackStateRepository(
                loadResults: [
                  UnsupportedError('Unsupported operation: Process.run'),
                ],
              ),
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
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(service.state.activeWorkspaceId, isNull);
      expect(
        service.state.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsNothing,
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      final activeLocalRow = find.byKey(
        const ValueKey('workspace-local:/tmp/trackstate-demo@main'),
      );
      expect(activeLocalRow, findsOneWidget);
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Active')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'workspace switcher marks the active local workspace unavailable when local sync fails after fail-soft startup',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: activeLocalWorkspaceId,
              displayName: 'Active local workspace',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/trackstate-demo',
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
          activeWorkspaceId: activeLocalWorkspaceId,
          migrationComplete: true,
        ),
      );
      final localRepository = _SyncErrorLocalTrackStateRepository(
        snapshot: await _snapshotForRepository('IstiN/trackstate-setup'),
        error: StateError(
          'Saved workspace path no longer matches the expected TrackState repository.',
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
          repositoryFactory: DemoTrackStateRepository.new,
          workspaceProfileService: service,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => localRepository,
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
      await tester.pump();
      final dynamic appState = tester.state(find.byType(TrackStateApp));
      for (var index = 0; index < 10; index += 1) {
        await tester.pump(const Duration(milliseconds: 100));
        final dynamic syncStatus = appState.viewModel.workspaceSyncStatus;
        if (syncStatus.health == WorkspaceSyncHealth.attentionNeeded) {
          break;
        }
      }
      final dynamic syncStatus = appState.viewModel.workspaceSyncStatus;
      expect(syncStatus.health, WorkspaceSyncHealth.attentionNeeded);

      await tester.tap(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );
      await tester.pumpAndSettle();

      final activeRow = find.byKey(
        const ValueKey('workspace-local:/tmp/trackstate-demo@main'),
      );
      expect(activeRow, findsOneWidget);
      expect(
        find.descendant(of: activeRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeRow, matching: find.text('Retry')),
        findsOneWidget,
      );
      expect(
        service.state.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
    },
  );

  testWidgets(
    'startup restore waits for active local workspace revalidation before falling back to hosted',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: activeLocalWorkspaceId,
              displayName: 'Active local workspace',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/trackstate-demo',
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
          activeWorkspaceId: activeLocalWorkspaceId,
          migrationComplete: true,
        ),
      );
      var localAccessReady = false;
      var localOpenAttempts = 0;

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
              }) async {
                localOpenAttempts += 1;
                if (!localAccessReady) {
                  throw StateError(
                    'File System Access handle revalidation is still pending.',
                  );
                }
                return DemoTrackStateRepository(
                  snapshot: await _snapshotForRepository(repositoryPath),
                );
              },
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

      await tester.pump();

      localAccessReady = true;
      await tester.pump(const Duration(milliseconds: 800));
      await tester.pumpAndSettle();

      expect(localOpenAttempts, greaterThan(1));
      expect(service.state.activeWorkspaceId, activeLocalWorkspaceId);
      expect(
        _findExplicitWorkspaceSwitcherSemantics(
          'Workspace switcher: Active local workspace, Local, Local Git',
        ),
        findsOneWidget,
      );
      expect(
        find.bySemanticsLabel(
          'Workspace switcher: stable/repo, Hosted, Needs sign-in',
        ),
        findsNothing,
      );

      await tester.tap(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );
      await tester.pumpAndSettle();

      final activeRow = find.byKey(
        const ValueKey('workspace-local:/tmp/trackstate-demo@main'),
      );
      expect(activeRow, findsOneWidget);
      expect(
        find.descendant(of: activeRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeRow, matching: find.text('Local Git')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeRow, matching: find.text('Open')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'startup restore keeps retrying active local workspace revalidation long enough to avoid hosted fallback',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: activeLocalWorkspaceId,
              displayName: 'Active local workspace',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/trackstate-demo',
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
          activeWorkspaceId: activeLocalWorkspaceId,
          migrationComplete: true,
        ),
      );
      var localAccessReady = false;
      var localOpenAttempts = 0;

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
              }) async {
                localOpenAttempts += 1;
                if (!localAccessReady) {
                  throw StateError(
                    'File System Access handle revalidation is still pending.',
                  );
                }
                return DemoTrackStateRepository(
                  snapshot: await _snapshotForRepository(repositoryPath),
                );
              },
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

      await tester.pump();
      await tester.pump(const Duration(seconds: 2));
      localAccessReady = true;
      await tester.pump(const Duration(seconds: 1));
      await tester.pumpAndSettle();

      expect(localOpenAttempts, greaterThan(4));
      expect(service.state.activeWorkspaceId, activeLocalWorkspaceId);
      expect(
        _findExplicitWorkspaceSwitcherSemantics(
          'Workspace switcher: Active local workspace, Local, Local Git',
        ),
        findsOneWidget,
      );
      expect(
        find.bySemanticsLabel(
          'Workspace switcher: stable/repo, Hosted, Needs sign-in',
        ),
        findsNothing,
      );

      await tester.tap(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );
      await tester.pumpAndSettle();

      final activeRow = find.byKey(
        const ValueKey('workspace-local:/tmp/trackstate-demo@main'),
      );
      expect(activeRow, findsOneWidget);
      expect(
        find.descendant(of: activeRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeRow, matching: find.text('Local Git')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeRow, matching: find.text('Open')),
        findsNothing,
      );
      expect(
        find.descendant(of: activeRow, matching: find.text('Unavailable')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'startup restore retries generic transient active local workspace failures before falling back',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: activeLocalWorkspaceId,
              displayName: 'Active local workspace',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/trackstate-demo',
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
          activeWorkspaceId: activeLocalWorkspaceId,
          migrationComplete: true,
        ),
      );
      var localAccessReady = false;
      var localOpenAttempts = 0;

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
              }) async {
                localOpenAttempts += 1;
                if (!localAccessReady) {
                  throw StateError('The local workspace is busy.');
                }
                return DemoTrackStateRepository(
                  snapshot: await _snapshotForRepository(repositoryPath),
                );
              },
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

      await tester.pump();
      await tester.pump(const Duration(seconds: 2));
      localAccessReady = true;
      await tester.pump(const Duration(seconds: 1));
      await tester.pumpAndSettle();

      expect(localOpenAttempts, greaterThan(4));
      expect(service.state.activeWorkspaceId, activeLocalWorkspaceId);
      expect(
        _findExplicitWorkspaceSwitcherSemantics(
          'Workspace switcher: Active local workspace, Local, Local Git',
        ),
        findsOneWidget,
      );
      expect(
        find.bySemanticsLabel(
          'Workspace switcher: stable/repo, Hosted, Needs sign-in',
        ),
        findsNothing,
      );

      await tester.tap(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );
      await tester.pumpAndSettle();

      final activeRow = find.byKey(
        const ValueKey('workspace-local:/tmp/trackstate-demo@main'),
      );
      expect(activeRow, findsOneWidget);
      expect(
        find.descendant(of: activeRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeRow, matching: find.text('Local Git')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeRow, matching: find.text('Open')),
        findsNothing,
      );
      expect(
        find.descendant(of: activeRow, matching: find.text('Unavailable')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'startup restore clears the active local workspace after revalidation retries exhaust',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: activeLocalWorkspaceId,
              displayName: 'Active local workspace',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/trackstate-demo',
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
          activeWorkspaceId: activeLocalWorkspaceId,
          migrationComplete: true,
        ),
      );
      var localOpenAttempts = 0;
      final localRepository = _QueuedLoadTrackStateRepository(
        loadResults: [
          StateError(
            'File system access to the selected directory is no longer available.',
          ),
        ],
      );

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
              }) async {
                localOpenAttempts += 1;
                return localRepository;
              },
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

      await tester.pump();
      await tester.pump(const Duration(seconds: 15));
      await tester.pump(const Duration(seconds: 1));

      expect(localOpenAttempts, greaterThan(5));
      expect(service.state.activeWorkspaceId, isNull);
      expect(
        service.state.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsNothing,
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      final activeLocalRow = find.byKey(
        const ValueKey('workspace-local:/tmp/trackstate-demo@main'),
      );
      expect(activeLocalRow, findsOneWidget);
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Active')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'workspace switcher restores an unavailable saved local workspace through the browser retry fallback without reopening the directory picker',
    (tester) async {
      const localWorkspaceId = 'local:/tmp/demo@main';
      const hostedWorkspaceId = 'hosted:stable/repo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: hostedWorkspaceId,
              displayName: 'stable/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'stable/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: localWorkspaceId,
              displayName: 'demo',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/demo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: hostedWorkspaceId,
          migrationComplete: true,
          unavailableLocalWorkspaceIds: {localWorkspaceId},
        ),
      );
      var directoryPickerCalls = 0;
      var productionOpenAttempts = 0;
      var browserRetryOpenAttempts = 0;

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
          workspaceDirectoryPicker:
              ({String? confirmButtonText, String? initialDirectory}) async {
                directoryPickerCalls += 1;
                expect(initialDirectory, '/tmp/demo');
                return '/tmp/demo';
              },
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
              }) async {
                productionOpenAttempts += 1;
                throw UnsupportedError('Unsupported operation: Process.run');
              },
          openBrowserLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async {
                browserRetryOpenAttempts += 1;
                expect(repositoryPath, '/tmp/demo');
                return _LocalQueuedLoadTrackStateRepository(
                  loadResults: [await _snapshotForRepository(repositoryPath)],
                );
              },
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.textContaining('stable/repo'), findsWidgets);
      expect(find.textContaining('/tmp/demo'), findsNothing);

      await tester.tap(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );
      await tester.pumpAndSettle();

      final localRow = find.byKey(
        const ValueKey('workspace-$localWorkspaceId'),
      );
      expect(localRow, findsOneWidget);
      expect(
        find.descendant(of: localRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: localRow, matching: find.text('Retry')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: localRow, matching: find.text('Open')),
        findsNothing,
      );

      await tester.tap(
        find.byKey(
          const ValueKey('workspace-primary-action-$localWorkspaceId'),
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      expect(directoryPickerCalls, 0);
      expect(productionOpenAttempts, 0);
      expect(browserRetryOpenAttempts, 1);
      expect(service.state.activeWorkspaceId, localWorkspaceId);
      expect(find.textContaining('/tmp/demo'), findsWidgets);
      expect(find.textContaining('stable/repo'), findsNothing);
      expect(
        _findExplicitWorkspaceSwitcherSemantics(
          'Workspace switcher: demo, Local, Local Git',
        ),
        findsOneWidget,
      );

      await tester.tap(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );
      await tester.pumpAndSettle();

      final restoredLocalRow = find.byKey(
        const ValueKey('workspace-$localWorkspaceId'),
      );
      expect(restoredLocalRow, findsOneWidget);
      expect(
        find.descendant(of: restoredLocalRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: restoredLocalRow, matching: find.text('Local Git')),
        findsOneWidget,
      );
      expect(
        find.descendant(
          of: restoredLocalRow,
          matching: find.text('Unavailable'),
        ),
        findsNothing,
      );
      expect(find.textContaining('Could not open demo'), findsNothing);
    },
  );

  testWidgets(
    'workspace switcher rejects a different directory during unavailable local workspace manual retry',
    (tester) async {
      const localWorkspaceId = 'local:/tmp/demo@main';
      const hostedWorkspaceId = 'hosted:stable/repo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: hostedWorkspaceId,
              displayName: 'stable/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'stable/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: localWorkspaceId,
              displayName: 'demo',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/demo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: hostedWorkspaceId,
          migrationComplete: true,
          unavailableLocalWorkspaceIds: {localWorkspaceId},
        ),
      );
      var directoryPickerCalls = 0;
      var localOpenCalls = 0;

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
          workspaceDirectoryPicker:
              ({String? confirmButtonText, String? initialDirectory}) async {
                directoryPickerCalls += 1;
                expect(initialDirectory, '/tmp/demo');
                return '/tmp/other';
              },
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
              }) async {
                localOpenCalls += 1;
                return DemoTrackStateRepository(
                  snapshot: await _snapshotForRepository(repositoryPath),
                );
              },
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      await tester.tap(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.byKey(
          const ValueKey('workspace-primary-action-$localWorkspaceId'),
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      expect(directoryPickerCalls, 1);
      expect(localOpenCalls, 0);
      expect(service.state.activeWorkspaceId, hostedWorkspaceId);
      expect(find.textContaining('stable/repo'), findsWidgets);
      expect(find.textContaining('/tmp/demo'), findsNothing);
      expect(find.textContaining('Could not open demo'), findsOneWidget);
      expect(
        find.textContaining(
          'Selected directory does not match the saved workspace configuration.',
        ),
        findsOneWidget,
      );

      await tester.tap(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );
      await tester.pumpAndSettle();

      final localRow = find.byKey(
        const ValueKey('workspace-$localWorkspaceId'),
      );
      final hostedRow = find.byKey(
        const ValueKey('workspace-$hostedWorkspaceId'),
      );
      expect(localRow, findsOneWidget);
      expect(hostedRow, findsOneWidget);
      expect(
        find.descendant(of: hostedRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: localRow, matching: find.text('Active')),
        findsNothing,
      );
      expect(
        find.descendant(of: localRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: localRow, matching: find.text('Retry')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: localRow, matching: find.text('Open')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'workspace switcher rejects a different directory during unavailable local workspace retry with a mismatch error',
    (tester) async {
      const localWorkspaceId = 'local:/tmp/demo@main';
      const hostedWorkspaceId = 'hosted:stable/repo@main';
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: hostedWorkspaceId,
              displayName: 'stable/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'stable/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: localWorkspaceId,
              displayName: 'Restorable local workspace',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/demo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: hostedWorkspaceId,
          migrationComplete: true,
        ),
      );
      var directoryPickerCalls = 0;
      final reopenedRepositoryPaths = <String>[];

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
          workspaceDirectoryPicker:
              ({String? confirmButtonText, String? initialDirectory}) async {
                directoryPickerCalls += 1;
                expect(initialDirectory, '/tmp/demo');
                return '/tmp/wrong-directory';
              },
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
              }) async {
                reopenedRepositoryPaths.add(repositoryPath);
                throw UnsupportedError('Unsupported operation: Process.run');
              },
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      await tester.tap(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.byKey(
          const ValueKey('workspace-primary-action-$localWorkspaceId'),
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      expect(directoryPickerCalls, 1);
      expect(reopenedRepositoryPaths, isNot(contains('/tmp/wrong-directory')));
      expect(service.state.activeWorkspaceId, hostedWorkspaceId);
      expect(
        find.text(
          'Could not open Restorable local workspace. Selected directory does not match the saved workspace configuration.',
        ),
        findsOneWidget,
      );

      await tester.tap(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );
      await tester.pumpAndSettle();

      final originalLocalRow = find.byKey(
        const ValueKey('workspace-$localWorkspaceId'),
      );
      expect(originalLocalRow, findsOneWidget);
      expect(
        find.descendant(
          of: originalLocalRow,
          matching: find.text('Unavailable'),
        ),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('workspace-local:/tmp/wrong-directory@main')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'startup restore opens onboarding when every saved workspace is invalid',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/missing@main';
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
          activeWorkspaceId: activeLocalWorkspaceId,
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
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(service.state.activeWorkspaceId, isNull);
      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsNothing,
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      final activeLocalRow = find.byKey(
        const ValueKey('workspace-local:/tmp/missing@main'),
      );
      expect(activeLocalRow, findsOneWidget);
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Active')),
        findsNothing,
      );
      expect(find.text('Project Settings'), findsNothing);
    },
  );

  testWidgets(
    'saved workspace recovery does not auto-validate hosted alternatives when the active local workspace is unavailable',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/missing@main';
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
          activeWorkspaceId: activeLocalWorkspaceId,
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
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(service.state.activeWorkspaceId, isNull);
      expect(hostedValidationAttempts, 0);
      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsNothing,
      );
      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      final activeLocalRow = find.byKey(
        const ValueKey('workspace-local:/tmp/missing@main'),
      );
      expect(activeLocalRow, findsOneWidget);
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Unavailable')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeLocalRow, matching: find.text('Active')),
        findsNothing,
      );
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
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repository),
              ),
        ),
      );
      await _pumpUntilVisible(
        tester,
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );

      final trigger = find.byKey(const ValueKey('workspace-switcher-trigger'));
      expect(trigger, findsOneWidget);
      expect(
        find.descendant(of: trigger, matching: find.text('alpha/repo')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: trigger, matching: find.textContaining('Hosted ·')),
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
    'workspace switcher opens an anchored desktop panel instead of a dialog',
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
        ),
      );
      await tester.pumpAndSettle();

      final trigger = find.byKey(const ValueKey('workspace-switcher-trigger'));
      expect(trigger, findsOneWidget);
      final triggerRect = tester.getRect(trigger);

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      final switcherSurface = find.byKey(
        const ValueKey('workspace-switcher-sheet'),
      );
      expect(switcherSurface, findsOneWidget);
      expect(find.byType(Dialog), findsNothing);

      final switcherRect = tester.getRect(switcherSurface);
      expect(switcherRect.top, greaterThanOrEqualTo(triggerRect.bottom - 12));
      expect(switcherRect.top, lessThanOrEqualTo(triggerRect.bottom + 120));
      expect(
        (switcherRect.right - triggerRect.right).abs(),
        lessThanOrEqualTo(120),
      );
    },
  );

  testWidgets(
    'desktop workspace switcher dismisses when tapping neutral main content',
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
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );

      await tester.tapAt(const Offset(96, 632));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsNothing,
      );
      expect(find.text('Dashboard'), findsWidgets);
    },
  );

  testWidgets(
    'desktop workspace switcher dismisses on Escape and returns focus to the trigger',
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
        ),
      );
      await tester.pumpAndSettle();

      final trigger = find.byKey(const ValueKey('workspace-switcher-trigger'));
      expect(trigger, findsOneWidget);

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );

      await tester.sendKeyEvent(LogicalKeyboardKey.escape);
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsNothing,
      );
      expect(_focusWithinFinder(tester, trigger), isTrue);
    },
  );

  testWidgets(
    'desktop workspace switcher keeps open on non-Escape keys and Arrow Down switches to the next saved workspace',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:main/repo@main',
              displayName: 'Hosted main workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'main/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:alt/repo@main',
              displayName: 'Hosted alt workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alt/repo',
              defaultBranch: 'main',
              writeBranch: 'ts-825-alt',
            ),
          ],
          activeWorkspaceId: 'hosted:main/repo@main',
          migrationComplete: true,
        ),
        reorderOnSelect: true,
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
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      final switcherSheet = find.byKey(
        const ValueKey('workspace-switcher-sheet'),
      );
      final mainRow = find.byKey(
        const ValueKey('workspace-hosted:main/repo@main'),
      );
      final altRow = find.byKey(
        const ValueKey('workspace-hosted:alt/repo@main'),
      );

      expect(switcherSheet, findsOneWidget);
      expect(
        find.descendant(of: mainRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: altRow, matching: find.text('Active')),
        findsNothing,
      );

      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await tester.pumpAndSettle();

      expect(switcherSheet, findsOneWidget);
      expect(service.state.activeWorkspaceId, 'hosted:alt/repo@main');
      expect(
        find.descendant(of: mainRow, matching: find.text('Active')),
        findsNothing,
      );
      expect(
        find.descendant(of: altRow, matching: find.text('Active')),
        findsOneWidget,
      );

      await tester.sendKeyDownEvent(LogicalKeyboardKey.shiftLeft);
      await tester.pump();
      await tester.sendKeyUpEvent(LogicalKeyboardKey.shiftLeft);
      await tester.pump();
      expect(switcherSheet, findsOneWidget);

      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pumpAndSettle();
      expect(switcherSheet, findsOneWidget);
    },
  );

  testWidgets(
    'desktop workspace switcher Arrow Down moves focus to the next row and switches once',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:main/repo@main',
              displayName: 'Hosted main workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'main/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:alt/repo@main',
              displayName: 'Hosted alt workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alt/repo',
              defaultBranch: 'main',
              writeBranch: 'ts-825-alt',
            ),
          ],
          activeWorkspaceId: 'hosted:main/repo@main',
          migrationComplete: true,
        ),
      );
      final hostedRepositoryLoads = <String>[];

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
              }) async {
                hostedRepositoryLoads.add(repository);
                return DemoTrackStateRepository(
                  snapshot: await _snapshotForRepository(repository),
                );
              },
        ),
      );
      await tester.pumpAndSettle();

      final switcherTrigger = find.byKey(
        const ValueKey('workspace-switcher-trigger'),
      );
      final switcherSheet = find.byKey(
        const ValueKey('workspace-switcher-sheet'),
      );
      final mainRow = find.byKey(
        const ValueKey('workspace-hosted:main/repo@main'),
      );
      final altRow = find.byKey(
        const ValueKey('workspace-hosted:alt/repo@main'),
      );

      expect(hostedRepositoryLoads, ['main/repo']);

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      expect(switcherSheet, findsOneWidget);
      expect(_focusWithinFinder(tester, switcherTrigger), isTrue);

      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await tester.pumpAndSettle();

      expect(service.state.activeWorkspaceId, 'hosted:alt/repo@main');
      expect(
        service.selectedProfileIds
            .where((workspaceId) => workspaceId == 'hosted:alt/repo@main')
            .length,
        1,
      );
      expect(hostedRepositoryLoads, ['main/repo', 'alt/repo']);
      expect(switcherSheet, findsOneWidget);
      expect(_focusWithinFinder(tester, switcherTrigger), isFalse);
      expect(
        FocusManager.instance.primaryFocus?.debugLabel,
        'workspace-switcher-row-summary-hosted:alt/repo@main',
      );
      expect(_focusWithinFinder(tester, altRow), isTrue);
      expect(
        find.descendant(of: mainRow, matching: find.text('Active')),
        findsNothing,
      );
      expect(
        find.descendant(of: altRow, matching: find.text('Active')),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'desktop workspace switcher trigger Arrow Down advances the active workspace while the switcher stays open',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:main/repo@main',
              displayName: 'Hosted main workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'main/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:alt/repo@main',
              displayName: 'Hosted alt workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alt/repo',
              defaultBranch: 'main',
              writeBranch: 'ts-825-alt',
            ),
          ],
          activeWorkspaceId: 'hosted:main/repo@main',
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
        ),
      );
      await tester.pumpAndSettle();

      final switcherTrigger = find.byKey(
        const ValueKey('workspace-switcher-trigger'),
      );
      final switcherSheet = find.byKey(
        const ValueKey('workspace-switcher-sheet'),
      );
      final mainRow = find.byKey(
        const ValueKey('workspace-hosted:main/repo@main'),
      );
      final altRow = find.byKey(
        const ValueKey('workspace-hosted:alt/repo@main'),
      );

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      final triggerButton = tester.widget<FilledButton>(
        find.descendant(
          of: switcherTrigger,
          matching: find.byType(FilledButton),
        ),
      );
      triggerButton.focusNode?.requestFocus();
      await tester.pumpAndSettle();

      expect(_focusWithinFinder(tester, switcherTrigger), isTrue);
      expect(
        find.descendant(of: mainRow, matching: find.text('Active')),
        findsOneWidget,
      );

      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await tester.pumpAndSettle();

      expect(switcherSheet, findsOneWidget);
      expect(service.state.activeWorkspaceId, 'hosted:alt/repo@main');
      expect(_focusWithinFinder(tester, switcherTrigger), isFalse);
      expect(
        find.descendant(of: mainRow, matching: find.text('Active')),
        findsNothing,
      );
      expect(
        find.descendant(of: altRow, matching: find.text('Active')),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'desktop workspace switcher Arrow Up moves focus to the previous saved workspace row',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'local:/tmp/first@main',
              displayName: 'First local workspace',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/first',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'local:/tmp/second@main',
              displayName: 'Second local workspace',
              targetType: WorkspaceProfileTargetType.local,
              target: '/tmp/second',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: 'local:/tmp/second@main',
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
              }) async => DemoTrackStateRepository(
                snapshot: await _snapshotForRepository(repositoryPath),
              ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      final switcherSheet = find.byKey(
        const ValueKey('workspace-switcher-sheet'),
      );
      final firstRow = find.byKey(
        const ValueKey('workspace-local:/tmp/first@main'),
      );
      final secondRow = find.byKey(
        const ValueKey('workspace-local:/tmp/second@main'),
      );

      expect(switcherSheet, findsOneWidget);
      expect(
        find.descendant(of: secondRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: firstRow, matching: find.text('Active')),
        findsNothing,
      );

      await tester.sendKeyEvent(LogicalKeyboardKey.arrowUp);
      await tester.pumpAndSettle();

      expect(switcherSheet, findsOneWidget);
      expect(service.state.activeWorkspaceId, 'local:/tmp/first@main');
      expect(
        find.descendant(of: firstRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: secondRow, matching: find.text('Active')),
        findsNothing,
      );
      expect(
        FocusManager.instance.primaryFocus?.debugLabel,
        'workspace-switcher-row-summary-local:/tmp/first@main',
      );
      expect(_focusWithinFinder(tester, firstRow), isTrue);
    },
  );

  testWidgets(
    'desktop workspace switcher Home and End move selection and focus to the saved workspace boundaries',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:main/repo@main',
              displayName: 'Hosted main workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'main/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:alt/repo@main',
              displayName: 'Hosted alt workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alt/repo',
              defaultBranch: 'main',
              writeBranch: 'ts-869-alt',
            ),
            WorkspaceProfile(
              id: 'hosted:end/repo@main',
              displayName: 'Hosted end workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'end/repo',
              defaultBranch: 'main',
              writeBranch: 'ts-869-end',
            ),
          ],
          activeWorkspaceId: 'hosted:main/repo@main',
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
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      final switcherSheet = find.byKey(
        const ValueKey('workspace-switcher-sheet'),
      );
      final mainRow = find.byKey(
        const ValueKey('workspace-hosted:main/repo@main'),
      );
      final altRow = find.byKey(
        const ValueKey('workspace-hosted:alt/repo@main'),
      );
      final endRow = find.byKey(
        const ValueKey('workspace-hosted:end/repo@main'),
      );

      expect(switcherSheet, findsOneWidget);
      expect(mainRow, findsOneWidget);
      expect(altRow, findsOneWidget);
      expect(endRow, findsOneWidget);

      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await tester.pumpAndSettle();

      expect(service.state.activeWorkspaceId, 'hosted:alt/repo@main');
      expect(
        tester.getTopLeft(mainRow).dy,
        lessThan(tester.getTopLeft(altRow).dy),
      );
      expect(
        tester.getTopLeft(altRow).dy,
        lessThan(tester.getTopLeft(endRow).dy),
      );
      expect(
        FocusManager.instance.primaryFocus?.debugLabel,
        'workspace-switcher-row-summary-hosted:alt/repo@main',
      );
      expect(_focusWithinFinder(tester, altRow), isTrue);

      await tester.sendKeyEvent(LogicalKeyboardKey.home);
      await tester.pumpAndSettle();

      expect(switcherSheet, findsOneWidget);
      expect(service.state.activeWorkspaceId, 'hosted:main/repo@main');
      expect(
        find.descendant(of: mainRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: altRow, matching: find.text('Active')),
        findsNothing,
      );
      expect(
        FocusManager.instance.primaryFocus?.debugLabel,
        'workspace-switcher-row-summary-hosted:main/repo@main',
      );
      expect(_focusWithinFinder(tester, mainRow), isTrue);

      await tester.sendKeyEvent(LogicalKeyboardKey.end);
      await tester.pumpAndSettle();

      expect(switcherSheet, findsOneWidget);
      expect(service.state.activeWorkspaceId, 'hosted:end/repo@main');
      expect(
        find.descendant(of: mainRow, matching: find.text('Active')),
        findsNothing,
      );
      expect(
        find.descendant(of: endRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        FocusManager.instance.primaryFocus?.debugLabel,
        'workspace-switcher-row-summary-hosted:end/repo@main',
      );
      expect(_focusWithinFinder(tester, endRow), isTrue);
    },
  );

  testWidgets(
    'desktop workspace switcher row click keeps keyboard focus inside the active row before Arrow Down navigation',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:main/repo@main',
              displayName: 'Hosted main workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'main/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:alt/repo@main',
              displayName: 'Hosted alt workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alt/repo',
              defaultBranch: 'main',
              writeBranch: 'ts-825-alt',
            ),
          ],
          activeWorkspaceId: 'hosted:main/repo@main',
          migrationComplete: true,
        ),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      try {
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
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(
          find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
        );
        await tester.pumpAndSettle();

        final switcherSheet = find.byKey(
          const ValueKey('workspace-switcher-sheet'),
        );
        final mainRow = find.byKey(
          const ValueKey('workspace-hosted:main/repo@main'),
        );
        final altRow = find.byKey(
          const ValueKey('workspace-hosted:alt/repo@main'),
        );

        expect(switcherSheet, findsOneWidget);
        expect(mainRow, findsOneWidget);
        expect(altRow, findsOneWidget);
        final semanticsLabels = tester
            .widgetList<Semantics>(find.byType(Semantics))
            .map((widget) => widget.properties.label ?? '')
            .where((label) => label.isNotEmpty)
            .toList();

        expect(
          semanticsLabels.any(
            (label) => label.startsWith('Hosted main workspace, Hosted, '),
          ),
          isTrue,
        );
        expect(
          semanticsLabels.any(
            (label) => label.startsWith('Hosted alt workspace, Hosted, '),
          ),
          isTrue,
        );
        expect(
          semanticsLabels.any(
            (label) =>
                label.contains("Instance of 'WorkspaceProfile'.displayName"),
          ),
          isFalse,
        );

        final mainRowRect = tester.getRect(mainRow);
        await tester.tapAt(mainRowRect.topLeft + const Offset(40, 28));
        await tester.pumpAndSettle();

        expect(
          _focusWithinFinder(tester, mainRow),
          isTrue,
          reason:
              'Clicking the active saved-workspace row should move keyboard focus '
              'to a focusable target inside that row.',
        );

        await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
        await tester.pumpAndSettle();

        expect(switcherSheet, findsOneWidget);
        expect(service.state.activeWorkspaceId, 'hosted:alt/repo@main');
        expect(
          find.descendant(of: mainRow, matching: find.text('Active')),
          findsNothing,
        );
        expect(
          find.descendant(of: altRow, matching: find.text('Active')),
          findsOneWidget,
        );
      } finally {
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'desktop workspace switcher wraps Arrow Down from the last saved workspace row and keeps focus inside the sheet',
    (tester) async {
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:main/repo@main',
              displayName: 'Hosted main workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'main/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:alt/repo@main',
              displayName: 'Hosted alt workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alt/repo',
              defaultBranch: 'main',
              writeBranch: 'ts-851-alt',
            ),
          ],
          activeWorkspaceId: 'hosted:main/repo@main',
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
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      final switcherSheet = find.byKey(
        const ValueKey('workspace-switcher-sheet'),
      );
      final mainRow = find.byKey(
        const ValueKey('workspace-hosted:main/repo@main'),
      );
      final altRow = find.byKey(
        const ValueKey('workspace-hosted:alt/repo@main'),
      );

      expect(switcherSheet, findsOneWidget);
      expect(mainRow, findsOneWidget);
      expect(altRow, findsOneWidget);

      final mainRowRect = tester.getRect(mainRow);
      await tester.tapAt(mainRowRect.topLeft + const Offset(40, 28));
      await tester.pumpAndSettle();

      expect(_focusWithinFinder(tester, mainRow), isTrue);

      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await tester.pumpAndSettle();

      expect(service.state.activeWorkspaceId, 'hosted:alt/repo@main');

      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await tester.pumpAndSettle();

      expect(switcherSheet, findsOneWidget);
      expect(
        service.state.activeWorkspaceId,
        'hosted:main/repo@main',
        reason:
            'Arrow Down on the last saved workspace row should wrap the active '
            'selection back to the first saved workspace.',
      );
      expect(
        _focusWithinFinder(tester, switcherSheet),
        isTrue,
        reason:
            'Boundary Arrow Down navigation should keep keyboard focus inside '
            'the open desktop workspace switcher.',
      );
      expect(
        find.descendant(of: mainRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: altRow, matching: find.text('Active')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'desktop workspace switcher keeps visible header controls interactive while open',
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
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      expect(find.bySemanticsLabel(RegExp('^Dark theme\$')), findsOneWidget);

      await tester.tap(find.bySemanticsLabel(RegExp('^Dark theme\$')).last);
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel(RegExp('^Light theme\$')), findsOneWidget);
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

  testWidgets(
    'desktop keyboard traversal keeps Settings, workspace switcher, and search adjacent',
    (tester) async {
      final semantics = tester.ensureSemantics();
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

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      try {
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
          ),
        );
        await _pumpUntilVisible(tester, find.byType(TextField));

        final candidates = <String, Finder>{
          'Create issue': _findSemanticsByLabel('Create issue', button: true),
          'Add workspace': _findSemanticsByLabel('Add workspace', button: true),
          'Board': _findSemanticsByLabel('Board', button: true),
          'JQL Search': _findSemanticsByLabel('JQL Search', button: true),
          'Hierarchy': _findSemanticsByLabel('Hierarchy', button: true),
          'Settings': _findSemanticsByLabel('Settings', button: true),
          'Workspace switcher': find.byKey(
            const ValueKey('workspace-switcher-trigger'),
          ),
          'Search issues': _findSemanticsByLabel(
            'Search issues',
            textField: true,
          ),
        };

        await tester.tap(candidates['Search issues']!);
        await tester.pump();
        expect(_focusedLabel(tester, candidates), 'Search issues');

        final reachedCreateIssue = await _focusByTabUntil(
          tester,
          isFocused: () => _focusedLabel(tester, candidates) == 'Create issue',
        );
        expect(reachedCreateIssue, isTrue);

        final observed = <String>['Create issue'];
        for (var index = 0; index < 16; index += 1) {
          await tester.sendKeyEvent(LogicalKeyboardKey.tab);
          await tester.pump();
          final label = _focusedLabel(tester, candidates);
          if (label == null) {
            continue;
          }
          if (observed.isEmpty || observed.last != label) {
            observed.add(label);
          }
          if (label == 'Search issues') {
            break;
          }
        }

        expect(
          observed,
          containsAllInOrder([
            'Create issue',
            'Add workspace',
            'Board',
            'JQL Search',
            'Hierarchy',
            'Settings',
            'Workspace switcher',
            'Search issues',
          ]),
        );
        final workspaceIndex = observed.indexOf('Workspace switcher');
        expect(workspaceIndex, greaterThan(0));
        expect(observed[workspaceIndex - 1], 'Settings');
        expect(observed[workspaceIndex + 1], 'Search issues');
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'workspace switcher keeps desktop and sheet keyboard focus traversal logical',
    (tester) async {
      final semantics = tester.ensureSemantics();
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
              id: 'hosted:beta/repo@main',
              displayName: 'beta/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'beta/repo',
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
      try {
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
                }) async =>
                    throw StateError('Missing repository $repositoryPath'),
          ),
        );
        await _pumpUntilVisible(tester, find.byType(TextField));

        final desktopCandidates = <String, Finder>{
          'Search issues': find.byType(TextField),
          'Create issue': find.bySemanticsLabel(RegExp('^Create issue\$')).last,
          'Add workspace': find
              .bySemanticsLabel(RegExp('^Add workspace\$'))
              .last,
          'Workspace switcher': find.byKey(
            const ValueKey('workspace-switcher-trigger'),
          ),
        };

        await tester.tap(desktopCandidates['Search issues']!);
        await tester.pump();
        expect(_focusedLabel(tester, desktopCandidates), 'Search issues');

        final reachedCreateIssue = await _focusByTabUntil(
          tester,
          isFocused: () =>
              _focusedLabel(tester, desktopCandidates) == 'Create issue',
        );
        expect(reachedCreateIssue, isTrue);

        final reachedAddWorkspace = await _focusByTabUntil(
          tester,
          isFocused: () =>
              _focusedLabel(tester, desktopCandidates) == 'Add workspace',
        );
        expect(reachedAddWorkspace, isTrue);

        final reachedWorkspaceSwitcher = await _focusByTabUntil(
          tester,
          isFocused: () =>
              _focusedLabel(tester, desktopCandidates) == 'Workspace switcher',
        );
        expect(reachedWorkspaceSwitcher, isTrue);

        await tester.sendKeyEvent(LogicalKeyboardKey.enter);
        await tester.pump();
        await _pumpUntilVisible(tester, find.text('Saved workspaces'));

        final sheetCandidates = <String, Finder>{
          'Open workspace': find.byKey(
            const ValueKey('workspace-open-hosted:beta/repo@main'),
          ),
          'Delete workspace': find.byKey(
            const ValueKey('workspace-delete-hosted:beta/repo@main'),
          ),
          'Repository': find.widgetWithText(TextFormField, 'Repository'),
          'Branch': find.widgetWithText(TextFormField, 'Branch'),
          'Save and switch': find.byKey(const ValueKey('workspace-add-button')),
        };

        await tester.enterText(sheetCandidates['Repository']!, 'gamma/repo');
        await tester.pump();

        await tester.tap(sheetCandidates['Repository']!);
        await tester.pump();
        expect(_focusedLabel(tester, sheetCandidates), 'Repository');

        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.pump();
        expect(_focusedLabel(tester, sheetCandidates), 'Branch');

        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.pump();
        expect(_focusedLabel(tester, sheetCandidates), 'Save and switch');
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'desktop header exports browser semantics sort keys through the workspace switcher trigger',
    (tester) async {
      final semantics = tester.ensureSemantics();
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

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      try {
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
          ),
        );
        await _pumpUntilVisible(tester, find.byType(TextField));

        expect(
          _findSemanticsWithSortOrder(
            label: 'Search issues',
            sortOrder: 8,
            textField: true,
          ),
          findsOneWidget,
        );
        expect(
          _findSemanticsWithSortOrder(label: 'Create issue', sortOrder: 1),
          findsOneWidget,
        );
        expect(
          _findSemanticsWithSortOrder(label: 'Board', sortOrder: 3),
          findsOneWidget,
        );
        expect(
          _findSemanticsWithSortOrder(label: 'JQL Search', sortOrder: 4),
          findsOneWidget,
        );
        expect(
          _findSemanticsWithSortOrder(label: 'Hierarchy', sortOrder: 5),
          findsOneWidget,
        );
        expect(
          _findSemanticsWithSortOrder(label: 'Settings', sortOrder: 6),
          findsOneWidget,
        );
        expect(
          _findSemanticsWithSortOrder(label: 'Add workspace', sortOrder: 1.5),
          findsOneWidget,
        );

        final trigger = find.byKey(
          const ValueKey('workspace-switcher-trigger'),
        );
        expect(
          find.descendant(
            of: trigger,
            matching: _findSemanticsWithSortOrder(
              label: 'Workspace switcher: alpha/repo, Hosted, Needs sign-in',
              sortOrder: 7,
            ),
          ),
          findsOneWidget,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'desktop workspace switcher trigger exports an actionable semantics node for browser keyboard flow',
    (tester) async {
      final semantics = tester.ensureSemantics();
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

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      try {
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
          ),
        );
        await _pumpUntilVisible(tester, find.byType(TextField));

        final trigger = find.byKey(
          const ValueKey('workspace-switcher-trigger'),
        );
        expect(
          find.descendant(
            of: trigger,
            matching: _findActionableSemanticsWithSortOrder(
              label: 'Workspace switcher: alpha/repo, Hosted, Needs sign-in',
              sortOrder: 7,
            ),
          ),
          findsOneWidget,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'desktop workspace switcher exports a single explicit button semantics node across desktop layouts',
    (tester) async {
      final semantics = tester.ensureSemantics();
      const label = 'Workspace switcher: alpha/repo, Hosted, Needs sign-in';
      final layouts = <({String name, Size size})>[
        (name: 'wide', size: const Size(1600, 960)),
        (name: 'condensed', size: const Size(1180, 900)),
        (name: 'compact', size: const Size(390, 844)),
      ];
      try {
        for (final layout in layouts) {
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

          tester.view.physicalSize = layout.size;
          tester.view.devicePixelRatio = 1;

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
            ),
          );
          await tester.pumpAndSettle();

          final trigger = find.byKey(
            const ValueKey('workspace-switcher-trigger'),
          );
          final explicitButtonSemantics = find.descendant(
            of: trigger,
            matching: find.byWidgetPredicate(
              (widget) =>
                  widget is Semantics &&
                  widget.properties.label == label &&
                  widget.properties.button == true,
              description:
                  'explicit button semantics for the desktop workspace switcher trigger',
            ),
          );

          expect(
            explicitButtonSemantics,
            findsOneWidget,
            reason:
                'The ${layout.name} workspace switcher trigger should export a '
                'single explicit button semantics node so Flutter web exposes one '
                'keyboard-focusable control instead of an inert outer wrapper.',
          );
          expect(
            _findExplicitWorkspaceSwitcherSemantics(label),
            findsOneWidget,
            reason:
                'The ${layout.name} workspace switcher trigger should expose one '
                'explicit labeled button semantics node.',
          );

          await tester.pumpWidget(const SizedBox.shrink());
          await tester.pump();
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'condensed desktop workspace switcher exports only one focusable button semantics node',
    (tester) async {
      final semantics = tester.ensureSemantics();
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
      try {
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
          ),
        );
        await tester.pumpAndSettle();

        final trigger = find.byKey(
          const ValueKey('workspace-switcher-trigger'),
        );
        final triggerSemantics = _semanticsFinderFor(
          tester: tester,
          finder: trigger,
        );
        final focusableButtonSemantics = find.semantics.descendant(
          of: triggerSemantics,
          matching: find.semantics.byPredicate((node) {
            final data = node.getSemanticsData();
            return data.flagsCollection.isButton &&
                data.flagsCollection.isFocusable;
          }, describeMatch: (_) => 'focusable button semantics node'),
          matchRoot: true,
        );

        expect(
          focusableButtonSemantics,
          kIsWeb ? findsOne : findsAtLeast(1),
          reason:
              'The condensed desktop workspace switcher trigger must export a '
              '${kIsWeb ? 'single' : 'stable'} focusable button semantics node '
              'so browser Tab and post-open focus stay on the canonical trigger '
              'control.',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'workspace switcher keeps state badges readable and the compact trigger keyboard reachable',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final authStore = _MemoryAuthStore()
        ..workspaceTokens['hosted:beta/repo@main'] = 'beta-token';
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
              id: 'hosted:beta/repo@main',
              displayName: 'beta/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'beta/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
              hostedAccessMode: HostedWorkspaceAccessMode.readOnly,
            ),
          ],
          activeWorkspaceId: 'hosted:alpha/repo@main',
          migrationComplete: true,
        ),
      );

      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      try {
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
        await _pumpUntilVisible(
          tester,
          find.byKey(const ValueKey('workspace-switcher-trigger')),
        );

        final triggerFinder = find.byKey(
          const ValueKey('workspace-switcher-trigger'),
        );

        FocusManager.instance.primaryFocus?.unfocus();
        await tester.pump();

        final reachedCompactTrigger = await _focusByTabUntil(
          tester,
          isFocused: () => _focusWithinFinder(tester, triggerFinder),
        );
        expect(reachedCompactTrigger, isTrue);
        expect(
          find.descendant(
            of: triggerFinder,
            matching: _findActionableSemanticsWithSortOrder(
              label: 'Workspace switcher: alpha/repo, Hosted, Needs sign-in',
              sortOrder: 5,
            ),
          ),
          findsOneWidget,
        );

        await tester.tap(
          find.bySemanticsLabel(RegExp('^Workspace switcher:')).last,
        );
        await _pumpUntilVisible(tester, find.text('Saved workspaces'));
        await _pumpUntilVisible(tester, find.text('Read-only'));

        final badgeText = find.text('Read-only');
        expect(badgeText, findsOneWidget);

        final badgeTextStyle = tester.widget<Text>(badgeText).style;
        final badgeContainer = _nearestDecoratedContainer(tester, badgeText);
        final badgeDecoration = badgeContainer.decoration! as BoxDecoration;
        final colors = Theme.of(
          tester.element(badgeText),
        ).extension<TrackStateColors>()!;
        final renderedBadgeBackground = Color.alphaBlend(
          badgeDecoration.color!,
          colors.surface,
        );
        final contrast = contrastRatio(
          badgeTextStyle!.color!,
          renderedBadgeBackground,
        );

        expect(contrast, greaterThanOrEqualTo(4.5));

        final deleteButton = tester.widget<TextButton>(
          find.byKey(const ValueKey('workspace-delete-hosted:beta/repo@main')),
        );
        final deleteForeground = deleteButton.style!.foregroundColor!.resolve(
          <WidgetState>{},
        )!;
        final deleteContrast = contrastRatio(deleteForeground, colors.surface);

        expect(deleteContrast, greaterThanOrEqualTo(4.5));
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
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

  testWidgets(
    'roving tabindex: only the active workspace row exports focusable semantics',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:main/repo@main',
              displayName: 'Hosted main workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'main/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:alt/repo@main',
              displayName: 'Hosted alt workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alt/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:third/repo@main',
              displayName: 'Hosted third workspace',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'third/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: 'hosted:main/repo@main',
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
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.bySemanticsLabel(RegExp('Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      // Initially, only the active (first) row should be focusable.
      final mainRowSemanticsNode = find.semantics.byPredicate(
        (node) =>
            node.label.contains('Hosted main workspace') &&
            node.getSemanticsData().identifier ==
                'trackstate-workspace-switcher-row-hosted:main/repo@main',
      );
      final altRowSemanticsNode = find.semantics.byPredicate(
        (node) =>
            node.label.contains('Hosted alt workspace') &&
            node.getSemanticsData().identifier ==
                'trackstate-workspace-switcher-row-hosted:alt/repo@main',
      );
      final thirdRowSemanticsNode = find.semantics.byPredicate(
        (node) =>
            node.label.contains('Hosted third workspace') &&
            node.getSemanticsData().identifier ==
                'trackstate-workspace-switcher-row-hosted:third/repo@main',
      );

      expect(mainRowSemanticsNode, findsOne);
      expect(altRowSemanticsNode, findsOne);
      expect(thirdRowSemanticsNode, findsOne);

      final mainSem = mainRowSemanticsNode.evaluate().single;
      final altSem = altRowSemanticsNode.evaluate().single;
      final thirdSem = thirdRowSemanticsNode.evaluate().single;

      expect(
        mainSem.getSemanticsData().flagsCollection.isFocusable,
        isTrue,
        reason: 'Active workspace row should be focusable.',
      );
      expect(
        altSem.getSemanticsData().flagsCollection.isFocusable,
        isFalse,
        reason: 'Inactive workspace row should NOT be focusable.',
      );
      expect(
        thirdSem.getSemanticsData().flagsCollection.isFocusable,
        isFalse,
        reason: 'Inactive workspace row should NOT be focusable.',
      );

      // Press ArrowDown to move selection to the second workspace.
      final mainRow = find.byKey(
        const ValueKey('workspace-hosted:main/repo@main'),
      );
      final mainRowRect = tester.getRect(mainRow);
      await tester.tapAt(mainRowRect.topLeft + const Offset(40, 28));
      await tester.pumpAndSettle();
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
      await tester.pumpAndSettle();

      expect(service.state.activeWorkspaceId, 'hosted:alt/repo@main');

      // After ArrowDown, only the newly active row should be focusable.
      final mainRowSemanticsNodeAfter = find.semantics.byPredicate(
        (node) =>
            node.getSemanticsData().identifier ==
            'trackstate-workspace-switcher-row-hosted:main/repo@main',
      );
      final altRowSemanticsNodeAfter = find.semantics.byPredicate(
        (node) =>
            node.getSemanticsData().identifier ==
            'trackstate-workspace-switcher-row-hosted:alt/repo@main',
      );
      final thirdRowSemanticsNodeAfter = find.semantics.byPredicate(
        (node) =>
            node.getSemanticsData().identifier ==
            'trackstate-workspace-switcher-row-hosted:third/repo@main',
      );

      final mainSemAfter = mainRowSemanticsNodeAfter.evaluate().single;
      final altSemAfter = altRowSemanticsNodeAfter.evaluate().single;
      final thirdSemAfter = thirdRowSemanticsNodeAfter.evaluate().single;

      expect(
        mainSemAfter.getSemanticsData().flagsCollection.isFocusable,
        isFalse,
        reason:
            'Previously active row should lose focusable after selection moves.',
      );
      expect(
        altSemAfter.getSemanticsData().flagsCollection.isFocusable,
        isTrue,
        reason: 'Newly active workspace row should be focusable.',
      );
      expect(
        thirdSemAfter.getSemanticsData().flagsCollection.isFocusable,
        isFalse,
        reason:
            'Inactive workspace row should remain not focusable after selection changes.',
      );

      semantics.dispose();
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
  _MemoryWorkspaceProfileService(this.state, {this.reorderOnSelect = false});

  WorkspaceProfilesState state;
  final bool reorderOnSelect;
  final List<String> selectedProfileIds = <String>[];

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
      unavailableLocalWorkspaceIds: state.unavailableLocalWorkspaceIds,
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
      unavailableLocalWorkspaceIds: state.unavailableLocalWorkspaceIds
          .difference({workspaceId}),
    );
    return state;
  }

  @override
  Future<WorkspaceProfilesState> clearActiveWorkspaceSelection() async {
    state = state.copyWith(activeWorkspaceId: null);
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
      unavailableLocalWorkspaceIds: state.unavailableLocalWorkspaceIds,
    );
    return state;
  }

  @override
  Future<WorkspaceProfilesState> saveLocalWorkspaceAvailability(
    String workspaceId, {
    required bool isAvailable,
  }) async {
    state = state.copyWith(
      unavailableLocalWorkspaceIds: isAvailable
          ? state.unavailableLocalWorkspaceIds.difference({workspaceId})
          : <String>{...state.unavailableLocalWorkspaceIds, workspaceId},
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
    selectedProfileIds.add(workspaceId);
    if (!reorderOnSelect) {
      state = state.copyWith(activeWorkspaceId: workspaceId);
      return state;
    }
    final selectedIndex = state.profiles.indexWhere(
      (profile) => profile.id == workspaceId,
    );
    if (selectedIndex < 0) {
      state = state.copyWith(activeWorkspaceId: workspaceId);
      return state;
    }
    final selectedProfile = state.profiles[selectedIndex];
    state = WorkspaceProfilesState(
      profiles: [
        selectedProfile.copyWith(lastOpenedAt: DateTime.utc(2026, 5, 20, 12)),
        for (var index = 0; index < state.profiles.length; index += 1)
          if (index != selectedIndex) state.profiles[index],
      ],
      activeWorkspaceId: workspaceId,
      migrationComplete: true,
      unavailableLocalWorkspaceIds: state.unavailableLocalWorkspaceIds,
    );
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
      unavailableLocalWorkspaceIds: state.unavailableLocalWorkspaceIds
          .difference({workspaceId, updated.id}),
    );
    return updated;
  }
}

Future<bool> _focusByTabUntil(
  WidgetTester tester, {
  required bool Function() isFocused,
  int maxTabs = 24,
}) async {
  for (var index = 0; index < maxTabs; index += 1) {
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    if (isFocused()) {
      return true;
    }
  }
  return false;
}

Finder _findSemanticsWithSortOrder({
  required String label,
  required double sortOrder,
  bool? textField,
}) {
  return find.byWidgetPredicate(
    (widget) =>
        widget is Semantics &&
        widget.properties.label == label &&
        widget.properties.sortKey is OrdinalSortKey &&
        (widget.properties.sortKey as OrdinalSortKey).order == sortOrder &&
        (textField == null || widget.properties.textField == textField),
    description:
        'Semantics(label: $label, sortKey: OrdinalSortKey($sortOrder))',
  );
}

Finder _findSemanticsByLabel(String label, {bool? button, bool? textField}) {
  return find.byWidgetPredicate(
    (widget) =>
        widget is Semantics &&
        widget.properties.label == label &&
        (button == null || widget.properties.button == button) &&
        (textField == null || widget.properties.textField == textField),
    description: 'Semantics(label: $label)',
  );
}

Finder _findActionableSemanticsWithSortOrder({
  required String label,
  required double sortOrder,
}) {
  return find.byWidgetPredicate(
    (widget) =>
        widget is Semantics &&
        widget.properties.label == label &&
        widget.properties.sortKey is OrdinalSortKey &&
        (widget.properties.sortKey as OrdinalSortKey).order == sortOrder &&
        widget.properties.onTap != null,
    description:
        'Semantics(label: $label, sortKey: OrdinalSortKey($sortOrder), onTap: set)',
  );
}

Finder _findExplicitWorkspaceSwitcherSemantics(String label) {
  return find.byWidgetPredicate(
    (widget) =>
        widget is Semantics &&
        widget.properties.label == label &&
        widget.properties.button == true,
    description: 'explicit workspace switcher semantics for $label',
  );
}

Future<void> _pumpUntilVisible(
  WidgetTester tester,
  Finder finder, {
  int maxPumps = 60,
  Duration step = const Duration(milliseconds: 100),
}) async {
  for (var index = 0; index < maxPumps; index += 1) {
    await tester.pump(step);
    if (finder.evaluate().isNotEmpty) {
      return;
    }
  }
  throw TestFailure('Expected $finder to become visible.');
}

String? _focusedLabel(WidgetTester tester, Map<String, Finder> candidates) {
  final focusedSemantics = find.semantics.byPredicate(
    (node) => node.getSemanticsData().flagsCollection.isFocused,
    describeMatch: (_) => 'focused semantics node',
  );
  final hasFocusedSemantics = focusedSemantics.evaluate().isNotEmpty;

  for (final entry in candidates.entries) {
    final matches = entry.value.evaluate().length;
    if (matches == 0) {
      continue;
    }
    for (var index = 0; index < matches; index += 1) {
      final candidateFinder = entry.value.at(index);
      if (_focusWithinFinder(tester, candidateFinder)) {
        return entry.key;
      }
      if (hasFocusedSemantics) {
        final candidateSemantics = _semanticsFinderFor(
          tester: tester,
          finder: candidateFinder,
        );
        final ownsFocusedNode = find.semantics.descendant(
          of: candidateSemantics,
          matching: focusedSemantics,
          matchRoot: true,
        );
        if (ownsFocusedNode.evaluate().isNotEmpty) {
          return entry.key;
        }
      }
    }
  }

  return null;
}

bool _focusWithinFinder(WidgetTester tester, Finder ancestorFinder) {
  final focusContext = FocusManager.instance.primaryFocus?.context;
  if (focusContext == null) {
    return false;
  }
  final targetElements = ancestorFinder.evaluate().toSet();
  if (targetElements.contains(focusContext)) {
    return true;
  }
  var found = false;
  focusContext.visitAncestorElements((element) {
    if (targetElements.contains(element)) {
      found = true;
      return false;
    }
    return true;
  });
  return found;
}

FinderBase<SemanticsNode> _semanticsFinderFor({
  required WidgetTester tester,
  required Finder finder,
}) {
  final semanticsId = tester.getSemantics(finder).id;
  return find.semantics.byPredicate(
    (node) => node.id == semanticsId,
    describeMatch: (_) => 'semantics node for $finder',
  );
}

Container _nearestDecoratedContainer(WidgetTester tester, Finder descendant) {
  final candidates = find.ancestor(
    of: descendant,
    matching: find.byWidgetPredicate(
      (widget) =>
          widget is Container &&
          widget.decoration is BoxDecoration &&
          (widget.decoration! as BoxDecoration).color != null,
      description: 'decorated container',
    ),
  );
  return tester.widgetList<Container>(candidates).last;
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

class _LocalQueuedLoadTrackStateRepository
    extends _QueuedLoadTrackStateRepository {
  _LocalQueuedLoadTrackStateRepository({required super.loadResults});

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;
}

class _DelayedConnectTrackStateRepository
    extends ProviderBackedTrackStateRepository {
  _DelayedConnectTrackStateRepository({required TrackerSnapshot snapshot})
    : this._(snapshot: snapshot, provider: _DelayedConnectTrackStateProvider());

  _DelayedConnectTrackStateRepository._({
    required TrackerSnapshot snapshot,
    required _DelayedConnectTrackStateProvider provider,
  }) : _snapshotOverride = snapshot,
       _provider = provider,
       super(provider: provider);

  final TrackerSnapshot _snapshotOverride;
  final _DelayedConnectTrackStateProvider _provider;

  void completeConnect() {
    _provider.completeConnect();
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    replaceCachedState(snapshot: _snapshotOverride);
    return _snapshotOverride;
  }
}

class _DelayedConnectTrackStateProvider implements TrackStateProviderAdapter {
  final Completer<void> _connectCompleter = Completer<void>();
  bool _connected = false;

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'stable/repo';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    await _connectCompleter.future;
    _connected = true;
    return const RepositoryUser(login: 'demo-user', displayName: 'Demo User');
  }

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => RepositoryCommitResult(
    branch: request.branch,
    message: request.message,
    revision: 'mock-revision',
  );

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == 'main');

  @override
  Future<RepositoryPermission> getPermission() async => RepositoryPermission(
    canRead: true,
    canWrite: _connected,
    isAdmin: false,
    canCreateBranch: _connected,
    canManageAttachments: _connected,
    attachmentUploadMode: _connected
        ? AttachmentUploadMode.full
        : AttachmentUploadMode.none,
    supportsReleaseAttachmentWrites: false,
    canCheckCollaborators: false,
  );

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async => RepositorySyncCheck(
    state: RepositorySyncState(
      providerType: providerType,
      repositoryRevision: 'mock-revision',
      sessionRevision: _connected ? 'connected' : 'disconnected',
      connectionState: _connected
          ? ProviderConnectionState.connected
          : ProviderConnectionState.disconnected,
      permission: await getPermission(),
    ),
  );

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async =>
      const <RepositoryTreeEntry>[];

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async => RepositoryAttachment(path: path, bytes: Uint8List(0));

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async => RepositoryTextFile(path: path, content: '');

  @override
  Future<String> resolveWriteBranch() async => 'main';

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async => RepositoryAttachmentWriteResult(
    path: request.path,
    branch: request.branch,
    revision: 'mock-revision',
  );

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async => RepositoryWriteResult(
    path: request.path,
    branch: request.branch,
    revision: 'mock-revision',
  );

  void completeConnect() {
    if (_connectCompleter.isCompleted) {
      return;
    }
    _connectCompleter.complete();
  }
}

class _SyncErrorLocalTrackStateRepository extends DemoTrackStateRepository
    implements WorkspaceSyncRepository {
  const _SyncErrorLocalTrackStateRepository({
    required super.snapshot,
    required this.error,
  });

  final Object error;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async => throw error;
}
