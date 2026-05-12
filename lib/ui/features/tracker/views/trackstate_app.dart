import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import '../../../../../data/repositories/trackstate_repository.dart';
import '../../../../../data/repositories/trackstate_repository_factory.dart';
import '../../../../../data/repositories/trackstate_runtime.dart';
import '../../../../../domain/models/trackstate_models.dart';
import '../../../../../l10n/generated/app_localizations.dart';
import '../../../core/trackstate_icons.dart';
import '../../../core/trackstate_theme.dart';
import '../services/attachment_picker.dart';
import '../view_models/tracker_view_model.dart';

typedef LocalRepositoryLoader =
    Future<TrackStateRepository> Function({
      required String repositoryPath,
      required String writeBranch,
    });
typedef _CreateIssueLauncher = void Function([_CreateIssuePrefill? prefill]);

typedef LocalRepositoryConfigurationApplier =
    Future<void> Function({
      required String repositoryPath,
      required String writeBranch,
    });

class TrackStateApp extends StatefulWidget {
  const TrackStateApp({
    super.key,
    this.repository,
    this.openLocalRepository,
    this.attachmentPicker = pickAttachmentWithFileSelector,
  });

  final TrackStateRepository? repository;
  final LocalRepositoryLoader? openLocalRepository;
  final AttachmentPicker attachmentPicker;

  @override
  State<TrackStateApp> createState() => _TrackStateAppState();
}

class _TrackStateAppState extends State<TrackStateApp> {
  late TrackerViewModel viewModel;
  bool _isCreateIssueVisible = false;
  _CreateIssuePrefill? _createIssuePrefill;
  String? _activeLocalGitConfigurationKey;
  String? _pendingLocalGitConfigurationKey;

  @override
  void initState() {
    super.initState();
    viewModel = _createViewModel();
  }

  @override
  void didUpdateWidget(covariant TrackStateApp oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.repository == widget.repository) {
      return;
    }
    final previousViewModel = viewModel;
    viewModel = _createViewModel(previous: previousViewModel);
    previousViewModel.dispose();
    _isCreateIssueVisible = false;
    _createIssuePrefill = null;
  }

  @override
  void dispose() {
    viewModel.dispose();
    super.dispose();
  }

  TrackerViewModel _createViewModel({
    TrackStateRepository? repository,
    TrackerViewModel? previous,
    bool autoLoad = true,
  }) {
    final nextViewModel = TrackerViewModel(
      repository:
          repository ?? widget.repository ?? createTrackStateRepository(),
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
    required String writeBranch,
  }) async {
    final loader = widget.openLocalRepository;
    if (loader != null) {
      return loader(repositoryPath: repositoryPath, writeBranch: writeBranch);
    }
    return createTrackStateRepository(
      runtime: TrackStateRuntime.localGit,
      localRepositoryPath: repositoryPath,
    );
  }

  Future<void> _switchToLocalRepository({
    required String repositoryPath,
    required String writeBranch,
  }) async {
    final normalizedRepositoryPath = repositoryPath.trim();
    final normalizedWriteBranch = writeBranch.trim();
    if (normalizedRepositoryPath.isEmpty || normalizedWriteBranch.isEmpty) {
      return;
    }
    final configurationKey =
        '$normalizedRepositoryPath\n$normalizedWriteBranch';
    if (_activeLocalGitConfigurationKey == configurationKey ||
        _pendingLocalGitConfigurationKey == configurationKey) {
      return;
    }

    _pendingLocalGitConfigurationKey = configurationKey;
    final previousViewModel = viewModel;
    try {
      final nextRepository = await _openLocalRepository(
        repositoryPath: normalizedRepositoryPath,
        writeBranch: normalizedWriteBranch,
      );
      if (!mounted) {
        return;
      }

      final nextViewModel = _createViewModel(
        repository: nextRepository,
        previous: previousViewModel,
        autoLoad: false,
      );
      setState(() {
        viewModel = nextViewModel;
        _activeLocalGitConfigurationKey = configurationKey;
        _isCreateIssueVisible = false;
        _createIssuePrefill = null;
      });
      previousViewModel.dispose();
      await nextViewModel.load();
    } finally {
      if (_pendingLocalGitConfigurationKey == configurationKey) {
        _pendingLocalGitConfigurationKey = null;
      }
    }
  }

  void _openCreateIssue([_CreateIssuePrefill? prefill]) {
    if (_isCreateIssueVisible) {
      return;
    }
    setState(() {
      _isCreateIssueVisible = true;
      _createIssuePrefill =
          prefill ?? _CreateIssuePrefill(originSection: viewModel.section);
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
          home: _TrackerHome(
            viewModel: viewModel,
            isCreateIssueVisible: _isCreateIssueVisible,
            onOpenCreateIssue: _openCreateIssue,
            onCloseCreateIssue: _closeCreateIssue,
            createIssuePrefill: _createIssuePrefill,
            onApplyLocalGitConfiguration: _switchToLocalRepository,
            attachmentPicker: widget.attachmentPicker,
          ),
        );
      },
    );
  }
}

class _TrackerHome extends StatelessWidget {
  const _TrackerHome({
    required this.viewModel,
    required this.isCreateIssueVisible,
    required this.onOpenCreateIssue,
    required this.onCloseCreateIssue,
    required this.createIssuePrefill,
    required this.onApplyLocalGitConfiguration,
    required this.attachmentPicker,
  });

  final TrackerViewModel viewModel;
  final bool isCreateIssueVisible;
  final _CreateIssueLauncher onOpenCreateIssue;
  final VoidCallback onCloseCreateIssue;
  final _CreateIssuePrefill? createIssuePrefill;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;
  final AttachmentPicker attachmentPicker;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    if (viewModel.snapshot == null && viewModel.isLoading) {
      return Scaffold(
        body: Center(
          child: Semantics(
            label: l10n.appTitle,
            child: CircularProgressIndicator(color: colors.primary),
          ),
        ),
      );
    }
    if (viewModel.snapshot == null) {
      if (viewModel.startupRecovery != null) {
        return Scaffold(
          backgroundColor: colors.page,
          body: SafeArea(child: _StartupRecoveryView(viewModel: viewModel)),
        );
      }
      return Scaffold(
        backgroundColor: colors.page,
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: _MessageBanner(
                message: viewModel.message,
                onDismiss: viewModel.message == null
                    ? null
                    : viewModel.dismissMessage,
              ),
            ),
          ),
        ),
      );
    }

    return Shortcuts(
      shortcuts: const {
        SingleActivator(LogicalKeyboardKey.digit1): _SelectSectionIntent(
          TrackerSection.dashboard,
        ),
        SingleActivator(LogicalKeyboardKey.digit2): _SelectSectionIntent(
          TrackerSection.board,
        ),
        SingleActivator(LogicalKeyboardKey.digit3): _SelectSectionIntent(
          TrackerSection.search,
        ),
      },
      child: Actions(
        actions: {
          _SelectSectionIntent: CallbackAction<_SelectSectionIntent>(
            onInvoke: (intent) {
              viewModel.selectSection(intent.section);
              return null;
            },
          ),
        },
        child: FocusTraversalGroup(
          policy: OrderedTraversalPolicy(),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final isCompact = constraints.maxWidth < 980;
              return Scaffold(
                backgroundColor: colors.page,
                body: SafeArea(
                  child: isCompact
                      ? _MobileShell(
                          viewModel: viewModel,
                          isCreateIssueVisible: isCreateIssueVisible,
                          onOpenCreateIssue: onOpenCreateIssue,
                          onCloseCreateIssue: onCloseCreateIssue,
                          createIssuePrefill: createIssuePrefill,
                          onApplyLocalGitConfiguration:
                              onApplyLocalGitConfiguration,
                          attachmentPicker: attachmentPicker,
                        )
                      : _DesktopShell(
                          viewModel: viewModel,
                          isCreateIssueVisible: isCreateIssueVisible,
                          onOpenCreateIssue: onOpenCreateIssue,
                          onCloseCreateIssue: onCloseCreateIssue,
                          createIssuePrefill: createIssuePrefill,
                          onApplyLocalGitConfiguration:
                              onApplyLocalGitConfiguration,
                          attachmentPicker: attachmentPicker,
                        ),
                ),
                bottomNavigationBar: isCompact && !isCreateIssueVisible
                    ? _BottomNavigation(viewModel: viewModel)
                    : null,
              );
            },
          ),
        ),
      ),
    );
  }
}

class _SelectSectionIntent extends Intent {
  const _SelectSectionIntent(this.section);
  final TrackerSection section;
}

class _DesktopShell extends StatelessWidget {
  const _DesktopShell({
    required this.viewModel,
    required this.isCreateIssueVisible,
    required this.onOpenCreateIssue,
    required this.onCloseCreateIssue,
    required this.createIssuePrefill,
    required this.onApplyLocalGitConfiguration,
    required this.attachmentPicker,
  });

  final TrackerViewModel viewModel;
  final bool isCreateIssueVisible;
  final _CreateIssueLauncher onOpenCreateIssue;
  final VoidCallback onCloseCreateIssue;
  final _CreateIssuePrefill? createIssuePrefill;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;
  final AttachmentPicker attachmentPicker;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(width: 268, child: _Sidebar(viewModel: viewModel)),
        Expanded(
          child: _TrackerMainPane(
            viewModel: viewModel,
            isCreateIssueVisible: isCreateIssueVisible,
            onOpenCreateIssue: onOpenCreateIssue,
            onCloseCreateIssue: onCloseCreateIssue,
            createIssuePrefill: createIssuePrefill,
            onApplyLocalGitConfiguration: onApplyLocalGitConfiguration,
            attachmentPicker: attachmentPicker,
          ),
        ),
      ],
    );
  }
}

class _MobileShell extends StatelessWidget {
  const _MobileShell({
    required this.viewModel,
    required this.isCreateIssueVisible,
    required this.onOpenCreateIssue,
    required this.onCloseCreateIssue,
    required this.createIssuePrefill,
    required this.onApplyLocalGitConfiguration,
    required this.attachmentPicker,
  });

  final TrackerViewModel viewModel;
  final bool isCreateIssueVisible;
  final _CreateIssueLauncher onOpenCreateIssue;
  final VoidCallback onCloseCreateIssue;
  final _CreateIssuePrefill? createIssuePrefill;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;
  final AttachmentPicker attachmentPicker;

  @override
  Widget build(BuildContext context) {
    return _TrackerMainPane(
      viewModel: viewModel,
      compact: true,
      isCreateIssueVisible: isCreateIssueVisible,
      onOpenCreateIssue: onOpenCreateIssue,
      onCloseCreateIssue: onCloseCreateIssue,
      createIssuePrefill: createIssuePrefill,
      onApplyLocalGitConfiguration: onApplyLocalGitConfiguration,
      attachmentPicker: attachmentPicker,
    );
  }
}

class _TrackerMainPane extends StatelessWidget {
  const _TrackerMainPane({
    required this.viewModel,
    required this.isCreateIssueVisible,
    required this.onOpenCreateIssue,
    required this.onCloseCreateIssue,
    required this.createIssuePrefill,
    required this.onApplyLocalGitConfiguration,
    required this.attachmentPicker,
    this.compact = false,
  });

  final TrackerViewModel viewModel;
  final bool compact;
  final bool isCreateIssueVisible;
  final _CreateIssueLauncher onOpenCreateIssue;
  final VoidCallback onCloseCreateIssue;
  final _CreateIssuePrefill? createIssuePrefill;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;
  final AttachmentPicker attachmentPicker;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Column(
          children: [
            _TopBar(
              viewModel: viewModel,
              compact: compact,
              onOpenCreateIssue: onOpenCreateIssue,
            ),
            _RepositoryAccessBanner(viewModel: viewModel),
            Expanded(
              child: _SectionBody(
                viewModel: viewModel,
                compact: compact,
                onOpenCreateIssue: onOpenCreateIssue,
                onApplyLocalGitConfiguration: onApplyLocalGitConfiguration,
                attachmentPicker: attachmentPicker,
              ),
            ),
          ],
        ),
        if (isCreateIssueVisible)
          Positioned.fill(
            child: _CreateIssueOverlay(
              compact: compact,
              child: _CreateIssueDialog(
                viewModel: viewModel,
                onDismiss: onCloseCreateIssue,
                prefill:
                    createIssuePrefill ??
                    _CreateIssuePrefill(originSection: viewModel.section),
              ),
            ),
          ),
      ],
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final items = _navItems(l10n);
    return Semantics(
      label: '${l10n.appTitle} navigation',
      child: Container(
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: colors.surfaceAlt,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: colors.border),
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final navigationSection = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    TrackStateIcon(
                      TrackStateIconGlyph.logo,
                      size: 34,
                      color: colors.secondary,
                      semanticLabel: l10n.appTitle,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            l10n.appTitle,
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          Text(
                            l10n.appTagline,
                            style: Theme.of(context).textTheme.labelSmall
                                ?.copyWith(color: colors.muted),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 28),
                for (final item in items)
                  _NavButton(
                    item: item,
                    selected: viewModel.section == item.section,
                    onPressed: () => viewModel.selectSection(item.section),
                  ),
              ],
            );
            final footerSection = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _SyncPill(label: l10n.syncStatus),
                const SizedBox(height: 12),
                _GitInfoCard(project: viewModel.project!),
              ],
            );

            return SingleChildScrollView(
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [navigationSection, footerSection],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.viewModel,
    required this.onOpenCreateIssue,
    this.compact = false,
  });

  final TrackerViewModel viewModel;
  final _CreateIssueLauncher onOpenCreateIssue;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final repositoryAccessLabel = _repositoryAccessLabel(l10n, viewModel);
    final openCreateIssue = viewModel.isSaving
        ? null
        : () => onOpenCreateIssue(
            _CreateIssuePrefill(originSection: viewModel.section),
          );
    return Padding(
      padding: EdgeInsets.fromLTRB(compact ? 12 : 8, 12, 12, 6),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final condensedDesktop = !compact && constraints.maxWidth < 1080;
          final iconOnlyActions = compact || condensedDesktop;
          final actionGap = iconOnlyActions ? 8.0 : 12.0;
          return Row(
            children: [
              if (compact) ...[
                TrackStateIcon(
                  TrackStateIconGlyph.logo,
                  color: colors.secondary,
                  size: 32,
                  semanticLabel: l10n.appTitle,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    l10n.appTitle,
                    style: Theme.of(context).textTheme.titleMedium,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ] else ...[
                _SyncPill(label: l10n.syncStatus),
                const SizedBox(width: 12),
                Expanded(
                  child: Semantics(
                    label: l10n.searchIssues,
                    textField: true,
                    child: TextField(
                      controller: TextEditingController(text: viewModel.jql),
                      onSubmitted: viewModel.updateQuery,
                      decoration: InputDecoration(
                        prefixIcon: Padding(
                          padding: const EdgeInsets.all(12),
                          child: TrackStateIcon(
                            TrackStateIconGlyph.search,
                            color: colors.muted,
                            semanticLabel: l10n.searchIssues,
                          ),
                        ),
                        hintText: l10n.jqlPlaceholder,
                      ),
                    ),
                  ),
                ),
              ],
              SizedBox(width: actionGap),
              if (iconOnlyActions)
                _IconButtonSurface(
                  label: l10n.createIssue,
                  glyph: TrackStateIconGlyph.plus,
                  onPressed: openCreateIssue,
                )
              else
                _PrimaryButton(
                  label: l10n.createIssue,
                  icon: TrackStateIconGlyph.plus,
                  onPressed: openCreateIssue,
                ),
              const SizedBox(width: 8),
              if (iconOnlyActions)
                _IconButtonSurface(
                  label: repositoryAccessLabel,
                  glyph: TrackStateIconGlyph.gitBranch,
                  onPressed: viewModel.isSaving
                      ? null
                      : () => _showRepositoryAccessDialog(context, viewModel),
                )
              else
                _PrimaryButton(
                  label: repositoryAccessLabel,
                  icon: TrackStateIconGlyph.gitBranch,
                  onPressed: viewModel.isSaving
                      ? null
                      : () => _showRepositoryAccessDialog(context, viewModel),
                ),
              const SizedBox(width: 8),
              _IconButtonSurface(
                label: viewModel.themePreference == ThemePreference.dark
                    ? l10n.lightTheme
                    : l10n.darkTheme,
                glyph: viewModel.themePreference == ThemePreference.dark
                    ? TrackStateIconGlyph.sun
                    : TrackStateIconGlyph.moon,
                onPressed: viewModel.toggleTheme,
              ),
              const SizedBox(width: 8),
              if (_hasVisibleProfileIdentity(viewModel) &&
                  !compact &&
                  !condensedDesktop) ...[
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 180),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Semantics(
                        container: true,
                        label: _profileDisplayName(viewModel),
                        child: ExcludeSemantics(
                          child: Text(
                            _profileDisplayName(viewModel),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.labelLarge
                                ?.copyWith(
                                  color: colors.text,
                                  fontWeight: FontWeight.w600,
                                ),
                          ),
                        ),
                      ),
                      if (_profileLogin(viewModel) case final login?)
                        Semantics(
                          container: true,
                          label: login,
                          child: ExcludeSemantics(
                            child: Text(
                              login,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context).textTheme.bodySmall
                                  ?.copyWith(color: colors.muted),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
              ],
              Semantics(
                label: _profileDisplayName(viewModel),
                image: true,
                child: ExcludeSemantics(
                  child: CircleAvatar(
                    radius: 18,
                    backgroundColor: colors.primarySoft,
                    child: Text(
                      _profileInitials(l10n, viewModel),
                      style: TextStyle(
                        color: colors.text,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

Future<void> _showRepositoryAccessDialog(
  BuildContext context,
  TrackerViewModel viewModel,
) async {
  final l10n = AppLocalizations.of(context)!;
  if (viewModel.usesLocalPersistence) {
    final project = viewModel.project;
    await showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(l10n.localGitRuntimeTitle),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${l10n.repository}: '
                '${project?.repository ?? l10n.configuredRepositoryFallback}',
              ),
              const SizedBox(height: 8),
              Text(
                '${l10n.branch}: '
                '${project?.branch ?? l10n.currentBranchFallback}',
              ),
              const SizedBox(height: 12),
              Text(l10n.localGitRuntimeDescription),
            ],
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text(l10n.close),
            ),
          ],
        );
      },
    );
    return;
  }
  final controller = TextEditingController();
  var rememberToken = true;
  final accessMode = viewModel.hostedRepositoryAccessMode;
  final dialogTitle = accessMode == HostedRepositoryAccessMode.disconnected
      ? l10n.connectGitHub
      : l10n.manageGitHubAccess;
  await showDialog<void>(
    context: context,
    builder: (context) {
      final project = viewModel.project;
      return StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            title: Text(dialogTitle),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${l10n.repository}: '
                  '${project?.repository ?? l10n.configuredRepositoryFallback}',
                ),
                const SizedBox(height: 12),
                Text(_repositoryAccessMessage(l10n, viewModel)),
                const SizedBox(height: 12),
                TextField(
                  controller: controller,
                  obscureText: true,
                  decoration: InputDecoration(
                    labelText: l10n.fineGrainedToken,
                    helperText: l10n.fineGrainedTokenHelper,
                  ),
                  onSubmitted: (_) {
                    Navigator.of(context).pop();
                    viewModel.connectGitHub(
                      controller.text,
                      remember: rememberToken,
                    );
                  },
                ),
                const SizedBox(height: 8),
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: rememberToken,
                  title: Text(l10n.rememberOnThisBrowser),
                  subtitle: Text(l10n.rememberOnThisBrowserHelp),
                  onChanged: (value) =>
                      setDialogState(() => rememberToken = value ?? true),
                ),
                if (viewModel.isGitHubAppAuthAvailable) ...[
                  const SizedBox(height: 8),
                  OutlinedButton(
                    onPressed: () {
                      Navigator.of(context).pop();
                      viewModel.startGitHubAppLogin();
                    },
                    child: Text(l10n.continueWithGitHubApp),
                  ),
                ],
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: Text(l10n.cancel),
              ),
              FilledButton(
                onPressed: () {
                  Navigator.of(context).pop();
                  viewModel.connectGitHub(
                    controller.text,
                    remember: rememberToken,
                  );
                },
                child: Text(l10n.connectToken),
              ),
            ],
          );
        },
      );
    },
  );
  controller.dispose();
}

String _repositoryAccessLabel(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  if (viewModel.exposesHostedAccessGates) {
    return switch (viewModel.hostedRepositoryAccessMode) {
      HostedRepositoryAccessMode.disconnected =>
        l10n.repositoryAccessConnectGitHub,
      HostedRepositoryAccessMode.readOnly => l10n.repositoryAccessReadOnly,
      HostedRepositoryAccessMode.writable => l10n.repositoryAccessConnected,
      HostedRepositoryAccessMode.attachmentRestricted =>
        l10n.repositoryAccessAttachmentsRestricted,
    };
  }
  return switch (viewModel.repositoryAccessState) {
    RepositoryAccessState.localGit => l10n.repositoryAccessLocalGit,
    RepositoryAccessState.connected => l10n.repositoryAccessConnected,
    RepositoryAccessState.connectGitHub => l10n.repositoryAccessConnectGitHub,
  };
}

String _repositoryAccessPrimaryActionLabel(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  return switch (viewModel.hostedRepositoryAccessMode) {
    HostedRepositoryAccessMode.disconnected => l10n.connectGitHub,
    HostedRepositoryAccessMode.readOnly => l10n.reconnectWriteAccess,
    HostedRepositoryAccessMode.writable ||
    HostedRepositoryAccessMode.attachmentRestricted => l10n.manageGitHubAccess,
  };
}

