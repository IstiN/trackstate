import 'package:flutter/material.dart';

import '../../../../../../l10n/generated/app_localizations.dart';
import '../../../../../ui/core/trackstate_icons.dart';
import '../../../../../ui/core/trackstate_theme.dart';
import '../../view_models/tracker_view_model.dart';

String trackerMessageText(AppLocalizations l10n, TrackerMessage message) {
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
    TrackerMessageKind.selectedIssueUnavailable =>
      l10n.selectedIssueUnavailable(message.issueKey!),
    TrackerMessageKind.workspaceSwitchFailed => l10n.workspaceSwitchFailed(
      message.repository!,
      message.error!,
    ),
    TrackerMessageKind.workspaceRestoreSkipped => l10n.workspaceRestoreSkipped(
      message.repository!,
      message.error!,
    ),
    TrackerMessageKind.workspaceRestoreFailed => l10n.workspaceRestoreFailed(
      message.repository!,
      message.error!,
    ),
  };
}

class MessageBanner extends StatelessWidget {
  const MessageBanner({super.key, required this.message, this.onDismiss});

  final TrackerMessage? message;
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final colors = context.ts;
    final resolvedMessage = message == null
        ? l10n.trackerDataNotFound
        : trackerMessageText(l10n, message!);
    final isError = message?.tone == TrackerMessageTone.error;
    return Semantics(
      container: true,
      explicitChildNodes: true,
      liveRegion: true,
      label: resolvedMessage,
      child: AnimatedContainer(
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
            ExcludeSemantics(
              child: TrackStateIcon(
                isError
                    ? TrackStateIconGlyph.issue
                    : TrackStateIconGlyph.gitBranch,
                size: 18,
                color: isError ? colors.accent : colors.primary,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(child: ExcludeSemantics(child: Text(resolvedMessage))),
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
      ),
    );
  }
}
