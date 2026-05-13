import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../testing/components/screens/settings_screen_robot.dart';
import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../testing/fixtures/issue_detail_accessibility_screen_fixture.dart';

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _restrictionTitle = 'Attachments stay download-only in the browser';
const String _restrictionMessage =
    'Attachment upload is unavailable in this browser session. Existing attachments remain available for download.';
const String _openSettingsLabel = 'Open settings';
const String _attachmentName = 'sync-sequence.svg';
const String _downloadAttachmentLabel = 'Download sync-sequence.svg';

const String _repositoryPathProjectJson = '''
{
  "key": "TRACK",
  "name": "TrackState.AI",
  "defaultLocale": "en",
  "issueKeyPattern": "TRACK-{number}",
  "dataModel": "nested-tree",
  "configPath": "config",
  "attachmentStorage": {
    "mode": "repository-path"
  }
}
''';

const RepositoryPermission _hostedRepositoryPathPermission =
    RepositoryPermission(
      canRead: true,
      canWrite: true,
      isAdmin: false,
      canCreateBranch: true,
      canManageAttachments: true,
      attachmentUploadMode: AttachmentUploadMode.noLfs,
      canCheckCollaborators: false,
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'hosted repository-path attachments stay download-only and route Open settings to Attachments settings',
    (tester) async {
      final settingsRobot = SettingsScreenRobot(tester);

      try {
        final screen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: _hostedRepositoryPathPermission,
            textFixtures: const <String, String>{
              'project.json': _repositoryPathProjectJson,
            },
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'repository-path-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);
        await screen.selectCollaborationTab(_issueKey, 'Attachments');

        expect(
          screen.showsAttachmentsRestrictionCallout(
            _issueKey,
            title: _restrictionTitle,
            message: _restrictionMessage,
          ),
          isTrue,
        );
        expect(
          screen.showsAttachmentsRestrictionAction(
            _issueKey,
            title: _restrictionTitle,
            message: _restrictionMessage,
            actionLabel: _openSettingsLabel,
          ),
          isTrue,
        );
        expect(screen.showsAttachmentRow(_issueKey, _attachmentName), isTrue);
        expect(
          screen.showsAttachmentAction(
            _issueKey,
            attachmentName: _attachmentName,
            actionLabel: _downloadAttachmentLabel,
          ),
          isTrue,
        );
        expect(
          find.widgetWithText(OutlinedButton, 'Choose attachment'),
          findsNothing,
        );
        expect(
          find.widgetWithText(FilledButton, 'Upload attachment'),
          findsNothing,
        );

        await screen.tapAttachmentsRestrictionAction(
          _issueKey,
          title: _restrictionTitle,
          message: _restrictionMessage,
          actionLabel: _openSettingsLabel,
        );

        expect(settingsRobot.showsProjectSettingsSurface(), isTrue);
        expect(settingsRobot.showsProjectSettingsTab('Attachments'), isTrue);
        expect(settingsRobot.showsAttachmentStorageModeSetting(), isTrue);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );
}