String _repositoryAccessTitle(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  return switch (viewModel.hostedRepositoryAccessMode) {
    HostedRepositoryAccessMode.disconnected =>
      l10n.repositoryAccessDisconnectedTitle,
    HostedRepositoryAccessMode.readOnly => l10n.repositoryAccessReadOnlyTitle,
    HostedRepositoryAccessMode.writable => l10n.repositoryAccessConnected,
    HostedRepositoryAccessMode.attachmentRestricted =>
      viewModel.canUploadIssueAttachments
          ? l10n.repositoryAccessAttachmentLimitedTitle
          : l10n.repositoryAccessAttachmentRestrictedTitle,
  };
}

String _repositoryAccessMessage(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  return switch (viewModel.hostedRepositoryAccessMode) {
    HostedRepositoryAccessMode.disconnected =>
      l10n.repositoryAccessDisconnectedMessage,
    HostedRepositoryAccessMode.readOnly => l10n.repositoryAccessReadOnlyMessage,
    HostedRepositoryAccessMode.writable => l10n.githubConnected(
      viewModel.connectedUser?.login ?? '',
      viewModel.project?.repository ?? l10n.configuredRepositoryFallback,
    ),
    HostedRepositoryAccessMode.attachmentRestricted =>
      viewModel.canUploadIssueAttachments
          ? l10n.repositoryAccessAttachmentLimitedMessage
          : l10n.repositoryAccessAttachmentRestrictedMessage,
  };
}

String _attachmentsAccessMessage(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  return switch (viewModel.hostedRepositoryAccessMode) {
    HostedRepositoryAccessMode.disconnected =>
      l10n.attachmentsAccessMessageDisconnected,
    HostedRepositoryAccessMode.readOnly =>
      l10n.attachmentsAccessMessageReadOnly,
    HostedRepositoryAccessMode.writable => '',
    HostedRepositoryAccessMode.attachmentRestricted =>
      viewModel.canUploadIssueAttachments
          ? l10n.attachmentsLimitedUploadMessage
          : l10n.attachmentsDownloadOnlyMessage,
  };
}

String _profileInitials(AppLocalizations l10n, TrackerViewModel viewModel) {
  final userInitials = viewModel.connectedUser?.initials.trim();
  if (userInitials != null && userInitials.isNotEmpty) {
    return userInitials;
  }
  final repositoryFallback = _initialsFromText(
    _repositoryAccessLabel(l10n, viewModel),
  );
  if (repositoryFallback.isNotEmpty) {
    return repositoryFallback;
  }
  return _initialsFromText(l10n.appTitle);
}

String _profileDisplayName(TrackerViewModel viewModel) {
  final user = viewModel.connectedUser;
  if (user == null) {
    return '';
  }
  final displayName = user.displayName.trim();
  if (displayName.isNotEmpty) {
    return displayName;
  }
  return user.login.trim();
}

String? _profileLogin(TrackerViewModel viewModel) {
  final user = viewModel.connectedUser;
  if (user == null) {
    return null;
  }
  final login = user.login.trim();
  if (login.isEmpty) {
    return null;
  }
  return login == _profileDisplayName(viewModel) ? null : login;
}

bool _hasVisibleProfileIdentity(TrackerViewModel viewModel) =>
    _profileDisplayName(viewModel).isNotEmpty ||
    (_profileLogin(viewModel)?.isNotEmpty ?? false);

String _initialsFromText(String value) {
  final parts = value
      .split(RegExp(r'[\s._-]+'))
      .where((part) => part.isNotEmpty)
      .toList();
  if (parts.isNotEmpty) {
    return parts.take(2).map((part) => part[0].toUpperCase()).join();
  }
  final compact = value.replaceAll(RegExp(r'[^A-Za-z0-9]'), '');
  if (compact.isEmpty) return '';
  return compact
      .substring(0, compact.length < 2 ? compact.length : 2)
      .toUpperCase();
}

String _trackerMessageText(AppLocalizations l10n, TrackerMessage message) {
  return switch (message.kind) {
    TrackerMessageKind.dataLoadFailed => l10n.trackerDataLoadFailed(
      message.error!,
    ),
    TrackerMessageKind.searchFailed => l10n.searchFailed(message.error!),
    TrackerMessageKind.repositoryConfigFallback =>
      l10n.repositoryConfigFallback(message.error!),
    TrackerMessageKind.localGitTokensNotNeeded => l10n.localGitTokensNotNeeded,
    TrackerMessageKind.tokenEmpty => l10n.tokenEmpty,
    TrackerMessageKind.githubConnectedDragCards =>
      l10n.githubConnectedDragCards(message.login!, message.repository!),
    TrackerMessageKind.githubConnectionFailed => l10n.githubConnectionFailed(
      message.error!,
    ),
    TrackerMessageKind.issueSaveFailed => l10n.saveFailed(message.error!),
    TrackerMessageKind.localGitMoveCommitted => l10n.localGitMoveCommitted(
      message.issueKey!,
      message.statusLabel!,
      message.branch!,
    ),
    TrackerMessageKind.githubMoveCommitted => l10n.githubMoveCommitted(
      message.issueKey!,
      message.statusLabel!,
    ),
    TrackerMessageKind.movePendingGitHubPersistence =>
      l10n.movePendingGitHubPersistence(message.issueKey!),
    TrackerMessageKind.moveFailed => l10n.moveFailed(message.error!),
    TrackerMessageKind.attachmentDownloadFailed =>
      l10n.attachmentDownloadFailed(message.error!),
    TrackerMessageKind.localGitHubAppUnavailable =>
      l10n.localGitHubAppUnavailable,
    TrackerMessageKind.githubAppLoginNotConfigured =>
      l10n.githubAppLoginNotConfigured,
    TrackerMessageKind.githubAuthorizationCodeReturned =>
      l10n.githubAuthorizationCodeReturned,
    TrackerMessageKind.githubConnected => l10n.githubConnected(
      message.login!,
      message.repository!,
    ),
    TrackerMessageKind.storedGitHubTokenInvalid =>
      l10n.storedGitHubTokenInvalid(message.error!),
  };
}

String _startupRecoveryTitle(
  AppLocalizations l10n,
  TrackerStartupRecovery recovery,
) {
  return switch (recovery.kind) {
    TrackerStartupRecoveryKind.githubRateLimit =>
      l10n.startupRateLimitRecoveryTitle,
  };
}

String _startupRecoveryMessage(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  final recovery = viewModel.startupRecovery;
  if (recovery == null) {
    return '';
  }
  return viewModel.snapshot == null
      ? l10n.startupRateLimitRecoveryBlockingMessage
      : l10n.startupRateLimitRecoveryShellMessage;
}

class _MessageBanner extends StatelessWidget {
  const _MessageBanner({required this.message, this.onDismiss});

