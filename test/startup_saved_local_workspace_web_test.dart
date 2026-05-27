@TestOn('browser')
library;

import 'dart:async';
import 'dart:convert';
import 'dart:js_interop';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/browser_local_workspace_repository.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/startup_auth_probe_diagnostics.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';
import 'package:web/web.dart' as web;

@JS('window.fetch')
external JSFunction get _windowFetch;

@JS('window.fetch')
external set _windowFetch(JSFunction value);

@JS('console.info')
external JSFunction get _consoleInfo;

@JS('console.info')
external set _consoleInfo(JSFunction value);

const String _hostedWorkspaceId = 'hosted:stable/repo@main';
const List<String> _shellNavigationLabels = <String>[
  'Dashboard',
  'Board',
  'JQL Search',
  'Hierarchy',
  'Settings',
];
final List<String> _startupDiagnosticMessages = <String>[];

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await clearRememberedBrowserLocalWorkspaceSelections();
    addTearDown(() => clearRememberedBrowserLocalWorkspaceSelections());
    _startupDiagnosticMessages.clear();
    final previousDiagnostics = startupAuthProbeDiagnostics;
    startupAuthProbeDiagnostics = StartupAuthProbeDiagnostics(
      logger: _startupDiagnosticMessages.add,
    );
    addTearDown(() {
      startupAuthProbeDiagnostics = previousDiagnostics;
      _startupDiagnosticMessages.clear();
    });
  });

  testWidgets(
    'web startup switches into the hosted fallback workspace before a slow hosted load completes',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken('github-token', repository: 'stable/repo');

      final delayedRepository = _SlowBrowserStartupAuthProbeRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );
      final browserHarness = _BrowserStartupAuthProbeHarness()..install();

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        browserHarness.dispose();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => delayedRepository,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();

      expect(delayedRepository.loadSnapshotPending, isTrue);
      expect(browserHarness.userProbeRequestCount, 1);
      expect(browserHarness.userProbePending, isTrue);
      expect(browserHarness.requestedPaths, contains('/user'));
      _expectRuntimeStartupFallbackSignal(
        authPending: browserHarness.userProbePending,
        consoleMessages: browserHarness.consoleMessages,
      );
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);
      final savedStateAfterStartup = await workspaceProfiles.loadState();
      _expectHostedFallbackWorkspaceState(savedStateAfterStartup);
      expect(
        savedStateAfterStartup.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
    },
  );

  testWidgets(
    'web startup switches to the hosted fallback workspace when the browser handle is missing and opens the shell fallback',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken('github-token', repository: 'stable/repo');

      final delayedRepository = _DelayedGitHubProbeRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => delayedRepository,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();

      expect(delayedRepository.userProbeRequestCount, 1);
      expect(delayedRepository.userProbePending, isTrue);
      expect(delayedRepository.requestedPaths, contains('/user'));
      _expectRuntimeStartupFallbackSignal(
        authPending: delayedRepository.userProbePending,
      );
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);
      final savedStateAfterStartup = await workspaceProfiles.loadState();
      _expectHostedFallbackWorkspaceState(savedStateAfterStartup);
      expect(
        savedStateAfterStartup.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
      delayedRepository.completeUserProbe();
      await tester.pump();
      await tester.pumpAndSettle();
    },
  );

  testWidgets(
    'web startup keeps the workspace switcher open when the browser handle is missing and no hosted token exists',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );

      var hostedRepositoryOpened = false;

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openBrowserLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => null,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async {
                hostedRepositoryOpened = true;
                return const DemoTrackStateRepository();
              },
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('workspace-switcher-sheet')),
        findsOneWidget,
      );
      expect(
        find.bySemanticsLabel(
          RegExp(
            r'Workspace switcher: Hosted setup workspace, .*Needs sign-in',
          ),
        ),
        findsNothing,
      );
      final localRow = find.byKey(
        const ValueKey('workspace-$activeLocalWorkspaceId'),
      );
      expect(localRow, findsOneWidget);
      expect(
        find.descendant(of: localRow, matching: find.text('Unavailable')),
        findsWidgets,
      );
      expect(
        find.descendant(of: localRow, matching: find.text('Retry')),
        findsWidgets,
      );
      expect(hostedRepositoryOpened, isFalse);

      final savedStateAfterStartup = await workspaceProfiles.loadState();
      expect(savedStateAfterStartup.activeWorkspaceId, isNull);
      expect(
        savedStateAfterStartup.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
    },
  );

  testWidgets(
    'web startup commits the hosted fallback shell before workspace persistence finishes for preserved local restore',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final persistedProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      final workspaceProfiles = _DelayedSelectWorkspaceProfileService(
        persistedProfiles,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken('github-token', repository: 'stable/repo');

      final delayedRepository = _DelayedGitHubProbeRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openBrowserLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => null,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => delayedRepository,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();
      for (
        var index = 0;
        index < 20 &&
            find
                .bySemanticsLabel(
                  RegExp(
                    r'Workspace switcher: Hosted setup workspace, .*Needs sign-in',
                  ),
                )
                .evaluate()
                .isEmpty;
        index += 1
      ) {
        await tester.pump(const Duration(milliseconds: 100));
      }

      expect(workspaceProfiles.selectProfilePending, isTrue);
      expect(delayedRepository.userProbePending, isTrue);
      _expectRuntimeStartupFallbackSignal(
        authPending: delayedRepository.userProbePending,
      );
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);
      await _expectBlockedCreateIssueGate(tester);

      final persistedStateBeforeSelection = await persistedProfiles.loadState();
      expect(
        persistedStateBeforeSelection.activeWorkspaceId,
        activeLocalWorkspaceId,
      );

      workspaceProfiles.completeSelectProfile();
      await tester.pump();
      await tester.pumpAndSettle();

      final persistedStateAfterSelection = await persistedProfiles.loadState();
      _expectHostedFallbackWorkspaceState(persistedStateAfterSelection);
      expect(
        persistedStateAfterSelection.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
    },
  );

  testWidgets(
    'web startup completes the delayed /user probe after opening the shell fallback for a missing browser handle',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken('github-token', repository: 'stable/repo');

      final delayedRepository = _DelayedGitHubProbeRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => delayedRepository,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();

      expect(delayedRepository.userProbeRequestCount, 1);
      expect(delayedRepository.userProbePending, isTrue);
      expect(delayedRepository.requestedPaths, contains('/user'));
      _expectRuntimeStartupFallbackSignal(
        authPending: delayedRepository.userProbePending,
      );
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);
      delayedRepository.completeUserProbe();
      await tester.pump();
      await tester.pumpAndSettle();

      expect(
        delayedRepository.session?.connectionState,
        ProviderConnectionState.connected,
      );
      expect(delayedRepository.session?.canWrite, isTrue);
      expect(delayedRepository.session?.canCreateBranch, isTrue);
      final savedStateAfterStartup = await workspaceProfiles.loadState();
      expect(savedStateAfterStartup.activeWorkspaceId, _hostedWorkspaceId);
      expect(
        savedStateAfterStartup.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
    },
  );

  testWidgets(
    'web startup starts the real browser /user probe after switching into the hosted fallback shell for a missing browser handle',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken('github-token', repository: 'stable/repo');

      final delayedRepository = _BrowserStartupAuthProbeRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );
      final browserHarness = _BrowserStartupAuthProbeHarness()..install();

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        browserHarness.dispose();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => delayedRepository,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();

      expect(browserHarness.userProbeRequestCount, 1);
      expect(browserHarness.userProbePending, isTrue);
      expect(browserHarness.requestedPaths, contains('/user'));
      expect(browserHarness.unexpectedConsoleMessages, isEmpty);
      _expectRuntimeStartupFallbackSignal(
        authPending: browserHarness.userProbePending,
        consoleMessages: browserHarness.consoleMessages,
      );
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);
      final savedStateAfterStartup = await workspaceProfiles.loadState();
      _expectHostedFallbackWorkspaceState(savedStateAfterStartup);
      expect(
        savedStateAfterStartup.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
      browserHarness.completeUserProbe();
      await tester.pump(const Duration(seconds: 11));
      await tester.pumpAndSettle();
    },
  );

  testWidgets(
    'web startup switches into the hosted fallback workspace after a restored local sync error while /user remains pending',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken('github-token', repository: 'stable/repo');

      final delayedRepository = _DelayedGitHubProbeRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );
      final localRepository = _SyncErrorLocalTrackStateRepository(
        snapshot: await _snapshotForRepository('IstiN/trackstate-setup'),
        error: StateError(
          'Saved workspace path no longer matches the expected TrackState repository.',
        ),
      );

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openBrowserLocalRepository:
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
              }) async => delayedRepository,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();

      var savedStateAfterStartup = await workspaceProfiles.loadState();
      for (
        var index = 0;
        index < 20 &&
            savedStateAfterStartup.activeWorkspaceId != _hostedWorkspaceId;
        index += 1
      ) {
        await tester.pump(const Duration(milliseconds: 100));
        savedStateAfterStartup = await workspaceProfiles.loadState();
      }

      expect(delayedRepository.userProbeRequestCount, 1);
      expect(delayedRepository.userProbePending, isTrue);
      expect(delayedRepository.requestedPaths, contains('/user'));
      _expectRuntimeStartupFallbackSignal(
        authPending: delayedRepository.userProbePending,
      );
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);
      await _expectBlockedCreateIssueGate(tester);
      _expectHostedFallbackWorkspaceState(savedStateAfterStartup);
      expect(
        savedStateAfterStartup.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
    },
  );

  testWidgets(
    'web startup keeps the restored active local workspace selected when an inactive saved workspace fails revalidation',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const inactiveLocalWorkspaceId = 'local:/tmp/trackstate-broken@main';
      const activeLocalWorkspacePath = '/tmp/trackstate-demo';
      const inactiveLocalWorkspacePath = '/tmp/trackstate-broken';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: activeLocalWorkspacePath,
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: inactiveLocalWorkspacePath,
          defaultBranch: 'main',
          displayName: 'Broken inactive workspace',
        ),
        select: false,
      );

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openBrowserLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async {
                if (repositoryPath == activeLocalWorkspacePath) {
                  return DemoTrackStateRepository(
                    snapshot: await _snapshotForRepository(repositoryPath),
                  );
                }
                if (repositoryPath == inactiveLocalWorkspacePath) {
                  throw StateError(
                    'Saved workspace path no longer matches the expected TrackState repository.',
                  );
                }
                return null;
              },
        ),
      );
      await tester.pump();
      for (var index = 0; index < 20; index += 1) {
        await tester.pump(const Duration(milliseconds: 100));
      }

      final savedStateAfterStartup = await workspaceProfiles.loadState();
      expect(savedStateAfterStartup.activeWorkspaceId, activeLocalWorkspaceId);
      expect(
        savedStateAfterStartup.unavailableLocalWorkspaceIds,
        contains(inactiveLocalWorkspaceId),
      );
      expect(
        savedStateAfterStartup.unavailableLocalWorkspaceIds,
        isNot(contains(activeLocalWorkspaceId)),
      );

      await tester.tap(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
      );
      await tester.pump();
      for (var index = 0; index < 10; index += 1) {
        await tester.pump(const Duration(milliseconds: 100));
      }

      final activeRow = find.byKey(
        const ValueKey('workspace-$activeLocalWorkspaceId'),
      );
      expect(activeRow, findsOneWidget);
      expect(
        find.descendant(of: activeRow, matching: find.text('Active')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: activeRow, matching: find.text('Local Git')),
        findsWidgets,
      );
      expect(
        find.descendant(of: activeRow, matching: find.text('Unavailable')),
        findsNothing,
      );

      final brokenRow = find.byKey(
        const ValueKey('workspace-$inactiveLocalWorkspaceId'),
      );
      expect(brokenRow, findsOneWidget);
      expect(
        find.descendant(of: brokenRow, matching: find.text('Unavailable')),
        findsWidgets,
      );
    },
  );

  testWidgets(
    'web startup opens the preserved local shell within the timeout while the real delayed /user probe is still pending',
    (tester) async {
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken('github-token', repository: 'stable/repo');

      final delayedRepository = _BrowserStartupAuthProbeRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );
      final browserHarness = _BrowserStartupAuthProbeHarness()..install();

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        browserHarness.dispose();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => delayedRepository,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();

      expect(browserHarness.userProbeRequestCount, 1);
      expect(browserHarness.userProbePending, isTrue);
      expect(browserHarness.requestedPaths, contains('/user'));
      _expectRuntimeStartupFallbackSignal(
        authPending: browserHarness.userProbePending,
        consoleMessages: browserHarness.consoleMessages,
      );
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);
      browserHarness.completeUserProbe();
      await tester.pump();
      await tester.pumpAndSettle();
    },
  );

  testWidgets(
    'web startup keeps the hosted fallback workspace trigger stable after delayed /user probe completion',
    (tester) async {
      const fallbackTriggerLabel =
          'Workspace switcher: Hosted setup workspace, Hosted, Needs sign-in';
      const connectedTriggerLabel =
          'Workspace switcher: Hosted setup workspace, Hosted, Connected';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken('github-token', repository: 'stable/repo');

      final delayedRepository = _BrowserStartupAuthProbeRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );
      final browserHarness = _BrowserStartupAuthProbeHarness()..install();

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        browserHarness.dispose();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => delayedRepository,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();

      _expectRuntimeStartupFallbackSignal(
        authPending: browserHarness.userProbePending,
        consoleMessages: browserHarness.consoleMessages,
      );
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();

      final trigger = find.byKey(const ValueKey('workspace-switcher-trigger'));
      expect(trigger, findsOneWidget);
      expect(
        find.descendant(of: trigger, matching: find.bySemanticsLabel(fallbackTriggerLabel)),
        findsWidgets,
      );

      browserHarness.completeUserProbe();
      await tester.pump();
      await tester.pumpAndSettle();

      expect(
        find.descendant(of: trigger, matching: find.bySemanticsLabel(fallbackTriggerLabel)),
        findsWidgets,
      );
      expect(
        find.descendant(of: trigger, matching: find.bySemanticsLabel(connectedTriggerLabel)),
        findsNothing,
      );
    },
  );

  testWidgets(
    'web startup commits the preserved local shell before the initial hosted search finishes',
    (tester) async {
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken('github-token', repository: 'stable/repo');

      final delayedRepository = _SearchBlockingBrowserStartupRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        delayedRepository.completeInitialSearch();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => delayedRepository,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();

      expect(delayedRepository.initialSearchRequestCount, 1);
      expect(delayedRepository.initialSearchPending, isTrue);
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);

      delayedRepository.completeInitialSearch();
      await tester.pump();
      await tester.pumpAndSettle();
    },
  );

  testWidgets(
    'web startup switches into the hosted fallback workspace and keeps Create issue fully gated while /user remains pending',
    (tester) async {
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken('github-token', repository: 'stable/repo');

      final delayedRepository = _DelayedGitHubProbeRepository(
        snapshot: await _snapshotForRepository('stable/repo'),
      );

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => delayedRepository,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();

      expect(delayedRepository.userProbePending, isTrue);
      _expectRuntimeStartupFallbackSignal(
        authPending: delayedRepository.userProbePending,
      );
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      final savedStateAfterSwitch = await workspaceProfiles.loadState();
      _expectHostedFallbackWorkspaceState(savedStateAfterSwitch);
      _expectRuntimeStartupFallbackSignal(
        authPending: delayedRepository.userProbePending,
      );
      _expectRestrictedFallbackShell(delayedRepository);
      await _expectBlockedCreateIssueGate(tester);
      delayedRepository.completeUserProbe();
      await tester.pump();
      await tester.pumpAndSettle();
    },
  );

  testWidgets(
    'web startup reaches the browser shell-ready contract on the default hosted loader while /user remains pending',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
          displayName: 'Active local workspace',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
        select: false,
      );
      await authStore.saveToken('github-token', repository: 'stable/repo');

      final browserHarness = _RealHostedBrowserFetchHarness()..install();

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        browserHarness.dispose();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();

      expect(browserHarness.userProbeRequestCount, 1);
      expect(browserHarness.userProbePending, isTrue);
      expect(browserHarness.requestedPaths, contains('/user'));
      expect(
        browserHarness.requestedPaths,
        contains('/repos/stable/repo/git/trees/main'),
      );
      _expectBrowserObservedShellReady(
        authPending: browserHarness.userProbePending,
        consoleMessages: browserHarness.consoleMessages,
      );
      expect(find.text('Connect GitHub'), findsWidgets);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);
      await _expectBlockedCreateIssueGate(tester);
      final savedStateAfterStartup = await workspaceProfiles.loadState();
      _expectHostedFallbackWorkspaceState(savedStateAfterStartup);
      expect(
        savedStateAfterStartup.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
      browserHarness.completeUserProbe();
      await tester.pump(const Duration(seconds: 11));
      await tester.pumpAndSettle();
      _expectHostedFallbackTrigger();
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

class _BrowserStartupAuthProbeProvider extends GitHubTrackStateProvider {
  _BrowserStartupAuthProbeProvider()
    : super(repositoryName: 'stable/repo', dataRef: 'main', sourceRef: 'main');

  bool _authenticated = false;

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    final user = await super.authenticate(connection);
    _authenticated = true;
    return user;
  }

  @override
  Future<RepositoryPermission> getPermission() async => RepositoryPermission(
    canRead: true,
    canWrite: _authenticated,
    isAdmin: false,
    supportsReleaseAttachmentWrites: false,
  );
}

