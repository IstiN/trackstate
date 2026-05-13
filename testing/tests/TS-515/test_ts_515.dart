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
    'TS-515 Open settings from the Attachments restriction notice overrides a previously selected Statuses tab',
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

        await settingsRobot.openSettings();

        if (!settingsRobot.showsProjectSettingsSurface()) {
          failures.add(
            'Step 1 failed: navigating to Project Settings did not open the visible Project Settings surface. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(settingsRobot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else if (!settingsRobot.showsProjectSettingsTab('Statuses')) {
          failures.add(
            'Step 1 failed: Project Settings did not expose the visible "Statuses" tab required by the precondition. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
          );
        } else {
          await settingsRobot.openStatusesTab();

          if (!settingsRobot.isVisibleText('Project settings administration')) {
            failures.add(
              'Step 1 failed: the Statuses view did not keep the visible "Project settings administration" heading on screen. '
              'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
            );
          }
          if (!settingsRobot.isVisibleText('Add status')) {
            failures.add(
              'Step 1 failed: the Statuses tab was not the active sub-tab before returning to the issue because the visible "Add status" action was missing. '
              'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
            );
          }
          if (settingsRobot.showsAttachmentStorageModeSetting()) {
            failures.add(
              'Step 1 failed: the Attachments configuration stayed visible even after selecting Statuses, so the test could not prove the stale-tab override scenario. '
              'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
            );
          }
        }

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);

        if (!screen.showsIssueDetail(_issueKey)) {
          failures.add(
            'Step 2 failed: returning from Project Settings did not reopen the $_issueKey issue detail surface. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(settingsRobot.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        if (!screen
            .buttonLabelsInIssueDetail(_issueKey)
            .contains('Attachments')) {
          failures.add(
            'Step 2 failed: the issue detail did not expose the visible "Attachments" tab after leaving Statuses. '
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
            'Step 3 failed: the Attachments tab did not render the storage restriction notice required for recovery navigation. '
            'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}. '
            'Visible semantics: ${_formatSnapshot(settingsRobot.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
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
                'Step 3 failed: the inline Attachments restriction notice did not keep "$text" visibly rendered before activation.',
              );
            }
          }

          if (!screen.showsAttachmentRow(_issueKey, _existingAttachmentName)) {
            failures.add(
              'Step 3 failed: the existing attachment row "$_existingAttachmentName" was not visible below the restriction notice. '
              'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
            );
          }

          if (!screen.showsAttachmentsRestrictionAction(
            _issueKey,
            title: _releaseRestrictionTitle,
            message: _releaseRestrictionMessage,
            actionLabel: _openSettingsLabel,
          )) {
            failures.add(
              'Step 4 failed: the inline restriction notice did not expose the "$_openSettingsLabel" recovery action.',
            );
          } else {
            await screen.tapAttachmentsRestrictionAction(
              _issueKey,
              title: _releaseRestrictionTitle,
              message: _releaseRestrictionMessage,
              actionLabel: _openSettingsLabel,
            );

            if (settingsRobot.showsModalDialog()) {
              failures.add(
                'Step 4 failed: tapping "$_openSettingsLabel" opened a modal instead of navigating back to Project Settings. '
                'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
              );
            }
            if (!settingsRobot.showsProjectSettingsSurface()) {
              failures.add(
                'Step 4 failed: tapping "$_openSettingsLabel" did not navigate to the visible Project Settings surface. '
                'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
              );
            }
            if (!settingsRobot.showsProjectSettingsTab('Attachments')) {
              failures.add(
                'Step 4 failed: Project Settings did not expose the visible "Attachments" tab after tapping "$_openSettingsLabel". '
                'Visible texts: ${_formatSnapshot(settingsRobot.visibleTexts())}.',
              );
            }
            if (!settingsRobot.showsAttachmentStorageModeSetting()) {
              failures.add(
                'Step 4 failed: the recovery navigation returned to Project Settings without activating the Attachments sub-tab. '
                'Expected to see the visible "Attachment storage mode" configuration, but visible texts were ${_formatSnapshot(settingsRobot.visibleTexts())}.',
              );
            }
            if (settingsRobot.isVisibleText('Add status')) {
              failures.add(
                'Human-style verification failed: after tapping "$_openSettingsLabel", the screen still showed the visible "Add status" control from the previously selected Statuses tab instead of only the Attachments configuration. '
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