  final TrackerMessage? message;
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final resolvedMessage = message == null
        ? l10n.trackerDataNotFound
        : _trackerMessageText(l10n, message!);
    final isError = message?.tone == TrackerMessageTone.error;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: isError
            ? colors.accent.withValues(alpha: .12)
            : colors.primarySoft.withValues(alpha: .72),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: isError ? colors.accent : colors.primary),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TrackStateIcon(
            isError ? TrackStateIconGlyph.issue : TrackStateIconGlyph.gitBranch,
            size: 18,
            color: isError ? colors.accent : colors.primary,
            semanticLabel: resolvedMessage,
          ),
          const SizedBox(width: 10),
          Expanded(child: Text(resolvedMessage)),
          if (onDismiss != null) ...[
            const SizedBox(width: 8),
            Semantics(
              button: true,
              label: l10n.close,
              child: TextButton(
                onPressed: onDismiss,
                style: TextButton.styleFrom(
                  foregroundColor: isError ? colors.accent : colors.primary,
                ),
                child: Text(l10n.close),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _RepositoryAccessBanner extends StatelessWidget {
  const _RepositoryAccessBanner({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final attachmentDownloadOnly =
        viewModel.hostedRepositoryAccessMode ==
            HostedRepositoryAccessMode.attachmentRestricted &&
        !viewModel.canUploadIssueAttachments;
    if (!viewModel.exposesHostedAccessGates ||
        viewModel.hostedRepositoryAccessMode ==
            HostedRepositoryAccessMode.writable) {
      return const SizedBox.shrink();
    }
    final l10n = AppLocalizations.of(context)!;
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 0, 12, 6),
      child: _AccessCallout(
        semanticLabel: _repositoryAccessTitle(l10n, viewModel),
        title: _repositoryAccessTitle(l10n, viewModel),
        message: _repositoryAccessMessage(l10n, viewModel),
        primaryActionLabel: attachmentDownloadOnly
            ? l10n.openSettings
            : _repositoryAccessPrimaryActionLabel(l10n, viewModel),
        onPrimaryAction: attachmentDownloadOnly
            ? () => viewModel.selectSection(TrackerSection.settings)
            : () => _showRepositoryAccessDialog(context, viewModel),
      ),
    );
  }
}

class _AccessCallout extends StatelessWidget {
  const _AccessCallout({
    required this.semanticLabel,
    required this.title,
    required this.message,
    this.primaryActionLabel,
    this.onPrimaryAction,
    this.secondaryActionLabel,
    this.onSecondaryAction,
  });

  final String semanticLabel;
  final String title;
  final String message;
  final String? primaryActionLabel;
  final VoidCallback? onPrimaryAction;
  final String? secondaryActionLabel;
  final VoidCallback? onSecondaryAction;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      container: true,
      label: '$semanticLabel $title $message',
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: colors.accent.withValues(alpha: .12),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: colors.accent),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TrackStateIcon(
                  TrackStateIconGlyph.gitBranch,
                  size: 18,
                  color: colors.accent,
                  semanticLabel: title,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(message),
            if ((primaryActionLabel != null && onPrimaryAction != null) ||
                (secondaryActionLabel != null &&
                    onSecondaryAction != null)) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (primaryActionLabel != null && onPrimaryAction != null)
                    Semantics(
                      button: true,
                      label: primaryActionLabel,
                      child: OutlinedButton(
                        onPressed: onPrimaryAction,
                        style: OutlinedButton.styleFrom(
                          foregroundColor: colors.text,
                          side: BorderSide(color: colors.accent),
                        ),
                        child: Text(primaryActionLabel!),
                      ),
                    ),
                  if (secondaryActionLabel != null && onSecondaryAction != null)
                    Semantics(
                      button: true,
                      label: secondaryActionLabel,
                      child: FilledButton(
                        onPressed: onSecondaryAction,
                        child: Text(secondaryActionLabel!),
                      ),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _StartupRecoveryView extends StatelessWidget {
  const _StartupRecoveryView({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final recovery = viewModel.startupRecovery;
    if (recovery == null) {
      return const SizedBox.shrink();
    }
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 720),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Semantics(
                header: true,
                child: Text(
                  l10n.appTitle,
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
              ),
              const SizedBox(height: 16),
              if (viewModel.message != null) ...[
                _MessageBanner(
                  message: viewModel.message!,
                  onDismiss: viewModel.dismissMessage,
                ),
                const SizedBox(height: 12),
              ],
              _AccessCallout(
                semanticLabel: l10n.startupRecovery,
                title: _startupRecoveryTitle(l10n, recovery),
                message: _startupRecoveryMessage(l10n, viewModel),
                primaryActionLabel: l10n.retry,
                onPrimaryAction: viewModel.retryStartupRecovery,
                secondaryActionLabel: viewModel.supportsGitHubAuth
                    ? l10n.connectGitHub
                    : null,
                onSecondaryAction: viewModel.supportsGitHubAuth
                    ? () => _showRepositoryAccessDialog(context, viewModel)
                    : null,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionBody extends StatelessWidget {
  const _SectionBody({
    required this.viewModel,
    required this.onOpenCreateIssue,
    required this.onApplyLocalGitConfiguration,
    required this.attachmentPicker,
    this.compact = false,
  });

  final TrackerViewModel viewModel;
  final _CreateIssueLauncher onOpenCreateIssue;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;
  final AttachmentPicker attachmentPicker;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final body = switch (viewModel.section) {
      TrackerSection.dashboard => _Dashboard(viewModel: viewModel),
      TrackerSection.board => _Board(viewModel: viewModel),
      TrackerSection.search => _SearchAndDetail(
        viewModel: viewModel,
        onOpenCreateIssue: onOpenCreateIssue,
        attachmentPicker: attachmentPicker,
      ),
      TrackerSection.hierarchy => _Hierarchy(
        viewModel: viewModel,
        onOpenCreateIssue: onOpenCreateIssue,
      ),
      TrackerSection.settings => _Settings(
        viewModel: viewModel,
        onApplyLocalGitConfiguration: onApplyLocalGitConfiguration,
      ),
    };
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(compact ? 12 : 8, 8, compact ? 12 : 18, 24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1280),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (viewModel.message != null) ...[
                _MessageBanner(
                  message: viewModel.message!,
                  onDismiss: viewModel.dismissMessage,
                ),
                const SizedBox(height: 12),
              ],
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 240),
                child: KeyedSubtree(
                  key: ValueKey(viewModel.section),
                  child: body,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Dashboard extends StatelessWidget {
  const _Dashboard({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final showBootstrapHint = viewModel.showsInitialBootstrapPlaceholders;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ScreenHeading(title: l10n.dashboard, subtitle: l10n.appTagline),
        if (showBootstrapHint) ...[
          _SectionLoadingBanner(
            semanticLabel: '${l10n.dashboard} ${l10n.loading}',
            label: l10n.loading,
          ),
          const SizedBox(height: 16),
        ],
        LayoutBuilder(
          builder: (context, constraints) {
            final cards = [
              _MetricCard(
                label: l10n.openIssues,
                value: '${viewModel.openIssueCount}',
                delta: '-6d',
                tone: MetricTone.accent,
                showDeltaPlaceholder: showBootstrapHint,
              ),
              _MetricCard(
                label: l10n.issuesInProgress,
                value: '${viewModel.inProgressIssueCount}',
                delta: '+4',
                tone: MetricTone.primary,
                showDeltaPlaceholder: showBootstrapHint,
              ),
              _MetricCard(
                label: l10n.completed,
                value: '${viewModel.completedIssueCount}',
                delta: '+12',
                tone: MetricTone.secondary,
                showDeltaPlaceholder: showBootstrapHint,
              ),
              _MetricCard(
                label: l10n.teamVelocity,
                value: '42',
                delta: '+18%',
                tone: MetricTone.secondary,
                showValuePlaceholder: showBootstrapHint,
                showDeltaPlaceholder: showBootstrapHint,
              ),
            ];
            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: constraints.maxWidth < 640 ? 420 : 280,
                mainAxisExtent: 152,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
              ),
              itemCount: cards.length,
              itemBuilder: (context, index) => cards[index],
            );
          },
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 980;
            if (compact) {
              return Column(
                children: [
                  _ActiveEpics(viewModel: viewModel),
                  const SizedBox(height: 16),
                  _RecentActivity(viewModel: viewModel),
                ],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: _ActiveEpics(viewModel: viewModel)),
                const SizedBox(width: 16),
                Expanded(child: _RecentActivity(viewModel: viewModel)),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _Board extends StatelessWidget {
  const _Board({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final grouped = viewModel.issuesByStatus;
    final showBootstrapHint = viewModel.showsInitialBootstrapPlaceholders;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ScreenHeading(title: l10n.board, subtitle: l10n.kanbanHint),
        if (showBootstrapHint) ...[
          _SectionLoadingBanner(
            semanticLabel: '${l10n.board} ${l10n.loading}',
            label: l10n.loading,
          ),
          const SizedBox(height: 16),
        ],
        LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 900;
            final columns = IssueStatus.values.map((status) {
              return _BoardColumn(
                title: _statusLabel(l10n, status),
                targetStatus: status,
                issues: grouped[status]!,
                onSelect: (issue) => viewModel.selectIssue(
                  issue,
                  returnSection: TrackerSection.board,
                ),
                onMove: viewModel.moveIssue,
              );
            }).toList();
            if (compact) {
              return Column(
                children: [
                  for (final column in columns) ...[
                    column,
                    const SizedBox(height: 12),
                  ],
                ],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final column in columns)
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.only(right: 12),
                      child: column,
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _SearchAndDetail extends StatelessWidget {
  const _SearchAndDetail({
    required this.viewModel,
    required this.onOpenCreateIssue,
    required this.attachmentPicker,
  });

  final TrackerViewModel viewModel;
  final _CreateIssueLauncher onOpenCreateIssue;
  final AttachmentPicker attachmentPicker;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final viewModel = this.viewModel;
    final subtitle = switch ((
      viewModel.hasLoadedInitialSearchResults,
      viewModel.shouldUseBootstrapSearchFallback,
      viewModel.isLoading,
    )) {
      (true, _, _) => l10n.issueCount(viewModel.totalSearchResults),
      (false, true, false) => l10n.issueCount(
        math.min(viewModel.issues.length, 6),
      ),
      _ => l10n.loading,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: _ScreenHeading(title: l10n.jqlSearch, subtitle: subtitle),
            ),
          ],
        ),
        LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 980;
            final list = _IssueList(viewModel: viewModel);
            final detail = _IssueDetail(
              issue: viewModel.selectedIssue!,
              viewModel: viewModel,
              onCreateChildIssue: () => onOpenCreateIssue(
                _CreateIssuePrefill.forChild(
                  originSection:
                      viewModel.issueDetailReturnSection ??
                      TrackerSection.search,
                  issue: viewModel.selectedIssue!,
                ),
              ),
              attachmentPicker: attachmentPicker,
            );
            return compact
                ? Column(children: [list, const SizedBox(height: 16), detail])
                : Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 5, child: list),
                      const SizedBox(width: 16),
                      Expanded(flex: 4, child: detail),
                    ],
                  );
          },
        ),
      ],
    );
  }
}

const Set<String> _hiddenCreateFieldIds = {
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
  'archived',
  'resolution',
};

List<TrackStateFieldDefinition> _createIssueFieldDefinitions(
  ProjectConfig? project,
) {
  if (project == null) {
    return const [];
  }
  return project.fieldDefinitions
      .where((field) => !_hiddenCreateFieldIds.contains(field.id))
      .toList(growable: false);
}

void _syncCreateFieldControllers(
  Map<String, TextEditingController> controllers,
  List<TrackStateFieldDefinition> fields,
) {
  final activeFieldIds = fields.map((field) => field.id).toSet();
  final staleFieldIds = controllers.keys
      .where((fieldId) => !activeFieldIds.contains(fieldId))
      .toList(growable: false);
  for (final fieldId in staleFieldIds) {
    controllers.remove(fieldId)?.dispose();
  }
  for (final field in fields) {
    controllers.putIfAbsent(field.id, TextEditingController.new);
  }
}

String _createIssueFieldLabel(
  ProjectConfig? project,
  TrackStateFieldDefinition field,
) => project?.fieldLabel(field.id) ?? field.name;

String _projectFieldLabel(
  ProjectConfig? project,
  String fieldId, {
  required String fallback,
}) {
  final resolved = project?.fieldLabel(fieldId);
  if (resolved == null || resolved == fieldId) {
    return fallback;
  }
  return resolved;
}

class _CreateIssuePrefill {
  const _CreateIssuePrefill({
    required this.originSection,
    this.issueTypeId,
    this.parentKey,
    this.epicKey,
  });

  factory _CreateIssuePrefill.forChild({
    required TrackerSection originSection,
    required TrackStateIssue issue,
  }) {
    if (issue.isEpic) {
      return _CreateIssuePrefill(
        originSection: originSection,
        issueTypeId: IssueType.story.id,
        epicKey: issue.key,
      );
    }
    return _CreateIssuePrefill(
      originSection: originSection,
      issueTypeId: IssueType.subtask.id,
      parentKey: issue.key,
      epicKey: issue.epicKey,
    );
  }

  final TrackerSection originSection;
  final String? issueTypeId;
  final String? parentKey;
  final String? epicKey;
}

TrackStateConfigEntry? _resolveConfigEntry(
  String? value,
  List<TrackStateConfigEntry> entries,
) {
  final canonicalValue = _canonicalConfigId(value);
  if (canonicalValue.isEmpty) {
    return null;
  }
  for (final entry in entries) {
    final entryId = _canonicalConfigId(entry.id);
    final entryName = _canonicalConfigId(entry.name);
    if (entryId == canonicalValue || entryName == canonicalValue) {
      return entry;
    }
  }
  return null;
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

TrackStateConfigEntry? _defaultCreateIssueType(ProjectConfig project) =>
    _resolveConfigEntry(IssueType.story.id, project.issueTypeDefinitions) ??
    project.issueTypeDefinitions.firstOrNull;

TrackStateConfigEntry? _defaultCreatePriority(ProjectConfig project) =>
    _resolveConfigEntry(IssuePriority.medium.id, project.priorityDefinitions) ??
    project.priorityDefinitions.firstOrNull;

TrackStateConfigEntry? _defaultCreateStatus(ProjectConfig project) =>
    _resolveConfigEntry(IssueStatus.todo.id, project.statusDefinitions) ??
    project.statusDefinitions.firstOrNull;

List<TrackStateConfigEntry> _supportedCreateIssueTypes(ProjectConfig project) =>
    project.issueTypeDefinitions
        .where(
          (definition) => switch (_canonicalConfigId(definition.id)) {
            'epic' || 'story' || 'task' || 'subtask' || 'bug' => true,
            _ => false,
          },
        )
        .toList(growable: false);

List<TrackStateIssue> _epicOptions(TrackerViewModel viewModel) =>
    [...viewModel.epics]..sort((left, right) => left.key.compareTo(right.key));

List<TrackStateIssue> _parentOptions(TrackerViewModel viewModel) => [
  for (final issue in viewModel.issues)
    if (!issue.isEpic && !issue.isArchived) issue,
]..sort((left, right) => left.key.compareTo(right.key));

String _trackerSectionLabel(AppLocalizations l10n, TrackerSection section) =>
    switch (section) {
      TrackerSection.dashboard => l10n.dashboard,
      TrackerSection.board => l10n.board,
      TrackerSection.search => l10n.jqlSearch,
      TrackerSection.hierarchy => l10n.hierarchy,
      TrackerSection.settings => l10n.settings,
    };

class _Hierarchy extends StatelessWidget {
  const _Hierarchy({required this.viewModel, required this.onOpenCreateIssue});

  final TrackerViewModel viewModel;
  final _CreateIssueLauncher onOpenCreateIssue;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ScreenHeading(
          title: l10n.hierarchy,
          subtitle: viewModel.project!.repository,
        ),
        _SurfaceCard(
          semanticLabel: l10n.hierarchy,
          child: Column(
            children: [
              for (final epic in viewModel.epics) ...[
                _TreeIssueRow(
                  issue: epic,
                  depth: 0,
                  onSelect: (issue) => viewModel.selectIssue(
                    issue,
                    returnSection: TrackerSection.hierarchy,
                  ),
                  onCreateChild: () => onOpenCreateIssue(
                    _CreateIssuePrefill.forChild(
                      originSection: TrackerSection.hierarchy,
                      issue: epic,
                    ),
                  ),
                ),
                for (final child in viewModel.issues.where(
                  (i) => i.epicKey == epic.key,
                ))
                  _TreeIssueRow(
                    issue: child,
                    depth: child.parentKey == null ? 1 : 2,
                    onSelect: (issue) => viewModel.selectIssue(
                      issue,
                      returnSection: TrackerSection.hierarchy,
                    ),
                    onCreateChild: () => onOpenCreateIssue(
                      _CreateIssuePrefill.forChild(
                        originSection: TrackerSection.hierarchy,
                        issue: child,
                      ),
                    ),
                  ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _Settings extends StatefulWidget {
  const _Settings({
    required this.viewModel,
    required this.onApplyLocalGitConfiguration,
  });

  final TrackerViewModel viewModel;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;

  @override
  State<_Settings> createState() => _SettingsState();
}

class _SettingsState extends State<_Settings> {
  late _SettingsProviderSelection _selectedProvider;
  final TextEditingController _repositoryPathController =
      TextEditingController();
  final TextEditingController _writeBranchController = TextEditingController();
  final FocusNode _repositoryPathFocusNode = FocusNode();
  final FocusNode _writeBranchFocusNode = FocusNode();
  String? _lastAppliedLocalGitConfigurationKey;

  @override
  void initState() {
    super.initState();
    _selectedProvider = _initialProvider(widget.viewModel);
    _repositoryPathController.addListener(_maybeApplyLocalGitConfiguration);
    _writeBranchController.addListener(_maybeApplyLocalGitConfiguration);
    _repositoryPathFocusNode.addListener(_maybeApplyLocalGitConfiguration);
    _writeBranchFocusNode.addListener(_maybeApplyLocalGitConfiguration);
  }

  @override
  void dispose() {
    _repositoryPathController.dispose();
    _writeBranchController.dispose();
    _repositoryPathFocusNode.dispose();
    _writeBranchFocusNode.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(covariant _Settings oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!widget.viewModel.supportsGitHubAuth &&
        _selectedProvider != _SettingsProviderSelection.localGit) {
      _selectedProvider = _SettingsProviderSelection.localGit;
    }
  }

  _SettingsProviderSelection _initialProvider(TrackerViewModel viewModel) {
    return viewModel.usesLocalPersistence
        ? _SettingsProviderSelection.localGit
        : _SettingsProviderSelection.hosted;
  }

  void _clearLocalGitDraft() {
    _repositoryPathController.clear();
    _writeBranchController.clear();
    _lastAppliedLocalGitConfigurationKey = null;
  }

  Future<void> _maybeApplyLocalGitConfiguration() async {
    if (_selectedProvider != _SettingsProviderSelection.localGit ||
        _repositoryPathFocusNode.hasFocus ||
        _writeBranchFocusNode.hasFocus) {
      return;
    }
    final repositoryPath = _repositoryPathController.text.trim();
    final writeBranch = _writeBranchController.text.trim();
    if (repositoryPath.isEmpty || writeBranch.isEmpty) {
      return;
    }
    final configurationKey = '$repositoryPath\n$writeBranch';
    if (_lastAppliedLocalGitConfigurationKey == configurationKey) {
      return;
    }
    _lastAppliedLocalGitConfigurationKey = configurationKey;
    var appliedSuccessfully = false;
    try {
      await widget.onApplyLocalGitConfiguration(
        repositoryPath: repositoryPath,
        writeBranch: writeBranch,
      );
      appliedSuccessfully = true;
    } finally {
      if (!appliedSuccessfully &&
          _lastAppliedLocalGitConfigurationKey == configurationKey) {
        _lastAppliedLocalGitConfigurationKey = null;
      }
    }
  }

  void _selectProvider(_SettingsProviderSelection selection) {
    if (_selectedProvider == selection) {
      return;
    }
    setState(() {
      if (_selectedProvider == _SettingsProviderSelection.localGit &&
          selection != _SettingsProviderSelection.localGit) {
        _clearLocalGitDraft();
      }
      _selectedProvider = selection;
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final project = widget.viewModel.project!;
    final hostedLabel = _repositoryAccessLabel(l10n, widget.viewModel);
    final selectorChildren = <Widget>[
      if (widget.viewModel.supportsGitHubAuth) ...[
        _SettingsProviderButton(
          label: hostedLabel,
          selected: _selectedProvider == _SettingsProviderSelection.hosted,
          tone:
              widget.viewModel.repositoryAccessState ==
                  RepositoryAccessState.connected
              ? _SettingsProviderButtonTone.connected
              : _SettingsProviderButtonTone.defaultTone,
          onPressed: () => _selectProvider(_SettingsProviderSelection.hosted),
        ),
        if (_selectedProvider == _SettingsProviderSelection.hosted) ...[
          const SizedBox(height: 12),
          _HostedProviderConfiguration(viewModel: widget.viewModel),
        ],
        const SizedBox(height: 12),
      ],
      _SettingsProviderButton(
        label: l10n.repositoryAccessLocalGit,
        selected: _selectedProvider == _SettingsProviderSelection.localGit,
        onPressed: () => _selectProvider(_SettingsProviderSelection.localGit),
      ),
      if (_selectedProvider == _SettingsProviderSelection.localGit) ...[
        const SizedBox(height: 12),
        _LocalGitConfiguration(
          repositoryPathController: _repositoryPathController,
          writeBranchController: _writeBranchController,
          repositoryPathFocusNode: _repositoryPathFocusNode,
          writeBranchFocusNode: _writeBranchFocusNode,
        ),
      ],
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ScreenHeading(
          title: l10n.projectSettings,
          subtitle: project.repository,
        ),
        if (widget.viewModel.startupRecovery case final recovery?) ...[
          _AccessCallout(
            semanticLabel: l10n.startupRecovery,
            title: _startupRecoveryTitle(l10n, recovery),
            message: _startupRecoveryMessage(l10n, widget.viewModel),
            primaryActionLabel: l10n.retry,
            onPrimaryAction: widget.viewModel.retryStartupRecovery,
            secondaryActionLabel: widget.viewModel.supportsGitHubAuth
                ? l10n.connectGitHub
                : null,
            onSecondaryAction: widget.viewModel.supportsGitHubAuth
                ? () => _showRepositoryAccessDialog(context, widget.viewModel)
                : null,
          ),
          const SizedBox(height: 16),
        ],
        _SurfaceCard(
          semanticLabel: l10n.repositoryAccessSettings,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _SectionTitle(l10n.repositoryAccessSettings),
              const SizedBox(height: 8),
              ...selectorChildren,
            ],
          ),
        ),
        const SizedBox(height: 16),
        _ProjectSettingsAdmin(viewModel: widget.viewModel),
      ],
    );
  }
}

enum _SettingsProviderSelection { hosted, localGit }

enum _SettingsCatalogTab { statuses, workflows, issueTypes, fields }

class _ProjectSettingsAdmin extends StatefulWidget {
  const _ProjectSettingsAdmin({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  State<_ProjectSettingsAdmin> createState() => _ProjectSettingsAdminState();
}

class _ProjectSettingsAdminState extends State<_ProjectSettingsAdmin>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  ProjectSettingsCatalog? _draftSettings;
  String? _projectSignature;

  @override
  void initState() {
    super.initState();
    _tabController =
        TabController(length: _SettingsCatalogTab.values.length, vsync: this)
          ..addListener(() {
            if (_tabController.indexIsChanging) {
              return;
            }
            setState(() {});
          });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _syncDraft(ProjectConfig project) {
    final signature = _projectSettingsSignature(project.settingsCatalog);
    if (_projectSignature == signature && _draftSettings != null) {
      return;
    }
    _projectSignature = signature;
    _draftSettings = _cloneProjectSettings(project.settingsCatalog);
  }

  void _replaceDraft(ProjectSettingsCatalog settings) {
    setState(() {
      _draftSettings = settings;
    });
  }

  void _resetDraft(ProjectConfig project) {
    setState(() {
      _projectSignature = _projectSettingsSignature(project.settingsCatalog);
      _draftSettings = _cloneProjectSettings(project.settingsCatalog);
    });
  }

  Future<T?> _showSettingsEditor<T>({
    required String title,
    required Widget child,
  }) async {
    final width = MediaQuery.of(context).size.width;
    final colors = context.ts;
    if (width >= 960) {
      return showGeneralDialog<T>(
        context: context,
        barrierDismissible: true,
        barrierLabel: title,
        barrierColor: Colors.black54,
        pageBuilder: (dialogContext, _, _) {
          return SafeArea(
            child: Align(
              alignment: Alignment.centerRight,
              child: Material(
                color: colors.surface,
                child: SizedBox(
                  width: math.min(width * 0.42, 520),
                  child: _SettingsEditorShell(title: title, child: child),
                ),
              ),
            ),
          );
        },
      );
    }
    return showDialog<T>(
      context: context,
      builder: (dialogContext) => Dialog(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: _SettingsEditorShell(title: title, child: child),
        ),
      ),
    );
  }

  Future<void> _editStatus({
    required AppLocalizations l10n,
    TrackStateConfigEntry? initial,
  }) async {
    final edited = await _showSettingsEditor<TrackStateConfigEntry>(
      title: initial == null ? l10n.addStatus : l10n.editStatus,
      child: _StatusEditor(initial: initial),
    );
    if (edited == null || _draftSettings == null) {
      return;
    }
    final current = _draftSettings!;
    final statuses = [...current.statusDefinitions];
    if (initial == null) {
      statuses.add(edited);
    } else {
      final index = statuses.indexWhere((entry) => entry.id == initial.id);
      if (index != -1) {
        statuses[index] = edited;
      }
    }
    _replaceDraft(current.copyWith(statusDefinitions: statuses));
  }

  Future<void> _editWorkflow({
    required AppLocalizations l10n,
    TrackStateWorkflowDefinition? initial,
  }) async {
    final statuses = _draftSettings?.statusDefinitions ?? const [];
    final edited = await _showSettingsEditor<TrackStateWorkflowDefinition>(
      title: initial == null ? l10n.addWorkflow : l10n.editWorkflow,
      child: _WorkflowEditor(initial: initial, statuses: statuses),
    );
    if (edited == null || _draftSettings == null) {
      return;
    }
    final current = _draftSettings!;
    final workflows = [...current.workflowDefinitions];
    if (initial == null) {
      workflows.add(edited);
    } else {
      final index = workflows.indexWhere((entry) => entry.id == initial.id);
      if (index != -1) {
        workflows[index] = edited;
      }
    }
    _replaceDraft(current.copyWith(workflowDefinitions: workflows));
  }

  Future<void> _editIssueType({
    required AppLocalizations l10n,
    TrackStateConfigEntry? initial,
  }) async {
    final workflows = _draftSettings?.workflowDefinitions ?? const [];
    final edited = await _showSettingsEditor<TrackStateConfigEntry>(
      title: initial == null ? l10n.addIssueType : l10n.editIssueType,
      child: _IssueTypeEditor(initial: initial, workflows: workflows),
    );
    if (edited == null || _draftSettings == null) {
      return;
    }
    final current = _draftSettings!;
    final issueTypes = [...current.issueTypeDefinitions];
    if (initial == null) {
      issueTypes.add(edited);
    } else {
      final index = issueTypes.indexWhere((entry) => entry.id == initial.id);
      if (index != -1) {
        issueTypes[index] = edited;
      }
    }
    _replaceDraft(current.copyWith(issueTypeDefinitions: issueTypes));
  }

  Future<void> _editField({
    required AppLocalizations l10n,
    TrackStateFieldDefinition? initial,
  }) async {
    final issueTypes = _draftSettings?.issueTypeDefinitions ?? const [];
    final edited = await _showSettingsEditor<TrackStateFieldDefinition>(
      title: initial == null ? l10n.addField : l10n.editField,
      child: _FieldEditor(initial: initial, issueTypes: issueTypes),
    );
    if (edited == null || _draftSettings == null) {
      return;
    }
    final current = _draftSettings!;
    final fields = [...current.fieldDefinitions];
    if (initial == null) {
      fields.add(edited);
    } else {
      final index = fields.indexWhere((entry) => entry.id == initial.id);
      if (index != -1) {
        fields[index] = edited;
      }
    }
    _replaceDraft(current.copyWith(fieldDefinitions: fields));
  }

  Future<void> _saveSettings() async {
    final settings = _draftSettings;
    if (settings == null) {
      return;
    }
    await widget.viewModel.saveProjectSettings(settings);
  }

  Widget _buildCatalogHeader({
    required AppLocalizations l10n,
    required String title,
    required String addLabel,
    required VoidCallback? onAdd,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
          ),
          Semantics(
            button: true,
            label: addLabel,
            child: FilledButton(
              onPressed: onAdd,
              child: ExcludeSemantics(child: Text(addLabel)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusTab(
    AppLocalizations l10n,
    ProjectSettingsCatalog settings,
    bool canEdit,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildCatalogHeader(
          l10n: l10n,
          title: l10n.statuses,
          addLabel: l10n.addStatus,
          onAdd: canEdit ? () => _editStatus(l10n: l10n) : null,
        ),
        for (final status in settings.statusDefinitions)
          _SettingsCatalogListTile(
            title: status.name,
            subtitle:
                '${l10n.catalogId}: ${status.id}'
                '${status.category == null ? '' : ' • ${l10n.catalogCategory}: ${status.category}'}',
            onEdit: canEdit
                ? () => _editStatus(l10n: l10n, initial: status)
                : null,
            onDelete: canEdit
                ? () => _replaceDraft(
                    settings.copyWith(
                      statusDefinitions: [
                        for (final entry in settings.statusDefinitions)
                          if (entry.id != status.id) entry,
                      ],
                    ),
                  )
                : null,
            editLabel: '${l10n.editStatus} ${status.name}',
            deleteLabel: '${l10n.deleteStatus} ${status.name}',
          ),
      ],
    );
  }

  Widget _buildWorkflowTab(
    AppLocalizations l10n,
    ProjectSettingsCatalog settings,
    bool canEdit,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildCatalogHeader(
          l10n: l10n,
          title: l10n.workflows,
          addLabel: l10n.addWorkflow,
          onAdd: canEdit ? () => _editWorkflow(l10n: l10n) : null,
        ),
        for (final workflow in settings.workflowDefinitions)
          _SettingsCatalogListTile(
            title: workflow.name,
            subtitle:
                '${l10n.catalogId}: ${workflow.id} • '
                '${l10n.catalogStatuses}: ${workflow.statusIds.join(', ')} • '
                '${l10n.catalogTransitions}: ${workflow.transitions.length}',
            onEdit: canEdit
                ? () => _editWorkflow(l10n: l10n, initial: workflow)
                : null,
            onDelete: canEdit
                ? () => _replaceDraft(
                    settings.copyWith(
                      workflowDefinitions: [
                        for (final entry in settings.workflowDefinitions)
                          if (entry.id != workflow.id) entry,
                      ],
                    ),
                  )
                : null,
            editLabel: '${l10n.editWorkflow} ${workflow.name}',
            deleteLabel: '${l10n.deleteWorkflow} ${workflow.name}',
          ),
      ],
    );
  }

  Widget _buildIssueTypeTab(
    AppLocalizations l10n,
    ProjectSettingsCatalog settings,
    bool canEdit,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildCatalogHeader(
          l10n: l10n,
          title: l10n.issueTypes,
          addLabel: l10n.addIssueType,
          onAdd: canEdit ? () => _editIssueType(l10n: l10n) : null,
        ),
        for (final issueType in settings.issueTypeDefinitions)
          _SettingsCatalogListTile(
            title: issueType.name,
            subtitle:
                '${l10n.catalogId}: ${issueType.id}'
                '${issueType.workflowId == null ? '' : ' • ${l10n.catalogWorkflow}: ${issueType.workflowId}'}'
                '${issueType.hierarchyLevel == null ? '' : ' • ${l10n.catalogHierarchyLevel}: ${issueType.hierarchyLevel}'}',
            onEdit: canEdit
                ? () => _editIssueType(l10n: l10n, initial: issueType)
                : null,
            onDelete: canEdit
                ? () => _replaceDraft(
                    settings.copyWith(
                      issueTypeDefinitions: [
                        for (final entry in settings.issueTypeDefinitions)
                          if (entry.id != issueType.id) entry,
                      ],
                    ),
                  )
                : null,
            editLabel: '${l10n.editIssueType} ${issueType.name}',
            deleteLabel: '${l10n.deleteIssueType} ${issueType.name}',
          ),
      ],
    );
  }

  Widget _buildFieldTab(
    AppLocalizations l10n,
    ProjectSettingsCatalog settings,
    bool canEdit,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildCatalogHeader(
          l10n: l10n,
          title: l10n.fields,
          addLabel: l10n.addField,
          onAdd: canEdit ? () => _editField(l10n: l10n) : null,
        ),
        for (final field in settings.fieldDefinitions)
          _SettingsCatalogListTile(
            title: field.name,
            subtitle:
                '${l10n.catalogId}: ${field.id} • '
                '${l10n.catalogType}: ${field.type} • '
                '${field.required ? l10n.catalogRequired : l10n.optional}'
                '${field.reserved ? ' • ${l10n.catalogReserved}' : ''}',
            onEdit: canEdit
                ? () => _editField(l10n: l10n, initial: field)
                : null,
            onDelete: canEdit && !field.reserved
                ? () => _replaceDraft(
                    settings.copyWith(
                      fieldDefinitions: [
                        for (final entry in settings.fieldDefinitions)
                          if (entry.id != field.id) entry,
                      ],
                    ),
                  )
                : null,
            editLabel: '${l10n.editField} ${field.name}',
            deleteLabel: '${l10n.deleteField} ${field.name}',
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final project = widget.viewModel.project!;
    _syncDraft(project);
    final l10n = AppLocalizations.of(context)!;
    final settings = _draftSettings!;
    final canEdit =
        widget.viewModel.supportsProjectSettingsAdmin &&
        !widget.viewModel.hasBlockedWriteAccess &&
        !widget.viewModel.isSaving;
    final tabBar = TabBar(
      controller: _tabController,
      isScrollable: true,
      tabs: [
        Tab(text: l10n.statuses),
        Tab(text: l10n.workflows),
        Tab(text: l10n.issueTypes),
        Tab(text: l10n.fields),
      ],
    );
    final content = switch (_SettingsCatalogTab.values[_tabController.index]) {
      _SettingsCatalogTab.statuses => _buildStatusTab(l10n, settings, canEdit),
      _SettingsCatalogTab.workflows => _buildWorkflowTab(
        l10n,
        settings,
        canEdit,
      ),
      _SettingsCatalogTab.issueTypes => _buildIssueTypeTab(
        l10n,
        settings,
        canEdit,
      ),
      _SettingsCatalogTab.fields => _buildFieldTab(l10n, settings, canEdit),
    };
    return _SurfaceCard(
      semanticLabel: l10n.projectSettingsAdmin,
      explicitChildNodes: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _SectionTitle(l10n.projectSettingsAdmin),
                    const SizedBox(height: 4),
                    Text(l10n.projectSettingsDescription),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _IssueDetailActionButton(
                    label: l10n.resetSettings,
                    onPressed: widget.viewModel.isSaving
                        ? null
                        : () => _resetDraft(project),
                  ),
                  _IssueDetailActionButton(
                    label: l10n.saveSettings,
                    emphasized: true,
                    onPressed: canEdit ? _saveSettings : null,
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          tabBar,
          const SizedBox(height: 16),
          content,
        ],
      ),
    );
  }
}

class _SettingsCatalogListTile extends StatelessWidget {
  const _SettingsCatalogListTile({
    required this.title,
    required this.subtitle,
    required this.editLabel,
    required this.deleteLabel,
    this.onEdit,
    this.onDelete,
  });

  final String title;
  final String subtitle;
  final String editLabel;
  final String deleteLabel;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      title: Text(title),
      subtitle: Text(subtitle),
      trailing: Wrap(
        spacing: 4,
        children: [
          if (onEdit != null)
            Semantics(
              button: true,
              label: editLabel,
              child: TextButton(
                onPressed: onEdit,
                child: ExcludeSemantics(child: Text(l10n.edit)),
              ),
            ),
          if (onDelete != null)
            Semantics(
              button: true,
              label: deleteLabel,
              child: TextButton(
                onPressed: onDelete,
                child: ExcludeSemantics(child: Text(l10n.delete)),
              ),
            ),
        ],
      ),
    );
  }
}

class _SettingsEditorShell extends StatelessWidget {
  const _SettingsEditorShell({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 16),
          Flexible(child: SingleChildScrollView(child: child)),
        ],
      ),
    );
  }
}

class _StatusEditor extends StatefulWidget {
  const _StatusEditor({this.initial});

  final TrackStateConfigEntry? initial;

  @override
  State<_StatusEditor> createState() => _StatusEditorState();
}

class _StatusEditorState extends State<_StatusEditor> {
  late final TextEditingController _idController;
  late final TextEditingController _nameController;
  String _category = 'indeterminate';

  @override
  void initState() {
    super.initState();
    _idController = TextEditingController(text: widget.initial?.id ?? '');
    _nameController = TextEditingController(text: widget.initial?.name ?? '');
    _category = widget.initial?.category ?? 'indeterminate';
  }

  @override
  void dispose() {
    _idController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SettingsTextField(label: l10n.catalogId, controller: _idController),
        const SizedBox(height: 12),
        _SettingsTextField(label: l10n.name, controller: _nameController),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _category,
          decoration: InputDecoration(labelText: l10n.catalogCategory),
          items: [
            DropdownMenuItem(value: 'new', child: Text(l10n.statusCategoryNew)),
            DropdownMenuItem(
              value: 'indeterminate',
              child: Text(l10n.statusCategoryIndeterminate),
            ),
            DropdownMenuItem(
              value: 'done',
              child: Text(l10n.statusCategoryDone),
            ),
          ],
          onChanged: (value) {
            setState(() {
              _category = value ?? 'indeterminate';
            });
          },
        ),
        const SizedBox(height: 16),
        _SettingsEditorActions(
          onSave: () {
            Navigator.of(context).pop(
              TrackStateConfigEntry(
                id: _normalizedEditorId(
                  _idController.text,
                  _nameController.text,
                ),
                name: _nameController.text.trim(),
                category: _category,
              ),
            );
          },
        ),
      ],
    );
  }
}

class _IssueTypeEditor extends StatefulWidget {
  const _IssueTypeEditor({required this.workflows, this.initial});

  final TrackStateConfigEntry? initial;
  final List<TrackStateWorkflowDefinition> workflows;

  @override
  State<_IssueTypeEditor> createState() => _IssueTypeEditorState();
}

class _IssueTypeEditorState extends State<_IssueTypeEditor> {
  late final TextEditingController _idController;
  late final TextEditingController _nameController;
  late final TextEditingController _hierarchyLevelController;
  late final TextEditingController _iconController;
  String? _workflowId;

  @override
  void initState() {
    super.initState();
    _idController = TextEditingController(text: widget.initial?.id ?? '');
    _nameController = TextEditingController(text: widget.initial?.name ?? '');
    _hierarchyLevelController = TextEditingController(
      text: widget.initial?.hierarchyLevel?.toString() ?? '0',
    );
    _iconController = TextEditingController(text: widget.initial?.icon ?? '');
    _workflowId =
        widget.initial?.workflowId ??
        (widget.workflows.isNotEmpty ? widget.workflows.first.id : null);
  }

  @override
  void dispose() {
    _idController.dispose();
    _nameController.dispose();
    _hierarchyLevelController.dispose();
    _iconController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SettingsTextField(label: l10n.catalogId, controller: _idController),
        const SizedBox(height: 12),
        _SettingsTextField(label: l10n.name, controller: _nameController),
        const SizedBox(height: 12),
        _SettingsTextField(
          label: l10n.catalogHierarchyLevel,
          controller: _hierarchyLevelController,
        ),
        const SizedBox(height: 12),
        _SettingsTextField(
          label: l10n.catalogIcon,
          controller: _iconController,
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _workflowId,
          decoration: InputDecoration(labelText: l10n.catalogWorkflow),
          items: [
            for (final workflow in widget.workflows)
              DropdownMenuItem(value: workflow.id, child: Text(workflow.name)),
          ],
          onChanged: (value) {
            setState(() {
              _workflowId = value;
            });
          },
        ),
        const SizedBox(height: 16),
        _SettingsEditorActions(
          onSave: () {
            Navigator.of(context).pop(
              TrackStateConfigEntry(
                id: _normalizedEditorId(
                  _idController.text,
                  _nameController.text,
                ),
                name: _nameController.text.trim(),
                hierarchyLevel:
                    int.tryParse(_hierarchyLevelController.text.trim()) ?? 0,
                icon: _iconController.text.trim(),
                workflowId: _workflowId,
              ),
            );
          },
        ),
      ],
    );
  }
}

class _FieldEditor extends StatefulWidget {
  const _FieldEditor({required this.issueTypes, this.initial});

  final TrackStateFieldDefinition? initial;
  final List<TrackStateConfigEntry> issueTypes;

  @override
  State<_FieldEditor> createState() => _FieldEditorState();
}

class _FieldEditorState extends State<_FieldEditor> {
  late final TextEditingController _idController;
  late final TextEditingController _nameController;
  late final TextEditingController _defaultValueController;
  late final TextEditingController _optionsController;
  late final Set<String> _applicableIssueTypeIds;
  String _type = 'string';
  bool _required = false;

  bool get _isReserved => widget.initial?.reserved ?? false;

  @override
  void initState() {
    super.initState();
    _idController = TextEditingController(text: widget.initial?.id ?? '');
    _nameController = TextEditingController(text: widget.initial?.name ?? '');
    _defaultValueController = TextEditingController(
      text: widget.initial?.defaultValue?.toString() ?? '',
    );
    _optionsController = TextEditingController(
      text: widget.initial == null
          ? ''
          : widget.initial!.options.map((option) => option.name).join(', '),
    );
    _applicableIssueTypeIds = {...?widget.initial?.applicableIssueTypeIds};
    _type = widget.initial?.type ?? 'string';
    _required = widget.initial?.required ?? false;
  }

  @override
  void dispose() {
    _idController.dispose();
    _nameController.dispose();
    _defaultValueController.dispose();
    _optionsController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SettingsTextField(label: l10n.catalogId, controller: _idController),
        const SizedBox(height: 12),
        _SettingsTextField(label: l10n.name, controller: _nameController),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _type,
          decoration: InputDecoration(labelText: l10n.catalogType),
          items: const [
            DropdownMenuItem(value: 'string', child: Text('string')),
            DropdownMenuItem(value: 'markdown', child: Text('markdown')),
            DropdownMenuItem(value: 'option', child: Text('option')),
            DropdownMenuItem(value: 'user', child: Text('user')),
            DropdownMenuItem(value: 'array', child: Text('array')),
            DropdownMenuItem(value: 'number', child: Text('number')),
          ],
          onChanged: _isReserved
              ? null
              : (value) {
                  setState(() {
                    _type = value ?? 'string';
                  });
                },
        ),
        const SizedBox(height: 12),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          value: _required,
          title: Text(l10n.catalogRequired),
          onChanged: (value) {
            setState(() {
              _required = value ?? false;
            });
          },
        ),
        const SizedBox(height: 12),
        _SettingsTextField(
          label: l10n.catalogDefaultValue,
          controller: _defaultValueController,
        ),
        const SizedBox(height: 12),
        _SettingsTextField(
          label: l10n.catalogOptions,
          controller: _optionsController,
        ),
        const SizedBox(height: 12),
        Text(
          l10n.applicableIssueTypes,
          style: Theme.of(context).textTheme.labelLarge,
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final issueType in widget.issueTypes)
              FilterChip(
                label: Text(issueType.name),
                selected: _applicableIssueTypeIds.contains(issueType.id),
                onSelected: (selected) {
                  setState(() {
                    if (selected) {
                      _applicableIssueTypeIds.add(issueType.id);
                    } else {
                      _applicableIssueTypeIds.remove(issueType.id);
                    }
                  });
                },
              ),
          ],
        ),
        const SizedBox(height: 16),
        _SettingsEditorActions(
          onSave: () {
            final normalizedId = _normalizedEditorId(
              _idController.text,
              _nameController.text,
            );
            Navigator.of(context).pop(
              TrackStateFieldDefinition(
                id: normalizedId,
                name: _nameController.text.trim(),
                type: _type,
                required: _required,
                options: _type == 'option'
                    ? _optionsController.text
                          .split(',')
                          .map((entry) => entry.trim())
                          .where((entry) => entry.isNotEmpty)
                          .map(
                            (entry) => TrackStateFieldOption(
                              id: _normalizedEditorId('', entry),
                              name: entry,
                            ),
                          )
                          .toList(growable: false)
                    : const [],
                defaultValue: _defaultValueController.text.trim().isEmpty
                    ? null
                    : _defaultValueController.text.trim(),
                applicableIssueTypeIds: _applicableIssueTypeIds.toList()
                  ..sort(),
                reserved:
                    _isReserved || _reservedFieldIds.contains(normalizedId),
              ),
            );
          },
        ),
      ],
    );
  }
}

