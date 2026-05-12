import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../core/interfaces/readiness_state_accessibility_screen.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/models/loading_banner_theme_observation.dart';
import 'readiness_state_accessibility_robot.dart';

class ReadinessStateAccessibilityScreen
    implements ReadinessStateAccessibilityScreenHandle {
  ReadinessStateAccessibilityScreen({
    required TrackStateAppComponent app,
    required ReadinessStateAccessibilityRobot robot,
    required TrackStateRepository repository,
  }) : _app = app,
       _robot = robot,
       _repository = repository;

  final TrackStateAppComponent _app;
  final ReadinessStateAccessibilityRobot _robot;
  final TrackStateRepository _repository;

  @override
  Future<void> launch() async {
    await _app.pump(_repository);
  }

  @override
  List<String> visibleTexts() => _app.visibleTextsSnapshot();

  @override
  List<String> visibleSemanticsLabels() =>
      _app.visibleSemanticsLabelsSnapshot();

  @override
  Future<void> openSection(String label) => _app.openSection(label);

  @override
  Future<void> openIssue(String key, String summary) =>
      _app.openIssue(key, summary);

  @override
  Future<void> waitWithoutInteraction(Duration duration) =>
      _app.waitWithoutInteraction(duration);

  @override
  List<String> visibleTextsWithinIssueDetail(String issueKey) =>
      _robot.visibleTextsWithinIssueDetail(issueKey);

  @override
  List<String> visibleSemanticsWithinIssueDetail(String issueKey) =>
      _robot.visibleSemanticsWithinIssueDetail(issueKey);

  @override
  LoadingBannerThemeObservation observeLoadingBanner(String semanticLabel) =>
      _robot.observeLoadingBanner(semanticLabel);

  @override
  LoadingBannerThemeObservation observeIssueDetailLoadingBanner(
    String issueKey, {
    required String semanticLabel,
  }) => _robot.observeIssueDetailLoadingBanner(
    issueKey,
    semanticLabel: semanticLabel,
  );

  @override
  void dispose() {
    _app.resetView();
  }
}
