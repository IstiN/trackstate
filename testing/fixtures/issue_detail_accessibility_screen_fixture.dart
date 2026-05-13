import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/services/attachment_picker.dart';

import '../core/interfaces/issue_detail_accessibility_screen.dart';
import '../frameworks/flutter/issue_detail_accessibility_widget_framework.dart';

Future<IssueDetailAccessibilityScreenHandle>
launchIssueDetailAccessibilityFixture(
  WidgetTester tester, {
  TrackStateRepository repository = const DemoTrackStateRepository(),
  Map<String, Object> sharedPreferences = const <String, Object>{},
  AttachmentPicker attachmentPicker = pickAttachmentWithFileSelector,
}) {
  return launchIssueDetailAccessibilityWidgetScreen(
    tester,
    repository: repository,
    sharedPreferences: sharedPreferences,
    attachmentPicker: attachmentPicker,
  );
}