class _WorkflowEditor extends StatefulWidget {
  const _WorkflowEditor({required this.statuses, this.initial});

  final TrackStateWorkflowDefinition? initial;
  final List<TrackStateConfigEntry> statuses;

  @override
  State<_WorkflowEditor> createState() => _WorkflowEditorState();
}

class _WorkflowEditorState extends State<_WorkflowEditor> {
  late final TextEditingController _idController;
  late final TextEditingController _nameController;
  late final Set<String> _statusIds;
  late final List<TrackStateWorkflowTransition> _transitions;

  @override
  void initState() {
    super.initState();
    _idController = TextEditingController(text: widget.initial?.id ?? '');
    _nameController = TextEditingController(text: widget.initial?.name ?? '');
    _statusIds = {...?widget.initial?.statusIds};
    _transitions = [...?widget.initial?.transitions];
  }

  @override
  void dispose() {
    _idController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SettingsTextField(label: l10n.catalogId, controller: _idController),
        const SizedBox(height: 12),
        _SettingsTextField(label: l10n.name, controller: _nameController),
        const SizedBox(height: 12),
        Text(
          l10n.allowedStatuses,
          style: Theme.of(context).textTheme.labelLarge,
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final status in widget.statuses)
              FilterChip(
                label: Text(status.name),
                selected: _statusIds.contains(status.id),
                onSelected: (selected) {
                  setState(() {
                    if (selected) {
                      _statusIds.add(status.id);
                    } else {
                      _statusIds.remove(status.id);
                    }
                  });
                },
              ),
          ],
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: Text(
                l10n.catalogTransitions,
                style: Theme.of(context).textTheme.labelLarge,
              ),
            ),
            TextButton(
              onPressed: () {
                final fallbackStatusId = _statusIds.isNotEmpty
                    ? _statusIds.first
                    : 'todo';
                setState(() {
                  _transitions.add(
                    TrackStateWorkflowTransition(
                      id: 'transition-${_transitions.length + 1}',
                      name: '',
                      fromStatusId: fallbackStatusId,
                      toStatusId: fallbackStatusId,
                    ),
                  );
                });
              },
              child: Text(l10n.addTransition),
            ),
          ],
        ),
        const SizedBox(height: 8),
        for (var index = 0; index < _transitions.length; index += 1)
          _WorkflowTransitionEditorRow(
            transition: _transitions[index],
            statuses: widget.statuses
                .where((status) => _statusIds.contains(status.id))
                .toList(growable: false),
            onChanged: (transition) {
              setState(() {
                _transitions[index] = transition;
              });
            },
            onDelete: () {
              setState(() {
                _transitions.removeAt(index);
              });
            },
          ),
        const SizedBox(height: 16),
        _SettingsEditorActions(
          onSave: () {
            Navigator.of(context).pop(
              TrackStateWorkflowDefinition(
                id: _normalizedEditorId(
                  _idController.text,
                  _nameController.text,
                ),
                name: _nameController.text.trim(),
                statusIds: _statusIds.toList()..sort(),
                transitions: _transitions,
              ),
            );
          },
        ),
      ],
    );
  }
}

class _WorkflowTransitionEditorRow extends StatefulWidget {
  const _WorkflowTransitionEditorRow({
    required this.transition,
    required this.statuses,
    required this.onChanged,
    required this.onDelete,
  });

  final TrackStateWorkflowTransition transition;
  final List<TrackStateConfigEntry> statuses;
  final ValueChanged<TrackStateWorkflowTransition> onChanged;
  final VoidCallback onDelete;

  @override
  State<_WorkflowTransitionEditorRow> createState() =>
      _WorkflowTransitionEditorRowState();
}

class _WorkflowTransitionEditorRowState
    extends State<_WorkflowTransitionEditorRow> {
  late final TextEditingController _idController;
  late final TextEditingController _nameController;
  late String _fromStatusId;
  late String _toStatusId;

  @override
  void initState() {
    super.initState();
    _idController = TextEditingController(text: widget.transition.id);
    _nameController = TextEditingController(text: widget.transition.name);
    _fromStatusId = widget.transition.fromStatusId;
    _toStatusId = widget.transition.toStatusId;
  }

  @override
  void dispose() {
    _idController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  void _emit() {
    widget.onChanged(
      TrackStateWorkflowTransition(
        id: _normalizedEditorId(_idController.text, _nameController.text),
        name: _nameController.text.trim(),
        fromStatusId: _fromStatusId,
        toStatusId: _toStatusId,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final statusItems = widget.statuses.isEmpty
        ? const [DropdownMenuItem(value: 'todo', child: Text('todo'))]
        : [
            for (final status in widget.statuses)
              DropdownMenuItem(value: status.id, child: Text(status.name)),
          ];
    if (!statusItems.any((item) => item.value == _fromStatusId)) {
      _fromStatusId = statusItems.first.value!;
    }
    if (!statusItems.any((item) => item.value == _toStatusId)) {
      _toStatusId = statusItems.first.value!;
    }
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            TextField(
              controller: _idController,
              decoration: InputDecoration(labelText: l10n.catalogId),
              onChanged: (_) => _emit(),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _nameController,
              decoration: InputDecoration(labelText: l10n.transitionName),
              onChanged: (_) => _emit(),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              initialValue: _fromStatusId,
              decoration: InputDecoration(labelText: l10n.transitionFrom),
              items: statusItems,
              onChanged: (value) {
                setState(() {
                  _fromStatusId = value ?? _fromStatusId;
                });
                _emit();
              },
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              initialValue: _toStatusId,
              decoration: InputDecoration(labelText: l10n.transitionTo),
              items: statusItems,
              onChanged: (value) {
                setState(() {
                  _toStatusId = value ?? _toStatusId;
                });
                _emit();
              },
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: widget.onDelete,
                child: Text(l10n.removeTransition),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SettingsEditorActions extends StatelessWidget {
  const _SettingsEditorActions({required this.onSave});

  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l10n.cancel),
        ),
        const SizedBox(width: 8),
        FilledButton(onPressed: onSave, child: Text(l10n.save)),
      ],
    );
  }
}

ProjectSettingsCatalog _cloneProjectSettings(ProjectSettingsCatalog settings) {
  return ProjectSettingsCatalog(
    statusDefinitions: [
      for (final status in settings.statusDefinitions) status.copyWith(),
    ],
    workflowDefinitions: [
      for (final workflow in settings.workflowDefinitions)
        workflow.copyWith(
          statusIds: [...workflow.statusIds],
          transitions: [
            for (final transition in workflow.transitions)
              transition.copyWith(),
          ],
        ),
    ],
    issueTypeDefinitions: [
      for (final issueType in settings.issueTypeDefinitions)
        issueType.copyWith(),
    ],
    fieldDefinitions: [
      for (final field in settings.fieldDefinitions)
        field.copyWith(
          options: [for (final option in field.options) option.copyWith()],
          applicableIssueTypeIds: [...field.applicableIssueTypeIds],
        ),
    ],
  );
}

String _projectSettingsSignature(ProjectSettingsCatalog settings) {
  return [
    for (final status in settings.statusDefinitions)
      'status:${status.id}:${status.name}:${status.category ?? ''}',
    for (final workflow in settings.workflowDefinitions)
      'workflow:${workflow.id}:${workflow.name}:${workflow.statusIds.join(',')}:${workflow.transitions.map((transition) => '${transition.id}:${transition.name}:${transition.fromStatusId}:${transition.toStatusId}').join('|')}',
    for (final issueType in settings.issueTypeDefinitions)
      'issueType:${issueType.id}:${issueType.name}:${issueType.workflowId ?? ''}:${issueType.hierarchyLevel ?? ''}:${issueType.icon ?? ''}',
    for (final field in settings.fieldDefinitions)
      'field:${field.id}:${field.name}:${field.type}:${field.required}:${field.reserved}:${field.options.map((option) => '${option.id}:${option.name}').join('|')}:${field.defaultValue ?? ''}:${field.applicableIssueTypeIds.join(',')}',
  ].join('\n');
}

const _reservedFieldIds = {
  'summary',
  'description',
  'acceptanceCriteria',
  'priority',
  'assignee',
  'labels',
  'storyPoints',
};

String _normalizedEditorId(String rawId, String fallbackName) {
  final trimmedId = rawId.trim();
  if (trimmedId.isNotEmpty) {
    return trimmedId;
  }
  final normalized = fallbackName
      .trim()
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'^-+|-+$'), '');
  return normalized;
}

class _IssueDetail extends StatefulWidget {
  const _IssueDetail({
    required this.issue,
    required this.viewModel,
    required this.onCreateChildIssue,
    required this.attachmentPicker,
  });

  final TrackStateIssue issue;
  final TrackerViewModel viewModel;
  final VoidCallback onCreateChildIssue;
  final AttachmentPicker attachmentPicker;

  @override
  State<_IssueDetail> createState() => _IssueDetailState();
}

class _IssueDetailState extends State<_IssueDetail> {
  late final TextEditingController _commentController;
  int _selectedCollaborationTab = 0;
  PickedAttachment? _selectedAttachment;
  String? _attachmentUploadNotice;

  @override
  void initState() {
    super.initState();
    _commentController = TextEditingController();
    _scheduleActiveIssueDataLoad();
  }

  @override
  void didUpdateWidget(covariant _IssueDetail oldWidget) {
    super.didUpdateWidget(oldWidget);
    final issueChanged = oldWidget.issue.key != widget.issue.key;
    if (issueChanged) {
      _commentController.clear();
      _selectedAttachment = null;
      _attachmentUploadNotice = null;
    }
    if (issueChanged ||
        (!_activeTabDataLoaded(widget.issue) &&
            !_activeTabHasDeferredError(widget.issue))) {
      _scheduleActiveIssueDataLoad();
    }
  }

