import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/issue_edit_accessibility_screen.dart';
import '../../core/models/issue_edit_text_contrast_observation.dart';
import '../../core/utils/local_trackstate_fixture.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'issue_edit_accessibility_robot.dart';

class IssueEditAccessibilityScreen
    implements IssueEditAccessibilityScreenHandle {
  IssueEditAccessibilityScreen({
    required this.tester,
    required TrackStateAppComponent app,
    required IssueEditAccessibilityRobot robot,
  }) : _app = app,
       _robot = robot;

  final WidgetTester tester;
  final TrackStateAppComponent _app;
  final IssueEditAccessibilityRobot _robot;

  LocalTrackStateFixture? _fixture;

  Future<void> launch() async {
    _fixture = await tester.runAsync(LocalTrackStateFixture.create);
    if (_fixture == null) {
      throw StateError('TS-402 fixture creation did not complete.');
    }

    await _app.pumpLocalGitApp(repositoryPath: _fixture!.repositoryPath);
    _app.expectLocalRuntimeChrome();
    await _app.openSection('JQL Search');
    await _app.expectIssueSearchResultVisible(
      LocalTrackStateFixture.issueKey,
      LocalTrackStateFixture.issueSummary,
    );
    await _app.openIssue(
      LocalTrackStateFixture.issueKey,
      LocalTrackStateFixture.issueSummary,
    );
    await _app.tapIssueDetailAction(
      LocalTrackStateFixture.issueKey,
      label: 'Edit',
    );
    _robot.expectEditIssueSurfaceVisible();
  }

  @override
  bool showsText(String text) => _robot.showsText(text);

  @override
  List<String> visibleTexts() => _robot.visibleTexts();

  @override
  List<String> visibleSemanticsLabels() => _robot.visibleSemanticsLabels();

  @override
  List<String> accessibilityFeedbackTexts() =>
      _robot.accessibilityFeedbackTexts();

  @override
  List<String> semanticsTraversal() => _robot.semanticsTraversal();

  @override
  Future<List<String>> collectForwardFocusOrder() =>
      _robot.collectForwardFocusOrder();

  @override
  Future<void> clearSummary() => _robot.clearSummary();

  @override
  Future<void> focusField(String label) => _robot.focusField(label);

  @override
  Future<String?> readLabeledTextFieldValue(String label) async =>
      _robot.readLabeledTextFieldValue(label);

  @override
  IssueEditTextContrastObservation observeSummaryPlaceholderContrast() =>
      _robot.observeSummaryPlaceholderContrast();

  @override
  Future<void> submit() => _robot.submit();

  @override
  String? focusedSemanticsLabel() => _robot.focusedSemanticsLabel();

  @override
  Future<void> dispose() async {
    await tester.runAsync(() async {
      if (_fixture != null) {
        await _fixture!.dispose();
      }
    });
    _app.resetView();
  }
}
