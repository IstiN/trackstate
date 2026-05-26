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
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
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

const List<String> _startupShellNavigationLabels = <String>[
  'Dashboard',
  'Board',
  'JQL Search',
  'Hierarchy',
  'Settings',
];
const String _hostedWorkspaceId = 'hosted:stable/repo@main';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
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

      expect(delayedRepository.loadSnapshotPending, isTrue);
      expect(browserHarness.userProbeRequestCount, 1);
      expect(browserHarness.userProbePending, isTrue);
      expect(browserHarness.requestedPaths, contains('/user'));
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);
      final savedStateAfterStartup = await workspaceProfiles.loadState();
      expect(savedStateAfterStartup.activeWorkspaceId, _hostedWorkspaceId);
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

      expect(delayedRepository.userProbeRequestCount, 1);
      expect(delayedRepository.userProbePending, isTrue);
      expect(delayedRepository.requestedPaths, contains('/user'));
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);
      final savedStateAfterStartup = await workspaceProfiles.loadState();
      expect(savedStateAfterStartup.activeWorkspaceId, _hostedWorkspaceId);
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

      expect(delayedRepository.userProbeRequestCount, 1);
      expect(delayedRepository.userProbePending, isTrue);
      expect(delayedRepository.requestedPaths, contains('/user'));
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

      expect(browserHarness.userProbeRequestCount, 1);
      expect(browserHarness.userProbePending, isTrue);
      expect(browserHarness.requestedPaths, contains('/user'));
      expect(browserHarness.unexpectedConsoleMessages, isEmpty);
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);
      final savedStateAfterStartup = await workspaceProfiles.loadState();
      expect(savedStateAfterStartup.activeWorkspaceId, _hostedWorkspaceId);
      expect(
        savedStateAfterStartup.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
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

      expect(browserHarness.userProbeRequestCount, 1);
      expect(browserHarness.userProbePending, isTrue);
      expect(browserHarness.requestedPaths, contains('/user'));
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      await _expectHostedFallbackWorkspaceRow(tester);
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

      expect(delayedRepository.userProbePending, isTrue);
      _expectRestrictedFallbackShell(delayedRepository);
      _expectHostedFallbackTrigger();
      final savedStateAfterSwitch = await workspaceProfiles.loadState();
      expect(savedStateAfterSwitch.activeWorkspaceId, _hostedWorkspaceId);
      _expectRestrictedFallbackShell(delayedRepository);
      await _expectBlockedCreateIssueGate(tester);
      delayedRepository.completeUserProbe();
      await tester.pump();
      await tester.pumpAndSettle();
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
  final List<String> consoleMessages = <String>[];
  final Completer<web.Response> _userProbeCompleter = Completer<web.Response>();
  bool _installed = false;
  late final JSFunction _previousFetch = _windowFetch;
  late final JSFunction _previousConsoleInfo = _consoleInfo;

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
    _windowFetch = ((JSAny? input, JSAny? init) {
      final requestUrl = (input! as JSString).toDart;
      final path = Uri.parse(requestUrl).path;
      requestedPaths.add(path);
      return switch (path) {
        '/user' => _userProbeCompleter.future.toJS,
        _ => Future<web.Response>.value(_jsonResponse('{}', status: 404)).toJS,
      };
    }).toJS;
    _consoleInfo = ((JSAny? message) {
      consoleMessages.add((message! as JSString).toDart);
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
    _consoleInfo = _previousConsoleInfo;
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

void _expectRestrictedFallbackShell(
  ProviderBackedTrackStateRepository repository,
) {
  _expectShellReadySurface();
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

void _expectHostedFallbackTrigger() {
  expect(
    find.bySemanticsLabel(
      RegExp(r'Workspace switcher: Hosted setup workspace, .*Needs sign-in'),
    ),
    findsWidgets,
  );
}

void _expectShellReadySurface() {
  expect(
    find.byKey(const ValueKey('workspace-switcher-trigger')),
    findsOneWidget,
  );
  for (final label in _startupShellNavigationLabels) {
    expect(find.text(label), findsWidgets);
  }
  expect(find.text('Git-native. Jira-compatible. Team-proven.'), findsWidgets);
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
         hostedStartupProbeTimeout: const Duration(minutes: 1),
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

Future<void> _expectBlockedCreateIssueGate(WidgetTester tester) async {
  await tester.tap(find.text('Create issue').first);
  await tester.pumpAndSettle();
  expect(find.text('GitHub write access is not connected'), findsWidgets);
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