class _DelayedGitHubProbeRepository extends ProviderBackedTrackStateRepository {
  _DelayedGitHubProbeRepository({required TrackerSnapshot snapshot})
    : this._(snapshot: snapshot, harness: _DelayedGitHubProbeHarness());

  _DelayedGitHubProbeRepository._({
    required TrackerSnapshot snapshot,
    required _DelayedGitHubProbeHarness harness,
  }) : _snapshotOverride = snapshot,
       _harness = harness,
       super(
         provider: GitHubTrackStateProvider(
           client: MockClient(harness.handle),
           repositoryName: 'stable/repo',
           dataRef: 'main',
           sourceRef: 'main',
         ),
       );

  final TrackerSnapshot _snapshotOverride;
  final _DelayedGitHubProbeHarness _harness;

  List<String> get requestedPaths => _harness.requestedPaths;
  int get userProbeRequestCount => _harness.userProbeRequestCount;
  bool get userProbePending => _harness.userProbePending;

  void completeUserProbe() {
    _harness.completeUserProbe();
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    replaceCachedState(snapshot: _snapshotOverride);
    return _snapshotOverride;
  }
}

class _DelayedGitHubProbeHarness {
  final Completer<void> _userProbeCompleter = Completer<void>();
  final List<String> requestedPaths = <String>[];
  int userProbeRequestCount = 0;
  bool get userProbePending =>
      userProbeRequestCount > 0 && !_userProbeCompleter.isCompleted;

