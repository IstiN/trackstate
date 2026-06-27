import 'dart:async' show unawaited;

import 'package:flutter/material.dart';

import '../../../../../../l10n/generated/app_localizations.dart';
import '../../../../../domain/models/trackstate_models.dart';
import '../../view_models/tracker_view_model.dart';
import 'access_callout.dart';
import 'message_banner.dart';

String startupRecoveryTitle(
  AppLocalizations l10n,
  TrackerStartupRecovery recovery,
) {
  return switch (recovery.kind) {
    TrackerStartupRecoveryKind.githubRateLimit =>
      l10n.startupRateLimitRecoveryTitle,
    TrackerStartupRecoveryKind.hostedBootstrapIndex =>
      l10n.startupHostedBootstrapIndexRecoveryTitle,
    TrackerStartupRecoveryKind.hostedBootstrapTimeout =>
      l10n.startupRateLimitRecoveryTitle,
  };
}

String startupRecoveryMessage(
  AppLocalizations l10n,
  TrackerViewModel viewModel,
) {
  final recovery = viewModel.startupRecovery;
  if (recovery == null) {
    return '';
  }
  return switch (recovery.kind) {
    TrackerStartupRecoveryKind.githubRateLimit =>
      viewModel.snapshot == null
          ? l10n.startupRateLimitRecoveryBlockingMessage
          : l10n.startupRateLimitRecoveryShellMessage,
    TrackerStartupRecoveryKind.hostedBootstrapIndex =>
      recovery.detail?.trim().isNotEmpty == true
          ? recovery.detail!
          : l10n.startupHostedBootstrapIndexRecoveryMessage,
    TrackerStartupRecoveryKind.hostedBootstrapTimeout =>
      viewModel.snapshot == null
          ? l10n.startupRateLimitRecoveryBlockingMessage
          : l10n.startupRateLimitRecoveryShellMessage,
  };
}

class StartupRecoveryView extends StatelessWidget {
  const StartupRecoveryView({
    super.key,
    required this.viewModel,
    required this.onRetryStartupRecovery,
    this.onSecondaryAction,
    this.secondaryActionLabel,
  });

  final TrackerViewModel viewModel;
  final Future<void> Function() onRetryStartupRecovery;
  final VoidCallback? onSecondaryAction;
  final String? secondaryActionLabel;

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
                MessageBanner(
                  message: viewModel.message!,
                  onDismiss: viewModel.dismissMessage,
                ),
                const SizedBox(height: 12),
              ],
              AccessCallout(
                semanticLabel: l10n.startupRecovery,
                title: startupRecoveryTitle(l10n, recovery),
                message: startupRecoveryMessage(l10n, viewModel),
                primaryActionLabel: l10n.retryStartup,
                onPrimaryAction: () {
                  unawaited(onRetryStartupRecovery());
                },
                secondaryActionLabel: secondaryActionLabel,
                onSecondaryAction: onSecondaryAction,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
