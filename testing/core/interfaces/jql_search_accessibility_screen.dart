import '../models/jql_search_button_style_observation.dart';

abstract interface class JqlSearchAccessibilityScreenHandle {
  Future<void> openSearch();

  List<String> visibleTexts();

  List<String> semanticsTraversal();

  int countExactSemanticsLabel(String label);

  Future<List<String>> collectForwardFocusOrder();

  Future<List<String>> collectBackwardFocusOrder();

  JqlSearchButtonStyleObservation observeLoadMoreButtonIdle();

  JqlSearchButtonStyleObservation observeLoadMoreButtonHovered();

  JqlSearchButtonStyleObservation observeLoadMoreButtonFocused();
}
