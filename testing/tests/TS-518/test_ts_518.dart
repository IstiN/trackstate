import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _attachmentsTabLabel = 'Attachments';
const String _noticeTitle =
    'GitHub Releases uploads are unavailable in the browser';
const String _noticeMessage =
    'This project stores new attachments in GitHub Releases. Existing attachments remain available for download, but hosted release-backed uploads are not available in this browser session yet.';
const String _openSettingsLabel = 'Open settings';
const String _chooseAttachmentLabel = 'Choose attachment';
const String _uploadAttachmentLabel = 'Upload attachment';
const String _attachmentName = 'sync-sequence.svg';
const String _downloadAttachmentLabel = 'Download sync-sequence.svg';

const String _githubReleasesProjectJson = '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "attachmentStorage": {
    "mode": "github-releases",
    "githubReleases": {
      "tagPrefix": "trackstate-attachments-"
    }
  },
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config"
}
''';

void main() {
  testWidgets(
    'TS-518 tabbing after Open settings focuses the first attachment download action',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final failures = <String>[];

      try {
        final screen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: const RepositoryPermission(
              canRead: true,
              canWrite: true,
              isAdmin: false,
              canCreateBranch: true,
              canManageAttachments: true,
              attachmentUploadMode: AttachmentUploadMode.full,
              supportsReleaseAttachmentWrites: false,
              canCheckCollaborators: false,
            ),
            textFixtures: const <String, String>{
              'project.json': _githubReleasesProjectJson,
            },
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'ts518-stored-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);
        await screen.selectCollaborationTab(_issueKey, _attachmentsTabLabel);

        final visibleTexts = screen.visibleTextsWithinIssueDetail(_issueKey);
        for (final requiredText in const <String>[
          _attachmentsTabLabel,
          _noticeTitle,
          _noticeMessage,
          _openSettingsLabel,
          _attachmentName,
        ]) {
          if (!_containsSnapshot(visibleTexts, requiredText)) {
            failures.add(
              'Step 1 failed: the Attachments tab did not keep the visible "$requiredText" text in the issue detail. '
              'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}.',
            );
          }
        }

        if (!screen.showsAttachmentsRestrictionCallout(
          _issueKey,
          title: _noticeTitle,
          message: _noticeMessage,
        )) {
          failures.add(
            'Step 1 failed: the release-restricted Attachments notice did not render as a visible inline callout. '
            'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}. '
            'Visible semantics: ${_formatSnapshot(screen.semanticsLabelsInIssueDetail(_issueKey))}.',
          );
        }

        if (!screen.showsAttachmentRow(_issueKey, _attachmentName)) {
          failures.add(
            'Step 1 failed: the first attachment row for "$_attachmentName" did not render in the Attachments tab. '
            'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}.',
          );
        }

        if (!screen.showsAttachmentsRestrictionAction(
          _issueKey,
          title: _noticeTitle,
          message: _noticeMessage,
          actionLabel: _openSettingsLabel,
        )) {
          failures.add(
            'Step 2 failed: the inline warning notice did not expose a keyboard-focusable "$_openSettingsLabel" action. '
            'Visible issue-detail buttons: ${_formatSnapshot(screen.buttonLabelsInIssueDetail(_issueKey))}.',
          );
        }
        if (!screen.showsAttachmentAction(
          _issueKey,
          attachmentName: _attachmentName,
          actionLabel: _downloadAttachmentLabel,
        )) {
          failures.add(
            'Step 2 failed: the first attachment row did not expose a keyboard-focusable "$_downloadAttachmentLabel" action. '
            'Visible issue-detail buttons: ${_formatSnapshot(screen.buttonLabelsInIssueDetail(_issueKey))}.',
          );
        }

        if (screen.showsAttachmentsRestrictionAction(
              _issueKey,
              title: _noticeTitle,
              message: _noticeMessage,
              actionLabel: _openSettingsLabel,
            ) &&
            screen.showsAttachmentAction(
              _issueKey,
              attachmentName: _attachmentName,
              actionLabel: _downloadAttachmentLabel,
            )) {
          final focusTransition = await screen
              .observeForwardFocusTransitionFromAttachmentsRestrictionAction(
                _issueKey,
                title: _noticeTitle,
                message: _noticeMessage,
                actionLabel: _openSettingsLabel,
              );
          if (!focusTransition.reachedTarget) {
            failures.add(
              'Step 2 failed: keyboard Tab traversal never reached the visible "$_openSettingsLabel" action in the Attachments warning notice. '
              'Observed focus sequence: ${_formatSnapshot(focusTransition.focusSequence)}. '
              'Focused semantics near failure: ${_formatSnapshot(focusTransition.lastFocusedLabels)}.',
            );
          } else if (focusTransition.nextFocusedLabel !=
              _downloadAttachmentLabel) {
            failures.add(
              'Step 4 failed: pressing Tab once after "$_openSettingsLabel" focused "${focusTransition.nextFocusedLabel ?? '<none>'}" instead of "$_downloadAttachmentLabel". '
              'Observed focus sequence: ${_formatSnapshot(focusTransition.focusSequence)}. '
              'Focused semantics after the extra Tab: ${_formatSnapshot(focusTransition.lastFocusedLabels)}.',
            );
          } else if (!screen
              .attachmentActionIsBelowAttachmentsRestrictionCallout(
                _issueKey,
                title: _noticeTitle,
                message: _noticeMessage,
                attachmentName: _attachmentName,
                actionLabel: _downloadAttachmentLabel,
              )) {
            failures.add(
              'Human-style verification failed: the keyboard-focused "$_downloadAttachmentLabel" action did not remain visually below the inline warning notice.',
            );
          }
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

bool _containsSnapshot(List<String> values, String expected) {
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed == expected ||
        trimmed.startsWith(expected) ||
        trimmed.contains(expected)) {
      return true;
    }
  }
  return false;
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}