  void _scheduleActiveIssueDataLoad() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      _ensureActiveIssueDataLoaded();
    });
  }

  void _ensureActiveIssueDataLoaded() {
    widget.viewModel.ensureIssueDetailLoaded(widget.issue);
    switch (_selectedCollaborationTab) {
      case 1:
        widget.viewModel.ensureIssueCommentsLoaded(widget.issue);
      case 2:
        widget.viewModel.ensureIssueAttachmentsLoaded(widget.issue);
      case 3:
        widget.viewModel.ensureIssueHistoryLoaded(widget.issue);
      case 0:
        break;
    }
  }

  bool _activeTabDataLoaded(TrackStateIssue issue) {
    if (!issue.hasDetailLoaded) {
      return false;
    }
    return switch (_selectedCollaborationTab) {
      1 => issue.hasCommentsLoaded,
      2 => issue.hasAttachmentsLoaded,
      _ => true,
    };
  }

  bool _activeTabHasDeferredError(TrackStateIssue issue) {
    final section = switch (_selectedCollaborationTab) {
      0 => IssueDeferredSection.detail,
      1 => IssueDeferredSection.comments,
      2 => IssueDeferredSection.attachments,
      _ => IssueDeferredSection.history,
    };
    return widget.viewModel.hasIssueDeferredError(issue.key, section);
  }

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _openEditDialog({required bool workflowOnly}) async {
    await showDialog<void>(
      context: context,
      barrierColor: Colors.black.withValues(alpha: 0.12),
      builder: (dialogContext) {
        return _IssueEditDialog(
          issue: widget.issue,
          viewModel: widget.viewModel,
          workflowOnly: workflowOnly,
        );
      },
    );
  }

  Future<void> _saveComment() async {
    final success = await widget.viewModel.postIssueComment(
      widget.issue,
      _commentController.text,
    );
    if (!mounted || !success) {
      return;
    }
    _commentController.clear();
  }

  Future<void> _chooseAttachment() async {
    if (!widget.viewModel.canUploadIssueAttachments) {
      return;
    }
    final pickedAttachment = await widget.attachmentPicker();
    if (!mounted || pickedAttachment == null) {
      return;
    }
    setState(() {
      _selectedAttachment = pickedAttachment;
      _attachmentUploadNotice = null;
    });
  }

  Future<void> _uploadAttachment() async {
    if (!widget.viewModel.canUploadIssueAttachments) {
      return;
    }
    final selectedAttachment = _selectedAttachment;
    if (selectedAttachment == null) {
      return;
    }
    final l10n = AppLocalizations.of(context)!;
    final inspection = await widget.viewModel.inspectIssueAttachmentUpload(
      widget.issue,
      selectedAttachment.name,
    );
    if (!mounted) {
      return;
    }
    if (widget.viewModel.hasAttachmentUploadRestriction &&
        inspection.isLfsTracked) {
      setState(() {
        _attachmentUploadNotice = l10n.attachmentRequiresLocalGitUpload(
          inspection.resolvedName,
        );
      });
      return;
    }
    if (inspection.existingAttachment != null) {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) {
          return AlertDialog(
            title: Text(l10n.replaceAttachmentTitle),
            content: Text(
              l10n.replaceAttachmentMessage(
                inspection.existingAttachment!.name,
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: Text(l10n.keepCurrentAttachment),
              ),
              FilledButton(
                onPressed: () => Navigator.of(context).pop(true),
                child: Text(l10n.replaceAttachmentAction),
              ),
            ],
          );
        },
      );
      if (!mounted || confirmed != true) {
        return;
      }
    }
    final success = await widget.viewModel.uploadIssueAttachment(
      issue: widget.issue,
      name: selectedAttachment.name,
      bytes: selectedAttachment.bytes,
    );
    if (!mounted || !success) {
      return;
    }
    setState(() {
      _selectedAttachment = null;
      _attachmentUploadNotice = null;
    });
  }

  Widget _detailTabContent(
    BuildContext context, {
    required TrackStateIssue issue,
    required AppLocalizations l10n,
    required TrackStateColors colors,
  }) {
    final errorText = widget.viewModel.issueDeferredError(
      issue.key,
      IssueDeferredSection.detail,
    );
    if (errorText != null) {
      return _DeferredSectionStateCard(
        semanticLabel: '${l10n.detail} error',
        title: l10n.detail,
        message: errorText,
        tone: _DeferredSectionTone.error,
        actionLabel: l10n.retry,
        onAction: () => widget.viewModel.ensureIssueDetailLoaded(issue),
      );
    }
    if (widget.viewModel.isIssueDetailLoading(issue.key) ||
        !issue.hasDetailLoaded) {
      return _SectionContentPlaceholder(
        semanticLabel: '${l10n.detail} ${l10n.loading}',
        lineWidths: const [.94, .78, .88, .72],
        blockCount: 3,
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionTitle(l10n.description),
        Text(issue.description),
        const SizedBox(height: 18),
        _SectionTitle(l10n.acceptanceCriteria),
        for (final criteria in issue.acceptanceCriteria)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TrackStateIcon(
                  TrackStateIconGlyph.subtask,
                  size: 16,
                  color: colors.secondary,
                  semanticLabel: criteria,
                ),
                const SizedBox(width: 8),
                Expanded(child: Text(criteria)),
              ],
            ),
          ),
        const SizedBox(height: 18),
        _SectionTitle(l10n.details),
        _DetailGrid(issue: issue),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final issue = widget.issue;
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final hasBlockedWriteAccess = widget.viewModel.hasBlockedWriteAccess;
    final canUseWriteActions =
        !hasBlockedWriteAccess && !widget.viewModel.isSaving;
    final actions = [
      if (widget.viewModel.issueDetailReturnSection case final returnSection?)
        _IssueDetailActionButton(
          label: '${l10n.back} ${_trackerSectionLabel(l10n, returnSection)}',
          onPressed: widget.viewModel.returnFromIssueDetail,
        ),
      _PrimaryButton(
        label: l10n.transition,
        icon: TrackStateIconGlyph.gitBranch,
        onPressed: canUseWriteActions
            ? () => _openEditDialog(workflowOnly: true)
            : null,
      ),
      _IssueDetailActionButton(
        label: l10n.createChildIssue,
        onPressed: widget.viewModel.isSaving ? null : widget.onCreateChildIssue,
      ),
      _IssueDetailActionButton(
        label: l10n.edit,
        onPressed: canUseWriteActions
            ? () => _openEditDialog(workflowOnly: false)
            : null,
      ),
    ];
    return _SurfaceCard(
      semanticLabel: '${l10n.issueDetail} ${issue.key}',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _IssueTypeGlyph(issue.issueType),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  issue.key,
                  style: TextStyle(
                    fontFamily: 'JetBrains Mono',
                    color: colors.muted,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Flexible(
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  alignment: WrapAlignment.end,
                  children: actions,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            issue.summary,
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 12),
          if (hasBlockedWriteAccess) ...[
            _AccessCallout(
              semanticLabel: l10n.issueDetail,
              title: _repositoryAccessTitle(l10n, widget.viewModel),
              message: _repositoryAccessMessage(l10n, widget.viewModel),
              primaryActionLabel: l10n.openSettings,
              onPrimaryAction: () =>
                  widget.viewModel.selectSection(TrackerSection.settings),
            ),
            const SizedBox(height: 12),
          ],
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _StatusBadge(status: issue.status),
              _PriorityBadge(priority: issue.priority),
              for (final label in issue.labels) _Chip(label: label),
            ],
          ),
          const SizedBox(height: 18),
          _IssueDetailTabs(
            selectedIndex: _selectedCollaborationTab,
            tabs: [l10n.detail, l10n.comments, l10n.attachments, l10n.history],
            failedTabIndexes: {
              if (widget.viewModel.hasIssueDeferredError(
                issue.key,
                IssueDeferredSection.detail,
              ))
                0,
              if (widget.viewModel.hasIssueDeferredError(
                issue.key,
                IssueDeferredSection.comments,
              ))
                1,
              if (widget.viewModel.hasIssueDeferredError(
                issue.key,
                IssueDeferredSection.attachments,
              ))
                2,
              if (widget.viewModel.hasIssueDeferredError(
                issue.key,
                IssueDeferredSection.history,
              ))
                3,
            },
            onSelected: (index) {
              setState(() {
                _selectedCollaborationTab = index;
              });
              switch (index) {
                case 0:
                  widget.viewModel.ensureIssueDetailLoaded(issue);
                case 1:
                  widget.viewModel.ensureIssueCommentsLoaded(issue);
                case 2:
                  widget.viewModel.ensureIssueAttachmentsLoaded(issue);
                case 3:
                  widget.viewModel.ensureIssueHistoryLoaded(issue);
              }
            },
          ),
          const SizedBox(height: 16),
          if (_selectedCollaborationTab == 0)
            _detailTabContent(context, issue: issue, l10n: l10n, colors: colors)
          else if (_selectedCollaborationTab == 1)
            _CommentsTab(
              issue: issue,
              viewModel: widget.viewModel,
              controller: _commentController,
              isSaving: widget.viewModel.isSaving,
              isLoading: widget.viewModel.isIssueCommentsLoading(issue.key),
              errorText: widget.viewModel.issueDeferredError(
                issue.key,
                IssueDeferredSection.comments,
              ),
              writeBlocked: hasBlockedWriteAccess,
              onSave: canUseWriteActions ? _saveComment : null,
              onRetry: () => widget.viewModel.ensureIssueCommentsLoaded(issue),
            )
          else if (_selectedCollaborationTab == 2)
            _AttachmentsTab(
              issue: issue,
              viewModel: widget.viewModel,
              onDownload: widget.viewModel.downloadIssueAttachment,
              selectedAttachment: _selectedAttachment,
              uploadNotice: _attachmentUploadNotice,
              isSaving: widget.viewModel.isSaving,
              isLoading: widget.viewModel.isIssueAttachmentsLoading(issue.key),
              errorText: widget.viewModel.issueDeferredError(
                issue.key,
                IssueDeferredSection.attachments,
              ),
              onChooseAttachment: _chooseAttachment,
              onClearSelection: () {
                setState(() {
                  _selectedAttachment = null;
                  _attachmentUploadNotice = null;
                });
              },
              onUpload: _uploadAttachment,
              onRetry: () =>
                  widget.viewModel.ensureIssueAttachmentsLoaded(issue),
            )
          else
            _HistoryTab(
              entries: widget.viewModel.issueHistoryFor(issue.key),
              isLoading: widget.viewModel.isIssueHistoryLoading(issue.key),
              errorText: widget.viewModel.issueDeferredError(
                issue.key,
                IssueDeferredSection.history,
              ),
              onRetry: () => widget.viewModel.ensureIssueHistoryLoaded(issue),
            ),
        ],
      ),
    );
  }
}

class _IssueDetailActionButton extends StatelessWidget {
  const _IssueDetailActionButton({
    required this.label,
    required this.onPressed,
    this.emphasized = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final child = ExcludeSemantics(child: Text(label));
    final button = emphasized
        ? FilledButton(
            onPressed: onPressed,
            style: FilledButton.styleFrom(
              backgroundColor: colors.primary,
              foregroundColor: colors.page,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            child: child,
          )
        : OutlinedButton(
            onPressed: onPressed,
            style: OutlinedButton.styleFrom(
              foregroundColor: colors.text,
              side: BorderSide(color: colors.border),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            child: child,
          );
    return Semantics(button: true, label: label, child: button);
  }
}

class _IssueList extends StatelessWidget {
  const _IssueList({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final searchResults = viewModel.searchResults;
    final bootstrapResults = viewModel.shouldUseBootstrapSearchFallback
        ? viewModel.issues.take(6).toList(growable: false)
        : const <TrackStateIssue>[];
    final visibleResults = searchResults.isEmpty
        ? bootstrapResults
        : searchResults;
    final showSearchBootstrapLoading = viewModel.isInitialSearchLoading;
    return _SurfaceCard(
      semanticLabel: l10n.jqlSearch,
      explicitChildNodes: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          FocusTraversalOrder(
            order: const NumericFocusOrder(1),
            child: Shortcuts(
              shortcuts: const <ShortcutActivator, Intent>{
                SingleActivator(LogicalKeyboardKey.tab): NextFocusIntent(),
                SingleActivator(LogicalKeyboardKey.tab, shift: true):
                    PreviousFocusIntent(),
              },
              child: TextField(
                controller: TextEditingController(text: viewModel.jql),
                onSubmitted: viewModel.updateQuery,
                decoration: InputDecoration(
                  labelText: l10n.searchIssues,
                  hintText: l10n.jqlPlaceholder,
                ),
              ),
            ),
          ),
          const SizedBox(height: 12),
          if (showSearchBootstrapLoading) ...[
            _SectionLoadingBanner(
              semanticLabel: '${l10n.jqlSearch} ${l10n.loading}',
              label: l10n.loading,
            ),
            const SizedBox(height: 12),
          ],
          if (visibleResults.isEmpty)
            Text(l10n.noResults)
          else ...[
            if (!showSearchBootstrapLoading &&
                searchResults.length < viewModel.totalSearchResults)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  l10n.showingResults(
                    searchResults.length,
                    viewModel.totalSearchResults,
                  ),
                  style: Theme.of(
                    context,
                  ).textTheme.labelMedium?.copyWith(color: colors.muted),
                ),
              ),
            for (var index = 0; index < visibleResults.length; index += 1)
              FocusTraversalOrder(
                order: NumericFocusOrder(index + 2.0),
                child: _IssueListRow(
                  issue: visibleResults[index],
                  onSelect: viewModel.selectIssue,
                  trailingAction: showSearchBootstrapLoading
                      ? _LoadingPill(
                          semanticLabel:
                              'Open ${visibleResults[index].key} ${visibleResults[index].summary} ${l10n.loading}',
                          label: l10n.loading,
                        )
                      : null,
                ),
              ),
            if (viewModel.hasMoreSearchResults)
              FocusTraversalOrder(
                order: NumericFocusOrder(searchResults.length + 2.0),
                child: Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Semantics(
                    container: true,
                    button: true,
                    label: l10n.loadMoreIssues,
                    child: OutlinedButton(
                      onPressed: viewModel.isLoadingMoreSearchResults
                          ? null
                          : viewModel.loadMoreSearchResults,
                      style: _searchLoadMoreButtonStyle(colors),
                      child: ExcludeSemantics(child: Text(l10n.loadMore)),
                    ),
                  ),
                ),
              ),
          ],
        ],
      ),
    );
  }
}

ButtonStyle _searchLoadMoreButtonStyle(TrackStateColors colors) {
  return OutlinedButton.styleFrom(
    foregroundColor: colors.primary,
    backgroundColor: colors.surface,
    side: BorderSide(color: colors.primary),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
  ).copyWith(
    foregroundColor: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.disabled)) {
        return colors.muted;
      }
      return colors.primary;
    }),
    side: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.disabled)) {
        return BorderSide(color: colors.border);
      }
      return BorderSide(color: colors.primary);
    }),
    overlayColor: WidgetStateProperty.resolveWith((states) {
      if (states.contains(WidgetState.pressed)) {
        return colors.primarySoft;
      }
      if (states.contains(WidgetState.hovered)) {
        return colors.primarySoft.withValues(alpha: .72);
      }
      if (states.contains(WidgetState.focused)) {
        return colors.primarySoft.withValues(alpha: .84);
      }
      return Colors.transparent;
    }),
  );
}

class _ActiveEpics extends StatelessWidget {
  const _ActiveEpics({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return _SurfaceCard(
      semanticLabel: l10n.activeEpics,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle(l10n.activeEpics),
          for (final epic in viewModel.epics)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: _EpicProgress(issue: epic),
            ),
        ],
      ),
    );
  }
}

class _RecentActivity extends StatelessWidget {
  const _RecentActivity({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return _SurfaceCard(
      semanticLabel: l10n.recentActivity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle(l10n.recentActivity),
          for (final issue in viewModel.issues.take(5))
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                children: [
                  _IssueTypeGlyph(issue.issueType),
                  const SizedBox(width: 10),
                  Expanded(child: Text('${issue.key} · ${issue.summary}')),
                  Text(
                    issue.updatedLabel,
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _BoardColumn extends StatelessWidget {
  const _BoardColumn({
    required this.title,
    required this.targetStatus,
    required this.issues,
    required this.onSelect,
    required this.onMove,
  });

  final String title;
  final IssueStatus targetStatus;
  final List<TrackStateIssue> issues;
  final ValueChanged<TrackStateIssue> onSelect;
  final void Function(TrackStateIssue issue, IssueStatus status) onMove;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return DragTarget<TrackStateIssue>(
      onWillAcceptWithDetails: (details) => details.data.status != targetStatus,
      onAcceptWithDetails: (details) => onMove(details.data, targetStatus),
      builder: (context, candidateData, rejectedData) {
        final isHovering = candidateData.isNotEmpty;
        return Semantics(
          label: '$title column',
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isHovering
                  ? colors.primarySoft.withValues(alpha: .72)
                  : colors.surfaceAlt.withValues(alpha: .62),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isHovering ? colors.primary : colors.border,
                width: isHovering ? 1.5 : 1,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(title, style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(width: 8),
                    _TinyCount('${issues.length}'),
                  ],
                ),
                const SizedBox(height: 12),
                AnimatedSize(
                  duration: const Duration(milliseconds: 220),
                  alignment: Alignment.topCenter,
                  child: Column(
                    children: [
                      for (final issue in issues)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: _IssueCard(
                            issue: issue,
                            onTap: () => onSelect(issue),
                          ),
                        ),
                      if (issues.isEmpty)
                        Container(
                          height: 96,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: colors.border),
                          ),
                          child: Text(
                            'Drop issue here',
                            style: TextStyle(color: colors.muted),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _IssueCard extends StatelessWidget {
  const _IssueCard({required this.issue, required this.onTap});

  final TrackStateIssue issue;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final card = Semantics(
      button: true,
      label: 'Open ${issue.key} ${issue.summary}',
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: ExcludeSemantics(
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: colors.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: colors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _IssueTypeGlyph(issue.issueType),
                    const SizedBox(width: 8),
                    Text(
                      issue.key,
                      style: TextStyle(
                        fontFamily: 'JetBrains Mono',
                        fontSize: 12,
                        color: colors.muted,
                      ),
                    ),
                    const Spacer(),
                    _Avatar(name: issue.assignee),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  issue.summary,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelLarge,
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    _Chip(label: issue.issueType.label),
                    _PriorityBadge(priority: issue.priority),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
    return Draggable<TrackStateIssue>(
      data: issue,
      feedback: Material(
        color: Colors.transparent,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 260),
          child: Opacity(opacity: .92, child: card),
        ),
      ),
      childWhenDragging: Opacity(opacity: .35, child: card),
      child: card,
    );
  }
}

class _IssueListRow extends StatelessWidget {
  const _IssueListRow({
    required this.issue,
    required this.onSelect,
    this.trailingAction,
  });

  final TrackStateIssue issue;
  final ValueChanged<TrackStateIssue> onSelect;
  final Widget? trailingAction;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      container: true,
      button: true,
      label: 'Open ${issue.key} ${issue.summary}',
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: colors.border)),
        ),
        child: Row(
          children: [
            Expanded(
              child: Stack(
                children: [
                  ExcludeSemantics(
                    child: Row(
                      children: [
                        _IssueTypeGlyph(issue.issueType),
                        const SizedBox(width: 10),
                        SizedBox(
                          width: 86,
                          child: Text(
                            issue.key,
                            style: TextStyle(
                              fontFamily: 'JetBrains Mono',
                              color: colors.muted,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(child: Text(issue.summary)),
                        _StatusBadge(status: issue.status),
                        const SizedBox(width: 8),
                        _Avatar(name: issue.assignee),
                      ],
                    ),
                  ),
                  Positioned.fill(
                    child: TextButton(
                      onPressed: () => onSelect(issue),
                      style: TextButton.styleFrom(
                        foregroundColor: colors.text,
                        backgroundColor: Colors.transparent,
                        overlayColor: Colors.transparent,
                        shadowColor: Colors.transparent,
                        surfaceTintColor: Colors.transparent,
                        padding: EdgeInsets.zero,
                        alignment: Alignment.centerLeft,
                        shape: const RoundedRectangleBorder(),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      child: const SizedBox.expand(),
                    ),
                  ),
                ],
              ),
            ),
            if (trailingAction != null) ...[
              const SizedBox(width: 8),
              trailingAction!,
            ],
          ],
        ),
      ),
    );
  }
}

class _TreeIssueRow extends StatelessWidget {
  const _TreeIssueRow({
    required this.issue,
    required this.depth,
    required this.onSelect,
    required this.onCreateChild,
  });

  final TrackStateIssue issue;
  final int depth;
  final ValueChanged<TrackStateIssue> onSelect;
  final VoidCallback onCreateChild;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(left: depth * 28.0, bottom: 8),
      child: _IssueListRow(
        issue: issue,
        onSelect: onSelect,
        trailingAction: _CompactActionIconButton(
          label: 'Create child issue for ${issue.key}',
          glyph: TrackStateIconGlyph.plus,
          onPressed: onCreateChild,
        ),
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
    required this.delta,
    required this.tone,
    this.showValuePlaceholder = false,
    this.showDeltaPlaceholder = false,
  });

  final String label;
  final String value;
  final String delta;
  final MetricTone tone;
  final bool showValuePlaceholder;
  final bool showDeltaPlaceholder;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final toneColor = switch (tone) {
      MetricTone.primary => colors.primary,
      MetricTone.secondary => colors.secondary,
      MetricTone.accent => colors.accent,
    };
    return _SurfaceCard(
      semanticLabel: showValuePlaceholder ? '$label loading' : '$label $value',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelLarge),
          if (showValuePlaceholder)
            const _SkeletonBar(widthFactor: .42, height: 34)
          else
            Text(value, style: Theme.of(context).textTheme.headlineLarge),
          if (showDeltaPlaceholder)
            const _SkeletonBar(widthFactor: .34)
          else
            Text(
              delta,
              style: TextStyle(color: toneColor, fontWeight: FontWeight.w700),
            ),
        ],
      ),
    );
  }
}

enum MetricTone { primary, secondary, accent }

class _LoadingPill extends StatelessWidget {
  const _LoadingPill({required this.semanticLabel, required this.label});

  final String semanticLabel;
  final String label;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      container: true,
      label: semanticLabel,
      child: ExcludeSemantics(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: colors.surfaceAlt,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: colors.border),
          ),
          child: Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.labelSmall?.copyWith(color: colors.muted),
          ),
        ),
      ),
    );
  }
}

class _SectionLoadingBanner extends StatelessWidget {
  const _SectionLoadingBanner({
    required this.semanticLabel,
    required this.label,
  });

  final String semanticLabel;
  final String label;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      container: true,
      label: semanticLabel,
      child: ExcludeSemantics(
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: colors.surfaceAlt,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: colors.border),
          ),
          child: Row(
            children: [
              Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: colors.primarySoft,
                  shape: BoxShape.circle,
                  border: Border.all(color: colors.primary),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  label,
                  style: Theme.of(
                    context,
                  ).textTheme.labelMedium?.copyWith(color: colors.muted),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionContentPlaceholder extends StatelessWidget {
  const _SectionContentPlaceholder({
    required this.semanticLabel,
    this.lineWidths = const [.94, .82, .68],
    this.blockCount = 0,
  });

  final String semanticLabel;
  final List<double> lineWidths;
  final int blockCount;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    return Semantics(
      container: true,
      label: semanticLabel,
      child: ExcludeSemantics(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _SectionLoadingBanner(
              semanticLabel: semanticLabel,
              label: l10n.loading,
            ),
            const SizedBox(height: 12),
            for (final width in lineWidths) ...[
              _SkeletonBar(widthFactor: width),
              const SizedBox(height: 10),
            ],
            for (var index = 0; index < blockCount; index += 1) ...[
              Container(
                width: double.infinity,
                height: 56,
                decoration: BoxDecoration(
                  color: colors.surfaceAlt,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: colors.border),
                ),
              ),
              if (index != blockCount - 1) const SizedBox(height: 10),
            ],
          ],
        ),
      ),
    );
  }
}

class _SkeletonBar extends StatelessWidget {
  const _SkeletonBar({required this.widthFactor, this.height = 12});

  final double widthFactor;
  final double height;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return FractionallySizedBox(
      widthFactor: widthFactor,
      alignment: Alignment.centerLeft,
      child: Container(
        height: height,
        decoration: BoxDecoration(
          color: colors.surfaceAlt,
          borderRadius: BorderRadius.circular(height / 2),
          border: Border.all(color: colors.border),
        ),
      ),
    );
  }
}