  Future<http.Response> handle(http.Request request) async {
    requestedPaths.add(request.url.path);
    switch (request.url.path) {
      case '/repos/stable/repo':
        return http.Response(
          jsonEncode({
            'full_name': 'stable/repo',
            'permissions': <String, Object?>{
              'pull': true,
              'push': true,
              'admin': false,
            },
          }),
          200,
        );
      case '/repos/stable/repo/branches/main':
        return http.Response(
          jsonEncode({
            'name': 'main',
            'commit': <String, Object?>{'sha': 'mock-revision'},
          }),
          200,
        );
      case '/user':
        userProbeRequestCount += 1;
        await _userProbeCompleter.future;
        return http.Response(
          jsonEncode({
            'login': 'demo-user',
            'name': 'Demo User',
            'id': 1,
            'email': 'demo@example.com',
          }),
          200,
        );
    }
    throw StateError('Unexpected request: ${request.method} ${request.url}');
  }

  void completeUserProbe() {
    if (_userProbeCompleter.isCompleted) {
      return;
    }
    _userProbeCompleter.complete();
  }
}

class _BrowserStartupAuthProbeRepository
    extends ProviderBackedTrackStateRepository {
  _BrowserStartupAuthProbeRepository({required TrackerSnapshot snapshot})
    : this._(snapshot: snapshot, provider: _BrowserStartupAuthProbeProvider());

  _BrowserStartupAuthProbeRepository._({
    required TrackerSnapshot snapshot,
    required _BrowserStartupAuthProbeProvider provider,
  }) : _snapshotOverride = snapshot,
       super(provider: provider);

  final TrackerSnapshot _snapshotOverride;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    replaceCachedState(snapshot: _snapshotOverride);
    return _snapshotOverride;
  }
}

