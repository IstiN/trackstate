import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

import '../../core/models/loading_banner_theme_observation.dart';
import '../../core/utils/color_contrast.dart';

class ReadinessStateAccessibilityRobot {
  ReadinessStateAccessibilityRobot(this.tester);

  final WidgetTester tester;

  List<String> visibleTextsWithinIssueDetail(String issueKey) =>
      _visibleTextsWithin(_issueDetail(issueKey));

  List<String> visibleSemanticsWithinIssueDetail(String issueKey) =>
      _visibleSemanticsWithin(_issueDetail(issueKey));

  LoadingBannerThemeObservation observeLoadingBanner(String semanticLabel) {
    return _observeLoadingBanner(semanticLabel: semanticLabel, within: null);
  }

  LoadingBannerThemeObservation observeIssueDetailLoadingBanner(
    String issueKey, {
    required String semanticLabel,
  }) {
    return _observeLoadingBanner(
      semanticLabel: semanticLabel,
      within: _issueDetail(issueKey),
    );
  }

  LoadingBannerThemeObservation _observeLoadingBanner({
    required String semanticLabel,
    required Finder? within,
  }) {
    final scope = _semanticsScope(semanticLabel, within: within);
    expect(
      scope,
      findsAtLeastNWidgets(1),
      reason: 'Expected to find a loading banner labeled "$semanticLabel".',
    );

    final foreground = _renderedTextColorWithin(scope.first, 'Loading...');
    final background = _largestColoredContainerBackground(scope.first);
    final colors = _trackStateColors(scope.first);
    return LoadingBannerThemeObservation(
      semanticLabel: semanticLabel,
      renderedForegroundHex: _rgbHex(foreground),
      expectedForegroundHex: _rgbHex(colors.muted),
      renderedBackgroundHex: _rgbHex(background),
      expectedBackgroundHex: _rgbHex(colors.surfaceAlt),
      contrastRatio: contrastRatio(foreground, background),
    );
  }

  Finder _issueDetail(String issueKey) {
    final label = 'Issue detail $issueKey';
    return find.byWidgetPredicate((widget) {
      return widget is Semantics && widget.properties.label == label;
    }, description: 'Semantics widget labeled $label');
  }

  Finder _semanticsScope(String label, {Finder? within}) {
    final finder = find.byWidgetPredicate((widget) {
      return widget is Semantics && widget.properties.label == label;
    }, description: 'Semantics widget labeled $label');
    return within == null
        ? finder
        : find.descendant(of: within, matching: finder);
  }

  TrackStateColors _trackStateColors(Finder scope) {
    final element = scope.evaluate().first;
    return Theme.of(element).extension<TrackStateColors>() ??
        TrackStateColors.light;
  }

  Color _renderedTextColorWithin(Finder scope, String text) {
    final richTextFinder = find.descendant(
      of: scope,
      matching: find.byType(RichText),
    );
    for (final element in richTextFinder.evaluate()) {
      final widget = element.widget as RichText;
      if (widget.text.toPlainText().trim() != text) {
        continue;
      }
      final color =
          widget.text.style?.color ?? DefaultTextStyle.of(element).style.color;
      if (color != null) {
        return color;
      }
    }

    final textFinder = find.descendant(
      of: scope,
      matching: find.text(text, findRichText: true),
    );
    for (final element in textFinder.evaluate()) {
      final widget = element.widget;
      if (widget is! Text) {
        continue;
      }
      final color =
          widget.style?.color ?? DefaultTextStyle.of(element).style.color;
      if (color != null) {
        return color;
      }
    }

    throw StateError('No rendered text "$text" found within $scope.');
  }

  Color _largestColoredContainerBackground(Finder scope) {
    final containers = find.descendant(
      of: scope,
      matching: find.byType(Container),
    );
    Color? bestColor;
    double bestArea = -1;
    final matches = containers.evaluate().length;
    for (var index = 0; index < matches; index += 1) {
      final candidate = containers.at(index);
      final widget = tester.widget<Container>(candidate);
      final decoration = widget.decoration;
      if (decoration is! BoxDecoration || decoration.color == null) {
        continue;
      }
      final rect = tester.getRect(candidate);
      final area = rect.width * rect.height;
      if (area > bestArea) {
        bestArea = area;
        bestColor = decoration.color;
      }
    }
    if (bestColor == null) {
      throw StateError('No colored container was found within $scope.');
    }
    return bestColor;
  }

  List<String> _visibleTextsWithin(Finder scope) {
    return tester
        .widgetList<Text>(
          find.descendant(of: scope, matching: find.byType(Text)),
        )
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList();
  }

  List<String> _visibleSemanticsWithin(Finder scope) {
    return tester
        .widgetList<Semantics>(
          find.descendant(of: scope, matching: find.byType(Semantics)),
        )
        .map((widget) => widget.properties.label?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList();
  }

  String _rgbHex(Color color) {
    final rgb = color.toARGB32() & 0x00FFFFFF;
    return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
  }
}
