import 'package:flutter/material.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

import '../../core/interfaces/loading_state_visual_quality_screen.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'loading_state_visual_quality_robot.dart';

class LoadingStateVisualQualityScreen
    implements LoadingStateVisualQualityScreenHandle {
  LoadingStateVisualQualityScreen({
    required TrackStateAppComponent app,
    required LoadingStateVisualQualityRobot robot,
    required TrackStateRepository repository,
  }) : _app = app,
       _robot = robot,
       _repository = repository;

  final TrackStateAppComponent _app;
  final LoadingStateVisualQualityRobot _robot;
  final TrackStateRepository _repository;

  Future<void> launch() async {
    await _app.pump(_repository);
  }

  @override
  List<String> visibleTexts() => _app.visibleTextsSnapshot();

  @override
  List<String> visibleSemanticsLabels() => _robot.visibleSemanticsLabels();

  @override
  Future<void> openJqlSearch() async {
    await _app.openSection('JQL Search');
    await _robot.waitForJqlSearchLoadingState();
  }

  @override
  int loadingRowCount() => _robot.loadingRowCount();

  @override
  Future<List<String>> collectLoadingFocusVisits({required int tabs}) {
    return _robot.collectLoadingFocusVisits(tabs: tabs);
  }

  @override
  TrackStateColors colors() => _robot.colors();

  @override
  Color resolveTopBarButtonBackground(String label, Set<WidgetState> states) {
    return _robot.resolveTopBarButtonBackground(label, states);
  }

  @override
  bool isNavigationSelected(String label) => _robot.isNavigationSelected(label);

  @override
  Color? navigationBackgroundColor(String label) {
    return _robot.navigationBackgroundColor(label);
  }

  @override
  Color navigationTextColor(String label) => _robot.navigationTextColor(label);

  @override
  Color loadingBannerTextColor() => _robot.loadingBannerTextColor();

  @override
  Color firstLoadingPillTextColor() => _robot.firstLoadingPillTextColor();

  @override
  Color topBarPlaceholderTextColor() => _robot.topBarPlaceholderTextColor();

  @override
  Color topBarEnteredTextColor() => _robot.topBarEnteredTextColor();

  @override
  void dispose() {
    _app.resetView();
  }
}