class _SettingsProviderButton extends StatelessWidget {
  const _SettingsProviderButton({
    required this.label,
    required this.selected,
    required this.onPressed,
    this.tone = _SettingsProviderButtonTone.defaultTone,
  });

  final String label;
  final bool selected;
  final VoidCallback onPressed;
  final _SettingsProviderButtonTone tone;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final style = selected
        ? _selectedStyle(context, colors)
        : OutlinedButton.styleFrom(
            foregroundColor: colors.text,
            alignment: Alignment.centerLeft,
            minimumSize: const Size.fromHeight(52),
            side: BorderSide(color: colors.border),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          );

    return Semantics(
      container: true,
      button: true,
      selected: selected,
      label: label,
      excludeSemantics: true,
      child: SizedBox(
        width: double.infinity,
        child: selected
            ? FilledButton(
                onPressed: onPressed,
                style: style,
                child: Text(label),
              )
            : OutlinedButton(
                onPressed: onPressed,
                style: style,
                child: Text(label),
              ),
      ),
    );
  }

  ButtonStyle _selectedStyle(BuildContext context, TrackStateColors colors) {
    if (tone == _SettingsProviderButtonTone.connected) {
      return _connectedStyle(context, colors);
    }
    final hoveredBackground = Color.lerp(colors.primary, colors.text, 0.04)!;
    final pressedBackground = Color.lerp(colors.primary, colors.text, 0.08)!;

    return FilledButton.styleFrom(
      foregroundColor: colors.page,
      alignment: Alignment.centerLeft,
      minimumSize: const Size.fromHeight(52),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    ).copyWith(
      backgroundColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.pressed)) {
          return pressedBackground;
        }
        if (states.contains(WidgetState.hovered) ||
            states.contains(WidgetState.focused)) {
          return hoveredBackground;
        }
        return colors.primary;
      }),
      overlayColor: const WidgetStatePropertyAll(Colors.transparent),
    );
  }

  ButtonStyle _connectedStyle(BuildContext context, TrackStateColors colors) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final foreground = isDark ? colors.page : colors.text;

    return FilledButton.styleFrom(
      backgroundColor: colors.success,
      foregroundColor: foreground,
      alignment: Alignment.centerLeft,
      minimumSize: const Size.fromHeight(52),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      overlayColor: Colors.transparent,
    );
  }
}

enum _SettingsProviderButtonTone { defaultTone, connected }

class _HostedProviderConfiguration extends StatefulWidget {
  const _HostedProviderConfiguration({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  State<_HostedProviderConfiguration> createState() =>
      _HostedProviderConfigurationState();
}

class _HostedProviderConfigurationState
    extends State<_HostedProviderConfiguration> {
  late final TextEditingController _tokenController;
  bool _rememberToken = true;

  @override
  void initState() {
    super.initState();
    _tokenController = TextEditingController();
  }

  @override
  void dispose() {
    _tokenController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final viewModel = widget.viewModel;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _AccessCallout(
          semanticLabel: l10n.manageGitHubAccess,
          title: _repositoryAccessTitle(l10n, viewModel),
          message:
              '${_repositoryAccessMessage(l10n, viewModel)} '
              '${l10n.repositoryAccessSettingsHint}',
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _tokenController,
          obscureText: true,
          decoration: InputDecoration(
            labelText: l10n.fineGrainedToken,
            helperText: l10n.fineGrainedTokenHelper,
          ),
        ),
        const SizedBox(height: 8),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          value: _rememberToken,
          title: Text(l10n.rememberOnThisBrowser),
          subtitle: Text(l10n.rememberOnThisBrowserHelp),
          onChanged: viewModel.isSaving
              ? null
              : (value) =>
                    setState(() => _rememberToken = value ?? _rememberToken),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            Semantics(
              button: true,
              label: l10n.connectToken,
              child: FilledButton(
                onPressed: viewModel.isSaving
                    ? null
                    : () => viewModel.connectGitHub(
                        _tokenController.text,
                        remember: _rememberToken,
                      ),
                child: Text(l10n.connectToken),
              ),
            ),
            if (viewModel.isGitHubAppAuthAvailable)
              Semantics(
                button: true,
                label: l10n.continueWithGitHubApp,
                child: OutlinedButton(
                  onPressed: viewModel.isSaving
                      ? null
                      : viewModel.startGitHubAppLogin,
                  child: Text(l10n.continueWithGitHubApp),
                ),
              ),
          ],
        ),
        if (viewModel.connectedUser != null) ...[
          const SizedBox(height: 12),
          Text(
            l10n.githubConnected(
              viewModel.connectedUser!.login,
              viewModel.project!.repository,
            ),
          ),
        ],
      ],
    );
  }
}

class _LocalGitConfiguration extends StatelessWidget {
  const _LocalGitConfiguration({
    required this.repositoryPathController,
    required this.writeBranchController,
    required this.repositoryPathFocusNode,
    required this.writeBranchFocusNode,
  });

  final TextEditingController repositoryPathController;
  final TextEditingController writeBranchController;
  final FocusNode repositoryPathFocusNode;
  final FocusNode writeBranchFocusNode;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      children: [
        _SettingsTextField(
          label: l10n.repositoryPath,
          controller: repositoryPathController,
          focusNode: repositoryPathFocusNode,
        ),
        const SizedBox(height: 12),
        _SettingsTextField(
          label: l10n.writeBranch,
          controller: writeBranchController,
          focusNode: writeBranchFocusNode,
        ),
      ],
    );
  }
}

class _SettingsTextField extends StatelessWidget {
  const _SettingsTextField({
    required this.label,
    required this.controller,
    this.focusNode,
  });

  final String label;
  final TextEditingController controller;
  final FocusNode? focusNode;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      focusNode: focusNode,
      decoration: InputDecoration(labelText: label),
    );
  }
}

class _SurfaceCard extends StatelessWidget {
  const _SurfaceCard({
    required this.child,
    required this.semanticLabel,
    this.explicitChildNodes = false,
  });

  final Widget child;
  final String semanticLabel;
  final bool explicitChildNodes;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      label: semanticLabel,
      container: true,
      explicitChildNodes: explicitChildNodes,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: colors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: colors.border),
          boxShadow: [
            BoxShadow(
              color: colors.shadow,
              blurRadius: 16,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: child,
      ),
    );
  }
}

class _ScreenHeading extends StatelessWidget {
  const _ScreenHeading({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.headlineLarge),
          const SizedBox(height: 4),
          Text(subtitle, style: TextStyle(color: colors.muted)),
        ],
      ),
    );
  }
}

class _PrimaryButton extends StatelessWidget {
  const _PrimaryButton({
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  final String label;
  final TrackStateIconGlyph icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final onPrimary = Theme.of(context).colorScheme.onPrimary;
    return Semantics(
      button: true,
      label: label,
      child: FilledButton.icon(
        onPressed: onPressed,
        style: FilledButton.styleFrom(
          backgroundColor: colors.primary,
          foregroundColor: onPrimary,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        ),
        icon: TrackStateIcon(icon, size: 16, color: onPrimary),
        label: Text(label, style: TextStyle(color: onPrimary)),
      ),
    );
  }
}

class _IconButtonSurface extends StatelessWidget {
  const _IconButtonSurface({
    required this.label,
    required this.glyph,
    required this.onPressed,
  });

  final String label;
  final TrackStateIconGlyph glyph;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final enabled = onPressed != null;
    return Semantics(
      button: true,
      enabled: enabled,
      label: label,
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onPressed,
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
            color: colors.surface,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: colors.border),
          ),
          foregroundDecoration: enabled
              ? null
              : BoxDecoration(
                  color: colors.page.withValues(alpha: 0.45),
                  borderRadius: BorderRadius.circular(10),
                ),
          child: TrackStateIcon(
            glyph,
            color: enabled ? colors.text : colors.muted,
            size: 18,
          ),
        ),
      ),
    );
  }
}

class _CompactActionIconButton extends StatelessWidget {
  const _CompactActionIconButton({
    required this.label,
    required this.glyph,
    required this.onPressed,
  });

  final String label;
  final TrackStateIconGlyph glyph;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      button: true,
      label: label,
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onPressed,
        child: Padding(
          padding: const EdgeInsets.all(6),
          child: TrackStateIcon(
            glyph,
            size: 16,
            color: onPressed == null ? colors.muted : colors.primary,
          ),
        ),
      ),
    );
  }
}

class _DropdownCreateField extends StatelessWidget {
  const _DropdownCreateField({
    required this.label,
    required this.items,
    required this.onChanged,
    this.value,
    this.enabled = true,
    this.hintText,
    this.helperText,
    this.errorText,
  });

  final String label;
  final String? value;
  final bool enabled;
  final String? hintText;
  final String? helperText;
  final String? errorText;
  final List<DropdownMenuItem<String>> items;
  final ValueChanged<String?>? onChanged;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      child: DropdownButtonFormField<String>(
        key: ValueKey('$label-${value ?? 'empty'}'),
        initialValue: items.any((item) => item.value == value) ? value : null,
        isExpanded: true,
        items: items,
        onChanged: enabled ? onChanged : null,
        decoration: InputDecoration(
          labelText: label,
          hintText: hintText,
          helperText: helperText,
          errorText: errorText,
        ),
      ),
    );
  }
}

class _ReadOnlyCreateField extends StatelessWidget {
  const _ReadOnlyCreateField({
    required this.label,
    required this.value,
    this.helperText,
  });

  final String label;
  final String value;
  final String? helperText;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      readOnly: true,
      child: InputDecorator(
        decoration: InputDecoration(labelText: label, helperText: helperText),
        child: Text(value),
      ),
    );
  }
}

class _SelectableChipField extends StatelessWidget {
  const _SelectableChipField({
    required this.label,
    required this.options,
    required this.selectedValues,
    required this.onToggle,
    this.enabled = true,
  });

  final String label;
  final List<TrackStateConfigEntry> options;
  final List<String> selectedValues;
  final ValueChanged<String> onToggle;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      container: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final option in options)
                FilterChip(
                  label: Text(option.label()),
                  selected: selectedValues.any(
                    (value) =>
                        _canonicalConfigId(value) ==
                        _canonicalConfigId(option.id),
                  ),
                  onSelected: enabled ? (_) => onToggle(option.id) : null,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _LabelTokenField extends StatelessWidget {
  const _LabelTokenField({
    required this.label,
    required this.controller,
    required this.labels,
    required this.enabled,
    required this.helperText,
    required this.onChanged,
    required this.onSubmitted,
    required this.onRemove,
  });

  final String label;
  final TextEditingController controller;
  final List<String> labels;
  final bool enabled;
  final String helperText;
  final ValueChanged<String> onChanged;
  final ValueChanged<String> onSubmitted;
  final ValueChanged<String> onRemove;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Semantics(
          label: label,
          textField: true,
          child: TextField(
            controller: controller,
            enabled: enabled,
            onChanged: onChanged,
            onSubmitted: onSubmitted,
            decoration: InputDecoration(
              labelText: label,
              helperText: helperText,
            ),
          ),
        ),
        if (labels.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final labelValue in labels)
                InputChip(
                  label: Text(labelValue),
                  onDeleted: enabled ? () => onRemove(labelValue) : null,
                ),
            ],
          ),
        ],
      ],
    );
  }
}

class _CreateIssueDialog extends StatefulWidget {
  const _CreateIssueDialog({
    required this.viewModel,
    required this.onDismiss,
    required this.prefill,
  });

  final TrackerViewModel viewModel;
  final VoidCallback onDismiss;
  final _CreateIssuePrefill prefill;

  @override
  State<_CreateIssueDialog> createState() => _CreateIssueDialogState();
}

class _CreateIssueOverlay extends StatelessWidget {
  const _CreateIssueOverlay({required this.child, this.compact = false});

  final Widget child;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.black.withValues(alpha: compact ? 0.18 : 0.12),
      child: child,
    );
  }
}

class _CreateIssueDialogState extends State<_CreateIssueDialog> {
  late final TextEditingController _summaryController;
  late final TextEditingController _descriptionController;
  late final TextEditingController _assigneeController;
  late final TextEditingController _labelEntryController;
  final Map<String, TextEditingController> _customFieldControllers = {};
  final List<String> _labels = <String>[];
  late String _selectedIssueTypeId;
  late String _selectedPriorityId;
  String? _selectedEpicKey;
  String? _selectedParentKey;
  bool _didAttemptSubmit = false;

  @override
  void initState() {
    super.initState();
    _summaryController = TextEditingController();
    _descriptionController = TextEditingController();
    _assigneeController = TextEditingController(text: _defaultAssignee());
    _labelEntryController = TextEditingController();
    final project = widget.viewModel.project;
    final defaultIssueType = project == null
        ? IssueType.story.id
        : (_resolveConfigEntry(
                    widget.prefill.issueTypeId,
                    _supportedCreateIssueTypes(project),
                  ) ??
                  _defaultCreateIssueType(project) ??
                  const TrackStateConfigEntry(id: 'story', name: 'Story'))
              .id;
    final defaultPriority = project == null
        ? IssuePriority.medium.id
        : (_defaultCreatePriority(project) ??
                  project.priorityDefinitions.firstOrNull ??
                  const TrackStateConfigEntry(id: 'medium', name: 'Medium'))
              .id;
    _selectedIssueTypeId = defaultIssueType;
    _selectedPriorityId = defaultPriority;
    _selectedEpicKey = widget.prefill.epicKey;
    _selectedParentKey = widget.prefill.parentKey;
    _syncHierarchyToIssueType();
  }