class _SearchBlockingBrowserStartupRepository
    extends _BrowserStartupAuthProbeRepository {
  _SearchBlockingBrowserStartupRepository({required super.snapshot});

  final Completer<void> _initialSearchCompleter = Completer<void>();
  int initialSearchRequestCount = 0;
  bool get initialSearchPending =>
      initialSearchRequestCount > 0 && !_initialSearchCompleter.isCompleted;

  void completeInitialSearch() {
    if (_initialSearchCompleter.isCompleted) {
      return;
    }
    _initialSearchCompleter.complete();
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    initialSearchRequestCount += 1;
    await _initialSearchCompleter.future;
    return super.searchIssuePage(
      jql,
      startAt: startAt,
      maxResults: maxResults,
      continuationToken: continuationToken,
    );
  }
}

class _BrowserStartupAuthProbeHarness {
  _BrowserStartupAuthProbeHarness();

  final List<String> requestedPaths = <String>[];
  final _ConsoleInfoCapture _consoleInfoCapture = _ConsoleInfoCapture();
  final Completer<web.Response> _userProbeCompleter = Completer<web.Response>();
  bool _installed = false;
  late final JSFunction _previousFetch = _windowFetch;

  List<String> get consoleMessages => _consoleInfoCapture.consoleMessages;

