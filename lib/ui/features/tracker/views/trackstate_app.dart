import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/foundation.dart' show kIsWeb, listEquals;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart';
import '../../../../../data/repositories/browser_local_workspace_repository.dart';
import '../../../../../data/repositories/local_trackstate_repository.dart';
import '../../../../../data/repositories/trackstate_repository.dart';
import '../../../../../data/repositories/trackstate_repository_factory.dart';
import '../../../../../data/providers/trackstate_provider.dart';
import '../../../../../data/services/local_workspace_onboarding_service.dart';
import '../../../../../data/services/trackstate_auth_store.dart';
import '../../../../../data/services/workspace_profile_service.dart';
import '../../../../../domain/models/trackstate_models.dart';
import '../../../../../domain/models/workspace_profile_models.dart';
import '../../../../../l10n/generated/app_localizations.dart';
import '../../../core/trackstate_icons.dart';
import '../../../core/trackstate_theme.dart';
import '../services/attachment_picker.dart';
import '../services/browser_header_controls_flex_container_stub.dart'
    if (dart.library.js_interop) '../services/browser_header_controls_flex_container_web.dart'
    as browser_header_controls_flex_container;
import '../services/browser_focusable_control_stub.dart'
    if (dart.library.js_interop) '../services/browser_focusable_control_web.dart'
    as browser_focusable_control;
import '../services/browser_workspace_switcher_focus_matcher.dart';
import '../services/browser_workspace_switcher_focus_monitor_stub.dart'
    if (dart.library.js_interop) '../services/browser_workspace_switcher_focus_monitor_web.dart'
    as browser_workspace_switcher_focus_monitor;
import '../services/workspace_directory_picker.dart';
import '../view_models/tracker_view_model.dart';
import 'trackstate_app_types.dart';
import 'trackstate_app_helpers.dart';
import 'widgets/message_banner.dart';
import 'widgets/access_callout.dart';
import 'widgets/startup_recovery_view.dart';
import 'widgets/workspace_initialization_view.dart';
import 'widgets/icon_button_surface.dart';
import 'widgets/action_buttons.dart';
import 'widgets/common_widgets.dart';
import 'widgets/ordered_focus_action.dart';
import 'widgets/settings_text_field.dart';
// ignore: unused_import
import 'widgets/settings_editors.dart';
export 'trackstate_app_types.dart';
export 'trackstate_app_helpers.dart';
part 'trackstate_app_widgets_main.dart';
part 'trackstate_app_widgets_settings.dart';
part 'trackstate_app_widgets_dialogs.dart';

