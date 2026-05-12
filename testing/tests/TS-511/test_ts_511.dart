import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-511 attachments tab notice keeps inline release guidance and routes Open settings to Project Settings > Attachments',
    (tester) async {
      final failures = <String>[];
      final settingsRobot = SettingsScreenRobot(tester);
      late final IssueDetailAccessibilityScreenHandle screen;

      try {
        screen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: _releaseRestrictedPermission,
            textFixtures: _githubReleasesProjectTextFixtures(),
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'release-backed-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);

        if (!screen.showsIssueDetail(_issueKey)) {
          failures.add(
            'Step 1 failed: opening JQL Search did not show the $_issueKey issue detail surface. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(settingsRobot.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        if (!screen
            .buttonLabelsInIssueDetail(_issueKey)
            .contains('Attachments')) {
          failures.add(
            'Step 1 failed: the issue detail did not expose the visible "Attachments" tab. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
          );
        } else {
          await screen.selectCollaborationTab(_issueKey, 'Attachments');
        }

        if (!screen.showsAttachmentsRestrictionCallout(
          _issueKey,
          title: _releaseRestrictionTitle,
          message: _releaseRestrictionMessage,
        )) {
          failures.add(
            'Step 2 failed: the Attachments tab did not render the release-storage restriction notice inline in the issue detail surface. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(settingsRobot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          if (find.byType(Dialog).evaluate().isNotEmpty) {
            failures.add(
              'Step 2 failed: opening the Attachments tab showed a modal dialog instead of keeping the restriction notice inline. '
              'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
            );
          }

          for (final text in const <String>[
            _releaseRestrictionTitle,
            _releaseRestrictionMessage,
            _openSettingsLabel,
          ]) {
            if (!screen.attachmentsRestrictionCalloutShowsText(
              _issueKey,
              title: _releaseRestrictionTitle,
              message: _releaseRestrictionMessage,
              text: text,
            )) {
              failures.add(
                'Step 2 failed: the inline Attachments notice did not render "$text" in the visible callout surface.',
              );
            }
          }

          if (!screen.showsAttachmentRow(_issueKey, _existingAttachmentName)) {
            failures.add(
              'Step 2 failed: the existing attachment list was not visible below the restriction notice. '
              'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
            );
          } else if (!screen.attachmentsRestrictionCalloutIsInline(
            _issueKey,
            tabLabel: 'Attachments',
            title: _releaseRestrictionTitle,
            message: _releaseRestrictionMessage,
          )) {
            failures.add(
              'Step 2 failed: the restriction notice rendered in the issue header area instead of below the Attachments tab controls.',
            );
          } else if (!screen.attachmentRowIsBelowAttachmentsRestrictionCallout(
            _issueKey,
            title: _releaseRestrictionTitle,
            message: _releaseRestrictionMessage,
            attachmentName: _existingAttachmentName,
          )) {
            failures.add(
              'Step 2 failed: the existing attachment row did not stay below the inline restriction notice.',
            );
          }

          if (!screen.showsAttachmentsRestrictionAction(
            _issueKey,
            title: _releaseRestrictionTitle,
            message: _releaseRestrictionMessage,
            actionLabel: _openSettingsLabel,
          )) {
            failures.add(
              'Step 3 failed: the inline Attachments notice did not expose the "$_openSettingsLabel" recovery action.',
            );
          } else {
            await screen.tapAttachmentsRestrictionAction(
              _issueKey,
              title: _releaseRestrictionTitle,
              message: _releaseRestrictionMessage,
              actionLabel: _openSettingsLabel,
            );

            if (find.byType(Dialog).evaluate().isNotEmpty) {
              failures.add(
                'Step 3 failed: tapping "$_openSettingsLabel" opened a modal instead of navigating to Project Settings > Attachments. '
                'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
              );
            }
            if (!settingsRobot.isVisibleText('Project Settings') ||
                settingsRobot.tabByLabel('Attachments').evaluate().isEmpty) {
              failures.add(
                'Step 3 failed: tapping "$_openSettingsLabel" did not navigate to Project Settings. '
                'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
              );
            }
            if (!settingsRobot.isVisibleText('Attachment storage mode')) {
              failures.add(
                'Step 3 failed: tapping "$_openSettingsLabel" did not land on the Project Settings > Attachments tab. '
                'The settings surface opened without the Attachment storage configuration. '
                'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
              );
            }
          }
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _existingAttachmentName = 'sync-sequence.svg';
const String _openSettingsLabel = 'Open settings';
const String _releaseRestrictionTitle =
    'GitHub Releases uploads are unavailable in the browser';
const String _releaseRestrictionMessage =
    'This project stores new attachments in GitHub Releases. Existing attachments remain available for download, but hosted release-backed uploads are not available in this browser session yet.';

const RepositoryPermission _releaseRestrictedPermission = RepositoryPermission(
  canRead: true,
  canWrite: true,
  isAdmin: false,
  canCreateBranch: true,
  canManageAttachments: true,
  attachmentUploadMode: AttachmentUploadMode.full,
  supportsReleaseAttachmentWrites: false,
  canCheckCollaborators: false,
);

String _formatSnapshot(List<String> values) {
  if (values.isEmpty) {
    return '<none>';
  }
  return values.join(' | ');
}

Map<String, String> _githubReleasesProjectTextFixtures() => const {
  'project.json': '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config",
  "attachmentStorage": {
    "mode": "github-releases",
    "githubReleases": {
      "tagPrefix": "browser-assets-"
    }
  }
}
''',
};