  int get userProbeRequestCount =>
      requestedPaths.where((path) => path == '/user').length;
  bool get userProbePending =>
      userProbeRequestCount > 0 && !_userProbeCompleter.isCompleted;
  List<String> get unexpectedConsoleMessages => consoleMessages
      .where(
        (message) =>
            !message.startsWith('TrackState startup diagnostic:') &&
            !message.startsWith('TrackState startup fallback diagnostic:'),
      )
      .toList(growable: false);

  void install() {
    if (_installed) {
      return;
    }
    _installed = true;
    _consoleInfoCapture.install();
    _windowFetch = ((JSAny? input, JSAny? init) {
      final requestUrl = (input! as JSString).toDart;
      final path = Uri.parse(requestUrl).path;
      requestedPaths.add(path);
      return switch (path) {
        '/user' => _userProbeCompleter.future.toJS,
        _ => Future<web.Response>.value(_jsonResponse('{}', status: 404)).toJS,
      };
    }).toJS;
  }

  void completeUserProbe() {
    if (_userProbeCompleter.isCompleted) {
      return;
    }
    _userProbeCompleter.complete(
      _jsonResponse(
        jsonEncode({
          'login': 'demo-user',
          'name': 'Demo User',
          'id': 1,
          'email': 'demo@example.com',
        }),
      ),
    );
  }

  void dispose() {
    if (!_installed) {
      return;
    }
    _windowFetch = _previousFetch;
    _consoleInfoCapture.dispose();
    completeUserProbe();
  }

  web.Response _jsonResponse(String body, {int status = 200}) {
    return web.Response(
      body.toJS,
      web.ResponseInit(
        status: status,
        headers: web.Headers()..set('content-type', 'application/json'),
      ),
    );
  }
}

