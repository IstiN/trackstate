import 'package:flutter/material.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

abstract interface class LoadingStateVisualQualityScreenHandle {
  List<String> visibleTexts();

  List<String> visibleSemanticsLabels();

  Future<void> openJqlSearch();

  int loadingRowCount();

  Future<List<String>> collectLoadingFocusVisits({required int tabs});

  TrackStateColors colors();

  Color resolveTopBarButtonBackground(String label, Set<WidgetState> states);

  bool isNavigationSelected(String label);

  Color? navigationBackgroundColor(String label);

  Color navigationTextColor(String label);

  Color loadingBannerTextColor();

  Color firstLoadingPillTextColor();

  Color topBarPlaceholderTextColor();

  Color topBarEnteredTextColor();

  void dispose();
}
