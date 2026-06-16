import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../testing/fixtures/issue_detail_accessibility_screen_fixture.dart';

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'issue detail exposes a writable Comments action and disables it when the hosted session is read-only',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        final writableScreen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'write-enabled-token',
          },
        );

        await writableScreen.openSearch();
        await writableScreen.selectIssue(_issueKey, _issueSummary);

        final writableComments = writableScreen.attachmentAction(
          _issueKey,
          'Comment',
        );
        expect(writableComments.visible, isTrue);
        expect(writableComments.enabled, isTrue);

        await writableScreen.tapIssueDetailAction(_issueKey, 'Comment');
        expect(writableScreen.showsCommentComposer(_issueKey), isTrue);

        final readOnlyScreen = await launchIssueDetailAccessibilityFixture(
          tester,
          repository: ReactiveIssueDetailTrackStateRepository(
            permission: const RepositoryPermission(
              canRead: true,
              canWrite: false,
              isAdmin: false,
              canCreateBranch: false,
              canManageAttachments: false,
              canCheckCollaborators: false,
            ),
          ),
          sharedPreferences: const <String, Object>{
            _hostedTokenKey: 'read-only-token',
          },
        );

        await readOnlyScreen.openSearch();
        await readOnlyScreen.selectIssue(_issueKey, _issueSummary);

        final readOnlyComments = readOnlyScreen.attachmentAction(
          _issueKey,
          'Comment',
        );
        expect(readOnlyComments.visible, isTrue);
        expect(readOnlyComments.enabled, isFalse);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );
}
