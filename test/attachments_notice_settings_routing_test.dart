import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../testing/components/screens/settings_screen_robot.dart';
import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../testing/fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'attachments notice Open settings opens Project Settings on Attachments tab',
    (tester) async {
      final settingsRobot = SettingsScreenRobot(tester);

      try {
        final screen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: _releaseRestrictedPermission,
            textFixtures: const <String, String>{'project.json': _projectJson},
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'release-backed-token',
          },
        );

        await screen.openSearch();
        await screen.selectIssue(_issueKey, _issueSummary);
        await screen.selectCollaborationTab(_issueKey, 'Attachments');
        await screen.tapAttachmentsRestrictionAction(
          _issueKey,
          title: _restrictionTitle,
          message: _restrictionMessage,
          actionLabel: 'Open settings',
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

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _restrictionTitle =
    'GitHub Releases uploads are unavailable in the browser';
const String _restrictionMessage =
    'This project stores new attachments in GitHub Releases. Existing attachments remain available for download, but hosted release-backed uploads are not available in this browser session yet.';
const String _projectJson = '''
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
''';

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
