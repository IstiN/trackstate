import 'dart:ui' show Rect;

import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/create_issue_accessibility_screen.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/models/create_issue_layout_observation.dart';
import '../../core/models/create_issue_scroll_observation.dart';
import '../../core/models/create_issue_text_contrast_observation.dart';
import '../../core/utils/local_trackstate_fixture.dart';
import 'create_issue_accessibility_robot.dart';

class CreateIssueAccessibilityScreen
    implements CreateIssueAccessibilityScreenHandle {
  CreateIssueAccessibilityScreen({
    required this.tester,
    required TrackStateAppComponent app,
    required CreateIssueAccessibilityRobot robot,
  }) : _app = app,
       _robot = robot;

  final WidgetTester tester;
  final TrackStateAppComponent _app;
  final CreateIssueAccessibilityRobot _robot;

  LocalTrackStateFixture? _fixture;
  String? _createIssueSection;

  Future<void> launch({
    double? initialViewportWidth,
    double? initialViewportHeight,
  }) async {
    _fixture = await tester.runAsync(LocalTrackStateFixture.create);
    if (_fixture == null) {
      throw StateError('TS-307 fixture creation did not complete.');
    }

    await _app.pumpLocalGitApp(repositoryPath: _fixture!.repositoryPath);
    _app.expectLocalRuntimeChrome();
    if (initialViewportWidth != null || initialViewportHeight != null) {
      if (initialViewportWidth == null || initialViewportHeight == null) {
        throw ArgumentError(
          'Both initialViewportWidth and initialViewportHeight are required together.',
        );
      }
      await _robot.resizeToViewport(
        width: initialViewportWidth,
        height: initialViewportHeight,
      );
    }
    _createIssueSection = await _app.openCreateIssueFlow();
    await _expectCreateIssueFormVisible();
    _robot.expectCreateIssueSurfaceVisible();
  }

  @override
  Finder get goldenTarget => _app.goldenTarget;

  @override
  bool showsText(String text) => _robot.showsText(text);

  @override
  List<String> visibleTexts() => _robot.visibleTexts();

  @override
  List<String> visibleSemanticsLabels() =>
      _app.visibleSemanticsLabelsSnapshot();

  @override
  CreateIssueLayoutObservation observeLayout() => _robot.observeLayout();

  @override
  CreateIssueScrollObservation observeVerticalScroll() =>
      _robot.observeVerticalScroll();

  @override
  List<String> semanticsTraversal() => _robot.semanticsTraversal();

  @override
  CreateIssueTextContrastObservation observeTextContrast(String text) =>
      _robot.observeTextContrast(text);

  @override
  Future<void> populateCreateIssueForm({
    required String summary,
    String? description,
  }) async {
    await _app.populateCreateIssueForm(
      summary: summary,
      description: description,
    );
  }

  @override
  Future<String?> readLabeledTextFieldValue(String label) async =>
      _robot.readLabeledTextFieldValue(label);

  @override
  Rect? observeLabeledTextFieldRect(String label) =>
      _robot.observeLabeledTextFieldRect(label);

  @override
  Rect? observeControlRect(String label) => _robot.observeControlRect(label);

  @override
  bool isTextVisibleInViewport(String text) =>
      _robot.isTextVisibleInViewport(text);

  @override
  Future<void> resizeToViewport({
    required double width,
    required double height,
  }) async {
    await _robot.resizeToViewport(width: width, height: height);
    await _expectCreateIssueFormVisible();
    _robot.expectCreateIssueSurfaceVisible();
  }

  @override
  Future<void> submitCreateIssue() async {
    final createIssueSection = _createIssueSection;
    if (createIssueSection == null) {
      throw StateError(
        'The Create issue flow was not opened before submission.',
      );
    }
    await _app.submitCreateIssue(createIssueSection: createIssueSection);
  }

  @override
  Future<void> waitWithoutInteraction(Duration duration) =>
      _app.waitWithoutInteraction(duration);

  @override
  Future<void> scrollToBottom() => _robot.scrollToBottom();

  @override
  Future<void> scrollToTop() => _robot.scrollToTop();

  @override
  Future<void> dispose() async {
    await tester.runAsync(() async {
      if (_fixture != null) {
        await _fixture!.dispose();
      }
    });
    _app.resetView();
  }

  Future<void> _expectCreateIssueFormVisible() {
    final createIssueSection = _createIssueSection;
    if (createIssueSection == null) {
      throw StateError(
        'The Create issue flow was not opened before validation.',
      );
    }
    return _app.expectCreateIssueFormVisible(
      createIssueSection: createIssueSection,
    );
  }
}