extension type _FetchRequestUrlAccessor._(JSObject _value) implements JSObject {
  external JSString get url;
}

class _RealHostedBrowserFetchHarness {
  _RealHostedBrowserFetchHarness();

  final _RealHostedStartupDelayedAuthHarness _delegate =
      _RealHostedStartupDelayedAuthHarness();
  final _ConsoleInfoCapture _consoleInfoCapture = _ConsoleInfoCapture();
  bool _installed = false;
  late final JSFunction _previousFetch = _windowFetch;

  List<String> get requestedPaths => _delegate.requestedPaths;
  int get userProbeRequestCount => _delegate.userProbeRequestCount;
  bool get userProbePending => _delegate.userProbePending;
  List<String> get consoleMessages => _consoleInfoCapture.consoleMessages;

  void install() {
    if (_installed) {
      return;
    }
    _installed = true;
    _consoleInfoCapture.install();
    _windowFetch = ((JSAny? input, JSAny? init) {
      final requestUrl = _requestUrl(input);
      if (requestUrl.isEmpty) {
        return Future<web.Response>.value(
          _jsonResponse('{}', status: 404),
        ).toJS;
      }
      final uri = Uri.parse(requestUrl);
      return _delegate
          .handle(http.Request('GET', uri))
          .then(
            (response) =>
                _jsonResponse(response.body, status: response.statusCode),
          )
          .toJS;
    }).toJS;
  }

  void completeUserProbe() {
    _delegate.completeUserProbe();
  }

  void dispose() {
    if (!_installed) {
      return;
    }
    _windowFetch = _previousFetch;
    _consoleInfoCapture.dispose();
    _delegate.completeUserProbe();
  }

  String _requestUrl(JSAny? input) {
    if (input == null) {
      return '';
    }
    try {
      return (input as JSString).toDart;
    } on Object {
      try {
        return _FetchRequestUrlAccessor._(input as JSObject).url.toDart;
      } on Object {
        return '';
      }
    }
  }

  web.Response _jsonResponse(String body, {int status = 200}) {
    return web.Response(
      body.toJS,
      web.ResponseInit(
        status: status,
        headers: web.Headers()..set('content-type', 'application/json'),
      ),
    );
  }
}

class _ConsoleInfoCapture {
  final List<String> consoleMessages = <String>[];
  bool _installed = false;
  late final JSFunction _previousConsoleInfo = _consoleInfo;

  void install() {
    if (_installed) {
      return;
    }
    _installed = true;
    _consoleInfo = ((JSAny? message) {
      consoleMessages.add((message! as JSString).toDart);
    }).toJS;
  }

  void dispose() {
    if (!_installed) {
      return;
    }
    _consoleInfo = _previousConsoleInfo;
    _installed = false;
  }
}

void _expectRestrictedFallbackShell(
  ProviderBackedTrackStateRepository repository,
) {
  expect(find.byType(CircularProgressIndicator), findsNothing);
  expect(find.text('Connect GitHub'), findsWidgets);
  expect(repository.session, isNotNull);
  expect(
    repository.session?.connectionState,
    isNot(ProviderConnectionState.connected),
  );
  expect(repository.session?.canWrite, isFalse);
  expect(repository.session?.canCreateBranch, isFalse);
}

void _expectRuntimeStartupFallbackSignal({
  required bool authPending,
  Iterable<String>? consoleMessages,
}) {
  _expectBrowserObservedShellReady(
    authPending: authPending,
    consoleMessages: consoleMessages,
    expectStartupDiagnostic: true,
  );
}

void _expectHostedFallbackTrigger() {
  expect(
    find.bySemanticsLabel(
      RegExp(r'Workspace switcher: Hosted setup workspace, .*Needs sign-in'),
    ),
    findsWidgets,
  );
  expect(
    find.bySemanticsLabel(
      RegExp(r'Workspace switcher: Active local workspace, .*Unavailable'),
    ),
    findsNothing,
  );
}