  @override
  void dispose() {
    _summaryController.dispose();
    _descriptionController.dispose();
    _assigneeController.dispose();
    _labelEntryController.dispose();
    for (final controller in _customFieldControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  bool get _isEpicType => _canonicalConfigId(_selectedIssueTypeId) == 'epic';

  bool get _isSubtaskType =>
      _canonicalConfigId(_selectedIssueTypeId) == 'subtask';

  String _defaultAssignee() {
    final connectedUser = widget.viewModel.connectedUser;
    if (connectedUser?.login case final login? when login.isNotEmpty) {
      return login;
    }
    final identity = widget.viewModel.providerSession?.resolvedUserIdentity
        .trim();
    if (identity != null && identity.isNotEmpty) {
      return identity;
    }
    return '';
  }

  TrackStateIssue? _issueByKey(String? key) =>
      widget.viewModel.issues.where((issue) => issue.key == key).firstOrNull;

  void _syncHierarchyToIssueType() {
    if (_isEpicType) {
      _selectedEpicKey = null;
      _selectedParentKey = null;
      return;
    }
    if (_isSubtaskType) {
      _selectedEpicKey = null;
      final parent = _issueByKey(_selectedParentKey);
      if (parent?.isEpic ?? false) {
        _selectedParentKey = null;
      }
      return;
    }
    _selectedParentKey = null;
  }

  String? _derivedEpicKey() {
    if (!_isSubtaskType) {
      return null;
    }
    final parentIssue = _issueByKey(_selectedParentKey);
    return parentIssue?.epicKey;
  }

  void _applyIssueType(String? issueTypeId) {
    if (issueTypeId == null || issueTypeId == _selectedIssueTypeId) {
      return;
    }
    setState(() {
      _selectedIssueTypeId = issueTypeId;
      _syncHierarchyToIssueType();
      if (!_isEpicType && !_isSubtaskType && _selectedEpicKey == null) {
        _selectedEpicKey = widget.prefill.epicKey;
      }
    });
  }

  void _commitLabels({bool commitRemainder = false}) {
    final currentValue = _labelEntryController.text;
    if (currentValue.trim().isEmpty) {
      return;
    }
    final fragments = currentValue.split(',');
    final remainder = commitRemainder ? '' : fragments.removeLast().trim();
    final newLabels = [
      for (final fragment in fragments)
        if (fragment.trim().isNotEmpty) fragment.trim(),
      if (commitRemainder && remainder.isNotEmpty) remainder,
    ];
    if (newLabels.isEmpty && remainder == _labelEntryController.text) {
      return;
    }
    setState(() {
      for (final label in newLabels) {
        if (!_labels.contains(label)) {
          _labels.add(label);
        }
      }
      _labelEntryController.value = TextEditingValue(
        text: commitRemainder ? '' : remainder,
        selection: TextSelection.collapsed(
          offset: commitRemainder ? 0 : remainder.length,
        ),
      );
    });
  }

  Future<void> _submitCreateIssue() async {
    setState(() {
      _didAttemptSubmit = true;
    });
    _commitLabels(commitRemainder: true);
    final customFields = <String, String>{};
    for (final field in _createIssueFieldDefinitions(
      widget.viewModel.project,
    )) {
      final value = _customFieldControllers[field.id]?.text.trim() ?? '';
      if (value.isEmpty) {
        continue;
      }
      customFields[field.id] = value;
    }
    final success = await widget.viewModel.createIssue(
      summary: _summaryController.text,
      description: _descriptionController.text,
      customFields: customFields,
      issueTypeId: _selectedIssueTypeId,
      priorityId: _selectedPriorityId,
      assignee: _assigneeController.text.trim(),
      parentKey: _isSubtaskType ? _selectedParentKey : null,
      epicKey: _isEpicType
          ? null
          : (_isSubtaskType ? _derivedEpicKey() : _selectedEpicKey),
      labels: _labels,
      returnSection: widget.prefill.originSection,
    );
    if (!mounted || !success) {
      return;
    }
    widget.onDismiss();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final project = widget.viewModel.project;
    final summaryLabel = _projectFieldLabel(
      project,
      'summary',
      fallback: 'Summary',
    );
    final issueTypeLabel = _projectFieldLabel(
      project,
      'issueType',
      fallback: l10n.issueType,
    );
    final priorityLabel = _projectFieldLabel(
      project,
      'priority',
      fallback: l10n.priority,
    );
    final assigneeLabel = _projectFieldLabel(
      project,
      'assignee',
      fallback: l10n.assignee,
    );
    final labelsLabel = _projectFieldLabel(
      project,
      'labels',
      fallback: l10n.labels,
    );
    final parentLabel = _projectFieldLabel(
      project,
      'parent',
      fallback: l10n.parent,
    );
    final epicLabel = _projectFieldLabel(project, 'epic', fallback: l10n.epic);
    final createFields = _createIssueFieldDefinitions(project);
    _syncCreateFieldControllers(_customFieldControllers, createFields);
    final issueTypeOptions = project == null
        ? const <TrackStateConfigEntry>[]
        : _supportedCreateIssueTypes(project);
    final priorityOptions =
        project?.priorityDefinitions ?? const <TrackStateConfigEntry>[];
    final epicOptions = _epicOptions(widget.viewModel);
    final parentOptions = _parentOptions(widget.viewModel);
    final defaultStatus = project == null
        ? null
        : _defaultCreateStatus(project);
    final derivedEpic = _issueByKey(_derivedEpicKey());
    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 980;
        final horizontalInset = isCompact ? 16.0 : 24.0;
        final verticalInset = isCompact ? 16.0 : 24.0;
        final availableWidth = math.max(
          0.0,
          constraints.maxWidth - (horizontalInset * 2),
        );
        final availableHeight = math.max(
          0.0,
          constraints.maxHeight - (verticalInset * 2),
        );
        final surfaceWidth = isCompact
            ? availableWidth
            : math.min(620.0, availableWidth);

        return Dialog(
          alignment: isCompact ? Alignment.topCenter : Alignment.centerRight,
          insetPadding: EdgeInsets.symmetric(
            horizontal: horizontalInset,
            vertical: verticalInset,
          ),
          child: SizedBox(
            width: surfaceWidth,
            height: availableHeight,
            child: ListenableBuilder(
              listenable: widget.viewModel,
              builder: (context, _) {
                final canEditFields =
                    !widget.viewModel.hasBlockedWriteAccess &&
                    !widget.viewModel.isSaving;
                final canSubmit =
                    !widget.viewModel.hasBlockedWriteAccess &&
                    !widget.viewModel.isSaving;
                return _SurfaceCard(
                  semanticLabel: l10n.createIssue,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: SingleChildScrollView(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _SectionTitle(l10n.createIssue),
                              const SizedBox(height: 12),
                              if (widget.viewModel.hasBlockedWriteAccess) ...[
                                _AccessCallout(
                                  semanticLabel: l10n.createIssue,
                                  title: _repositoryAccessTitle(
                                    l10n,
                                    widget.viewModel,
                                  ),
                                  message: _repositoryAccessMessage(
                                    l10n,
                                    widget.viewModel,
                                  ),
                                  primaryActionLabel: l10n.openSettings,
                                  onPrimaryAction: () {
                                    widget.onDismiss();
                                    widget.viewModel.selectSection(
                                      TrackerSection.settings,
                                    );
                                  },
                                ),
                                const SizedBox(height: 12),
                              ],
                              _DropdownCreateField(
                                label: issueTypeLabel,
                                value: _selectedIssueTypeId,
                                enabled: canEditFields,
                                items: [
                                  for (final option in issueTypeOptions)
                                    DropdownMenuItem<String>(
                                      value: option.id,
                                      child: Text(
                                        option.label(project?.defaultLocale),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                ],
                                onChanged: _applyIssueType,
                              ),
                              const SizedBox(height: 12),
                              Semantics(
                                label: summaryLabel,
                                textField: true,
                                child: TextField(
                                  controller: _summaryController,
                                  enabled: canEditFields,
                                  decoration: InputDecoration(
                                    labelText: summaryLabel,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              Semantics(
                                label: l10n.description,
                                textField: true,
                                child: TextField(
                                  controller: _descriptionController,
                                  minLines: 3,
                                  maxLines: null,
                                  enabled: canEditFields,
                                  decoration: InputDecoration(
                                    labelText: l10n.description,
                                    alignLabelWithHint: true,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              _DropdownCreateField(
                                label: priorityLabel,
                                value: _selectedPriorityId,
                                enabled: canEditFields,
                                items: [
                                  for (final option in priorityOptions)
                                    DropdownMenuItem<String>(
                                      value: option.id,
                                      child: Text(
                                        option.label(project?.defaultLocale),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                ],
                                onChanged: (value) {
                                  if (value == null) {
                                    return;
                                  }
                                  setState(() {
                                    _selectedPriorityId = value;
                                  });
                                },
                              ),
                              const SizedBox(height: 12),
                              _ReadOnlyCreateField(
                                label: l10n.initialStatus,
                                value:
                                    defaultStatus?.label(
                                      project?.defaultLocale,
                                    ) ??
                                    l10n.toDo,
                              ),
                              if (!_isEpicType && !_isSubtaskType) ...[
                                const SizedBox(height: 12),
                                _DropdownCreateField(
                                  label: epicLabel,
                                  value: _selectedEpicKey,
                                  enabled: canEditFields,
                                  hintText: l10n.optional,
                                  items: [
                                    for (final option in epicOptions)
                                      DropdownMenuItem<String>(
                                        value: option.key,
                                        child: Text(
                                          '${option.key} · ${option.summary}',
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                  ],
                                  onChanged: (value) {
                                    setState(() {
                                      _selectedEpicKey = value;
                                    });
                                  },
                                ),
                              ],
                              if (_isSubtaskType) ...[
                                const SizedBox(height: 12),
                                _DropdownCreateField(
                                  label: parentLabel,
                                  value: _selectedParentKey,
                                  enabled: canEditFields,
                                  hintText: parentOptions.isEmpty
                                      ? l10n.noEligibleParents
                                      : null,
                                  errorText:
                                      _didAttemptSubmit &&
                                          _selectedParentKey == null
                                      ? l10n.subTaskParentRequired
                                      : null,
                                  items: [
                                    for (final option in parentOptions)
                                      DropdownMenuItem<String>(
                                        value: option.key,
                                        child: Text(
                                          '${option.key} · ${option.summary}',
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                  ],
                                  onChanged: parentOptions.isEmpty
                                      ? null
                                      : (value) {
                                          setState(() {
                                            _selectedParentKey = value;
                                          });
                                        },
                                ),
                                const SizedBox(height: 12),
                                _ReadOnlyCreateField(
                                  label: epicLabel,
                                  value: derivedEpic == null
                                      ? l10n.derivedFromParent
                                      : '${derivedEpic.key} · ${derivedEpic.summary}',
                                  helperText: l10n.epicDerivedFromParent,
                                ),
                              ],
                              const SizedBox(height: 12),
                              Semantics(
                                label: assigneeLabel,
                                textField: true,
                                child: TextField(
                                  controller: _assigneeController,
                                  enabled: canEditFields,
                                  decoration: InputDecoration(
                                    labelText: assigneeLabel,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              _LabelTokenField(
                                label: labelsLabel,
                                controller: _labelEntryController,
                                labels: _labels,
                                enabled: canEditFields,
                                helperText: l10n.labelsTokenHelper,
                                onChanged: (_) => _commitLabels(),
                                onSubmitted: (_) =>
                                    _commitLabels(commitRemainder: true),
                                onRemove: (label) {
                                  setState(() {
                                    _labels.remove(label);
                                  });
                                },
                              ),
                              for (final field in createFields) ...[
                                const SizedBox(height: 12),
                                Semantics(
                                  label: _createIssueFieldLabel(project, field),
                                  textField: true,
                                  child: TextField(
                                    key: ValueKey('create-field-${field.id}'),
                                    controller:
                                        _customFieldControllers[field.id],
                                    minLines: field.type == 'markdown' ? 3 : 1,
                                    maxLines: field.type == 'markdown'
                                        ? null
                                        : 1,
                                    enabled: canEditFields,
                                    decoration: InputDecoration(
                                      labelText: _createIssueFieldLabel(
                                        project,
                                        field,
                                      ),
                                      alignLabelWithHint:
                                          field.type == 'markdown',
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _IssueDetailActionButton(
                            label: l10n.save,
                            emphasized: true,
                            onPressed: canSubmit ? _submitCreateIssue : null,
                          ),
                          _IssueDetailActionButton(
                            label: l10n.cancel,
                            onPressed: widget.viewModel.isSaving
                                ? null
                                : widget.onDismiss,
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        );
      },
    );
  }
}

class _IssueEditDialog extends StatefulWidget {
  const _IssueEditDialog({
    required this.issue,
    required this.viewModel,
    required this.workflowOnly,
  });

  final TrackStateIssue issue;
  final TrackerViewModel viewModel;
  final bool workflowOnly;

  @override
  State<_IssueEditDialog> createState() => _IssueEditDialogState();
}

class _IssueEditDialogState extends State<_IssueEditDialog> {
  late final TextEditingController _summaryController;
  late final TextEditingController _descriptionController;
  late final TextEditingController _assigneeController;
  late final TextEditingController _labelEntryController;
  late String _selectedPriorityId;
  late final List<String> _labels;
  late final List<String> _components;
  late final List<String> _fixVersions;
  String? _selectedParentKey;
  String? _selectedEpicKey;
  String? _selectedTransitionStatusId;
  String? _selectedResolutionId;
  List<TrackStateConfigEntry> _transitionOptions = const [];
  bool _loadingTransitions = true;
  bool _didAttemptSubmit = false;

  bool get _isEpicType =>
      _canonicalConfigId(widget.issue.issueTypeId) == 'epic';

  bool get _isSubtaskType =>
      _canonicalConfigId(widget.issue.issueTypeId) == 'subtask';

  @override
  void initState() {
    super.initState();
    _summaryController = TextEditingController(text: widget.issue.summary);
    _descriptionController = TextEditingController(
      text: widget.issue.description,
    );
    _assigneeController = TextEditingController(text: widget.issue.assignee);
    _labelEntryController = TextEditingController();
    _selectedPriorityId = widget.issue.priorityId;
    _labels = [...widget.issue.labels];
    _components = [...widget.issue.components];
    _fixVersions = [...widget.issue.fixVersionIds];
    _selectedParentKey = widget.issue.parentKey;
    _selectedEpicKey = widget.issue.epicKey;
    _loadTransitions();
  }

  @override
  void dispose() {
    _summaryController.dispose();
    _descriptionController.dispose();
    _assigneeController.dispose();
    _labelEntryController.dispose();
    super.dispose();
  }

  Future<void> _loadTransitions() async {
    final transitions = await widget.viewModel.availableWorkflowTransitions(
      widget.issue,
    );
    if (!mounted) {
      return;
    }
    setState(() {
      _transitionOptions = transitions;
      _loadingTransitions = false;
    });
  }

  TrackStateIssue? _issueByKey(String? key) =>
      widget.viewModel.issues.where((issue) => issue.key == key).firstOrNull;

  String? _derivedEpicKey() {
    if (!_isSubtaskType) {
      return null;
    }
    return _issueByKey(_selectedParentKey)?.epicKey;
  }

  List<TrackStateIssue> _availableParentOptions() {
    final currentRoot = _issueRoot(widget.issue.storagePath);
    return [
      for (final issue in widget.viewModel.issues)
        if (!issue.isEpic &&
            !issue.isArchived &&
            issue.key != widget.issue.key &&
            !issue.storagePath.startsWith('$currentRoot/'))
          issue,
    ]..sort((left, right) => left.key.compareTo(right.key));
  }

  void _commitLabels({bool commitRemainder = false}) {
    final currentValue = _labelEntryController.text;
    if (currentValue.trim().isEmpty) {
      return;
    }
    final fragments = currentValue.split(',');
    final remainder = commitRemainder ? '' : fragments.removeLast().trim();
    final newLabels = [
      for (final fragment in fragments)
        if (fragment.trim().isNotEmpty) fragment.trim(),
      if (commitRemainder && remainder.isNotEmpty) remainder,
    ];
    if (newLabels.isEmpty && remainder == _labelEntryController.text) {
      return;
    }
    setState(() {
      for (final label in newLabels) {
        if (!_labels.contains(label)) {
          _labels.add(label);
        }
      }
      _labelEntryController.value = TextEditingValue(
        text: commitRemainder ? '' : remainder,
        selection: TextSelection.collapsed(
          offset: commitRemainder ? 0 : remainder.length,
        ),
      );
    });
  }

  void _toggleConfigSelection(List<String> values, String value) {
    setState(() {
      final index = values.indexWhere(
        (existing) => _canonicalConfigId(existing) == _canonicalConfigId(value),
      );
      if (index == -1) {
        values.add(value);
      } else {
        values.removeAt(index);
      }
    });
  }

  bool _requiresHierarchyConfirmation() {
    if (_selectedParentKey == widget.issue.parentKey &&
        _selectedEpicKey == widget.issue.epicKey) {
      return false;
    }
    final currentRoot = _issueRoot(widget.issue.storagePath);
    return widget.viewModel.issues.any(
      (issue) =>
          issue.key != widget.issue.key &&
          issue.storagePath.startsWith('$currentRoot/'),
    );
  }

  int _descendantCount() {
    final currentRoot = _issueRoot(widget.issue.storagePath);
    return widget.viewModel.issues
        .where(
          (issue) =>
              issue.key != widget.issue.key &&
              issue.storagePath.startsWith('$currentRoot/'),
        )
        .length;
  }

  Future<bool> _confirmHierarchyMove(AppLocalizations l10n) async {
    if (!_requiresHierarchyConfirmation()) {
      return true;
    }
    final descendantCount = _descendantCount();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(l10n.hierarchyChangeConfirmationTitle),
          content: Text(
            l10n.hierarchyChangeConfirmationMessage(descendantCount),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: Text(l10n.cancel),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: Text(l10n.confirmMove),
            ),
          ],
        );
      },
    );
    return confirmed ?? false;
  }

  Future<void> _submit() async {
    setState(() {
      _didAttemptSubmit = true;
    });
    _commitLabels(commitRemainder: true);
    if (_summaryController.text.trim().isEmpty) {
      return;
    }
    if (_isSubtaskType && _selectedParentKey == null) {
      return;
    }
    final l10n = AppLocalizations.of(context)!;
    final project = widget.viewModel.project;
    final resolutionOptions =
        project?.resolutionDefinitions ?? const <TrackStateConfigEntry>[];
    final targetStatusIsDone =
        _selectedTransitionStatusId != null &&
        _canonicalConfigId(_selectedTransitionStatusId) == 'done';
    final resolutionId = !targetStatusIsDone
        ? null
        : (_selectedResolutionId ??
              (resolutionOptions.length == 1
                  ? resolutionOptions.single.id
                  : null));
    if (targetStatusIsDone && resolutionId == null) {
      return;
    }
    final confirmed = await _confirmHierarchyMove(l10n);
    if (!confirmed) {
      return;
    }
    final success = await widget.viewModel.saveIssueEdits(
      widget.issue,
      IssueEditRequest(
        summary: _summaryController.text,
        description: _descriptionController.text,
        priorityId: _selectedPriorityId,
        assignee: _assigneeController.text,
        labels: _labels,
        components: _components,
        fixVersionIds: _fixVersions,
        parentKey: _isSubtaskType ? _selectedParentKey : null,
        epicKey: _isEpicType
            ? null
            : (_isSubtaskType
                  ? _derivedEpicKey()
                  : _emptyToNull(_selectedEpicKey)),
        transitionStatusId: _selectedTransitionStatusId,
        resolutionId: resolutionId,
      ),
    );
    if (!mounted || !success) {
      return;
    }
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final project = widget.viewModel.project;
    final issueTypeLabel =
        project?.issueTypeLabel(
          widget.issue.issueTypeId,
          locale: project.defaultLocale,
        ) ??
        widget.issue.issueType.label;
    final summaryLabel = _projectFieldLabel(
      project,
      'summary',
      fallback: 'Summary',
    );
    final priorityLabel = _projectFieldLabel(
      project,
      'priority',
      fallback: l10n.priority,
    );
    final assigneeLabel = _projectFieldLabel(
      project,
      'assignee',
      fallback: l10n.assignee,
    );
    final labelsLabel = _projectFieldLabel(
      project,
      'labels',
      fallback: l10n.labels,
    );
    final parentLabel = _projectFieldLabel(
      project,
      'parent',
      fallback: l10n.parent,
    );
    final epicLabel = _projectFieldLabel(project, 'epic', fallback: l10n.epic);
    final componentsLabel = _projectFieldLabel(
      project,
      'components',
      fallback: l10n.components,
    );
    final fixVersionsLabel = _projectFieldLabel(
      project,
      'fixVersions',
      fallback: l10n.fixVersions,
    );
    final resolutionLabel = _projectFieldLabel(
      project,
      'resolution',
      fallback: l10n.resolution,
    );
    final parentOptions = _availableParentOptions();
    final epicOptions = _epicOptions(widget.viewModel);
    final priorityOptions =
        project?.priorityDefinitions ?? const <TrackStateConfigEntry>[];
    final componentOptions =
        project?.componentDefinitions ?? const <TrackStateConfigEntry>[];
    final versionOptions =
        project?.versionDefinitions ?? const <TrackStateConfigEntry>[];
    final resolutionOptions =
        project?.resolutionDefinitions ?? const <TrackStateConfigEntry>[];
    final derivedEpic = _issueByKey(_derivedEpicKey());
    final showResolution =
        _selectedTransitionStatusId != null &&
        _canonicalConfigId(_selectedTransitionStatusId) == 'done' &&
        resolutionOptions.length > 1;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 980;
        final horizontalInset = isCompact ? 16.0 : 24.0;
        final verticalInset = isCompact ? 16.0 : 24.0;
        final availableWidth = math.max(
          0.0,
          constraints.maxWidth - (horizontalInset * 2),
        );
        final availableHeight = math.max(
          0.0,
          constraints.maxHeight - (verticalInset * 2),
        );
        final surfaceWidth = isCompact
            ? availableWidth
            : math.min(620.0, availableWidth);

        return Dialog(
          alignment: isCompact ? Alignment.topCenter : Alignment.centerRight,
          insetPadding: EdgeInsets.symmetric(
            horizontal: horizontalInset,
            vertical: verticalInset,
          ),
          child: SizedBox(
            width: surfaceWidth,
            height: availableHeight,
            child: ListenableBuilder(
              listenable: widget.viewModel,
              builder: (context, _) {
                final canEditFields =
                    !widget.viewModel.hasBlockedWriteAccess &&
                    !widget.viewModel.isSaving;
                return _SurfaceCard(
                  semanticLabel: widget.workflowOnly
                      ? l10n.transitionIssue
                      : l10n.editIssue,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: SingleChildScrollView(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (widget.viewModel.message != null) ...[
                                _MessageBanner(
                                  message: widget.viewModel.message!,
                                  onDismiss: widget.viewModel.dismissMessage,
                                ),
                                const SizedBox(height: 12),
                              ],
                              _SectionTitle(
                                widget.workflowOnly
                                    ? l10n.transitionIssue
                                    : l10n.editIssue,
                              ),
                              const SizedBox(height: 6),
                              Text(
                                '${widget.issue.key} · $issueTypeLabel',
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                              const SizedBox(height: 12),
                              _ReadOnlyCreateField(
                                label: l10n.currentStatus,
                                value:
                                    project?.statusLabel(
                                      widget.issue.statusId,
                                      locale: project.defaultLocale,
                                    ) ??
                                    widget.issue.status.label,
                              ),
                              const SizedBox(height: 12),
                              _DropdownCreateField(
                                label: l10n.status,
                                value: _selectedTransitionStatusId,
                                enabled: canEditFields && !_loadingTransitions,
                                hintText: _transitionOptions.isEmpty
                                    ? l10n.noTransitionsAvailable
                                    : l10n.optional,
                                helperText: l10n.statusTransitionHelper,
                                items: [
                                  for (final option in _transitionOptions)
                                    DropdownMenuItem<String>(
                                      value: option.id,
                                      child: Text(
                                        option.label(project?.defaultLocale),
                                      ),
                                    ),
                                ],
                                onChanged: (value) {
                                  setState(() {
                                    _selectedTransitionStatusId = value;
                                    _selectedResolutionId =
                                        _canonicalConfigId(value) != 'done'
                                        ? null
                                        : (resolutionOptions.length == 1
                                              ? resolutionOptions.single.id
                                              : _selectedResolutionId);
                                  });
                                },
                              ),
                              if (showResolution) ...[
                                const SizedBox(height: 12),
                                _DropdownCreateField(
                                  label: resolutionLabel,
                                  value: _selectedResolutionId,
                                  enabled: canEditFields,
                                  errorText:
                                      _didAttemptSubmit &&
                                          _selectedResolutionId == null
                                      ? l10n.resolutionRequired
                                      : null,
                                  items: [
                                    for (final option in resolutionOptions)
                                      DropdownMenuItem<String>(
                                        value: option.id,
                                        child: Text(
                                          option.label(project?.defaultLocale),
                                        ),
                                      ),
                                  ],
                                  onChanged: (value) {
                                    setState(() {
                                      _selectedResolutionId = value;
                                    });
                                  },
                                ),
                              ],
                              const SizedBox(height: 20),
                              Semantics(
                                label: summaryLabel,
                                textField: true,
                                child: TextField(
                                  controller: _summaryController,
                                  enabled: canEditFields,
                                  decoration: InputDecoration(
                                    labelText: summaryLabel,
                                    errorText:
                                        _didAttemptSubmit &&
                                            _summaryController.text
                                                .trim()
                                                .isEmpty
                                        ? l10n.summaryRequired
                                        : null,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              Semantics(
                                label: l10n.description,
                                textField: true,
                                child: TextField(
                                  controller: _descriptionController,
                                  minLines: 4,
                                  maxLines: null,
                                  enabled: canEditFields,
                                  decoration: InputDecoration(
                                    labelText: l10n.description,
                                    alignLabelWithHint: true,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              _DropdownCreateField(
                                label: priorityLabel,
                                value: _selectedPriorityId,
                                enabled: canEditFields,
                                items: [
                                  for (final option in priorityOptions)
                                    DropdownMenuItem<String>(
                                      value: option.id,
                                      child: Text(
                                        option.label(project?.defaultLocale),
                                      ),
                                    ),
                                ],
                                onChanged: (value) {
                                  if (value == null) {
                                    return;
                                  }
                                  setState(() {
                                    _selectedPriorityId = value;
                                  });
                                },
                              ),
                              const SizedBox(height: 12),
                              Semantics(
                                label: assigneeLabel,
                                textField: true,
                                child: TextField(
                                  controller: _assigneeController,
                                  enabled: canEditFields,
                                  decoration: InputDecoration(
                                    labelText: assigneeLabel,
                                    hintText: l10n.unassigned,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              _LabelTokenField(
                                label: labelsLabel,
                                controller: _labelEntryController,
                                labels: _labels,
                                enabled: canEditFields,
                                helperText: l10n.labelsTokenHelper,
                                onChanged: (_) => _commitLabels(),
                                onSubmitted: (_) =>
                                    _commitLabels(commitRemainder: true),
                                onRemove: (label) {
                                  setState(() {
                                    _labels.remove(label);
                                  });
                                },
                              ),
                              const SizedBox(height: 16),
                              _SelectableChipField(
                                label: componentsLabel,
                                options: componentOptions,
                                selectedValues: _components,
                                enabled: canEditFields,
                                onToggle: (value) =>
                                    _toggleConfigSelection(_components, value),
                              ),
                              const SizedBox(height: 16),
                              _SelectableChipField(
                                label: fixVersionsLabel,
                                options: versionOptions,
                                selectedValues: _fixVersions,
                                enabled: canEditFields,
                                onToggle: (value) =>
                                    _toggleConfigSelection(_fixVersions, value),
                              ),
                              if (!_isEpicType && !_isSubtaskType) ...[
                                const SizedBox(height: 16),
                                _DropdownCreateField(
                                  label: epicLabel,
                                  value: _selectedEpicKey ?? '',
                                  enabled: canEditFields,
                                  items: [
                                    DropdownMenuItem<String>(
                                      value: '',
                                      child: Text(l10n.noEpic),
                                    ),
                                    for (final option in epicOptions)
                                      DropdownMenuItem<String>(
                                        value: option.key,
                                        child: Text(
                                          '${option.key} · ${option.summary}',
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                  ],
                                  onChanged: (value) {
                                    setState(() {
                                      _selectedEpicKey = _emptyToNull(value);
                                    });
                                  },
                                ),
                              ],
                              if (_isSubtaskType) ...[
                                const SizedBox(height: 16),
                                _DropdownCreateField(
                                  label: parentLabel,
                                  value: _selectedParentKey,
                                  enabled: canEditFields,
                                  hintText: parentOptions.isEmpty
                                      ? l10n.noEligibleParents
                                      : null,
                                  errorText:
                                      _didAttemptSubmit &&
                                          _selectedParentKey == null
                                      ? l10n.subTaskParentRequired
                                      : null,
                                  items: [
                                    for (final option in parentOptions)
                                      DropdownMenuItem<String>(
                                        value: option.key,
                                        child: Text(
                                          '${option.key} · ${option.summary}',
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                  ],
                                  onChanged: parentOptions.isEmpty
                                      ? null
                                      : (value) {
                                          setState(() {
                                            _selectedParentKey = value;
                                          });
                                        },
                                ),
                                const SizedBox(height: 12),
                                _ReadOnlyCreateField(
                                  label: epicLabel,
                                  value: derivedEpic == null
                                      ? l10n.derivedFromParent
                                      : '${derivedEpic.key} · ${derivedEpic.summary}',
                                  helperText: l10n.epicDerivedFromParent,
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _IssueDetailActionButton(
                            label: l10n.save,
                            emphasized: true,
                            onPressed: canEditFields ? _submit : null,
                          ),
                          _IssueDetailActionButton(
                            label: l10n.cancel,
                            onPressed: widget.viewModel.isSaving
                                ? null
                                : () => Navigator.of(context).pop(),
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        );
      },
    );
  }
}

String _issueRoot(String storagePath) {
  if (storagePath.endsWith('/main.md')) {
    return storagePath.substring(0, storagePath.length - '/main.md'.length);
  }
  final lastSeparator = storagePath.lastIndexOf('/');
  if (lastSeparator == -1) {
    return storagePath;
  }
  return storagePath.substring(0, lastSeparator);
}

String? _emptyToNull(String? value) {
  final trimmed = value?.trim() ?? '';
  return trimmed.isEmpty ? null : trimmed;
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.item,
    required this.selected,
    required this.onPressed,
  });

  final _NavItem item;
  final bool selected;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Semantics(
        button: true,
        selected: selected,
        label: item.label,
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: onPressed,
          child: ExcludeSemantics(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
              decoration: BoxDecoration(
                color: selected ? colors.secondary : Colors.transparent,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  TrackStateIcon(
                    item.glyph,
                    color: selected ? colors.page : colors.muted,
                    size: 18,
                  ),
                  const SizedBox(width: 10),
                  Text(
                    item.label,
                    style: TextStyle(
                      color: selected ? colors.page : colors.text,
                      fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _BottomNavigation extends StatelessWidget {
  const _BottomNavigation({required this.viewModel});

  final TrackerViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final items = _navItems(l10n).take(4).toList();
    return Container(
      decoration: BoxDecoration(
        color: colors.surface,
        border: Border(top: BorderSide(color: colors.border)),
      ),
      child: SafeArea(
        child: Row(
          children: [
            for (final item in items)
              Expanded(
                child: Semantics(
                  button: true,
                  selected: viewModel.section == item.section,
                  label: item.label,
                  child: InkWell(
                    onTap: () => viewModel.selectSection(item.section),
                    child: ExcludeSemantics(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            TrackStateIcon(
                              item.glyph,
                              color: viewModel.section == item.section
                                  ? colors.primary
                                  : colors.muted,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              item.label,
                              style: Theme.of(context).textTheme.labelSmall,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _SyncPill extends StatelessWidget {
  const _SyncPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      label: label,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: colors.secondarySoft,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            TrackStateIcon(
              TrackStateIconGlyph.sync,
              color: colors.secondary,
              size: 16,
            ),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                label,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: colors.text,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GitInfoCard extends StatelessWidget {
  const _GitInfoCard({required this.project});

  final ProjectConfig project;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return _SurfaceCard(
      semanticLabel: l10n.repository,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle(l10n.repository),
          _KeyValue(label: l10n.repository, value: project.repository),
          _KeyValue(label: l10n.branch, value: project.branch),
        ],
      ),
    );
  }
}

class _DetailGrid extends StatelessWidget {
  const _DetailGrid({required this.issue});

  final TrackStateIssue issue;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        _KeyValue(label: l10n.status, value: issue.status.label),
        _KeyValue(label: l10n.priority, value: issue.priority.label),
        _KeyValue(label: l10n.assignee, value: issue.assignee),
        _KeyValue(label: l10n.reporter, value: issue.reporter),
      ],
    );
  }
}

class _KeyValue extends StatelessWidget {
  const _KeyValue({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return SizedBox(
      width: 180,
      child: Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: Theme.of(context).textTheme.labelSmall),
            const SizedBox(height: 2),
            Text(
              value,
              style: TextStyle(color: colors.text, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }
}

class _EpicProgress extends StatelessWidget {
  const _EpicProgress({required this.issue});

  final TrackStateIssue issue;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      label:
          '${issue.key} ${issue.summary} ${(issue.progress * 100).round()} percent',
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${issue.key} · ${issue.summary}'),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: LinearProgressIndicator(
                    minHeight: 8,
                    value: issue.progress,
                    color: colors.secondary,
                    backgroundColor: colors.border,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text('${(issue.progress * 100).round()}%'),
        ],
      ),
    );
  }
}

class _IssueDetailTabs extends StatelessWidget {
  const _IssueDetailTabs({
    required this.selectedIndex,
    required this.tabs,
    this.failedTabIndexes = const <int>{},
    required this.onSelected,
  });

  final int selectedIndex;
  final List<String> tabs;
  final Set<int> failedTabIndexes;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (var index = 0; index < tabs.length; index++)
          _IssueDetailTabChip(
            label: tabs[index],
            selected: index == selectedIndex,
            showFailureIndicator: failedTabIndexes.contains(index),
            onPressed: () => onSelected(index),
          ),
      ],
    );
  }
}

class _IssueDetailTabChip extends StatelessWidget {
  const _IssueDetailTabChip({
    required this.label,
    required this.selected,
    required this.showFailureIndicator,
    required this.onPressed,
  });

  final String label;
  final bool selected;
  final bool showFailureIndicator;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      button: true,
      selected: selected,
      label: label,
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onPressed,
        child: ExcludeSemantics(
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: selected ? colors.primary : colors.surfaceAlt,
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: selected ? colors.primary : colors.border,
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    label,
                    style: TextStyle(
                      color: selected ? colors.page : colors.text,
                    ),
                  ),
                  if (showFailureIndicator) ...[
                    const SizedBox(width: 8),
                    ExcludeSemantics(
                      child: Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: selected ? colors.page : colors.error,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _CommentsTab extends StatelessWidget {
  const _CommentsTab({
    required this.issue,
    required this.viewModel,
    required this.controller,
    required this.isSaving,
    required this.isLoading,
    required this.errorText,
    required this.writeBlocked,
    required this.onSave,
    required this.onRetry,
  });

  final TrackStateIssue issue;
  final TrackerViewModel viewModel;
  final TextEditingController controller;
  final bool isSaving;
  final bool isLoading;
  final String? errorText;
  final bool writeBlocked;
  final VoidCallback? onSave;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (writeBlocked) ...[
          _AccessCallout(
            semanticLabel: l10n.comments,
            title: _repositoryAccessTitle(l10n, viewModel),
            message: _repositoryAccessMessage(l10n, viewModel),
            primaryActionLabel: l10n.openSettings,
            onPrimaryAction: () =>
                viewModel.selectSection(TrackerSection.settings),
          ),
          const SizedBox(height: 12),
        ],
        Semantics(
          label: l10n.comments,
          textField: true,
          child: TextField(
            controller: controller,
            minLines: 3,
            maxLines: null,
            enabled: !isSaving && !isLoading && !writeBlocked,
            decoration: InputDecoration(
              labelText: l10n.comments,
              alignLabelWithHint: true,
            ),
          ),
        ),
        const SizedBox(height: 12),
        Align(
          alignment: Alignment.centerRight,
          child: _IssueDetailActionButton(
            label: l10n.postComment,
            emphasized: true,
            onPressed: writeBlocked || isLoading ? null : onSave,
          ),
        ),
        const SizedBox(height: 16),
        if (errorText != null)
          _DeferredSectionStateCard(
            semanticLabel: '${l10n.comments} error',
            title: l10n.comments,
            message: errorText!,
            tone: _DeferredSectionTone.error,
            actionLabel: l10n.retry,
            onAction: onRetry,
          )
        else if (isLoading || !issue.hasCommentsLoaded)
          _DeferredSectionStateCard(
            semanticLabel: '${l10n.comments} loading',
            title: l10n.comments,
            message: l10n.loading,
            tone: _DeferredSectionTone.loading,
          )
        else if (issue.comments.isEmpty)
          Text(l10n.noResults, style: TextStyle(color: colors.muted))
        else
          for (final comment in issue.comments)
            _CommentBubble(comment: comment),
      ],
    );
  }
}

class _AttachmentsTab extends StatelessWidget {
  const _AttachmentsTab({
    required this.issue,
    required this.viewModel,
    required this.onDownload,
    required this.selectedAttachment,
    required this.uploadNotice,
    required this.isSaving,
    required this.isLoading,
    required this.errorText,
    required this.onChooseAttachment,
    required this.onClearSelection,
    required this.onUpload,
    required this.onRetry,
  });

  final TrackStateIssue issue;
  final TrackerViewModel viewModel;
  final ValueChanged<IssueAttachment> onDownload;
  final PickedAttachment? selectedAttachment;
  final String? uploadNotice;
  final bool isSaving;
  final bool isLoading;
  final String? errorText;
  final VoidCallback onChooseAttachment;
  final VoidCallback onClearSelection;
  final VoidCallback onUpload;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    final accessMessage = _attachmentsAccessMessage(l10n, viewModel);
    final attachmentDownloadOnly =
        viewModel.hostedRepositoryAccessMode ==
            HostedRepositoryAccessMode.attachmentRestricted &&
        !viewModel.canUploadIssueAttachments;
    final canChooseAttachment =
        !isSaving && !isLoading && viewModel.canUploadIssueAttachments;
    final canUploadAttachment =
        canChooseAttachment && selectedAttachment != null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (accessMessage.isNotEmpty) ...[
          _AccessCallout(
            semanticLabel: l10n.attachments,
            title: _repositoryAccessTitle(l10n, viewModel),
            message: accessMessage,
            primaryActionLabel: attachmentDownloadOnly
                ? l10n.openSettings
                : null,
            onPrimaryAction: attachmentDownloadOnly
                ? () => viewModel.selectSection(TrackerSection.settings)
                : null,
          ),
          const SizedBox(height: 12),
        ],
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: colors.surfaceAlt,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: colors.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.attachments,
                style: Theme.of(context).textTheme.labelLarge,
              ),
              const SizedBox(height: 8),
              if (selectedAttachment == null)
                Text(
                  l10n.noAttachmentSelected,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: colors.muted),
                )
              else
                Semantics(
                  container: true,
                  label: l10n.selectedAttachmentSummary(
                    selectedAttachment!.name,
                    _formatAttachmentFileSize(selectedAttachment!.sizeBytes),
                  ),
                  child: ExcludeSemantics(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          selectedAttachment!.name,
                          style: Theme.of(context).textTheme.labelLarge,
                        ),
                        Text(
                          _formatAttachmentFileSize(
                            selectedAttachment!.sizeBytes,
                          ),
                          style: Theme.of(
                            context,
                          ).textTheme.bodySmall?.copyWith(color: colors.muted),
                        ),
                      ],
                    ),
                  ),
                ),
              if ((uploadNotice ?? '').isNotEmpty) ...[
                const SizedBox(height: 12),
                _AccessCallout(
                  semanticLabel: l10n.attachments,
                  title: l10n.attachments,
                  message: uploadNotice!,
                ),
              ],
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _IssueDetailActionButton(
                    label: l10n.chooseAttachment,
                    onPressed: canChooseAttachment ? onChooseAttachment : null,
                  ),
                  _IssueDetailActionButton(
                    label: l10n.uploadAttachment,
                    emphasized: true,
                    onPressed: canUploadAttachment ? onUpload : null,
                  ),
                  if (selectedAttachment != null)
                    _IssueDetailActionButton(
                      label: l10n.clearSelectedAttachment,
                      onPressed: isSaving ? null : onClearSelection,
                    ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        if (errorText != null)
          _DeferredSectionStateCard(
            semanticLabel: '${l10n.attachments} error',
            title: l10n.attachments,
            message: errorText!,
            tone: _DeferredSectionTone.error,
            actionLabel: l10n.retry,
            onAction: onRetry,
          )
        else if (isLoading || !issue.hasAttachmentsLoaded)
          _DeferredSectionStateCard(
            semanticLabel: '${l10n.attachments} loading',
            title: l10n.attachments,
            message: l10n.loading,
            tone: _DeferredSectionTone.loading,
          )
        else if (issue.attachments.isEmpty)
          Text(l10n.noResults, style: TextStyle(color: colors.muted))
        else
          for (final attachment in issue.attachments)
            _AttachmentRow(attachment: attachment, onDownload: onDownload),
      ],
    );
  }
}

class _AttachmentRow extends StatelessWidget {
  const _AttachmentRow({required this.attachment, required this.onDownload});

  final IssueAttachment attachment;
  final ValueChanged<IssueAttachment> onDownload;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    final downloadLabel = l10n.downloadAttachment(attachment.name);
    final summaryLabel =
        '${attachment.name} ${attachment.author} ${attachment.createdAt}';
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: colors.surfaceAlt,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.border),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TrackStateIcon(
            TrackStateIconGlyph.attachment,
            color: colors.text,
            semanticLabel: attachment.name,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Semantics(
              container: true,
              label: summaryLabel,
              child: ExcludeSemantics(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      attachment.name,
                      style: Theme.of(context).textTheme.labelLarge,
                    ),
                    Text(
                      '${attachment.author} · ${attachment.createdAt}',
                      style: Theme.of(
                        context,
                      ).textTheme.labelSmall?.copyWith(color: colors.text),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${attachment.sizeBytes} B',
                style: Theme.of(context).textTheme.labelSmall,
              ),
              const SizedBox(height: 4),
              Semantics(
                button: true,
                label: downloadLabel,
                child: ExcludeSemantics(
                  child: IconButton(
                    onPressed: () => onDownload(attachment),
                    tooltip: downloadLabel,
                    iconSize: 18,
                    visualDensity: VisualDensity.compact,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(
                      minWidth: 32,
                      minHeight: 32,
                    ),
                    icon: TrackStateIcon(
                      TrackStateIconGlyph.attachment,
                      size: 18,
                      color: colors.text,
                      semanticLabel: downloadLabel,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HistoryTab extends StatelessWidget {
  const _HistoryTab({
    required this.entries,
    required this.isLoading,
    required this.errorText,
    required this.onRetry,
  });

  final List<IssueHistoryEntry> entries;
  final bool isLoading;
  final String? errorText;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    if (errorText != null) {
      return _DeferredSectionStateCard(
        semanticLabel: '${l10n.history} error',
        title: l10n.history,
        message: errorText!,
        tone: _DeferredSectionTone.error,
        actionLabel: l10n.retry,
        onAction: onRetry,
      );
    }
    if (isLoading) {
      return _DeferredSectionStateCard(
        semanticLabel: '${l10n.history} loading',
        title: l10n.history,
        message: l10n.loading,
        tone: _DeferredSectionTone.loading,
      );
    }
    if (entries.isEmpty) {
      return Text(l10n.noResults, style: TextStyle(color: colors.muted));
    }
    return Column(
      children: [for (final entry in entries) _HistoryRow(entry: entry)],
    );
  }
}

enum _DeferredSectionTone { loading, error }

class _DeferredSectionStateCard extends StatelessWidget {
  const _DeferredSectionStateCard({
    required this.semanticLabel,
    required this.title,
    required this.message,
    required this.tone,
    this.actionLabel,
    this.onAction,
  });

  final String semanticLabel;
  final String title;
  final String message;
  final _DeferredSectionTone tone;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final accentColor = switch (tone) {
      _DeferredSectionTone.loading => colors.info,
      _DeferredSectionTone.error => colors.error,
    };
    return Semantics(
      container: true,
      label: semanticLabel,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: colors.surfaceAlt,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: colors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (tone == _DeferredSectionTone.loading) ...[
              const LinearProgressIndicator(minHeight: 2),
              const SizedBox(height: 12),
            ],
            Text(
              title,
              style: Theme.of(
                context,
              ).textTheme.labelLarge?.copyWith(color: accentColor),
            ),
            const SizedBox(height: 8),
            Text(message),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 12),
              _IssueDetailActionButton(
                label: actionLabel!,
                onPressed: onAction,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _HistoryRow extends StatelessWidget {
  const _HistoryRow({required this.entry});

  final IssueHistoryEntry entry;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      container: true,
      label: '${entry.summary} ${entry.author} ${entry.timestamp}',
      child: ExcludeSemantics(
        child: Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: colors.surfaceAlt,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: colors.border),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TrackStateIcon(
                TrackStateIconGlyph.sync,
                color: colors.text,
                semanticLabel: entry.summary,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entry.summary,
                      style: Theme.of(context).textTheme.labelLarge,
                    ),
                    Text(
                      '${entry.author} · ${entry.timestamp}',
                      style: Theme.of(
                        context,
                      ).textTheme.labelSmall?.copyWith(color: colors.text),
                    ),
                    if ((entry.before ?? '').isNotEmpty ||
                        (entry.after ?? '').isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Text(
                          '${entry.before ?? ''} -> ${entry.after ?? ''}'
                              .trim(),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CommentBubble extends StatelessWidget {
  const _CommentBubble({required this.comment});

  final IssueComment comment;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    final metadata = _commentMetadata(comment, l10n);
    return Semantics(
      container: true,
      label: '${comment.author} ${comment.body} $metadata',
      child: ExcludeSemantics(
        child: Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: colors.surfaceAlt,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: colors.border),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _Avatar(name: comment.author),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      comment.author,
                      style: Theme.of(context).textTheme.labelLarge,
                    ),
                    Text(
                      metadata,
                      style: Theme.of(
                        context,
                      ).textTheme.labelSmall?.copyWith(color: colors.text),
                    ),
                    const SizedBox(height: 6),
                    Text(comment.body),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

String _commentMetadata(IssueComment comment, AppLocalizations l10n) {
  final createdAt = comment.createdAt ?? comment.updatedLabel;
  final updatedAt = comment.updatedAt;
  if (updatedAt != null && updatedAt.isNotEmpty && updatedAt != createdAt) {
    return '$createdAt · ${l10n.editedAt(updatedAt)}';
  }
  return createdAt;
}

String _formatAttachmentFileSize(int sizeBytes) {
  if (sizeBytes < 1024) {
    return '$sizeBytes B';
  }
  if (sizeBytes < 1024 * 1024) {
    return '${(sizeBytes / 1024).toStringAsFixed(1)} KB';
  }
  return '${(sizeBytes / (1024 * 1024)).toStringAsFixed(1)} MB';
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});

  final IssueStatus status;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final bg = switch (status) {
      IssueStatus.todo => colors.surfaceAlt,
      IssueStatus.inProgress => colors.accentSoft,
      IssueStatus.inReview => colors.primarySoft,
      IssueStatus.done => colors.secondarySoft,
    };
    final fg = switch (status) {
      IssueStatus.todo => colors.muted,
      IssueStatus.inProgress => colors.accent,
      IssueStatus.inReview => colors.primary,
      IssueStatus.done => colors.secondary,
    };
    return _Pill(label: status.label, background: bg, foreground: fg);
  }
}

class _PriorityBadge extends StatelessWidget {
  const _PriorityBadge({required this.priority});

  final IssuePriority priority;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final foreground = switch (priority) {
      IssuePriority.highest => colors.error,
      IssuePriority.high => colors.error,
      IssuePriority.medium => colors.accent,
      IssuePriority.low => colors.secondary,
    };
    return _Pill(
      label: priority.label,
      background: foreground.withValues(alpha: .14),
      foreground: foreground,
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return _Pill(
      label: label,
      background: colors.surfaceAlt,
      foreground: colors.muted,
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({
    required this.label,
    required this.background,
    required this.foreground,
  });

  final String label;
  final Color background;
  final Color foreground;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: foreground,
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class _TinyCount extends StatelessWidget {
  const _TinyCount(this.value);

  final String value;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: colors.border.withValues(alpha: .45),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(value, style: Theme.of(context).textTheme.labelSmall),
    );
  }
}

class _IssueTypeGlyph extends StatelessWidget {
  const _IssueTypeGlyph(this.type);

  final IssueType type;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final glyph = switch (type) {
      IssueType.epic => TrackStateIconGlyph.epic,
      IssueType.story => TrackStateIconGlyph.story,
      IssueType.task => TrackStateIconGlyph.issue,
      IssueType.subtask => TrackStateIconGlyph.subtask,
      IssueType.bug => TrackStateIconGlyph.issue,
    };
    final tone = switch (type) {
      IssueType.epic => colors.primary,
      IssueType.story => colors.secondary,
      IssueType.task => colors.accent,
      IssueType.subtask => colors.muted,
      IssueType.bug => colors.error,
    };
    return TrackStateIcon(glyph, color: tone, semanticLabel: type.label);
  }
}

class _Avatar extends StatelessWidget {
  const _Avatar({required this.name});

  final String name;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    return Semantics(
      label: name,
      image: true,
      child: CircleAvatar(
        radius: 14,
        backgroundColor: colors.primarySoft,
        child: Text(
          name.characters.first,
          style: TextStyle(
            color: colors.text,
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Text(label, style: Theme.of(context).textTheme.titleMedium),
    );
  }
}

String _statusLabel(AppLocalizations l10n, IssueStatus status) =>
    switch (status) {
      IssueStatus.todo => l10n.toDo,
      IssueStatus.inProgress => l10n.inProgress,
      IssueStatus.inReview => l10n.inReview,
      IssueStatus.done => l10n.done,
    };

List<_NavItem> _navItems(AppLocalizations l10n) => [
  _NavItem(
    l10n.dashboard,
    TrackerSection.dashboard,
    TrackStateIconGlyph.dashboard,
  ),
  _NavItem(l10n.board, TrackerSection.board, TrackStateIconGlyph.board),
  _NavItem(l10n.jqlSearch, TrackerSection.search, TrackStateIconGlyph.search),
  _NavItem(
    l10n.hierarchy,
    TrackerSection.hierarchy,
    TrackStateIconGlyph.hierarchy,
  ),
  _NavItem(
    l10n.settings,
    TrackerSection.settings,
    TrackStateIconGlyph.settings,
  ),
];

class _NavItem {
  const _NavItem(this.label, this.section, this.glyph);

  final String label;
  final TrackerSection section;
  final TrackStateIconGlyph glyph;
}
