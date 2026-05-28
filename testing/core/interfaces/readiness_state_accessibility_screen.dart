import '../models/loading_banner_theme_observation.dart';

abstract interface class ReadinessStateAccessibilityScreenHandle {
  Future<void> launch();

  List<String> visibleTexts();

  List<String> visibleSemanticsLabels();

  Future<void> openSection(String label);

  Future<void> openIssue(String key, String summary);

  Future<void> waitWithoutInteraction(Duration duration);

  List<String> visibleTextsWithinIssueDetail(String issueKey);

  List<String> visibleSemanticsWithinIssueDetail(String issueKey);

  LoadingBannerThemeObservation observeLoadingBanner(String semanticLabel);

  LoadingBannerThemeObservation observeIssueDetailLoadingBanner(
    String issueKey, {
    required String semanticLabel,
  });

  void dispose();
}