class TrackStateApp extends StatefulWidget {
  const TrackStateApp({
    super.key,
    this.repository,
    this.repositoryFactory,
    this.openLocalRepository,
    this.openBrowserLocalRepository = openBrowserLocalWorkspaceRepository,
    this.requestBrowserLocalRepositoryAccess =
        requestBrowserLocalWorkspaceRepositoryAccess,
    this.openHostedRepository,
    this.workspaceProfileService =
        const SharedPreferencesWorkspaceProfileService(),
    this.authStore = const SharedPreferencesTrackStateAuthStore(),
    this.attachmentPicker = pickAttachmentWithFileSelector,
    this.localWorkspaceOnboardingService,
    this.workspaceDirectoryPicker = pickWorkspaceDirectory,
  });
  final TrackStateRepository? repository;
  final TrackStateRepository Function()? repositoryFactory;
  final LocalRepositoryLoader? openLocalRepository;
  final BrowserLocalRepositoryLoader openBrowserLocalRepository;
  final BrowserLocalRepositoryAccessRequester
  requestBrowserLocalRepositoryAccess;
  final HostedRepositoryLoader? openHostedRepository;
  final WorkspaceProfileService workspaceProfileService;
  final TrackStateAuthStore authStore;
  final AttachmentPicker attachmentPicker;
  final LocalWorkspaceOnboardingService? localWorkspaceOnboardingService;
  final WorkspaceDirectoryPicker workspaceDirectoryPicker;
  @override
  State<TrackStateApp> createState() => _TrackStateAppState();
}
class _TrackStateAppState extends State<TrackStateApp>
    with WidgetsBindingObserver {
  late TrackerViewModel viewModel;
  bool _isCreateIssueVisible = false;
  bool _isDesktopWorkspaceSwitcherVisible = false;
  CreateIssuePrefill? _createIssuePrefill;
  String? _activeLocalGitConfigurationKey;
  String? _pendingLocalGitConfigurationKey;
  bool _workspaceProfilesReady = false;
  bool _showsWorkspaceOnboarding = false;
  WorkspaceProfilesState _workspaceState = const WorkspaceProfilesState();
  Set<String> _authenticatedWorkspaceIds = const <String>{};
  Map<String, HostedWorkspaceAccessMode> _hostedWorkspaceAccessModes =
      const <String, HostedWorkspaceAccessMode>{};
  Map<String, bool> _localWorkspaceAvailability = const <String, bool>{};
  final Map<String, String> _workspaceValidationFailures = <String, String>{};
  List<String>? _desktopWorkspaceSwitcherProfileOrder;
  browser_workspace_switcher_focus_monitor.BrowserViewportScrollSnapshot?
  _desktopWorkspaceSwitcherScrollSnapshot;
  String? _requestedWorkspaceSwitcherRowFocusId;
  int _workspaceSwitcherRowFocusRequestVersion = 0;
  final GlobalKey _workspaceSwitcherTriggerAnchorKey = GlobalKey(
    debugLabel: 'workspace-switcher-trigger-anchor',
  );
  final GlobalKey _workspaceSwitcherOverlayHostKey = GlobalKey(
    debugLabel: 'workspace-switcher-overlay-host',
  );
  final FocusNode _workspaceSwitcherTriggerFocusNode = FocusNode(
    debugLabel: 'workspace-switcher-trigger',
  );
  final FocusNode _desktopSearchFocusNode = FocusNode(
    debugLabel: 'desktop-search',
  );
  final FocusNode _desktopSettingsFocusNode = FocusNode(
    debugLabel: 'desktop-settings',
  );
  final FocusScopeNode _desktopWorkspaceSwitcherFocusScopeNode = FocusScopeNode(
    debugLabel: 'desktop-workspace-switcher',
  );
  browser_workspace_switcher_focus_monitor.BrowserWorkspaceSwitcherFocusMonitorSubscription?
  _desktopWorkspaceSwitcherBrowserFocusMonitor;
  browser_workspace_switcher_focus_monitor.BrowserWorkspaceSwitcherFocusRequest?
  _desktopWorkspaceSwitcherBrowserFocusRequest;
  Timer? _desktopWorkspaceSwitcherBrowserBlurCheckTimer;
  _WorkspaceRestoreFailure? _pendingWorkspaceRestoreFailure;
  bool _isEnsuringCurrentContextWorkspaceMigration = false;
  String? _pendingStartupLocalFallbackWorkspaceId;
  String? _startupHostedFallbackWorkspaceId;
  _HostedRepositoryConfiguration? _lastHostedRepositoryConfiguration;
  bool _isSwitchingStartupHostedFallback = false;
  bool _isPersistingStartupHostedFallbackSelection = false;
  int _deferredStartupLocalWorkspaceRestoreVersion = 0;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _workspaceSwitcherTriggerFocusNode.addListener(
      _handleDesktopWorkspaceSwitcherFocusChange,
    );
    _desktopWorkspaceSwitcherFocusScopeNode.addListener(
      _handleDesktopWorkspaceSwitcherFocusChange,
    );
    viewModel = _createViewModel(autoLoad: false);
    _rememberHostedRepositoryConfiguration(viewModel);
    viewModel.addListener(_handleViewModelChanged);
    unawaited(_initializeWorkspaceProfiles());
  }
  @override
  void didUpdateWidget(covariant TrackStateApp oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.repository == widget.repository &&
        oldWidget.workspaceProfileService == widget.workspaceProfileService) {
      return;
    }
    final previousViewModel = viewModel;
    viewModel = _createViewModel(previous: previousViewModel, autoLoad: false);
    previousViewModel.removeListener(_handleViewModelChanged);
    previousViewModel.dispose();
    viewModel.addListener(_handleViewModelChanged);
    _isCreateIssueVisible = false;
    _createIssuePrefill = null;
    _workspaceProfilesReady = false;
    _showsWorkspaceOnboarding = false;
    _workspaceState = const WorkspaceProfilesState();
    _hostedWorkspaceAccessModes = const <String, HostedWorkspaceAccessMode>{};
    _isDesktopWorkspaceSwitcherVisible = false;
    _pendingStartupLocalFallbackWorkspaceId = null;
    _startupHostedFallbackWorkspaceId = null;
    _isSwitchingStartupHostedFallback = false;
    _isPersistingStartupHostedFallbackSelection = false;
    _requestedWorkspaceSwitcherRowFocusId = null;
    _workspaceSwitcherRowFocusRequestVersion = 0;
    unawaited(_initializeWorkspaceProfiles());
  }
  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _stopDesktopWorkspaceSwitcherBrowserFocusMonitor();
    _cancelDesktopWorkspaceSwitcherBrowserFocusRequest();
    _cancelDesktopWorkspaceSwitcherBrowserBlurCheck();
    _workspaceSwitcherTriggerFocusNode.removeListener(
      _handleDesktopWorkspaceSwitcherFocusChange,
    );
    _desktopWorkspaceSwitcherFocusScopeNode.removeListener(
      _handleDesktopWorkspaceSwitcherFocusChange,
    );
    viewModel.removeListener(_handleViewModelChanged);
    _workspaceSwitcherTriggerFocusNode.dispose();
    _desktopSearchFocusNode.dispose();
    _desktopSettingsFocusNode.dispose();
    _desktopWorkspaceSwitcherFocusScopeNode.dispose();
    viewModel.dispose();
    super.dispose();
  }
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    if (state == AppLifecycleState.resumed) {
      unawaited(viewModel.handleAppResumed());
    }
  }
  void _handleViewModelChanged() {
    if (_shouldEnsureCurrentContextWorkspaceMigration) {
      unawaited(_ensureCurrentContextWorkspaceMigrationIfNeeded());
    }
  }
  bool get _shouldEnsureCurrentContextWorkspaceMigration =>
      !_isEnsuringCurrentContextWorkspaceMigration &&
      widget.repository == null &&
      !_workspaceState.hasProfiles &&
      viewModel.project != null;
  Future<void> _ensureCurrentContextWorkspaceMigrationIfNeeded() async {
    if (!_shouldEnsureCurrentContextWorkspaceMigration) {
      return;
    }
    _isEnsuringCurrentContextWorkspaceMigration = true;
    try {
      await _ensureCurrentContextWorkspaceMigration();
    } finally {
      _isEnsuringCurrentContextWorkspaceMigration = false;
    }
  }
  TrackerViewModel _createViewModel({
    TrackStateRepository? repository,
    TrackerViewModel? previous,
    bool autoLoad = true,
    String? workspaceId,
  }) {
    final nextViewModel = TrackerViewModel(
      repository:
          repository ??
          widget.repository ??
          widget.repositoryFactory?.call() ??
          createTrackStateRepository(),
      workspaceProfileService: widget.workspaceProfileService,
      workspaceId: workspaceId ?? _workspaceState.activeWorkspaceId,
    );
    if (previous != null) {
      nextViewModel.restorePresentationStateFrom(previous);
    }
    if (autoLoad) {
      nextViewModel.load();
    }
    return nextViewModel;
  }
  Future<TrackStateRepository> _openLocalRepository({
    required String repositoryPath,
    required String defaultBranch,
    required String writeBranch,
  }) async {
    final loader = widget.openLocalRepository;
    if (loader != null) {
      return loader(
        repositoryPath: repositoryPath,
        defaultBranch: defaultBranch,
        writeBranch: writeBranch,
      );
    }
    return LocalTrackStateRepository(
      repositoryPath: repositoryPath,
      dataRef: defaultBranch,
      writeBranch: writeBranch,
    );
  }
  Future<TrackStateRepository> _openWorkspaceRepository(
    WorkspaceProfile workspace,
  ) async {
    if (!workspace.isLocal) {
      return _openHostedRepository(
        repository: workspace.target,
        defaultBranch: workspace.defaultBranch,
        writeBranch: workspace.writeBranch,
      );
    }
    if (!kIsWeb) {
      return _openLocalRepository(
        repositoryPath: workspace.target,
        defaultBranch: workspace.defaultBranch,
        writeBranch: workspace.writeBranch,
      );
    }
    final repository = await widget.openBrowserLocalRepository(
      repositoryPath: workspace.target,
      defaultBranch: workspace.defaultBranch,
      writeBranch: workspace.writeBranch,
    );
    if (repository != null) {
      return repository;
    }
    throw StateError(
      'Saved local workspace access is unavailable until the folder is reselected in this browser.',
    );
  }
  Future<_PreparedWorkspaceSwitch?> _prepareBrowserLocalWorkspaceSwitch(
    WorkspaceProfile workspace, {
    required TrackerViewModel previousViewModel,
    bool deferAccessRestore = false,
  }) async {
    return _prepareBrowserLocalWorkspaceSwitchWithLoader(
      workspace,
      previousViewModel: previousViewModel,
      repositoryLoader: widget.openBrowserLocalRepository,
      deferAccessRestore: deferAccessRestore,
    );
  }
  Future<_PreparedWorkspaceSwitch?>
  _prepareBrowserLocalWorkspaceSwitchWithLoader(
    WorkspaceProfile workspace, {
    required TrackerViewModel previousViewModel,
    required BrowserLocalRepositoryLoader repositoryLoader,
    bool deferAccessRestore = false,
  }) async {
    try {
      final repository = await repositoryLoader(
        repositoryPath: workspace.target,
        defaultBranch: workspace.defaultBranch,
        writeBranch: workspace.writeBranch,
      );
      if (repository == null) {
        return null;
      }
      final nextViewModel = _createViewModel(
        repository: repository,
        previous: previousViewModel,
        autoLoad: false,
        workspaceId: workspace.id,
      );
      await nextViewModel.load(deferAccessRestore: deferAccessRestore);
      if (nextViewModel.snapshot == null) {
        final reason = _normalizeWorkspaceFailureReason(nextViewModel.message);
        nextViewModel.dispose();
        _rememberWorkspaceValidationFailure(workspace, reason);
        return null;
      }
      _workspaceValidationFailures.remove(workspace.id);
      return _PreparedWorkspaceSwitch(
        viewModel: nextViewModel,
        workspace: workspace,
        localConfigurationKey:
            '${workspace.target}\n${workspace.defaultBranch}\n${workspace.writeBranch}',
      );
    } on Object catch (error) {
      _rememberWorkspaceValidationFailure(
        workspace,
        _normalizeWorkspaceFailureReason(error),
      );
      return null;
    }
  }
  Future<TrackStateRepository> _openHostedRepository({
    required String repository,
    required String defaultBranch,
    required String writeBranch,
  }) async {
    final loader = widget.openHostedRepository;
    if (loader != null) {
      return loader(
        repository: repository,
        defaultBranch: defaultBranch,
        writeBranch: writeBranch,
      );
    }
    return SetupTrackStateRepository(
      repositoryName: repository,
      sourceRef: writeBranch,
      dataRef: defaultBranch,
    );
  }
  Future<void> _refreshWorkspaceSwitcherState([
    WorkspaceProfilesState? state,
  ]) async {
    var workspaceState = state ?? _workspaceState;
    final activeWorkspace = workspaceState.selectedWorkspace;
    if (activeWorkspace != null &&
        activeWorkspace.isHosted &&
        activeWorkspace.id == viewModel.workspaceId) {
      final liveAccessMode = _hostedWorkspaceAccessModeForViewModel(viewModel);
      final shouldDeferHostedAccessModePersistence =
          _isPersistingStartupHostedFallbackSelection &&
          activeWorkspace.id == _startupHostedFallbackWorkspaceId;
      if (!shouldDeferHostedAccessModePersistence &&
          activeWorkspace.hostedAccessMode != liveAccessMode) {
        workspaceState = await widget.workspaceProfileService
            .saveHostedAccessMode(activeWorkspace.id, liveAccessMode);
      }
    }
    final authenticatedWorkspaceIds = <String>{};
    final hostedWorkspaceAccessModes = <String, HostedWorkspaceAccessMode>{};
    final localWorkspaceAvailability = <String, bool>{};
    WorkspaceProfile? startupUnavailableLocalWorkspace;
    for (final workspace in workspaceState.profiles) {
      if (workspace.isHosted) {
        final token = await widget.authStore.readToken(
          workspaceId: workspace.id,
        );
        if (token != null && token.trim().isNotEmpty) {
          authenticatedWorkspaceIds.add(workspace.id);
        }
        if (workspace.hostedAccessMode case final accessMode?) {
          hostedWorkspaceAccessModes[workspace.id] = accessMode;
        }
        continue;
      }
      final localToken = await widget.authStore.readToken(
        workspaceId: workspace.id,
      );
      if (localToken != null && localToken.trim().isNotEmpty) {
        authenticatedWorkspaceIds.add(workspace.id);
      }
      if (activeWorkspace != null &&
          activeWorkspace.isLocal &&
          workspace.id == activeWorkspace.id &&
          workspace.id == viewModel.workspaceId) {
        if (_shouldMarkActiveLocalWorkspaceUnavailableFromSync(workspace)) {
          workspaceState = await _saveLocalWorkspaceAvailability(
            workspace.id,
            isAvailable: false,
          );
          localWorkspaceAvailability[workspace.id] = false;
          if (_shouldSwitchStartupUnavailableLocalWorkspace(
            workspace,
            workspaceState,
          )) {
            startupUnavailableLocalWorkspace = workspace;
          }
          continue;
        }
        localWorkspaceAvailability[workspace.id] = !workspaceState
            .unavailableLocalWorkspaceIds
            .contains(workspace.id);
        continue;
      }
      if (kIsWeb &&
          activeWorkspace?.isLocal == true &&
          workspace.id == activeWorkspace!.id) {
        localWorkspaceAvailability[workspace.id] = !workspaceState
            .unavailableLocalWorkspaceIds
            .contains(workspace.id);
        continue;
      }
      if (workspaceState.unavailableLocalWorkspaceIds.contains(workspace.id)) {
        localWorkspaceAvailability[workspace.id] = false;
        if (activeWorkspace?.id == workspace.id &&
            _shouldSwitchStartupUnavailableLocalWorkspace(
              workspace,
              workspaceState,
            )) {
          startupUnavailableLocalWorkspace = workspace;
        }
        continue;
      }
      final isAvailable = await _validateLocalWorkspaceAvailability(workspace);
      if (!isAvailable) {
        workspaceState = await _saveLocalWorkspaceAvailability(
          workspace.id,
          isAvailable: false,
        );
        if (activeWorkspace?.id == workspace.id &&
            _shouldSwitchStartupUnavailableLocalWorkspace(
              workspace,
              workspaceState,
            )) {
          startupUnavailableLocalWorkspace = workspace;
        }
      }
      localWorkspaceAvailability[workspace.id] = isAvailable;
    }
    if (!mounted) {
      return;
    }
    final nextActiveWorkspaceId = resolveWorkspaceSwitcherSelectedWorkspaceId(
      currentSelectedWorkspaceId:
          _startupHostedFallbackWorkspaceId != null &&
              workspaceState.profiles.any(
                (workspace) =>
                    workspace.id == _startupHostedFallbackWorkspaceId,
              )
          ? _startupHostedFallbackWorkspaceId
          : _workspaceState.activeWorkspaceId,
      previousWorkspaces: state ?? _workspaceState,
      nextWorkspaces: workspaceState,
    );
    setState(() {
      _workspaceState = workspaceState.copyWith(
        activeWorkspaceId: nextActiveWorkspaceId,
      );
      _authenticatedWorkspaceIds = authenticatedWorkspaceIds;
      _hostedWorkspaceAccessModes = hostedWorkspaceAccessModes;
      _localWorkspaceAvailability = localWorkspaceAvailability;
      _workspaceValidationFailures.removeWhere(
        (workspaceId, _) => !workspaceState.profiles.any(
          (profile) => profile.id == workspaceId,
        ),
      );
    });
    if (startupUnavailableLocalWorkspace != null) {
      await _switchStartupUnavailableLocalWorkspaceToHostedFallback(
        startupUnavailableLocalWorkspace,
      );
    }
  }
  bool _shouldMarkActiveLocalWorkspaceUnavailableFromSync(
    WorkspaceProfile workspace,
  ) {
    if (!workspace.isLocal || !viewModel.usesLocalPersistence) {
      return false;
    }
    final status = viewModel.workspaceSyncStatus;
    final latestError = status.latestError?.trim();
    if (status.health != WorkspaceSyncHealth.attentionNeeded ||
        latestError == null ||
        latestError.isEmpty) {
      return false;
    }
    return !_isUnsupportedActiveLocalStartupAccess(latestError);
  }
  Future<bool> _validateLocalWorkspaceAvailability(
    WorkspaceProfile workspace,
  ) async {
    try {
      final repository = await _openWorkspaceRepository(workspace);
      await repository.loadSnapshot();
      return true;
    } on Object {
      return false;
    }
  }
  Future<bool> _restoreWorkspaceFromSavedState(
    WorkspaceProfilesState state, {
    bool allowFallbackFromActive = true,
    bool deferAccessRestore = false,
    bool preserveActiveLocalSelectionOnUnsupportedAccess = false,
  }) async {
    final activeWorkspaceId = state.activeWorkspaceId;
    final candidates = <WorkspaceProfile>[
      if (activeWorkspaceId != null)
        ...state.profiles.where((profile) => profile.id == activeWorkspaceId),
      if (allowFallbackFromActive || activeWorkspaceId == null)
        ...state.profiles.where((profile) => profile.id != activeWorkspaceId),
    ];
    final previousViewModel = viewModel;
    _WorkspaceRestoreFailure? lastFailure;
    for (final workspace in candidates) {
      if (_shouldBlockAutomaticRestore(state, workspace)) {
        lastFailure = _WorkspaceRestoreFailure(
          workspaceName: workspace.displayName,
          reason: _workspaceValidationFailureReason(workspace),
        );
        continue;
      }
      final prepared = await _prepareWorkspaceSwitch(
        workspace,
        previousViewModel: previousViewModel,
        showFailureMessage: false,
        preserveActiveLocalSelectionOnUnsupportedAccess:
            preserveActiveLocalSelectionOnUnsupportedAccess &&
            workspace.id == activeWorkspaceId,
        preserveActiveLocalSelectionOnStartupFailure:
            workspace.id == activeWorkspaceId && workspace.isLocal,
        deferAccessRestore: deferAccessRestore,
      );
      if (prepared == null) {
        lastFailure = _WorkspaceRestoreFailure(
          workspaceName: workspace.displayName,
          reason: _workspaceValidationFailureReason(workspace),
        );
        continue;
      }
      final restoredWorkspaceId = prepared.workspace?.id ?? workspace.id;
      final preservesActiveLocalSelectionWithHostedShell =
          kIsWeb &&
          workspace.isLocal &&
          workspace.id == activeWorkspaceId &&
          prepared.workspace?.isHosted == true &&
          restoredWorkspaceId != workspace.id;
      if (preservesActiveLocalSelectionWithHostedShell &&
          prepared.preserveActiveLocalAvailability) {
        final optimisticHostedAccessMode =
            _hostedWorkspaceAccessModeForViewModel(prepared.viewModel);
        final optimisticState = _workspaceState.copyWith(
          profiles: [
            for (final profile in _workspaceState.profiles)
              if (profile.id == restoredWorkspaceId && profile.isHosted)
                profile.copyWith(hostedAccessMode: optimisticHostedAccessMode)
              else
                profile,
          ],
          activeWorkspaceId: workspace.id,
          unavailableLocalWorkspaceIds: _workspaceState
              .unavailableLocalWorkspaceIds
              .difference({workspace.id}),
        );
        _pendingStartupLocalFallbackWorkspaceId = null;
        _pendingWorkspaceRestoreFailure = null;
        if (lastFailure != null) {
          prepared.viewModel.showMessage(
            TrackerMessage.workspaceRestoreSkipped(
              workspaceName: lastFailure.workspaceName,
              reason: lastFailure.reason,
            ),
          );
        }
        await _commitPreparedWorkspaceSwitch(
          prepared,
          previousViewModel: previousViewModel,
          workspaceState: optimisticState,
        );
        var preservedState = await widget.workspaceProfileService.loadState();
        preservedState = preservedState.copyWith(
          activeWorkspaceId: workspace.id,
          unavailableLocalWorkspaceIds: preservedState
              .unavailableLocalWorkspaceIds
              .difference({workspace.id}),
        );
        preservedState =
            await _persistPreparedHostedWorkspaceState(
              prepared,
              workspaceState: preservedState,
              preserveActiveSelection: true,
            ) ??
            preservedState;
        if (!mounted) {
          return true;
        }
        setState(() {
          _workspaceState = preservedState;
        });
        await _refreshWorkspaceSwitcherState(preservedState);
        return true;
      }
      final preservesUnavailableActiveLocalSelection =
          preservesActiveLocalSelectionWithHostedShell;
      if (preservesUnavailableActiveLocalSelection) {
        final optimisticHostedAccessMode =
            _hostedWorkspaceAccessModeForViewModel(prepared.viewModel);
        final optimisticState = _workspaceState.copyWith(
          profiles: [
            for (final profile in _workspaceState.profiles)
              if (profile.id == restoredWorkspaceId && profile.isHosted)
                profile.copyWith(hostedAccessMode: optimisticHostedAccessMode)
              else
                profile,
          ],
          activeWorkspaceId: workspace.id,
          unavailableLocalWorkspaceIds: {
            ..._workspaceState.unavailableLocalWorkspaceIds,
            workspace.id,
          },
        );
        _pendingStartupLocalFallbackWorkspaceId = null;
        _pendingWorkspaceRestoreFailure = null;
        if (lastFailure != null) {
          prepared.viewModel.showMessage(
            TrackerMessage.workspaceRestoreSkipped(
              workspaceName: lastFailure.workspaceName,
              reason: lastFailure.reason,
            ),
          );
        }
        await _commitPreparedWorkspaceSwitch(
          prepared,
          previousViewModel: previousViewModel,
          workspaceState: optimisticState,
        );
        var preservedState = await widget.workspaceProfileService.loadState();
        preservedState = preservedState.copyWith(
          activeWorkspaceId: workspace.id,
          unavailableLocalWorkspaceIds: {
            ...preservedState.unavailableLocalWorkspaceIds,
            workspace.id,
          },
        );
        preservedState =
            await _persistPreparedHostedWorkspaceState(
              prepared,
              workspaceState: preservedState,
              preserveActiveSelection: true,
            ) ??
            preservedState;
        if (!mounted) {
          return true;
        }
        setState(() {
          _workspaceState = preservedState;
        });
        await _refreshWorkspaceSwitcherState(preservedState);
        return true;
      }
      final shouldCommitHostedFallbackBeforePersistence =
          deferAccessRestore &&
          kIsWeb &&
          workspace.isLocal &&
          prepared.workspace?.isHosted == true &&
          restoredWorkspaceId != workspace.id;
      if (shouldCommitHostedFallbackBeforePersistence) {
        final optimisticHostedAccessMode =
            _hostedWorkspaceAccessModeForViewModel(prepared.viewModel);
        final optimisticState = _workspaceState.copyWith(
          profiles: [
            for (final profile in _workspaceState.profiles)
              if (profile.id == restoredWorkspaceId && profile.isHosted)
                profile.copyWith(hostedAccessMode: optimisticHostedAccessMode)
              else
                profile,
          ],
          activeWorkspaceId: restoredWorkspaceId,
          unavailableLocalWorkspaceIds: {
            ..._workspaceState.unavailableLocalWorkspaceIds,
            workspace.id,
          },
        );
        _startupHostedFallbackWorkspaceId = restoredWorkspaceId;
        _isPersistingStartupHostedFallbackSelection = true;
        _pendingStartupLocalFallbackWorkspaceId = null;
        _pendingWorkspaceRestoreFailure = null;
        if (lastFailure != null) {
          prepared.viewModel.showMessage(
            TrackerMessage.workspaceRestoreSkipped(
              workspaceName: lastFailure.workspaceName,
              reason: lastFailure.reason,
            ),
          );
        }
        try {
          await _commitPreparedWorkspaceSwitch(
            prepared,
            previousViewModel: previousViewModel,
            workspaceState: optimisticState,
          );
          var selectedState = await widget.workspaceProfileService
              .selectProfile(restoredWorkspaceId);
          selectedState =
              await _persistPreparedHostedWorkspaceState(
                prepared,
                workspaceState: selectedState,
              ) ??
              selectedState;
          if (!mounted) {
            return true;
          }
          setState(() {
            _workspaceState = selectedState;
          });
          await _refreshWorkspaceSwitcherState(selectedState);
        } finally {
          _isPersistingStartupHostedFallbackSelection = false;
          if (viewModel.workspaceId == restoredWorkspaceId) {
            _startupHostedFallbackWorkspaceId = null;
          }
        }
        return true;
      }
      var selectedState = await widget.workspaceProfileService.selectProfile(
        restoredWorkspaceId,
      );
      selectedState =
          await _persistPreparedHostedWorkspaceState(
            prepared,
            workspaceState: selectedState,
          ) ??
          selectedState;
      _pendingWorkspaceRestoreFailure = null;
      if (lastFailure != null) {
        prepared.viewModel.showMessage(
          TrackerMessage.workspaceRestoreSkipped(
            workspaceName: lastFailure.workspaceName,
            reason: lastFailure.reason,
          ),
        );
      }
      await _commitPreparedWorkspaceSwitch(
        prepared,
        previousViewModel: previousViewModel,
        workspaceState: selectedState,
      );
      return true;
    }
    if (lastFailure != null) {
      _pendingWorkspaceRestoreFailure = lastFailure;
    }
    return false;
  }
  bool _shouldBlockAutomaticRestore(
    WorkspaceProfilesState state,
    WorkspaceProfile workspace,
  ) {
    if (kIsWeb &&
        widget.repository == null &&
        workspace.id == state.activeWorkspaceId) {
      return false;
    }
    return workspace.isLocal &&
        state.unavailableLocalWorkspaceIds.contains(workspace.id);
  }
  bool _shouldDeferAccessRestoreForWorkspace(WorkspaceProfile workspace) {
    return kIsWeb && workspace.isHosted;
  }
  Future<WorkspaceProfilesState?> _persistPreparedHostedWorkspaceState(
    _PreparedWorkspaceSwitch prepared, {
    WorkspaceProfilesState? workspaceState,
    bool preserveActiveSelection = false,
  }) async {
    if (widget.repository != null) {
      return workspaceState;
    }
    final workspace = prepared.workspace;
    if (workspace == null || !workspace.isHosted) {
      return workspaceState;
    }
    var nextState = workspaceState;
    nextState ??= await widget.workspaceProfileService.loadState();
    if (!preserveActiveSelection &&
        nextState.activeWorkspaceId != workspace.id) {
      nextState = await widget.workspaceProfileService.selectProfile(
        workspace.id,
      );
    }
    final activeWorkspace = nextState.activeWorkspace;
    final accessMode = _hostedWorkspaceAccessModeForViewModel(
      prepared.viewModel,
    );
    if (activeWorkspace?.hostedAccessMode != accessMode) {
      nextState = await widget.workspaceProfileService.saveHostedAccessMode(
        workspace.id,
        accessMode,
      );
    }
    return nextState;
  }
  Future<WorkspaceProfile?> _resolvePreservedLocalHostedFallbackWorkspace({
    bool requireAuthenticatedWorkspace = false,
  }) async {
    final hostedWorkspaces = _workspaceState.profiles
        .where((workspace) => workspace.isHosted)
        .toList(growable: false);
    if (hostedWorkspaces.isEmpty) {
      return null;
    }
    for (final workspace in hostedWorkspaces) {
      final token = await widget.authStore.readToken(
        repository: workspace.target,
        workspaceId: workspace.id,
      );
      if (token != null && token.trim().isNotEmpty) {
        return workspace;
      }
    }
    if (requireAuthenticatedWorkspace) {
      return null;
    }
    return hostedWorkspaces.first;
  }
  Future<_PreparedWorkspaceSwitch?> _preparePreservedLocalHostedFallbackSwitch(
    TrackerViewModel previousViewModel, {
    required bool deferAccessRestore,
    bool requireAuthenticatedWorkspace = false,
  }) async {
    final fallbackWorkspace =
        await _resolvePreservedLocalHostedFallbackWorkspace(
          requireAuthenticatedWorkspace: requireAuthenticatedWorkspace,
        );
    if (fallbackWorkspace == null) {
      return null;
    }
    try {
      final repository = await _openWorkspaceRepository(fallbackWorkspace);
      final fallbackViewModel = _createViewModel(
        repository: repository,
        previous: previousViewModel,
        autoLoad: false,
        workspaceId: fallbackWorkspace.id,
      );
      final loadFuture = fallbackViewModel.load(
        deferAccessRestore: deferAccessRestore,
      );
      await _awaitStartupLoadWithHostedFallback(
        fallbackViewModel,
        loadFuture: loadFuture,
        allowHostedFallback: deferAccessRestore && kIsWeb,
        waitForLoadAfterHostedFallback: false,
      );
      if (fallbackViewModel.snapshot == null) {
        final reason = _normalizeWorkspaceFailureReason(
          fallbackViewModel.message,
        );
        fallbackViewModel.dispose();
        _rememberWorkspaceValidationFailure(fallbackWorkspace, reason);
        return null;
      }
      return _PreparedWorkspaceSwitch(
        viewModel: fallbackViewModel,
        workspace: fallbackWorkspace,
        localConfigurationKey: null,
      );
    } on Object catch (error) {
      _rememberWorkspaceValidationFailure(
        fallbackWorkspace,
        _normalizeWorkspaceFailureReason(error),
      );
      return null;
    }
  }
  Future<void> _awaitStartupLoadWithHostedFallback(
    TrackerViewModel model, {
    required Future<void> loadFuture,
    required bool allowHostedFallback,
    bool waitForLoadAfterHostedFallback = true,
  }) async {
    if (!allowHostedFallback) {
      await loadFuture;
      return;
    }
    unawaited(loadFuture);
    await Future<void>.microtask(() {});
    final publishedFallback = await model.publishHostedStartupFallbackShell();
    if (publishedFallback && !waitForLoadAfterHostedFallback) {
      return;
    }
    await loadFuture;
  }
  Future<_PreparedWorkspaceSwitch?> _prepareWorkspaceSwitch(
    WorkspaceProfile workspace, {
    required TrackerViewModel previousViewModel,
    required bool showFailureMessage,
    bool preserveActiveLocalSelectionOnUnsupportedAccess = false,
    bool preserveActiveLocalSelectionOnStartupFailure = false,
    bool deferAccessRestore = false,
  }) async {
    try {
      final repositoryOpen = _openWorkspaceRepository(workspace);
      final repository =
          preserveActiveLocalSelectionOnStartupFailure &&
              workspace.isLocal &&
              kIsWeb
          ? await repositoryOpen.timeout(
              const Duration(seconds: 2),
              onTimeout: () => throw StateError(
                'Saved local workspace access is unavailable until the folder is reselected in this browser.',
              ),
            )
          : await repositoryOpen;
      final nextViewModel = _createViewModel(
        repository: repository,
        previous: previousViewModel,
        autoLoad: false,
        workspaceId: workspace.id,
      );
      await nextViewModel.load(deferAccessRestore: deferAccessRestore);
      if (nextViewModel.snapshot != null) {
        _workspaceValidationFailures.remove(workspace.id);
        return _PreparedWorkspaceSwitch(
          viewModel: nextViewModel,
          workspace: workspace,
          localConfigurationKey: workspace.isLocal
              ? '${workspace.target}\n${workspace.defaultBranch}\n${workspace.writeBranch}'
              : null,
        );
      }
      final reason = _normalizeWorkspaceFailureReason(nextViewModel.message);
      if (preserveActiveLocalSelectionOnStartupFailure && workspace.isLocal) {
        nextViewModel.dispose();
        if (kIsWeb && _shouldRetryActiveLocalWorkspaceRevalidation(reason)) {
          final preserved = await _preserveActiveLocalWorkspaceSelection(
            workspace,
            previousViewModel,
            deferAccessRestore: deferAccessRestore,
            requireAuthenticatedHostedFallback: false,
          );
          if (preserved != null) {
            _scheduleDeferredStartupLocalWorkspaceRestore(workspace);
            return preserved;
          }
        }
        final requiresBrowserReselection =
            _requiresBrowserLocalWorkspaceReselection(reason);
        if (preserveActiveLocalSelectionOnUnsupportedAccess &&
            (requiresBrowserReselection ||
                _isUnsupportedActiveLocalStartupAccess(reason))) {
          return _preserveActiveLocalWorkspaceSelection(
            workspace,
            previousViewModel,
            deferAccessRestore: deferAccessRestore,
            markUnavailable: requiresBrowserReselection,
            requireAuthenticatedHostedFallback: true,
          );
        }
        _rememberWorkspaceValidationFailure(workspace, reason);
        await _saveLocalWorkspaceAvailability(workspace.id, isAvailable: false);
        return null;
      }
      nextViewModel.dispose();
      _rememberWorkspaceValidationFailure(workspace, reason);
      if (showFailureMessage) {
        previousViewModel.showMessage(
          TrackerMessage.workspaceSwitchFailed(
            workspaceName: workspace.displayName,
            reason: reason,
          ),
        );
      }
      return null;
    } on Object catch (error) {
      final reason = _normalizeWorkspaceFailureReason(error);
      if (preserveActiveLocalSelectionOnStartupFailure && workspace.isLocal) {
        if (kIsWeb && _shouldRetryActiveLocalWorkspaceRevalidation(reason)) {
          final preserved = await _preserveActiveLocalWorkspaceSelection(
            workspace,
            previousViewModel,
            deferAccessRestore: deferAccessRestore,
            requireAuthenticatedHostedFallback: false,
          );
          if (preserved != null) {
            _scheduleDeferredStartupLocalWorkspaceRestore(workspace);
            return preserved;
          }
        }
        final requiresBrowserReselection =
            _requiresBrowserLocalWorkspaceReselection(reason);
        if (preserveActiveLocalSelectionOnUnsupportedAccess &&
            (requiresBrowserReselection ||
                _isUnsupportedActiveLocalStartupAccess(reason))) {
          return _preserveActiveLocalWorkspaceSelection(
            workspace,
            previousViewModel,
            deferAccessRestore: deferAccessRestore,
            markUnavailable: requiresBrowserReselection,
            requireAuthenticatedHostedFallback: true,
          );
        }
        _rememberWorkspaceValidationFailure(workspace, reason);
        await _saveLocalWorkspaceAvailability(workspace.id, isAvailable: false);
        return null;
      }
      _rememberWorkspaceValidationFailure(workspace, reason);
      if (showFailureMessage) {
        previousViewModel.showMessage(
          TrackerMessage.workspaceSwitchFailed(
            workspaceName: workspace.displayName,
            reason: reason,
          ),
        );
      }
      return null;
    }
  }
  Future<_PreparedWorkspaceSwitch?> _preserveActiveLocalWorkspaceSelection(
    WorkspaceProfile workspace,
    TrackerViewModel previousViewModel, {
    bool deferAccessRestore = false,
    bool markUnavailable = false,
    bool requireAuthenticatedHostedFallback = false,
  }) async {
    final hostedFallbackSwitch =
        await _preparePreservedLocalHostedFallbackSwitch(
          previousViewModel,
          deferAccessRestore: deferAccessRestore,
          requireAuthenticatedWorkspace: requireAuthenticatedHostedFallback,
        );
    if (hostedFallbackSwitch != null) {
      if (markUnavailable) {
        await _saveLocalWorkspaceAvailability(workspace.id, isAvailable: false);
      } else {
        _workspaceValidationFailures.remove(workspace.id);
      }
      return _PreparedWorkspaceSwitch(
        viewModel: hostedFallbackSwitch.viewModel,
        workspace: hostedFallbackSwitch.workspace,
        localConfigurationKey: hostedFallbackSwitch.localConfigurationKey,
        preserveActiveLocalAvailability: !markUnavailable,
      );
    }
    if (requireAuthenticatedHostedFallback) {
      return null;
    }
    previousViewModel.updateWorkspaceScope(workspace.id);
    if (previousViewModel.snapshot == null) {
      if (deferAccessRestore && kIsWeb) {
        unawaited(
          previousViewModel.load(deferAccessRestore: deferAccessRestore),
        );
      } else {
        await previousViewModel.load(deferAccessRestore: deferAccessRestore);
      }
    }
    final preservedViewModel = previousViewModel.workspaceId == workspace.id
        ? previousViewModel
        : _createViewModel(
            repository: previousViewModel.repository,
            previous: previousViewModel,
            autoLoad: false,
            workspaceId: workspace.id,
          );
    if (!identical(preservedViewModel, previousViewModel) &&
        preservedViewModel.snapshot == null) {
      if (deferAccessRestore && kIsWeb) {
        unawaited(
          preservedViewModel.load(deferAccessRestore: deferAccessRestore),
        );
      } else {
        await preservedViewModel.load(deferAccessRestore: deferAccessRestore);
      }
    }
    if (markUnavailable) {
      await _saveLocalWorkspaceAvailability(workspace.id, isAvailable: false);
    } else {
      _workspaceValidationFailures.remove(workspace.id);
    }
    return _PreparedWorkspaceSwitch(
      viewModel: preservedViewModel,
      workspace: workspace,
      localConfigurationKey: null,
    );
  }
  bool _shouldSwitchStartupUnavailableLocalWorkspace(
    WorkspaceProfile workspace,
    WorkspaceProfilesState workspaceState,
  ) {
    return kIsWeb &&
        widget.repository == null &&
        !_isSwitchingStartupHostedFallback &&
        _pendingStartupLocalFallbackWorkspaceId == workspace.id &&
        workspaceState.profiles.any((profile) => profile.isHosted);
  }
  Future<void> _switchStartupUnavailableLocalWorkspaceToHostedFallback(
    WorkspaceProfile workspace,
  ) async {
    if (_isSwitchingStartupHostedFallback) {
      return;
    }
    _isSwitchingStartupHostedFallback = true;
    try {
      final previousViewModel = viewModel;
      final prepared = await _preparePreservedLocalHostedFallbackSwitch(
        previousViewModel,
        deferAccessRestore: true,
        requireAuthenticatedWorkspace: true,
      );
      if (prepared == null || prepared.workspace == null || !mounted) {
        _pendingStartupLocalFallbackWorkspaceId = null;
        return;
      }
      _pendingStartupLocalFallbackWorkspaceId = null;
      final optimisticHostedAccessMode = _hostedWorkspaceAccessModeForViewModel(
        prepared.viewModel,
      );
      final optimisticState = _workspaceState.copyWith(
        profiles: [
          for (final profile in _workspaceState.profiles)
            if (profile.id == prepared.workspace!.id && profile.isHosted)
              profile.copyWith(hostedAccessMode: optimisticHostedAccessMode)
            else
              profile,
        ],
        activeWorkspaceId: workspace.id,
        unavailableLocalWorkspaceIds: {
          ..._workspaceState.unavailableLocalWorkspaceIds,
          workspace.id,
        },
      );
      await _commitPreparedWorkspaceSwitch(
        prepared,
        previousViewModel: previousViewModel,
        workspaceState: optimisticState,
      );
      var preservedState = await widget.workspaceProfileService.loadState();
      preservedState = preservedState.copyWith(
        activeWorkspaceId: workspace.id,
        unavailableLocalWorkspaceIds: {
          ...preservedState.unavailableLocalWorkspaceIds,
          workspace.id,
        },
      );
      preservedState =
          await _persistPreparedHostedWorkspaceState(
            prepared,
            workspaceState: preservedState,
            preserveActiveSelection: true,
          ) ??
          preservedState;
      if (mounted) {
        setState(() {
          _workspaceState = preservedState;
        });
        await _refreshWorkspaceSwitcherState(preservedState);
      }
    } finally {
      if (_pendingStartupLocalFallbackWorkspaceId == workspace.id &&
          !viewModel.usesLocalPersistence) {
        _pendingStartupLocalFallbackWorkspaceId = null;
      }
      _isSwitchingStartupHostedFallback = false;
    }
  }
  Future<WorkspaceProfilesState> _saveLocalWorkspaceAvailability(
    String workspaceId, {
    required bool isAvailable,
  }) async {
    final nextState = await widget.workspaceProfileService
        .saveLocalWorkspaceAvailability(workspaceId, isAvailable: isAvailable);
    if (!mounted) {
      return nextState;
    }
    setState(() {
      _workspaceState = nextState;
    });
    return nextState;
  }
  void _scheduleDeferredStartupLocalWorkspaceRestore(
    WorkspaceProfile workspace,
  ) {
    if (!kIsWeb || widget.repository != null || !workspace.isLocal) {
      return;
    }
    final restoreVersion = ++_deferredStartupLocalWorkspaceRestoreVersion;
    unawaited(
      _runDeferredStartupLocalWorkspaceRestore(
        workspace,
        restoreVersion: restoreVersion,
      ),
    );
  }
  bool _shouldContinueDeferredStartupLocalWorkspaceRestore(
    WorkspaceProfile workspace, {
    required int restoreVersion,
  }) {
    return mounted &&
        restoreVersion == _deferredStartupLocalWorkspaceRestoreVersion &&
        _workspaceState.activeWorkspaceId == workspace.id;
  }
  Future<void> _runDeferredStartupLocalWorkspaceRestore(
    WorkspaceProfile workspace, {
    required int restoreVersion,
  }) async {
    const retryDelays = <Duration>[
      Duration(milliseconds: 100),
      Duration(milliseconds: 150),
      Duration(milliseconds: 250),
      Duration(milliseconds: 400),
      Duration(milliseconds: 600),
    ];
    const maxStartupRevalidationWait = Duration(seconds: 10);
    var elapsedWait = Duration.zero;
    var attempt = 0;
    while (_shouldContinueDeferredStartupLocalWorkspaceRestore(
      workspace,
      restoreVersion: restoreVersion,
    )) {
      final previousViewModel = viewModel;
      final prepared = await _prepareBrowserLocalWorkspaceSwitch(
        workspace,
        previousViewModel: previousViewModel,
        deferAccessRestore: true,
      );
      if (!_shouldContinueDeferredStartupLocalWorkspaceRestore(
        workspace,
        restoreVersion: restoreVersion,
      )) {
        prepared?.viewModel.dispose();
        return;
      }
      if (prepared != null) {
        var selectedState = await widget.workspaceProfileService.selectProfile(
          workspace.id,
        );
        selectedState = await _saveLocalWorkspaceAvailability(
          workspace.id,
          isAvailable: true,
        );
        await _commitPreparedWorkspaceSwitch(
          prepared,
          previousViewModel: previousViewModel,
          workspaceState: selectedState,
        );
        return;
      }
      final reason = _workspaceValidationFailureReason(workspace);
      final retryable = _shouldRetryActiveLocalWorkspaceRevalidation(reason);
      if (!retryable ||
          _requiresBrowserLocalWorkspaceReselection(reason) ||
          _isUnsupportedActiveLocalStartupAccess(reason)) {
        await _saveLocalWorkspaceAvailability(workspace.id, isAvailable: false);
        if (_shouldContinueDeferredStartupLocalWorkspaceRestore(
          workspace,
          restoreVersion: restoreVersion,
        )) {
          await _refreshWorkspaceSwitcherState();
        }
        return;
      }
      final remaining = maxStartupRevalidationWait - elapsedWait;
      if (remaining <= Duration.zero) {
        break;
      }
      final delay = retryDelays[math.min(attempt, retryDelays.length - 1)];
      final appliedDelay = remaining < delay ? remaining : delay;
      await Future<void>.delayed(appliedDelay);
      elapsedWait += appliedDelay;
      attempt += 1;
    }
    if (!_shouldContinueDeferredStartupLocalWorkspaceRestore(
      workspace,
      restoreVersion: restoreVersion,
    )) {
      return;
    }
    await _saveLocalWorkspaceAvailability(workspace.id, isAvailable: false);
    if (_shouldContinueDeferredStartupLocalWorkspaceRestore(
      workspace,
      restoreVersion: restoreVersion,
    )) {
      await _refreshWorkspaceSwitcherState();
    }
  }
  bool _isUnsupportedActiveLocalStartupAccess(String reason) {
    final normalizedReason = reason.toLowerCase();
    return normalizedReason.contains(
          'local git startup access is unavailable',
        ) ||
        normalizedReason.contains('unsupported operation: process.run') ||
        normalizedReason.contains('process.run') ||
        normalizedReason.contains('unsupported operation') ||
        normalizedReason.contains('process.start') ||
        normalizedReason.contains('not supported on the web') ||
        normalizedReason.contains('local git runtime is not available') ||
        (normalizedReason.contains('local') &&
            normalizedReason.contains('not available in this build'));
  }
  void _rememberWorkspaceValidationFailure(
    WorkspaceProfile workspace,
    String reason,
  ) {
    if (!mounted) {
      return;
    }
    setState(() {
      if (workspace.isLocal) {
        _localWorkspaceAvailability = <String, bool>{
          ..._localWorkspaceAvailability,
          workspace.id: false,
        };
      } else {
        _authenticatedWorkspaceIds = <String>{..._authenticatedWorkspaceIds}
          ..remove(workspace.id);
        _hostedWorkspaceAccessModes = <String, HostedWorkspaceAccessMode>{
          ..._hostedWorkspaceAccessModes,
          workspace.id: HostedWorkspaceAccessMode.disconnected,
        };
      }
    });
    _workspaceValidationFailures[workspace.id] = reason;
  }
  String _workspaceValidationFailureReason(WorkspaceProfile workspace) {
    return _workspaceValidationFailures[workspace.id] ??
        (workspace.isLocal
            ? 'The local repository path is unavailable.'
            : 'The saved hosted repository could not be opened.');
  }
  String _normalizeWorkspaceFailureReason(Object? source) {
    final raw = switch (source) {
      TrackerMessage(
        kind: TrackerMessageKind.dataLoadFailed,
        error: final error?,
      ) =>
        error,
      TrackerMessage(
        kind: TrackerMessageKind.githubConnectionFailed,
        error: final error?,
      ) =>
        error,
      TrackerMessage(
        kind: TrackerMessageKind.storedGitHubTokenInvalid,
        error: final error?,
      ) =>
        error,
      TrackerMessage(
        kind: TrackerMessageKind.repositoryConfigFallback,
        error: final error?,
      ) =>
        error,
      _ => '$source',
    }.trim();
    if (raw.isEmpty || raw == 'null') {
      return 'The workspace could not be opened.';
    }
    return raw
        .replaceFirst(RegExp(r'^(Exception|Bad state):\s*'), '')
        .replaceFirst(RegExp(r'^Invalid argument\(s\):\s*'), '');
  }
  Future<void> _initializeWorkspaceProfiles() async {
    final loadedState = await widget.workspaceProfileService.loadState();
    final startsWithoutSavedWorkspaces =
        shouldOpenProjectSettingsForStartupWithoutSavedWorkspaces(
          isWeb: kIsWeb,
          hasRepository: widget.repository != null,
          hasProfiles: loadedState.hasProfiles,
        );
    if (!mounted) {
      return;
    }
    _pendingStartupLocalFallbackWorkspaceId =
        widget.repository == null &&
            kIsWeb &&
            loadedState.selectedWorkspace?.isLocal == true
        ? loadedState.selectedWorkspace!.id
        : null;
    setState(() {
      _workspaceState = loadedState;
    });
    await _awaitActiveLocalWorkspaceRevalidation(loadedState);
    if (!mounted) {
      return;
    }
    var startupState = await widget.workspaceProfileService.loadState();
    if (!mounted) {
      return;
    }
    setState(() {
      _workspaceState = startupState;
    });
    await _refreshWorkspaceSwitcherState(startupState);
    if (widget.repository != null) {
      if (startupState.selectedWorkspace case final activeWorkspace?) {
        viewModel.updateWorkspaceScope(activeWorkspace.id);
      }
      setState(() {
        _workspaceProfilesReady = true;
      });
      _pendingStartupLocalFallbackWorkspaceId = null;
      await _awaitStartupLoadWithHostedFallback(
        viewModel,
        loadFuture: viewModel.load(deferAccessRestore: true),
        allowHostedFallback: kIsWeb,
      );
      return;
    }
    if (_workspaceProfilesReady &&
        _workspaceState.activeWorkspaceId != null &&
        viewModel.workspaceId == _workspaceState.activeWorkspaceId) {
      _scheduleWebStartupRefresh();
      return;
    }
    startupState = await widget.workspaceProfileService.loadState();
    if (!mounted) {
      return;
    }
    if (startupState.hasProfiles) {
      if (kIsWeb) {
        final restored = await _restoreWorkspaceFromSavedState(
          startupState,
          allowFallbackFromActive: false,
          deferAccessRestore: true,
          preserveActiveLocalSelectionOnUnsupportedAccess: true,
        );
        _scheduleWebStartupRefresh();
        if (restored || !mounted) {
          return;
        }
        await _handleStartupWorkspaceRestoreFailure(startupState);
        return;
      }
      final restored = await _restoreWorkspaceFromSavedState(
        startupState,
        allowFallbackFromActive: false,
      );
      if (!restored) {
        await _handleStartupWorkspaceRestoreFailure(startupState);
      }
      return;
    }
    if (_shouldShowWorkspaceOnboarding(startupState)) {
      setState(() {
        _showsWorkspaceOnboarding = true;
        _workspaceProfilesReady = true;
      });
      _pendingStartupLocalFallbackWorkspaceId = null;
      return;
    }
    await _awaitStartupLoadWithHostedFallback(
      viewModel,
      loadFuture: viewModel.load(deferAccessRestore: true),
      allowHostedFallback: kIsWeb,
    );
    await _ensureCurrentContextWorkspaceMigration();
    if (!mounted) {
      return;
    }
    final migratedState = await widget.workspaceProfileService.loadState();
    if (!mounted) {
      return;
    }
    setState(() {
      _workspaceState = migratedState;
      _showsWorkspaceOnboarding = _shouldShowWorkspaceOnboarding(migratedState);
      _workspaceProfilesReady = true;
    });
    _pendingStartupLocalFallbackWorkspaceId = null;
    if (startsWithoutSavedWorkspaces) {
      viewModel.openProjectSettings();
    }
  }
  Future<void> _handleStartupWorkspaceRestoreFailure(
    WorkspaceProfilesState state,
  ) async {
    var nextState = state;
    if (state.activeWorkspaceId != null) {
      nextState = await widget.workspaceProfileService
          .clearActiveWorkspaceSelection();
      viewModel.updateWorkspaceScope(null);
      await _refreshWorkspaceSwitcherState(nextState);
    }
    if (!mounted) {
      return;
    }
    setState(() {
      _workspaceState = nextState;
      _showsWorkspaceOnboarding = true;
      _workspaceProfilesReady = true;
    });
  }
  void _scheduleWebStartupRefresh() {
    if (!kIsWeb) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      setState(() {});
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) {
          return;
        }
        setState(() {});
      });
    });
  }
  Future<void> _awaitActiveLocalWorkspaceRevalidation(
    WorkspaceProfilesState state,
  ) async {
    if (widget.repository != null || kIsWeb) {
      return;
    }
    final activeWorkspace = state.selectedWorkspace;
    if (activeWorkspace == null || !activeWorkspace.isLocal) {
      return;
    }
    const retryDelays = <Duration>[
      Duration(milliseconds: 100),
      Duration(milliseconds: 150),
      Duration(milliseconds: 250),
      Duration(milliseconds: 400),
      Duration(milliseconds: 600),
    ];
    const maxStartupRevalidationWait = Duration(seconds: 10);
    var elapsedWait = Duration.zero;
    var attempt = 0;
    while (true) {
      final validationReady = await _tryAwaitActiveLocalWorkspaceOpen(
        activeWorkspace,
      );
      if (validationReady) {
        return;
      }
      if (!mounted) {
        return;
      }
      final remaining = maxStartupRevalidationWait - elapsedWait;
      if (remaining <= Duration.zero) {
        return;
      }
      final delay = retryDelays[math.min(attempt, retryDelays.length - 1)];
      final appliedDelay = remaining < delay ? remaining : delay;
      await Future<void>.delayed(appliedDelay);
      if (!mounted) {
        return;
      }
      elapsedWait += appliedDelay;
      attempt += 1;
    }
  }
  Future<bool> _tryAwaitActiveLocalWorkspaceOpen(
    WorkspaceProfile workspace,
  ) async {
    try {
      final repository = await _openWorkspaceRepository(workspace);
      await repository.loadSnapshot();
      return true;
    } on UnsupportedError {
      return true;
    } on Object catch (error) {
      if (_isUnavailableBrowserLocalWorkspaceAccess(error)) {
        await _saveLocalWorkspaceAvailability(workspace.id, isAvailable: false);
        return true;
      }
      return !_shouldRetryActiveLocalWorkspaceRevalidation(error);
    }
  }
  bool _isUnavailableBrowserLocalWorkspaceAccess(Object error) {
    return _requiresBrowserLocalWorkspaceReselection(
      _normalizeWorkspaceFailureReason(error),
    );
  }
  bool _requiresBrowserLocalWorkspaceReselection(String reason) {
    final normalizedReason = reason.toLowerCase();
    return normalizedReason.contains(
          'saved local workspace access is unavailable until the folder is reselected in this browser',
        ) ||
        normalizedReason.contains('reselected in this browser');
  }
  bool _shouldRetryActiveLocalWorkspaceRevalidation(Object error) {
    final reason = _normalizeWorkspaceFailureReason(error).toLowerCase();
    return reason.contains('file system access') ||
        reason.contains('handle revalidation') ||
        reason.contains('revalidation') ||
        reason.contains('busy') ||
        reason.contains('temporar') ||
        reason.contains('transient') ||
        reason.contains('locked') ||
        reason.contains('unavailable') ||
        reason.contains('permission') ||
        reason.contains('pending');
  }
  bool _shouldShowWorkspaceOnboarding(WorkspaceProfilesState state) {
    return shouldShowWorkspaceOnboardingForStartup(
      isWeb: kIsWeb,
      hasRepository: widget.repository != null,
      hasProfiles: state.hasProfiles,
    );
  }
  Future<void> _switchToLocalRepository({
    required String repositoryPath,
    required String defaultBranch,
    required String writeBranch,
  }) async {
    await _switchToLocalRepositoryWithProfile(
      repositoryPath: repositoryPath,
      defaultBranch: defaultBranch,
      writeBranch: writeBranch,
    );
  }
  Future<void> _switchToLocalRepositoryWithProfile({
    required String repositoryPath,
    required String defaultBranch,
    required String writeBranch,
    String? displayName,
  }) async {
    final normalizedRepositoryPath = normalizeWorkspaceTarget(
      WorkspaceProfileTargetType.local,
      repositoryPath,
    );
    final normalizedDefaultBranch = normalizeWorkspaceBranch(defaultBranch);
    final normalizedWriteBranch = normalizeWorkspaceBranch(writeBranch);
    if (normalizedRepositoryPath.isEmpty ||
        normalizedDefaultBranch.isEmpty ||
        normalizedWriteBranch.isEmpty) {
      return;
    }
    final configurationKey =
        '$normalizedRepositoryPath\n$normalizedDefaultBranch\n$normalizedWriteBranch';
    if (_activeLocalGitConfigurationKey == configurationKey ||
        _pendingLocalGitConfigurationKey == configurationKey) {
      return;
    }
    _pendingLocalGitConfigurationKey = configurationKey;
    final previousViewModel = viewModel;
    _rememberHostedRepositoryConfiguration(previousViewModel);
    try {
      WorkspaceProfile? workspace;
      if (widget.repository == null) {
        final input = WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: normalizedRepositoryPath,
          defaultBranch: normalizedDefaultBranch,
          writeBranch: normalizedWriteBranch,
          displayName: displayName,
        );
        try {
          workspace = await widget.workspaceProfileService.createProfile(
            input,
            select: false,
          );
        } on WorkspaceProfileException {
          final savedState = await widget.workspaceProfileService.loadState();
          workspace = savedState.profiles.firstWhere(
            (profile) =>
                profile.targetType == WorkspaceProfileTargetType.local &&
                profile.normalizedTarget == normalizedRepositoryPath &&
                profile.normalizedDefaultBranch == normalizedDefaultBranch &&
                profile.normalizedWriteBranch == normalizedWriteBranch,
          );
        }
      }
      final prepared = await _prepareWorkspaceSwitch(
        workspace ??
            WorkspaceProfile.create(
              WorkspaceProfileInput(
                targetType: WorkspaceProfileTargetType.local,
                target: normalizedRepositoryPath,
                defaultBranch: normalizedDefaultBranch,
                writeBranch: normalizedWriteBranch,
              ),
            ),
        previousViewModel: previousViewModel,
        showFailureMessage: true,
      );
      if (prepared == null) {
        return;
      }
      WorkspaceProfilesState? selectedState;
      if (workspace != null) {
        selectedState = await widget.workspaceProfileService.selectProfile(
          workspace.id,
        );
        selectedState = await _saveLocalWorkspaceAvailability(
          workspace.id,
          isAvailable: true,
        );
      }
      await _commitPreparedWorkspaceSwitch(
        prepared,
        previousViewModel: previousViewModel,
        workspaceState: selectedState,
      );
    } finally {
      if (_pendingLocalGitConfigurationKey == configurationKey) {
        _pendingLocalGitConfigurationKey = null;
      }
    }
  }
  Future<void> _switchToHostedRepository({
    required String repository,
    required String defaultBranch,
    required String writeBranch,
  }) async {
    final normalizedRepository = normalizeWorkspaceTarget(
      WorkspaceProfileTargetType.hosted,
      repository,
    );
    final normalizedDefaultBranch = normalizeWorkspaceBranch(defaultBranch);
    final normalizedWriteBranch = normalizeWorkspaceBranch(writeBranch);
    if (normalizedRepository.isEmpty ||
        normalizedDefaultBranch.isEmpty ||
        normalizedWriteBranch.isEmpty) {
      return;
    }
    final previousViewModel = viewModel;
    WorkspaceProfile? workspace;
    if (widget.repository == null) {
      final input = WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.hosted,
        target: normalizedRepository,
        defaultBranch: normalizedDefaultBranch,
        writeBranch: normalizedWriteBranch,
      );
      try {
        workspace = await widget.workspaceProfileService.createProfile(
          input,
          select: false,
        );
      } on WorkspaceProfileException {
        final savedState = await widget.workspaceProfileService.loadState();
        workspace = savedState.profiles.firstWhere(
          (profile) =>
              profile.targetType == WorkspaceProfileTargetType.hosted &&
              profile.normalizedTarget == normalizedRepository &&
              profile.normalizedDefaultBranch == normalizedDefaultBranch &&
              profile.normalizedWriteBranch == normalizedWriteBranch,
        );
      }
    }
    final targetWorkspace =
        workspace ??
        WorkspaceProfile.create(
          WorkspaceProfileInput(
            targetType: WorkspaceProfileTargetType.hosted,
            target: normalizedRepository,
            defaultBranch: normalizedDefaultBranch,
            writeBranch: normalizedWriteBranch,
          ),
        );
    final prepared = await _prepareWorkspaceSwitch(
      targetWorkspace,
      previousViewModel: previousViewModel,
      showFailureMessage: true,
      deferAccessRestore: _shouldDeferAccessRestoreForWorkspace(
        targetWorkspace,
      ),
    );
    if (prepared == null) {
      return;
    }
    WorkspaceProfilesState? selectedState;
    if (workspace != null) {
      selectedState = await widget.workspaceProfileService.selectProfile(
        workspace.id,
      );
      selectedState =
          await _persistPreparedHostedWorkspaceState(
            prepared,
            workspaceState: selectedState,
          ) ??
          selectedState;
    }
    await _commitPreparedWorkspaceSwitch(
      prepared,
      previousViewModel: previousViewModel,
      workspaceState: selectedState,
    );
  }
  Future<void> _switchToLastHostedRepository() async {
    final configuration = _lastHostedRepositoryConfiguration;
    if (configuration == null) {
      return;
    }
    if (widget.repository != null) {
      final previousViewModel = viewModel;
      final nextViewModel = _createViewModel(
        repository: widget.repository,
        previous: previousViewModel,
        autoLoad: false,
        workspaceId: null,
      );
      await nextViewModel.load();
      if (!mounted) {
        nextViewModel.dispose();
        return;
      }
      setState(() {
        viewModel = nextViewModel;
        _rememberHostedRepositoryConfiguration(nextViewModel);
        _activeLocalGitConfigurationKey = null;
        _isCreateIssueVisible = false;
        _createIssuePrefill = null;
        _pendingWorkspaceRestoreFailure = null;
      });
      if (!identical(previousViewModel, nextViewModel)) {
        previousViewModel.dispose();
      }
      return;
    }
    await _switchToHostedRepository(
      repository: configuration.repository,
      defaultBranch: configuration.defaultBranch,
      writeBranch: configuration.writeBranch,
    );
  }
  void _rememberHostedRepositoryConfiguration(TrackerViewModel model) {
    if (model.usesLocalPersistence) {
      return;
    }
    final project = model.project;
    if (project == null || project.repository.trim().isEmpty) {
      return;
    }
    _lastHostedRepositoryConfiguration = _HostedRepositoryConfiguration(
      repository: project.repository,
      defaultBranch: project.branch,
      writeBranch: project.branch,
    );
  }
  Future<void> _switchToWorkspace(
    WorkspaceProfile workspace, {
    String? workspaceSwitcherFocusWorkspaceId,
  }) async {
    final preservedBrowserScrollSnapshot =
        _isDesktopWorkspaceSwitcherVisible && kIsWeb
        ? (_desktopWorkspaceSwitcherScrollSnapshot ??
              browser_workspace_switcher_focus_monitor
                  .captureBrowserViewportScrollSnapshot())
        : null;
    final previousViewModel = viewModel;
    final prepared = await _prepareWorkspaceSwitch(
      workspace,
      previousViewModel: previousViewModel,
      showFailureMessage: true,
      deferAccessRestore: _shouldDeferAccessRestoreForWorkspace(workspace),
    );
    if (prepared == null) {
      return;
    }
    var selectedState = await widget.workspaceProfileService.selectProfile(
      workspace.id,
    );
    if (workspace.isLocal) {
      selectedState = await _saveLocalWorkspaceAvailability(
        workspace.id,
        isAvailable: true,
      );
    }
    selectedState =
        await _persistPreparedHostedWorkspaceState(
          prepared,
          workspaceState: selectedState,
        ) ??
        selectedState;
    await _commitPreparedWorkspaceSwitch(
      prepared,
      previousViewModel: previousViewModel,
      workspaceState: selectedState,
      workspaceSwitcherFocusWorkspaceId: workspaceSwitcherFocusWorkspaceId,
      preservedBrowserScrollSnapshot: preservedBrowserScrollSnapshot,
    );
  }
  Future<void> _commitPreparedWorkspaceSwitch(
    _PreparedWorkspaceSwitch prepared, {
    required TrackerViewModel previousViewModel,
    WorkspaceProfilesState? workspaceState,
    String? workspaceSwitcherFocusWorkspaceId,
    browser_workspace_switcher_focus_monitor.BrowserViewportScrollSnapshot?
    preservedBrowserScrollSnapshot,
  }) async {
    if (!mounted) {
      prepared.viewModel.dispose();
      return;
    }
    final preservesStartupHostedFallback =
        _startupHostedFallbackWorkspaceId != null &&
        prepared.workspace?.isHosted == true &&
        prepared.workspace?.id == _startupHostedFallbackWorkspaceId;
    if (!preservesStartupHostedFallback) {
      _startupHostedFallbackWorkspaceId = null;
      _isPersistingStartupHostedFallbackSelection = false;
    }
    setState(() {
      viewModel = prepared.viewModel;
      _rememberHostedRepositoryConfiguration(prepared.viewModel);
      _activeLocalGitConfigurationKey = prepared.localConfigurationKey;
      _isCreateIssueVisible = false;
      _createIssuePrefill = null;
      _showsWorkspaceOnboarding = false;
      _workspaceProfilesReady = true;
      _pendingWorkspaceRestoreFailure = null;
      if (workspaceState != null) {
        _workspaceState = workspaceState;
      } else if (prepared.workspace != null) {
        _workspaceState = _workspaceState.copyWith(
          activeWorkspaceId: prepared.workspace!.id,
        );
      }
      if (workspaceSwitcherFocusWorkspaceId != null) {
        _requestedWorkspaceSwitcherRowFocusId =
            workspaceSwitcherFocusWorkspaceId;
        _workspaceSwitcherRowFocusRequestVersion += 1;
      } else {
        _requestedWorkspaceSwitcherRowFocusId = null;
      }
    });
    if (prepared.workspace == null || !prepared.workspace!.isLocal) {
      _pendingStartupLocalFallbackWorkspaceId = null;
    }
    if (!identical(previousViewModel, prepared.viewModel)) {
      previousViewModel.dispose();
    }
    await _refreshWorkspaceSwitcherState(workspaceState ?? _workspaceState);
    if (preservesStartupHostedFallback &&
        !_isPersistingStartupHostedFallbackSelection &&
        viewModel.workspaceId == _startupHostedFallbackWorkspaceId) {
      _startupHostedFallbackWorkspaceId = null;
    }
    if (_isDesktopWorkspaceSwitcherVisible &&
        workspaceSwitcherFocusWorkspaceId != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || !_isDesktopWorkspaceSwitcherVisible) {
          return;
        }
        browser_workspace_switcher_focus_monitor
            .syncBrowserWorkspaceSwitcherRowTabIndices(
              activeWorkspaceId: workspaceSwitcherFocusWorkspaceId,
            );
        _requestDesktopWorkspaceSwitcherBrowserFocus(
          browserWorkspaceSwitcherRowSemanticsIdentifier(
            workspaceSwitcherFocusWorkspaceId,
          ),
        );
        if (preservedBrowserScrollSnapshot != null) {
          browser_workspace_switcher_focus_monitor
              .restoreBrowserViewportScrollSnapshot(
                snapshot: preservedBrowserScrollSnapshot,
              );
        }
      });
    } else if (_isDesktopWorkspaceSwitcherVisible &&
        workspaceSwitcherFocusWorkspaceId == null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted || !_isDesktopWorkspaceSwitcherVisible) {
          return;
        }
        _desktopWorkspaceSwitcherFocusScopeNode.requestFocus();
        if (preservedBrowserScrollSnapshot != null) {
          browser_workspace_switcher_focus_monitor
              .restoreBrowserViewportScrollSnapshot(
                snapshot: preservedBrowserScrollSnapshot,
              );
        }
      });
    }
  }
  Future<void> _ensureCurrentContextWorkspaceMigration() async {
    if (widget.repository != null) {
      return;
    }
    final currentContext = _workspaceProfileInputForCurrentContext();
    var workspace = await widget.workspaceProfileService
        .ensureLegacyContextMigrated(currentContext);
    var updatedState = await widget.workspaceProfileService.loadState();
    if (workspace == null &&
        currentContext != null &&
        currentContext.isValid &&
        !updatedState.hasProfiles) {
      try {
        workspace = await widget.workspaceProfileService.createProfile(
          currentContext,
        );
      } on WorkspaceProfileException {
        updatedState = await widget.workspaceProfileService.loadState();
        if (updatedState.activeWorkspace case final activeWorkspace?) {
          workspace = activeWorkspace;
        }
      }
      updatedState = await widget.workspaceProfileService.loadState();
    }
    if (!mounted) {
      return;
    }
    setState(() {
      _workspaceState = updatedState;
    });
    if (workspace != null) {
      viewModel.updateWorkspaceScope(workspace.id);
    }
    await _refreshWorkspaceSwitcherState(updatedState);
  }
  WorkspaceProfileInput? _workspaceProfileInputForCurrentContext() {
    final project = viewModel.project;
    if (project == null) {
      return null;
    }
    return WorkspaceProfileInput(
      targetType: viewModel.usesLocalPersistence
          ? WorkspaceProfileTargetType.local
          : WorkspaceProfileTargetType.hosted,
      target: project.repository,
      defaultBranch: project.branch,
      writeBranch: project.branch,
    );
  }
  Future<void> _selectWorkspaceProfile(WorkspaceProfile workspace) async {
    if (widget.repository != null) {
      return;
    }
    await _switchToWorkspace(workspace);
  }
  Future<void> _retryWorkspaceRestore() async {
    if (widget.repository != null) {
      return;
    }
    final nextState = await widget.workspaceProfileService.loadState();
    if (!mounted) {
      return;
    }
    setState(() {
      _workspaceState = nextState;
      _workspaceProfilesReady = true;
    });
    await _refreshWorkspaceSwitcherState(nextState);
    final restored = await _restoreWorkspaceFromSavedState(nextState);
    if (restored) {
      return;
    }
    if (!mounted) {
      return;
    }
    if (_pendingWorkspaceRestoreFailure case final failure?) {
      viewModel.showMessage(
        TrackerMessage.workspaceRestoreFailed(
          workspaceName: failure.workspaceName,
          reason: failure.reason,
        ),
      );
    }
    setState(() {
      _showsWorkspaceOnboarding = true;
    });
  }
  Future<void> _retryStartupRecovery() async {
    await viewModel.retryStartupRecovery();
    if (!mounted) {
      return;
    }
    await _ensureCurrentContextWorkspaceMigrationIfNeeded();
  }
  Future<void> _retryUnavailableLocalWorkspace(
    WorkspaceProfile workspace,
  ) async {
    if (widget.repository != null || !workspace.isLocal) {
      return;
    }
    final previousViewModel = viewModel;
    final nextWorkspace = workspace;
    if (!mounted) {
      return;
    }
    final browserPrepared = await _prepareBrowserLocalWorkspaceSwitch(
      nextWorkspace,
      previousViewModel: previousViewModel,
    );
    if (browserPrepared != null) {
      var selectedState = await widget.workspaceProfileService.selectProfile(
        nextWorkspace.id,
      );
      selectedState = await _saveLocalWorkspaceAvailability(
        nextWorkspace.id,
        isAvailable: true,
      );
      await _commitPreparedWorkspaceSwitch(
        browserPrepared,
        previousViewModel: previousViewModel,
        workspaceState: selectedState,
      );
      return;
    }
    final browserReauthenticated =
        await _prepareBrowserLocalWorkspaceSwitchWithLoader(
          nextWorkspace,
          previousViewModel: previousViewModel,
          repositoryLoader: widget.requestBrowserLocalRepositoryAccess,
        );
    if (browserReauthenticated != null) {
      var selectedState = await widget.workspaceProfileService.selectProfile(
        nextWorkspace.id,
      );
      selectedState = await _saveLocalWorkspaceAvailability(
        nextWorkspace.id,
        isAvailable: true,
      );
      await _commitPreparedWorkspaceSwitch(
        browserReauthenticated,
        previousViewModel: previousViewModel,
        workspaceState: selectedState,
      );
      return;
    }
    String? selectedPath;
    try {
      selectedPath = await widget.workspaceDirectoryPicker(
        initialDirectory: workspace.target,
      );
    } on WorkspaceDirectorySelectionMismatchException catch (error) {
      await _showUnavailableLocalWorkspaceRetryMismatch(
        workspace,
        message: error.message,
      );
      return;
    }
    if (!mounted || selectedPath == null || selectedPath.trim().isEmpty) {
      return;
    }
    final normalizedTarget = normalizeWorkspaceTarget(
      WorkspaceProfileTargetType.local,
      selectedPath,
    );
    if (normalizedTarget.isEmpty) {
      return;
    }
    if (normalizedTarget != workspace.normalizedTarget) {
      await _showUnavailableLocalWorkspaceRetryMismatch(
        workspace,
        message:
            'Selected directory does not match the saved workspace configuration.',
      );
      return;
    }
    if (!mounted) {
      return;
    }
    final prepared =
        await _prepareBrowserLocalWorkspaceSwitchWithLoader(
          nextWorkspace,
          previousViewModel: previousViewModel,
          repositoryLoader: widget.requestBrowserLocalRepositoryAccess,
        ) ??
        await _prepareWorkspaceSwitch(
          nextWorkspace,
          previousViewModel: previousViewModel,
          showFailureMessage: false,
        );
    if (prepared != null) {
      var selectedState = await widget.workspaceProfileService.selectProfile(
        nextWorkspace.id,
      );
      selectedState = await _saveLocalWorkspaceAvailability(
        nextWorkspace.id,
        isAvailable: true,
      );
      await _commitPreparedWorkspaceSwitch(
        prepared,
        previousViewModel: previousViewModel,
        workspaceState: selectedState,
      );
      return;
    }
    var reason = _workspaceValidationFailureReason(nextWorkspace);
    if (_isUnsupportedActiveLocalStartupAccess(reason)) {
      final browserPrepared = await _prepareBrowserLocalWorkspaceSwitch(
        nextWorkspace,
        previousViewModel: previousViewModel,
      );
      if (browserPrepared != null) {
        var selectedState = await widget.workspaceProfileService.selectProfile(
          nextWorkspace.id,
        );
        selectedState = await _saveLocalWorkspaceAvailability(
          nextWorkspace.id,
          isAvailable: true,
        );
        await _commitPreparedWorkspaceSwitch(
          browserPrepared,
          previousViewModel: previousViewModel,
          workspaceState: selectedState,
        );
        return;
      }
      reason = _workspaceValidationFailureReason(nextWorkspace);
    }
    previousViewModel.showMessage(
      TrackerMessage.workspaceSwitchFailed(
        workspaceName: nextWorkspace.displayName,
        reason: reason,
      ),
    );
  }
  Future<void> _showUnavailableLocalWorkspaceRetryMismatch(
    WorkspaceProfile workspace, {
    required String message,
  }) async {
    _rememberWorkspaceValidationFailure(workspace, message);
    await _saveLocalWorkspaceAvailability(workspace.id, isAvailable: false);
    if (!mounted) {
      return;
    }
    viewModel.showMessage(
      TrackerMessage.workspaceSwitchFailed(
        workspaceName: workspace.displayName,
        reason: message,
      ),
    );
  }
  Future<void> _deleteWorkspaceProfile(WorkspaceProfile workspace) async {
    final nextState = await widget.workspaceProfileService.deleteProfile(
      workspace.id,
    );
    if (!mounted) {
      return;
    }
    setState(() {
      _workspaceState = nextState;
      _showsWorkspaceOnboarding = _shouldShowWorkspaceOnboarding(nextState);
    });
    await _refreshWorkspaceSwitcherState(nextState);
    final nextActiveWorkspace = nextState.activeWorkspace;
    if (nextActiveWorkspace != null) {
      final restored = await _restoreWorkspaceFromSavedState(nextState);
      if (restored) {
        return;
      }
    }
    if (_shouldShowWorkspaceOnboarding(nextState)) {
      viewModel.updateWorkspaceScope(null);
      setState(() {
        _activeLocalGitConfigurationKey = null;
        _isCreateIssueVisible = false;
        _createIssuePrefill = null;
        _workspaceProfilesReady = true;
        _showsWorkspaceOnboarding = true;
      });
      return;
    }
    viewModel.updateWorkspaceScope(null);
    if (widget.repository != null) {
      return;
    }
    final previousViewModel = viewModel;
    final nextViewModel = _createViewModel(autoLoad: false, workspaceId: null);
    setState(() {
      viewModel = nextViewModel;
      _activeLocalGitConfigurationKey = null;
      _isCreateIssueVisible = false;
      _createIssuePrefill = null;
      _workspaceProfilesReady = true;
    });
    previousViewModel.dispose();
    await nextViewModel.load();
    if (_pendingWorkspaceRestoreFailure case final failure?) {
      nextViewModel.showMessage(
        TrackerMessage.workspaceRestoreFailed(
          workspaceName: failure.workspaceName,
          reason: failure.reason,
        ),
      );
    }
    nextViewModel.openProjectSettings();
  }
  Future<void> _addWorkspaceProfile(WorkspaceProfileInput input) async {
    final normalizedInput = WorkspaceProfileInput(
      targetType: input.targetType,
      target: normalizeWorkspaceTarget(input.targetType, input.target),
      defaultBranch: normalizeWorkspaceBranch(input.defaultBranch),
      writeBranch: normalizeWorkspaceBranch(input.writeBranch),
    );
    try {
      final workspace = await widget.workspaceProfileService.createProfile(
        normalizedInput,
        select: false,
      );
      final nextState = await widget.workspaceProfileService.loadState();
      if (!mounted) {
        return;
      }
      setState(() {
        _workspaceState = nextState;
      });
      await _refreshWorkspaceSwitcherState(nextState);
      await _switchToWorkspace(workspace);
    } on WorkspaceProfileException catch (error) {
      viewModel.showMessage(
        TrackerMessage.workspaceSwitchFailed(
          workspaceName: normalizedInput.target,
          reason: error.message,
        ),
      );
    }
  }
  Future<void> _openWorkspaceSwitcher(
    BuildContext context, {
    required bool compact,
  }) async {
    await _refreshWorkspaceSwitcherState();
    if (!mounted) {
      return;
    }
    if (!context.mounted) {
      return;
    }
    if (compact) {
      final content = _buildWorkspaceSwitcherContent(compact: true);
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (sheetContext) => SafeArea(
          child: Padding(
            padding: EdgeInsets.only(
              bottom: MediaQuery.of(sheetContext).viewInsets.bottom,
            ),
            child: content,
          ),
        ),
      );
      return;
    }
    if (_isDesktopWorkspaceSwitcherVisible) {
      _closeDesktopWorkspaceSwitcher();
      return;
    }
    final activeWorkspaceId = _workspaceState.activeWorkspaceId;
    _startDesktopWorkspaceSwitcherBrowserFocusMonitor();
    _cancelDesktopWorkspaceSwitcherBrowserFocusRequest();
    setState(() {
      _isDesktopWorkspaceSwitcherVisible = true;
      _desktopWorkspaceSwitcherProfileOrder = [
        for (final profile in _workspaceState.profiles) profile.id,
      ];
      _desktopWorkspaceSwitcherScrollSnapshot = kIsWeb
          ? browser_workspace_switcher_focus_monitor
                .captureBrowserViewportScrollSnapshot()
          : null;
      _requestedWorkspaceSwitcherRowFocusId = null;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_isDesktopWorkspaceSwitcherVisible) {
        return;
      }
      if (activeWorkspaceId != null) {
        browser_workspace_switcher_focus_monitor
            .syncBrowserWorkspaceSwitcherRowTabIndices(
              activeWorkspaceId: activeWorkspaceId,
            );
      }
      _workspaceSwitcherTriggerFocusNode.requestFocus();
      if (kIsWeb) {
        _requestDesktopWorkspaceSwitcherBrowserFocus(
          browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
        );
      }
    });
  }
  void _startDesktopWorkspaceSwitcherBrowserFocusMonitor() {
    _stopDesktopWorkspaceSwitcherBrowserFocusMonitor();
    if (!kIsWeb) {
      return;
    }
    _desktopWorkspaceSwitcherBrowserFocusMonitor =
        browser_workspace_switcher_focus_monitor
            .createBrowserWorkspaceSwitcherFocusMonitorSubscription(
              onBrowserTab: () {
                _scheduleDesktopWorkspaceSwitcherBrowserBlurCheck();
              },
              onBrowserFocusOutside: () {
                if (!mounted || !_isDesktopWorkspaceSwitcherVisible) {
                  return;
                }
                _closeDesktopWorkspaceSwitcher(restoreTriggerFocus: false);
              },
              onBrowserEscape: () {
                if (!mounted || !_isDesktopWorkspaceSwitcherVisible) {
                  return;
                }
                _closeDesktopWorkspaceSwitcher();
              },
              onBrowserBoundaryKey: (key) {
                if (!mounted || !_isDesktopWorkspaceSwitcherVisible) {
                  return;
                }
                switch (key) {
                  case 'Home':
                    unawaited(_switchToBoundaryWorkspace(selectFirst: true));
                  case 'End':
                    unawaited(_switchToBoundaryWorkspace(selectFirst: false));
                }
              },
            );
  }
  void _stopDesktopWorkspaceSwitcherBrowserFocusMonitor() {
    _desktopWorkspaceSwitcherBrowserFocusMonitor?.cancel();
    _desktopWorkspaceSwitcherBrowserFocusMonitor = null;
  }
  void _scheduleDesktopWorkspaceSwitcherBrowserBlurCheck() {
    _cancelDesktopWorkspaceSwitcherBrowserBlurCheck();
    var attemptsRemaining = 6;
    void verifyFocus() {
      if (!mounted || !_isDesktopWorkspaceSwitcherVisible) {
        _cancelDesktopWorkspaceSwitcherBrowserBlurCheck();
        return;
      }
      final browserFocusWithinSwitcher =
          browser_workspace_switcher_focus_monitor
              .isBrowserFocusWithinWorkspaceSwitcher();
      if (!browserFocusWithinSwitcher ||
          !_isDesktopWorkspaceSwitcherFocused()) {
        _cancelDesktopWorkspaceSwitcherBrowserBlurCheck();
        _closeDesktopWorkspaceSwitcher(restoreTriggerFocus: false);
        return;
      }
      attemptsRemaining -= 1;
      if (attemptsRemaining <= 0) {
        _cancelDesktopWorkspaceSwitcherBrowserBlurCheck();
      }
    }
    _desktopWorkspaceSwitcherBrowserBlurCheckTimer = Timer.periodic(
      const Duration(milliseconds: 16),
      (_) => verifyFocus(),
    );
    Timer.run(verifyFocus);
  }
  void _cancelDesktopWorkspaceSwitcherBrowserBlurCheck() {
    _desktopWorkspaceSwitcherBrowserBlurCheckTimer?.cancel();
    _desktopWorkspaceSwitcherBrowserBlurCheckTimer = null;
  }
  bool _isDesktopWorkspaceSwitcherFocused() {
    if (kIsWeb &&
        browser_workspace_switcher_focus_monitor
            .isBrowserFocusWithinWorkspaceSwitcher()) {
      return true;
    }
    return _workspaceSwitcherTriggerFocusNode.hasFocus ||
        _desktopWorkspaceSwitcherFocusScopeNode.hasFocus;
  }
  void _handleDesktopWorkspaceSwitcherFocusChange() {
    if (!kIsWeb || !_isDesktopWorkspaceSwitcherVisible) {
      return;
    }
    Timer.run(() {
      if (!mounted || !_isDesktopWorkspaceSwitcherVisible) {
        return;
      }
      if (_isDesktopWorkspaceSwitcherFocused()) {
        return;
      }
      _closeDesktopWorkspaceSwitcher(restoreTriggerFocus: false);
    });
  }
  void _requestDesktopWorkspaceSwitcherBrowserFocus(
    String semanticsIdentifier,
  ) {
    _cancelDesktopWorkspaceSwitcherBrowserFocusRequest();
    _desktopWorkspaceSwitcherBrowserFocusRequest =
        browser_workspace_switcher_focus_monitor
            .requestBrowserWorkspaceSwitcherFocus(
              semanticsIdentifier: semanticsIdentifier,
            );
  }
  void _cancelDesktopWorkspaceSwitcherBrowserFocusRequest() {
    _desktopWorkspaceSwitcherBrowserFocusRequest?.cancel();
    _desktopWorkspaceSwitcherBrowserFocusRequest = null;
  }
  void _closeDesktopWorkspaceSwitcher({bool restoreTriggerFocus = true}) {
    if (!_isDesktopWorkspaceSwitcherVisible) {
      return;
    }
    _stopDesktopWorkspaceSwitcherBrowserFocusMonitor();
    _cancelDesktopWorkspaceSwitcherBrowserFocusRequest();
    _cancelDesktopWorkspaceSwitcherBrowserBlurCheck();
    setState(() {
      _isDesktopWorkspaceSwitcherVisible = false;
      _desktopWorkspaceSwitcherProfileOrder = null;
      _desktopWorkspaceSwitcherScrollSnapshot = null;
      _requestedWorkspaceSwitcherRowFocusId = null;
    });
    if (!restoreTriggerFocus) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      final triggerContext = _workspaceSwitcherTriggerAnchorKey.currentContext;
      if (triggerContext != null) {
        FocusScope.of(
          triggerContext,
        ).requestFocus(_workspaceSwitcherTriggerFocusNode);
      } else {
        _workspaceSwitcherTriggerFocusNode.requestFocus();
      }
      if (kIsWeb) {
        _requestDesktopWorkspaceSwitcherBrowserFocus(
          browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
        );
      }
    });
  }
  Rect _resolveWorkspaceSwitcherDesktopPanelRect({
    required Size viewportSize,
    required EdgeInsets safePadding,
    Rect? overlayHostRect,
  }) {
    const horizontalMargin = 12.0;
    const topGap = 8.0;
    final availableWidth = math.max(
      0.0,
      viewportSize.width - (horizontalMargin * 2),
    );
    final panelWidth = availableWidth <= 360
        ? availableWidth
        : math.min(560.0, availableWidth);
    final triggerRect = _workspaceSwitcherTriggerRect();
    final anchoredRight = triggerRect == null || overlayHostRect == null
        ? viewportSize.width - horizontalMargin
        : triggerRect.right - overlayHostRect.left;
    final anchoredTop =
        ((triggerRect == null || overlayHostRect == null
            ? (safePadding.top + _desktopTopBarControlHeight)
            : triggerRect.bottom - overlayHostRect.top) +
        topGap);
    final maxLeft = math.max(
      horizontalMargin,
      viewportSize.width - horizontalMargin - panelWidth,
    );
    final left = (anchoredRight - panelWidth).clamp(horizontalMargin, maxLeft);
    final maxTop = math.max(
      safePadding.top + 8,
      viewportSize.height - safePadding.bottom - 24,
    );
    final top = anchoredTop.clamp(safePadding.top + 8, maxTop);
    return Rect.fromLTWH(left.toDouble(), top.toDouble(), panelWidth, 0);
  }
  Rect? _workspaceSwitcherOverlayHostRect() {
    final hostContext = _workspaceSwitcherOverlayHostKey.currentContext;
    if (hostContext == null) {
      return null;
    }
    final renderObject = hostContext.findRenderObject();
    if (renderObject is! RenderBox || !renderObject.hasSize) {
      return null;
    }
    final offset = renderObject.localToGlobal(Offset.zero);
    return offset & renderObject.size;
  }
  Rect? _desktopWorkspaceSwitcherPanelRect() {
    final hostRect = _workspaceSwitcherOverlayHostRect();
    if (hostRect == null || hostRect.width <= 24 || hostRect.height <= 24) {
      return null;
    }
    return _resolveWorkspaceSwitcherDesktopPanelRect(
      viewportSize: hostRect.size,
      safePadding: EdgeInsets.zero,
      overlayHostRect: hostRect,
    );
  }
  Rect? _workspaceSwitcherTriggerRect() {
    final triggerContext = _workspaceSwitcherTriggerAnchorKey.currentContext;
    if (triggerContext == null) {
      return null;
    }
    final renderObject = triggerContext.findRenderObject();
    if (renderObject is! RenderBox || !renderObject.hasSize) {
      return null;
    }
    final offset = renderObject.localToGlobal(Offset.zero);
    return offset & renderObject.size;
  }
  Future<void> _confirmAndDeleteWorkspaceFromSwitcher(
    BuildContext context,
    WorkspaceProfile workspace, {
    VoidCallback? closeSwitcher,
  }) async {
    final confirmed = await _confirmWorkspaceDeletion(context, workspace);
    if (!mounted || !confirmed) {
      return;
    }
    closeSwitcher?.call();
    await _deleteWorkspaceProfile(workspace);
  }
  Widget _buildWorkspaceSwitcherContent({
    required bool compact,
    bool desktopVisible = true,
  }) {
    final content = Builder(
      builder: (sheetContext) {
        final workspaceSwitcherState = _workspaceState.copyWith(
          profiles: _desktopWorkspaceSwitcherProfiles(),
        );
        final closeSwitcher = compact
            ? () => Navigator.of(sheetContext, rootNavigator: true).pop()
            : _closeDesktopWorkspaceSwitcher;
        return Semantics(
          container: true,
          explicitChildNodes: true,
          identifier: browserWorkspaceSwitcherSemanticsIdentifier,
          label: AppLocalizations.of(sheetContext)!.workspaceSwitcher,
          onDidLoseAccessibilityFocus:
              shouldCloseDesktopWorkspaceSwitcherOnAccessibilityFocusLoss(
                compact: compact,
                isWeb: kIsWeb,
              )
              ? () {
                  if (!desktopVisible) {
                    return;
                  }
                  _closeDesktopWorkspaceSwitcher(restoreTriggerFocus: false);
                }
              : null,
          child: SizedBox(
            width: desktopVisible || compact ? null : 1,
            height: desktopVisible || compact ? null : 1,
            child: Offstage(
              offstage: !desktopVisible && !compact,
              child: _WorkspaceSwitcherSheet(
                sheetKey: desktopVisible || compact
                    ? const ValueKey('workspace-switcher-sheet')
                    : null,
                exposeActiveSummarySemantics: true,
                viewModel: viewModel,
                workspaces: workspaceSwitcherState,
                authenticatedWorkspaceIds: _authenticatedWorkspaceIds,
                hostedWorkspaceAccessModes: _hostedWorkspaceAccessModes,
                localWorkspaceAvailability: _localWorkspaceAvailability,
                requestedFocusedWorkspaceId:
                    _requestedWorkspaceSwitcherRowFocusId,
                focusRequestVersion: _workspaceSwitcherRowFocusRequestVersion,
                onSelectWorkspace: (workspace) {
                  closeSwitcher();
                  unawaited(_switchToWorkspace(workspace));
                },
                onRetryUnavailableLocalWorkspace: (workspace) {
                  closeSwitcher();
                  unawaited(_retryUnavailableLocalWorkspace(workspace));
                },
                onDeleteWorkspace: (workspace) {
                  unawaited(
                    _confirmAndDeleteWorkspaceFromSwitcher(
                      sheetContext,
                      workspace,
                      closeSwitcher: closeSwitcher,
                    ),
                  );
                },
                onAddWorkspace: (input) async {
                  closeSwitcher();
                  await _addWorkspaceProfile(input);
                },
                onMoveWorkspaceSelection: (step) =>
                    unawaited(_switchToAdjacentWorkspace(step: step)),
                onSelectFirstWorkspace: () =>
                    unawaited(_switchToBoundaryWorkspace(selectFirst: true)),
                onSelectLastWorkspace: () =>
                    unawaited(_switchToBoundaryWorkspace(selectFirst: false)),
              ),
            ),
          ),
        );
      },
    );
    if (compact) {
      return content;
    }
    return CallbackShortcuts(
      bindings: desktopVisible
          ? <ShortcutActivator, VoidCallback>{
              const SingleActivator(LogicalKeyboardKey.escape):
                  _closeDesktopWorkspaceSwitcher,
              const SingleActivator(LogicalKeyboardKey.arrowDown): () =>
                  unawaited(_switchToAdjacentWorkspace(step: 1)),
              const SingleActivator(LogicalKeyboardKey.arrowUp): () =>
                  unawaited(_switchToAdjacentWorkspace(step: -1)),
              const SingleActivator(LogicalKeyboardKey.home): () =>
                  unawaited(_switchToBoundaryWorkspace(selectFirst: true)),
              const SingleActivator(LogicalKeyboardKey.end): () =>
                  unawaited(_switchToBoundaryWorkspace(selectFirst: false)),
            }
          : const <ShortcutActivator, VoidCallback>{},
      child: FocusScope(
        node: _desktopWorkspaceSwitcherFocusScopeNode,
        autofocus: desktopVisible,
        canRequestFocus: desktopVisible,
        descendantsAreFocusable: desktopVisible,
        descendantsAreTraversable: desktopVisible,
        onKeyEvent: (node, event) {
          if (!desktopVisible) {
            return KeyEventResult.ignored;
          }
          if (!node.hasPrimaryFocus) {
            return KeyEventResult.ignored;
          }
          if (event is! KeyDownEvent && event is! KeyRepeatEvent) {
            return KeyEventResult.ignored;
          }
          final logicalKey = event.logicalKey;
          if (logicalKey != LogicalKeyboardKey.space &&
              logicalKey != LogicalKeyboardKey.enter &&
              logicalKey != LogicalKeyboardKey.numpadEnter) {
            return KeyEventResult.ignored;
          }
          _closeDesktopWorkspaceSwitcher();
          return KeyEventResult.handled;
        },
        child: content,
      ),
    );
  }
  void _openWorkspaceOnboarding() {
    if (_showsWorkspaceOnboarding) {
      return;
    }
    setState(() {
      _showsWorkspaceOnboarding = true;
    });
  }
  void _closeWorkspaceOnboarding() {
    if (!_showsWorkspaceOnboarding ||
        _shouldShowWorkspaceOnboarding(_workspaceState)) {
      return;
    }
    setState(() {
      _showsWorkspaceOnboarding = false;
    });
  }
  Future<void> _switchToAdjacentWorkspace({required int step}) async {
    final profiles = _desktopWorkspaceSwitcherProfiles();
    if (!_isDesktopWorkspaceSwitcherVisible || profiles.length < 2) {
      return;
    }
    final activeWorkspaceId = _workspaceState.activeWorkspaceId;
    final currentIndex = activeWorkspaceId == null
        ? 0
        : profiles.indexWhere((profile) => profile.id == activeWorkspaceId);
    final safeCurrentIndex = currentIndex < 0 ? 0 : currentIndex;
    final nextIndex =
        (safeCurrentIndex + step + profiles.length) % profiles.length;
    await _switchToWorkspace(
      profiles[nextIndex],
      workspaceSwitcherFocusWorkspaceId: profiles[nextIndex].id,
    );
  }
  Future<void> _switchToBoundaryWorkspace({required bool selectFirst}) async {
    final profiles = _desktopWorkspaceSwitcherProfiles();
    if (!_isDesktopWorkspaceSwitcherVisible || profiles.isEmpty) {
      return;
    }
    final workspace = selectFirst ? profiles.first : profiles.last;
    await _switchToWorkspace(
      workspace,
      workspaceSwitcherFocusWorkspaceId: workspace.id,
    );
  }
  void _focusActiveWorkspaceSwitcherRow() {
    final activeWorkspaceId = _workspaceState.activeWorkspaceId;
    if (!_isDesktopWorkspaceSwitcherVisible || activeWorkspaceId == null) {
      return;
    }
    setState(() {
      _requestedWorkspaceSwitcherRowFocusId = activeWorkspaceId;
      _workspaceSwitcherRowFocusRequestVersion += 1;
    });
    if (!kIsWeb) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_isDesktopWorkspaceSwitcherVisible) {
        return;
      }
      browser_workspace_switcher_focus_monitor
          .syncBrowserWorkspaceSwitcherRowTabIndices(
            activeWorkspaceId: activeWorkspaceId,
          );
      _requestDesktopWorkspaceSwitcherBrowserFocus(
        browserWorkspaceSwitcherRowSemanticsIdentifier(activeWorkspaceId),
      );
    });
  }
  List<WorkspaceProfile> _desktopWorkspaceSwitcherProfiles() {
    final storedOrder = _desktopWorkspaceSwitcherProfileOrder;
    if (!_isDesktopWorkspaceSwitcherVisible ||
        storedOrder == null ||
        storedOrder.isEmpty) {
      return _workspaceState.profiles;
    }
    final profilesById = <String, WorkspaceProfile>{
      for (final profile in _workspaceState.profiles) profile.id: profile,
    };
    final orderedProfiles = <WorkspaceProfile>[
      for (final workspaceId in storedOrder)
        if (profilesById.containsKey(workspaceId))
          profilesById.remove(workspaceId)!,
    ];
    orderedProfiles.addAll(profilesById.values);
    return orderedProfiles;
  }
  void _openCreateIssue([CreateIssuePrefill? prefill]) {
    if (_isCreateIssueVisible) {
      return;
    }
    setState(() {
      _isCreateIssueVisible = true;
      _createIssuePrefill =
          prefill ?? CreateIssuePrefill(originSection: viewModel.section);
    });
  }
  void _closeCreateIssue() {
    if (!_isCreateIssueVisible) {
      return;
    }
    setState(() {
      _isCreateIssueVisible = false;
      _createIssuePrefill = null;
    });
  }
  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: viewModel,
      builder: (context, _) {
        return MaterialApp(
          onGenerateTitle: (context) => AppLocalizations.of(context)!.appTitle,
          debugShowCheckedModeBanner: false,
          theme: TrackStateTheme.light(),
          darkTheme: TrackStateTheme.dark(),
          themeMode: viewModel.themePreference == ThemePreference.dark
              ? ThemeMode.dark
              : ThemeMode.light,
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: !_workspaceProfilesReady
              ? WorkspaceInitializationView(viewModel: viewModel)
              : _showsWorkspaceOnboarding
              ? _pendingWorkspaceRestoreFailure != null &&
                        _workspaceState.hasProfiles
                    ? _WorkspaceRestoreLandingView(
                        viewModel: viewModel,
                        workspaces: _workspaceState,
                        authenticatedWorkspaceIds: _authenticatedWorkspaceIds,
                        hostedWorkspaceAccessModes: _hostedWorkspaceAccessModes,
                        localWorkspaceAvailability: _localWorkspaceAvailability,
                        onSelectWorkspace: _switchToWorkspace,
                        onRetryUnavailableLocalWorkspace:
                            _retryUnavailableLocalWorkspace,
                        onDeleteWorkspace: _deleteWorkspaceProfile,
                        onAddWorkspace: _addWorkspaceProfile,
                        onMoveWorkspaceSelection: (step) =>
                            unawaited(_switchToAdjacentWorkspace(step: step)),
                        onSelectFirstWorkspace: () => unawaited(
                          _switchToBoundaryWorkspace(selectFirst: true),
                        ),
                        onSelectLastWorkspace: () => unawaited(
                          _switchToBoundaryWorkspace(selectFirst: false),
                        ),
                      )
                    : _WorkspaceOnboardingScreen(
                        canCancel: _workspaceState.hasProfiles,
                        canBrowseHostedRepositories:
                            viewModel.canBrowseHostedRepositories,
                        directoryPicker: widget.workspaceDirectoryPicker,
                        localWorkspaceOnboardingService:
                            widget.localWorkspaceOnboardingService ??
                            createLocalWorkspaceOnboardingService(),
                        loadHostedRepositories:
                            viewModel.canBrowseHostedRepositories
                            ? viewModel.loadAccessibleHostedRepositories
                            : null,
                        onCancel: _workspaceState.hasProfiles
                            ? _closeWorkspaceOnboarding
                            : null,
                        onOpenLocalWorkspace:
                            ({
                              required String repositoryPath,
                              required String displayName,
                              required String defaultBranch,
                              required String writeBranch,
                            }) => _switchToLocalRepositoryWithProfile(
                              repositoryPath: repositoryPath,
                              defaultBranch: defaultBranch,
                              writeBranch: writeBranch,
                              displayName: displayName,
                            ),
                        onOpenHostedWorkspace: _switchToHostedRepository,
                      )
              : _TrackerHome(
                  viewModel: viewModel,
                  workspaces: _workspaceState,
                  authenticatedWorkspaceIds: _authenticatedWorkspaceIds,
                  localWorkspaceAvailability: _localWorkspaceAvailability,
                  workspaceSwitcherTriggerKey:
                      _workspaceSwitcherTriggerAnchorKey,
                  workspaceSwitcherTriggerFocusNode:
                      _workspaceSwitcherTriggerFocusNode,
                  desktopSearchFocusNode: _desktopSearchFocusNode,
                  desktopSettingsFocusNode: _desktopSettingsFocusNode,
                  workspaceSwitcherOverlayHostKey:
                      _workspaceSwitcherOverlayHostKey,
                  isCreateIssueVisible: _isCreateIssueVisible,
                  isDesktopWorkspaceSwitcherVisible:
                      _isDesktopWorkspaceSwitcherVisible,
                  desktopWorkspaceSwitcherPanelRect:
                      _desktopWorkspaceSwitcherPanelRect(),
                  desktopWorkspaceSwitcherContent:
                      _buildWorkspaceSwitcherContent(
                        compact: false,
                        desktopVisible: _isDesktopWorkspaceSwitcherVisible,
                      ),
                  onOpenCreateIssue: _openCreateIssue,
                  onOpenWorkspaceSwitcher: _openWorkspaceSwitcher,
                  onCloseDesktopWorkspaceSwitcher:
                      _closeDesktopWorkspaceSwitcher,
                  onCloseCreateIssue: _closeCreateIssue,
                  createIssuePrefill: _createIssuePrefill,
                  onOpenWorkspaceOnboarding: _openWorkspaceOnboarding,
                  canOpenWorkspaceOnboarding:
                      !kIsWeb && widget.repository == null,
                  onApplyLocalGitConfiguration: _switchToLocalRepository,
                  onApplyHostedConfiguration: _switchToLastHostedRepository,
                  onSelectWorkspace: _selectWorkspaceProfile,
                  onDeleteWorkspace: _deleteWorkspaceProfile,
                  onMoveWorkspaceSelection: (step) =>
                      unawaited(_switchToAdjacentWorkspace(step: step)),
                  onFocusActiveWorkspaceSwitcherRow:
                      _focusActiveWorkspaceSwitcherRow,
                  workspaceRestoreFailure: _pendingWorkspaceRestoreFailure,
                  onRetryStartupRecovery: _retryStartupRecovery,
                  onRetryWorkspaceRestore: _retryWorkspaceRestore,
                  attachmentPicker: widget.attachmentPicker,
                ),
        );
      },
    );
  }
}
