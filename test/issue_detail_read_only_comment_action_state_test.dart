import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import '../testing/fixtures/read_only_issue_detail_screen_fixture.dart';

const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets(
    'issue detail page object resolves the capability-gated Comment action before the Comments tab',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        final writableScreen = await launchWritableIssueDetailFixture(tester);
        await writableScreen.openSearch();
        await writableScreen.selectIssue(_issueKey, _issueSummary);

        final writableComment = writableScreen.commentAction(_issueKey);
        expect(writableComment.visible, isTrue);
        expect(writableComment.enabled, isTrue);

        writableScreen.dispose();

        final readOnlyScreen = await launchReadOnlyIssueDetailFixture(tester);
        await readOnlyScreen.openSearch();
        await readOnlyScreen.selectIssue(_issueKey, _issueSummary);

        final readOnlyComment = readOnlyScreen.commentAction(_issueKey);
        expect(readOnlyComment.visible, isTrue);
        expect(readOnlyComment.enabled, isFalse);

        readOnlyScreen.dispose();
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