void _expectBrowserObservedShellReady({
  required bool authPending,
  Iterable<String>? consoleMessages,
  bool expectStartupDiagnostic = false,
}) {
  if (expectStartupDiagnostic) {
    final shellReadyObserved =
        _startupDiagnosticMessages.any(
          (message) =>
              message.startsWith('TrackState startup fallback diagnostic:') &&
              message.contains('shell_ready transition after timeout fallback'),
        ) ||
        (consoleMessages?.any(
              (message) =>
                  message.startsWith(
                    'TrackState startup fallback diagnostic:',
                  ) &&
                  message.contains(
                    'shell_ready transition after timeout fallback',
                  ),
            ) ??
            false);
    expect(
      shellReadyObserved,
      isTrue,
      reason:
          'Expected the startup flow to emit the fallback shell_ready diagnostic before auth finished.',
    );
  }
  expect(
    authPending,
    isTrue,
    reason:
        'Expected the browser regression to observe the startup shell contract while the delayed /user probe was still pending.',
  );
  final visibleNavigationLabels = <String>[
    for (final label in _shellNavigationLabels)
      if (find.text(label).evaluate().isNotEmpty) label,
  ];
  expect(
    visibleNavigationLabels,
    orderedEquals(_shellNavigationLabels),
    reason:
        'Expected the same browser-observed shell_ready contract used by TS-1001: all navigation labels must be visible while auth is still pending.',
  );
  expect(
    find.byKey(const ValueKey('workspace-switcher-trigger')),
    findsOneWidget,
    reason:
        'Expected the mounted header workspace trigger to be visible while the delayed auth probe remains pending.',
  );
  expect(find.text('Git-native. Jira-compatible. Team-proven.'), findsWidgets);
  for (final label in _shellNavigationLabels) {
    expect(find.text(label), findsWidgets);
  }
}

class _DelayedSelectWorkspaceProfileService implements WorkspaceProfileService {
  _DelayedSelectWorkspaceProfileService(this._delegate);

  final WorkspaceProfileService _delegate;
  final Completer<void> _selectProfileCompleter = Completer<void>();
  bool _selectProfileStarted = false;

  bool get selectProfilePending =>
      _selectProfileStarted && !_selectProfileCompleter.isCompleted;

  void completeSelectProfile() {
    if (_selectProfileCompleter.isCompleted) {
      return;
    }
    _selectProfileCompleter.complete();
  }

  @override
  Future<WorkspaceProfilesState> clearActiveWorkspaceSelection() =>
      _delegate.clearActiveWorkspaceSelection();

  @override
  Future<WorkspaceProfile> createProfile(
    WorkspaceProfileInput input, {
    bool select = true,
  }) => _delegate.createProfile(input, select: select);

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) =>
      _delegate.deleteProfile(workspaceId);

  @override
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  ) => _delegate.ensureLegacyContextMigrated(input);

  @override
  Future<WorkspaceProfilesState> loadState() => _delegate.loadState();

  @override
  Future<WorkspaceProfilesState> saveHostedAccessMode(
    String workspaceId,
    HostedWorkspaceAccessMode? accessMode,
  ) => _delegate.saveHostedAccessMode(workspaceId, accessMode);

  @override
  Future<WorkspaceProfilesState> saveLocalWorkspaceAvailability(
    String workspaceId, {
    required bool isAvailable,
  }) => _delegate.saveLocalWorkspaceAvailability(
    workspaceId,
    isAvailable: isAvailable,
  );

  @override
  Future<WorkspaceProfilesState> selectProfile(String workspaceId) async {
    _selectProfileStarted = true;
    await _selectProfileCompleter.future;
    return _delegate.selectProfile(workspaceId);
  }

  @override
  Future<WorkspaceProfile> updateProfile(
    String workspaceId,
    WorkspaceProfileInput input, {
    bool select = true,
  }) => _delegate.updateProfile(workspaceId, input, select: select);
}

