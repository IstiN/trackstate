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
  const TrackStateApp({super.key, this.repository, this.openLocalRepository});

  final TrackStateRepository? repository;
  final LocalRepositoryLoader? openLocalRepository;

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
  });

  final TrackerViewModel viewModel;
  final bool isCreateIssueVisible;
  final _CreateIssueLauncher onOpenCreateIssue;
  final VoidCallback onCloseCreateIssue;
  final _CreateIssuePrefill? createIssuePrefill;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    if (viewModel.isLoading) {
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
                        )
                      : _DesktopShell(
                          viewModel: viewModel,
                          isCreateIssueVisible: isCreateIssueVisible,
                          onOpenCreateIssue: onOpenCreateIssue,
                          onCloseCreateIssue: onCloseCreateIssue,
                          createIssuePrefill: createIssuePrefill,
                          onApplyLocalGitConfiguration:
                              onApplyLocalGitConfiguration,
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
  });

  final TrackerViewModel viewModel;
  final bool isCreateIssueVisible;
  final _CreateIssueLauncher onOpenCreateIssue;
  final VoidCallback onCloseCreateIssue;
  final _CreateIssuePrefill? createIssuePrefill;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;

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
  });

  final TrackerViewModel viewModel;
  final bool isCreateIssueVisible;
  final _CreateIssueLauncher onOpenCreateIssue;
  final VoidCallback onCloseCreateIssue;
  final _CreateIssuePrefill? createIssuePrefill;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;

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
    this.compact = false,
  });

  final TrackerViewModel viewModel;
  final bool compact;
  final bool isCreateIssueVisible;
  final _CreateIssueLauncher onOpenCreateIssue;
  final VoidCallback onCloseCreateIssue;
  final _CreateIssuePrefill? createIssuePrefill;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;

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
            Expanded(
              child: _SectionBody(
                viewModel: viewModel,
                compact: compact,
                onOpenCreateIssue: onOpenCreateIssue,
                onApplyLocalGitConfiguration: onApplyLocalGitConfiguration,
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
        child: Column(
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
                        style: Theme.of(
                          context,
                        ).textTheme.labelSmall?.copyWith(color: colors.muted),
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
            const Spacer(),
            _SyncPill(label: l10n.syncStatus),
            const SizedBox(height: 12),
            _GitInfoCard(project: viewModel.project!),
          ],
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
    final openCreateIssue = viewModel.hasReadOnlySession || viewModel.isSaving
        ? null
        : () => onOpenCreateIssue(
            _CreateIssuePrefill(originSection: viewModel.section),
          );
    return Padding(
      padding: EdgeInsets.fromLTRB(compact ? 12 : 8, 12, 12, 6),
      child: Row(
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
          SizedBox(width: compact ? 8 : 12),
          if (compact)
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
          if (compact)
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
          if (_hasVisibleProfileIdentity(viewModel) && !compact) ...[
            ConstrainedBox(
              constraints: BoxConstraints(maxWidth: compact ? 160 : 240),
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
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
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
                          style: Theme.of(
                            context,
                          ).textTheme.bodySmall?.copyWith(color: colors.muted),
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
  await showDialog<void>(
    context: context,
    builder: (context) {
      final project = viewModel.project;
      return StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            title: Text(l10n.connectGitHub),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${l10n.repository}: '
                  '${project?.repository ?? l10n.configuredRepositoryFallback}',
                ),
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
  return switch (viewModel.repositoryAccessState) {
    RepositoryAccessState.localGit => l10n.repositoryAccessLocalGit,
    RepositoryAccessState.connected => l10n.repositoryAccessConnected,
    RepositoryAccessState.connectGitHub => l10n.repositoryAccessConnectGitHub,
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

class _SectionBody extends StatelessWidget {
  const _SectionBody({
    required this.viewModel,
    required this.onOpenCreateIssue,
    required this.onApplyLocalGitConfiguration,
    this.compact = false,
  });

  final TrackerViewModel viewModel;
  final _CreateIssueLauncher onOpenCreateIssue;
  final LocalRepositoryConfigurationApplier onApplyLocalGitConfiguration;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final body = switch (viewModel.section) {
      TrackerSection.dashboard => _Dashboard(viewModel: viewModel),
      TrackerSection.board => _Board(viewModel: viewModel),
      TrackerSection.search => _SearchAndDetail(
        viewModel: viewModel,
        onOpenCreateIssue: onOpenCreateIssue,
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ScreenHeading(title: l10n.dashboard, subtitle: l10n.appTagline),
        LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 900;
            final cards = [
              _MetricCard(
                label: l10n.openIssues,
                value: '${viewModel.openIssueCount}',
                delta: '-6d',
                tone: MetricTone.accent,
              ),
              _MetricCard(
                label: l10n.issuesInProgress,
                value: '${viewModel.inProgressIssueCount}',
                delta: '+4',
                tone: MetricTone.primary,
              ),
              _MetricCard(
                label: l10n.completed,
                value: '${viewModel.completedIssueCount}',
                delta: '+12',
                tone: MetricTone.secondary,
              ),
              _MetricCard(
                label: l10n.teamVelocity,
                value: '42',
                delta: '+18%',
                tone: MetricTone.secondary,
              ),
            ];
            return GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: compact ? 2 : 4,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: compact ? 1.05 : 1.75,
              children: cards,
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
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ScreenHeading(title: l10n.board, subtitle: l10n.kanbanHint),
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
  });

  final TrackerViewModel viewModel;
  final _CreateIssueLauncher onOpenCreateIssue;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final viewModel = this.viewModel;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: _ScreenHeading(
                title: l10n.jqlSearch,
                subtitle: l10n.issueCount(viewModel.totalSearchResults),
              ),
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
          _HostedProviderConfiguration(
            viewModel: widget.viewModel,
            providerLabel: hostedLabel,
          ),
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
        LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 860;
            final cards = [
              _ConfigCard(title: l10n.issueTypes, items: project.issueTypes),
              _ConfigCard(title: l10n.workflow, items: project.statuses),
              _ConfigCard(title: l10n.fields, items: project.fields),
              _ConfigCard(
                title: l10n.language,
                items: const [
                  'English',
                  'Fallback language packs in config/i18n',
                ],
              ),
            ];
            return GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: compact ? 1 : 2,
              crossAxisSpacing: 16,
              mainAxisSpacing: 16,
              childAspectRatio: compact ? 2.2 : 1.7,
              children: cards,
            );
          },
        ),
      ],
    );
  }
}

enum _SettingsProviderSelection { hosted, localGit }

class _IssueDetail extends StatefulWidget {
  const _IssueDetail({
    required this.issue,
    required this.viewModel,
    required this.onCreateChildIssue,
  });

  final TrackStateIssue issue;
  final TrackerViewModel viewModel;
  final VoidCallback onCreateChildIssue;

  @override
  State<_IssueDetail> createState() => _IssueDetailState();
}

class _IssueDetailState extends State<_IssueDetail> {
  late final TextEditingController _descriptionController;
  late final TextEditingController _commentController;
  bool _isEditing = false;
  int _selectedCollaborationTab = 0;

  @override
  void initState() {
    super.initState();
    _descriptionController = TextEditingController(
      text: widget.issue.description,
    );
    _commentController = TextEditingController();
  }

  @override
  void didUpdateWidget(covariant _IssueDetail oldWidget) {
    super.didUpdateWidget(oldWidget);
    final issueChanged = oldWidget.issue.key != widget.issue.key;
    final descriptionChanged =
        oldWidget.issue.description != widget.issue.description;
    if (issueChanged) {
      _isEditing = false;
    }
    if (issueChanged || (!_isEditing && descriptionChanged)) {
      _descriptionController.text = widget.issue.description;
    }
    if (issueChanged) {
      _commentController.clear();
      if (_selectedCollaborationTab == 3) {
        widget.viewModel.ensureIssueHistoryLoaded(widget.issue);
      }
    }
  }

  @override
  void dispose() {
    _descriptionController.dispose();
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _saveDescription() async {
    final success = await widget.viewModel.saveIssueDescription(
      widget.issue,
      _descriptionController.text,
    );
    if (!mounted || !success) {
      return;
    }
    setState(() {
      _isEditing = false;
    });
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

  Widget _detailTabContent(
    BuildContext context, {
    required TrackStateIssue issue,
    required AppLocalizations l10n,
    required TrackStateColors colors,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionTitle(l10n.description),
        if (_isEditing)
          Semantics(
            label: l10n.description,
            textField: true,
            child: TextField(
              controller: _descriptionController,
              minLines: 4,
              maxLines: null,
              enabled: !widget.viewModel.isSaving,
              decoration: InputDecoration(
                labelText: l10n.description,
                alignLabelWithHint: true,
              ),
            ),
          )
        else
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
    final hasReadOnlySession = widget.viewModel.hasReadOnlySession;
    final canUseWriteActions =
        !hasReadOnlySession && !widget.viewModel.isSaving;
    final actions = [
      if (widget.viewModel.issueDetailReturnSection case final returnSection?)
        _IssueDetailActionButton(
          label: '${l10n.back} ${_trackerSectionLabel(l10n, returnSection)}',
          onPressed: widget.viewModel.returnFromIssueDetail,
        ),
      _PrimaryButton(
        label: l10n.transition,
        icon: TrackStateIconGlyph.gitBranch,
        onPressed: canUseWriteActions ? () {} : null,
      ),
      _IssueDetailActionButton(
        label: l10n.createChildIssue,
        onPressed: canUseWriteActions ? widget.onCreateChildIssue : null,
      ),
      if (_isEditing)
        _IssueDetailActionButton(
          label: l10n.save,
          emphasized: true,
          onPressed: canUseWriteActions ? _saveDescription : null,
        )
      else
        _IssueDetailActionButton(
          label: l10n.edit,
          onPressed: canUseWriteActions
              ? () {
                  setState(() {
                    _isEditing = true;
                    _descriptionController.text = issue.description;
                  });
                }
              : null,
        ),
      if (_isEditing)
        _IssueDetailActionButton(
          label: l10n.cancel,
          onPressed: widget.viewModel.isSaving
              ? null
              : () {
                  setState(() {
                    _isEditing = false;
                    _descriptionController.text = issue.description;
                  });
                },
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
          if (hasReadOnlySession) ...[
            Text(
              l10n.issueDetailReadOnlyMessage,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: colors.muted),
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
            onSelected: (index) {
              setState(() {
                _selectedCollaborationTab = index;
              });
              if (index == 3) {
                widget.viewModel.ensureIssueHistoryLoaded(issue);
              }
            },
          ),
          const SizedBox(height: 16),
          if (_selectedCollaborationTab == 0)
            _detailTabContent(
              context,
              issue: issue,
              l10n: l10n,
              colors: colors,
            )
          else if (_selectedCollaborationTab == 1)
            _CommentsTab(
              issue: issue,
              controller: _commentController,
              isSaving: widget.viewModel.isSaving,
              readOnly: hasReadOnlySession,
              onSave: canUseWriteActions ? _saveComment : null,
            )
          else if (_selectedCollaborationTab == 2)
            _AttachmentsTab(
              issue: issue,
              onDownload: widget.viewModel.downloadIssueAttachment,
              readOnly: hasReadOnlySession,
            )
          else
            _HistoryTab(
              entries: widget.viewModel.issueHistoryFor(issue.key),
              isLoading: widget.viewModel.isIssueHistoryLoading(issue.key),
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
    return Semantics(
      button: true,
      label: label,
      child: button,
    );
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
                SingleActivator(
                  LogicalKeyboardKey.tab,
                  shift: true,
                ): PreviousFocusIntent(),
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
          if (searchResults.isEmpty)
            Text(l10n.noResults)
          else ...[
            if (searchResults.length < viewModel.totalSearchResults)
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
            for (var index = 0; index < searchResults.length; index += 1)
              FocusTraversalOrder(
                order: NumericFocusOrder(index + 2.0),
                child: _IssueListRow(
                  issue: searchResults[index],
                  onSelect: viewModel.selectIssue,
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
  });

  final String label;
  final String value;
  final String delta;
  final MetricTone tone;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final toneColor = switch (tone) {
      MetricTone.primary => colors.primary,
      MetricTone.secondary => colors.secondary,
      MetricTone.accent => colors.accent,
    };
    return _SurfaceCard(
      semanticLabel: '$label $value',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelLarge),
          Text(value, style: Theme.of(context).textTheme.headlineLarge),
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

class _ConfigCard extends StatelessWidget {
  const _ConfigCard({required this.title, required this.items});

  final String title;
  final List<String> items;

  @override
  Widget build(BuildContext context) {
    return _SurfaceCard(
      semanticLabel: title,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle(title),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [for (final item in items) _Chip(label: item)],
          ),
        ],
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

class _HostedProviderConfiguration extends StatelessWidget {
  const _HostedProviderConfiguration({
    required this.viewModel,
    required this.providerLabel,
  });

  final TrackerViewModel viewModel;
  final String providerLabel;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          initialValue: '',
          obscureText: true,
          decoration: InputDecoration(
            labelText: l10n.fineGrainedToken,
            helperText: l10n.fineGrainedTokenHelper,
          ),
        ),
        if (viewModel.connectedUser != null) ...[
          const SizedBox(height: 12),
          Text(
            l10n.githubConnected(
              viewModel.connectedUser!.login,
              viewModel.project!.repository,
            ),
          ),
        ] else if (providerLabel != l10n.connectGitHub) ...[
          const SizedBox(height: 12),
          Text(providerLabel),
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
    required this.focusNode,
  });

  final String label;
  final TextEditingController controller;
  final FocusNode focusNode;

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
    this.errorText,
  });

  final String label;
  final String? value;
  final bool enabled;
  final String? hintText;
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
                final canSubmit =
                    !widget.viewModel.hasReadOnlySession &&
                    !widget.viewModel.isSaving;
                return _SurfaceCard(
                  semanticLabel: l10n.createIssue,
                  child: SingleChildScrollView(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _SectionTitle(l10n.createIssue),
                        const SizedBox(height: 12),
                        _DropdownCreateField(
                          label: issueTypeLabel,
                          value: _selectedIssueTypeId,
                          enabled: !widget.viewModel.isSaving,
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
                            enabled: !widget.viewModel.isSaving,
                            decoration: InputDecoration(labelText: summaryLabel),
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
                            enabled: !widget.viewModel.isSaving,
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
                          enabled: !widget.viewModel.isSaving,
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
                              defaultStatus?.label(project?.defaultLocale) ??
                              l10n.toDo,
                        ),
                        if (!_isEpicType && !_isSubtaskType) ...[
                          const SizedBox(height: 12),
                          _DropdownCreateField(
                            label: epicLabel,
                            value: _selectedEpicKey,
                            enabled: !widget.viewModel.isSaving,
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
                            enabled: !widget.viewModel.isSaving,
                            hintText: parentOptions.isEmpty
                                ? l10n.noEligibleParents
                                : null,
                            errorText:
                                _didAttemptSubmit && _selectedParentKey == null
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
                            enabled: !widget.viewModel.isSaving,
                            decoration: InputDecoration(labelText: assigneeLabel),
                          ),
                        ),
                        const SizedBox(height: 12),
                        _LabelTokenField(
                          label: labelsLabel,
                          controller: _labelEntryController,
                          labels: _labels,
                          enabled: !widget.viewModel.isSaving,
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
                              controller: _customFieldControllers[field.id],
                              minLines: field.type == 'markdown' ? 3 : 1,
                              maxLines: field.type == 'markdown' ? null : 1,
                              enabled: !widget.viewModel.isSaving,
                              decoration: InputDecoration(
                                labelText: _createIssueFieldLabel(project, field),
                                alignLabelWithHint: field.type == 'markdown',
                              ),
                            ),
                          ),
                        ],
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
    required this.onSelected,
  });

  final int selectedIndex;
  final List<String> tabs;
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
    required this.onPressed,
  });

  final String label;
  final bool selected;
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
              border: Border.all(color: selected ? colors.primary : colors.border),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Text(
                label,
                style: TextStyle(color: selected ? colors.page : colors.text),
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
    required this.controller,
    required this.isSaving,
    required this.readOnly,
    required this.onSave,
  });

  final TrackStateIssue issue;
  final TextEditingController controller;
  final bool isSaving;
  final bool readOnly;
  final VoidCallback? onSave;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (!readOnly) ...[
          Semantics(
            label: l10n.comments,
            textField: true,
            child: TextField(
              controller: controller,
              minLines: 3,
              maxLines: null,
              enabled: !isSaving,
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
              onPressed: onSave,
            ),
          ),
          const SizedBox(height: 16),
        ],
        if (issue.comments.isEmpty)
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
    required this.onDownload,
    required this.readOnly,
  });

  final TrackStateIssue issue;
  final ValueChanged<IssueAttachment> onDownload;
  final bool readOnly;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    if (issue.attachments.isEmpty) {
      return Text(l10n.noResults, style: TextStyle(color: colors.muted));
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (readOnly) ...[
          Semantics(
            container: true,
            label: l10n.attachmentsDownloadOnlyMessage,
            child: ExcludeSemantics(
              child: Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  l10n.attachmentsDownloadOnlyMessage,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: colors.muted),
                ),
              ),
            ),
          ),
        ],
        for (final attachment in issue.attachments)
          _AttachmentRow(attachment: attachment, onDownload: onDownload),
      ],
    );
  }
}

class _AttachmentRow extends StatelessWidget {
  const _AttachmentRow({
    required this.attachment,
    required this.onDownload,
  });

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
                    constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
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
  const _HistoryTab({required this.entries, required this.isLoading});

  final List<IssueHistoryEntry> entries;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    final colors = context.ts;
    final l10n = AppLocalizations.of(context)!;
    if (isLoading) {
      return const LinearProgressIndicator(minHeight: 2);
    }
    if (entries.isEmpty) {
      return Text(l10n.noResults, style: TextStyle(color: colors.muted));
    }
    return Column(
      children: [
        for (final entry in entries)
          _HistoryRow(entry: entry),
      ],
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
                          '${entry.before ?? ''} -> ${entry.after ?? ''}'.trim(),
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
    return Semantics(
      container: true,
      label: '${comment.author} ${comment.body} ${comment.updatedLabel}',
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
                    Text(comment.body),
                  ],
                ),
              ),
              Text(
                comment.updatedLabel,
                style: Theme.of(context).textTheme.labelSmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
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