class _SlowBrowserStartupAuthProbeRepository
    extends ProviderBackedTrackStateRepository {
  _SlowBrowserStartupAuthProbeRepository({required TrackerSnapshot snapshot})
    : this._(snapshot: snapshot, provider: _BrowserStartupAuthProbeProvider());

  _SlowBrowserStartupAuthProbeRepository._({
    required TrackerSnapshot snapshot,
    required _BrowserStartupAuthProbeProvider provider,
  }) : _snapshotOverride = snapshot,
       super(
         provider: provider,
         hostedStartupProbeTimeout: const Duration(seconds: 11),
       );

  final TrackerSnapshot _snapshotOverride;
  final Completer<void> _loadSnapshotCompleter = Completer<void>();
  bool _loadSnapshotStarted = false;

  bool get loadSnapshotPending =>
      _loadSnapshotStarted && !_loadSnapshotCompleter.isCompleted;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    _loadSnapshotStarted = true;
    await _loadSnapshotCompleter.future;
    replaceCachedState(snapshot: _snapshotOverride);
    return _snapshotOverride;
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

class _RealHostedStartupDelayedAuthHarness {
  final Completer<http.Response> _userProbeCompleter =
      Completer<http.Response>();
  final List<String> requestedPaths = <String>[];

  int get userProbeRequestCount =>
      requestedPaths.where((path) => path == '/user').length;
  bool get userProbePending =>
      userProbeRequestCount > 0 && !_userProbeCompleter.isCompleted;

  void completeUserProbe() {
    if (_userProbeCompleter.isCompleted) {
      return;
    }
    _userProbeCompleter.complete(
      http.Response(
        jsonEncode({
          'login': 'demo-user',
          'name': 'Demo User',
          'id': 1,
          'email': 'demo@example.com',
        }),
        200,
      ),
    );
  }

  Future<http.Response> handle(http.Request request) async {
    final path = request.url.path;
    final ref = request.url.queryParameters['ref'] ?? '';
    requestedPaths.add(path);
    switch (path) {
      case '/repos/stable/repo':
        return http.Response(
          jsonEncode({
            'full_name': 'stable/repo',
            'permissions': <String, Object?>{
              'pull': true,
              'push': true,
              'admin': false,
            },
          }),
          200,
        );
      case '/user':
        return _userProbeCompleter.future;
      case '/repos/stable/repo/branches/main':
        return http.Response(
          jsonEncode({
            'name': 'main',
            'commit': <String, Object?>{'sha': 'mock-revision'},
          }),
          200,
        );
      case '/repos/stable/repo/git/trees/main':
        return http.Response(
          jsonEncode({
            'tree': [
              {'path': 'DEMO/project.json', 'type': 'blob'},
              {'path': 'DEMO/config/statuses.json', 'type': 'blob'},
              {'path': 'DEMO/config/issue-types.json', 'type': 'blob'},
              {'path': 'DEMO/config/fields.json', 'type': 'blob'},
              {'path': 'DEMO/.trackstate/index/issues.json', 'type': 'blob'},
              {'path': 'DEMO/DEMO-1/main.md', 'type': 'blob'},
            ],
          }),
          200,
        );
      case '/repos/stable/repo/contents/DEMO/project.json':
        expect(ref, 'main');
        return _contentResponse(
          jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
            'defaultLocale': 'en',
          }),
        );
      case '/repos/stable/repo/contents/DEMO/config/statuses.json':
        return _contentResponse(
          jsonEncode([
            {'id': 'todo', 'name': 'To Do'},
          ]),
        );
      case '/repos/stable/repo/contents/DEMO/config/issue-types.json':
        return _contentResponse(
          jsonEncode([
            {'id': 'story', 'name': 'Story'},
          ]),
        );
      case '/repos/stable/repo/contents/DEMO/config/fields.json':
        return _contentResponse(
          jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
          ]),
        );
      case '/repos/stable/repo/contents/DEMO/.trackstate/index/issues.json':
        return _contentResponse(
          jsonEncode([
            {
              'key': 'DEMO-1',
              'path': 'DEMO/DEMO-1/main.md',
              'parent': null,
              'epic': null,
              'summary': 'Indexed markdown issue',
              'issueType': 'story',
              'status': 'todo',
              'labels': [],
              'updated': '2026-05-05T00:05:00Z',
              'children': [],
              'archived': false,
            },
          ]),
        );
    }
    throw StateError('Unexpected request: ${request.method} ${request.url}');
  }

  http.Response _contentResponse(String content) {
    return http.Response(
      jsonEncode({
        'content': base64Encode(utf8.encode(content)),
        'encoding': 'base64',
        'sha': 'mock-revision',
      }),
      200,
    );
  }
}

Future<void> _expectHostedFallbackWorkspaceRow(WidgetTester tester) async {
  await tester.tap(find.byKey(const ValueKey('workspace-switcher-trigger')));
  await tester.pumpAndSettle();
  final hostedRow = find.byKey(const ValueKey('workspace-$_hostedWorkspaceId'));
  expect(hostedRow, findsOneWidget);
  expect(
    find.descendant(of: hostedRow, matching: find.text('Needs sign-in')),
    findsWidgets,
  );
  await tester.tapAt(const Offset(8, 8));
  await tester.pumpAndSettle();
}

void _expectHostedFallbackWorkspaceState(WorkspaceProfilesState state) {
  expect(state.activeWorkspaceId, _hostedWorkspaceId);
  final hostedWorkspace = state.profiles.firstWhere(
    (workspace) => workspace.id == _hostedWorkspaceId,
  );
  expect(
    hostedWorkspace.hostedAccessMode,
    HostedWorkspaceAccessMode.disconnected,
  );
}

Future<void> _expectBlockedCreateIssueGate(WidgetTester tester) async {
  await tester.tap(find.text('Create issue').first);
  await tester.pumpAndSettle();
  expect(find.text('GitHub write access is not connected'), findsWidgets);
  expect(
    find.text('Current session flags: canWrite=false, canCreateBranch=false.'),
    findsWidgets,
  );
  expect(
    find.byWidgetPredicate(
      (widget) =>
          widget is TextField && widget.decoration?.labelText == 'Summary',
    ),
    findsNothing,
  );
  expect(find.widgetWithText(FilledButton, 'Save'), findsNothing);
  expect(find.widgetWithText(OutlinedButton, 'Open settings'), findsOneWidget);
  expect(find.widgetWithText(OutlinedButton, 'Cancel'), findsOneWidget);
  await tester.tap(find.widgetWithText(OutlinedButton, 'Cancel'));
  await tester.pumpAndSettle();
}
