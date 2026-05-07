import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../core/models/status_badge_contrast_observation.dart';
import '../../core/utils/color_contrast.dart';

class IssueDetailAccessibilityRobot
    implements IssueDetailAccessibilityScreenHandle {
  IssueDetailAccessibilityRobot(this.tester);

  final WidgetTester tester;

  @override
  Future<void> openSearch() async {
    await tester.tap(find.text('JQL Search').first);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> selectIssue(String issueKey, String issueSummary) async {
    final issueLink = find.bySemanticsLabel(
      RegExp('Open ${RegExp.escape(issueKey)} ${RegExp.escape(issueSummary)}'),
    );
    await tester.ensureVisible(issueLink.first);
    await tester.tap(issueLink.first);
    await tester.pumpAndSettle();
  }

  Finder _issueDetail(String issueKey) {
    final label = 'Issue detail $issueKey';
    return find.byWidgetPredicate((widget) {
      if (widget is! Semantics) {
        return false;
      }
      return widget.properties.label == label;
    }, description: 'Semantics widget labeled $label');
  }

  @override
  bool showsIssueDetail(String issueKey) =>
      _issueDetail(issueKey).evaluate().length == 1;

  @override
  List<String> visibleTextsWithinIssueDetail(String issueKey) {
    return tester
        .widgetList<Text>(
          find.descendant(
            of: _issueDetail(issueKey),
            matching: find.byType(Text),
          ),
        )
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList();
  }

  @override
  List<String> semanticsLabelsInIssueDetail(String issueKey) {
    final issueDetail = _issueDetail(issueKey);
    final rootLabel = 'Issue detail $issueKey';
    final targets = <_AccessibilityTarget>[];

    for (final element in find
        .descendant(of: issueDetail, matching: find.byType(Semantics))
        .evaluate()) {
      final widget = element.widget as Semantics;
      final label = _normalizedLabel(widget.properties.label);
      if (label.isEmpty || label == rootLabel) {
        continue;
      }
      targets.add(
        _AccessibilityTarget(
          label: label,
          rect: _rectFor(element),
          priority: 0,
        ),
      );
    }

    return _sortedLabels(targets);
  }

  @override
  List<String> semanticsLabelsInIssueDetailTraversal(String issueKey) {
    final issueDetail = _issueDetail(issueKey);
    final semanticsTargets = _accessibilityTargetsFromSemantics(issueKey);
    final traversalTargets = <_AccessibilityTarget>[...semanticsTargets];

    for (final element in find
        .descendant(of: issueDetail, matching: find.byType(RichText))
        .evaluate()) {
      final widget = element.widget as RichText;
      final label = _normalizedLabel(widget.text.toPlainText());
      if (label.isEmpty) {
        continue;
      }
      final rect = _rectFor(element);
      if (_isRepresentedByNearbySemanticsTarget(label, rect, semanticsTargets)) {
        continue;
      }
      traversalTargets.add(
        _AccessibilityTarget(label: label, rect: rect, priority: 1),
      );
    }

    return _sortedLabels(traversalTargets);
  }

  @override
  List<String> commentActionLabels(String issueKey) {
    final heading = find.descendant(
      of: _issueDetail(issueKey),
      matching: find.text('Comments'),
    );
    if (heading.evaluate().isEmpty) {
      return const [];
    }

    final commentsTop = tester.getRect(heading.first).top;
    final buttonFinders = find.descendant(
      of: _issueDetail(issueKey),
      matching: find.byWidgetPredicate(
        (widget) => widget is Semantics && widget.properties.button == true,
        description: 'button semantics',
      ),
    );
    final labels = <String>[];
    final count = buttonFinders.evaluate().length;
    for (var index = 0; index < count; index++) {
      final candidate = buttonFinders.at(index);
      if (tester.getRect(candidate).top <= commentsTop) {
        continue;
      }
      final label = tester.getSemantics(candidate).label.trim();
      if (label.isNotEmpty) {
        labels.add(label);
      }
    }
    return labels;
  }

  @override
  StatusBadgeContrastObservation observeStatusBadgeContrast(
    String issueKey,
    String label,
  ) {
    final badge = _statusBadge(issueKey, label);
    final foreground = _renderedTextColorWithin(badge, label);
    final background = _renderedBadgeBackground(badge);
    return StatusBadgeContrastObservation(
      label: label,
      foregroundHex: _rgbHex(foreground),
      backgroundHex: _rgbHex(background),
      contrastRatio: contrastRatio(foreground, background),
    );
  }

  Finder _statusBadge(String issueKey, String label) {
    final decoratedContainers = find.descendant(
      of: _issueDetail(issueKey),
      matching: find.byWidgetPredicate((widget) {
        if (widget is! Container) {
          return false;
        }
        final decoration = widget.decoration;
        return decoration is BoxDecoration &&
            decoration.color != null &&
            decoration.borderRadius != null;
      }, description: 'decorated badge container'),
    );

    Finder? bestMatch;
    double? smallestArea;
    final labelTexts = find.descendant(
      of: _issueDetail(issueKey),
      matching: find.text(label, findRichText: true),
    );
    final labelCount = labelTexts.evaluate().length;
    for (var labelIndex = 0; labelIndex < labelCount; labelIndex++) {
      final text = labelTexts.at(labelIndex);
      final ancestors = find.ancestor(of: text, matching: decoratedContainers);
      final ancestorCount = ancestors.evaluate().length;
      for (var index = 0; index < ancestorCount; index++) {
        final candidate = ancestors.at(index);
        final rect = tester.getRect(candidate);
        final area = rect.width * rect.height;
        if (smallestArea == null || area < smallestArea) {
          smallestArea = area;
          bestMatch = candidate;
        }
      }
    }

    if (bestMatch == null) {
      throw StateError(
        'No rendered status badge found for "$label" in issue detail $issueKey.',
      );
    }
    return bestMatch;
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

  Color _renderedBadgeBackground(Finder scope) {
    for (final element in scope.evaluate()) {
      final widget = element.widget;
      if (widget is! Container) {
        continue;
      }
      final decoration = widget.decoration;
      if (decoration is BoxDecoration && decoration.color != null) {
        return decoration.color!;
      }
    }
    throw StateError('No rendered badge background found within $scope.');
  }

  String _rgbHex(Color color) {
    final rgb = color.toARGB32() & 0x00FFFFFF;
    return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
  }

  List<_AccessibilityTarget> _accessibilityTargetsFromSemantics(
    String issueKey,
  ) {
    final issueDetail = _issueDetail(issueKey);
    final rootLabel = 'Issue detail $issueKey';
    final targets = <_AccessibilityTarget>[];

    for (final element in find
        .descendant(of: issueDetail, matching: find.byType(Semantics))
        .evaluate()) {
      final widget = element.widget as Semantics;
      final label = _normalizedLabel(widget.properties.label);
      if (label.isEmpty || label == rootLabel) {
        continue;
      }
      targets.add(
        _AccessibilityTarget(
          label: label,
          rect: _rectFor(element),
          priority: 0,
        ),
      );
    }

    return targets;
  }

  Rect _rectFor(Element element) {
    final renderObject = element.renderObject;
    if (renderObject is! RenderBox) {
      return Rect.zero;
    }
    final topLeft = renderObject.localToGlobal(Offset.zero);
    return topLeft & renderObject.size;
  }

  bool _isRepresentedByNearbySemanticsTarget(
    String label,
    Rect rect,
    List<_AccessibilityTarget> semanticsTargets,
  ) {
    for (final target in semanticsTargets) {
      if (target.label != label) {
        continue;
      }
      final topDelta = (target.rect.top - rect.top).abs();
      final leftDelta = (target.rect.left - rect.left).abs();
      if (target.rect.overlaps(rect) || (topDelta <= 24 && leftDelta <= 120)) {
        return true;
      }
    }
    return false;
  }

  List<String> _sortedLabels(List<_AccessibilityTarget> targets) {
    targets.sort((left, right) {
      final topOrder = left.rect.top.compareTo(right.rect.top);
      if (topOrder != 0) {
        return topOrder;
      }
      final leftOrder = left.rect.left.compareTo(right.rect.left);
      if (leftOrder != 0) {
        return leftOrder;
      }
      return left.priority.compareTo(right.priority);
    });

    final ordered = <String>[];
    for (final target in targets) {
      if (ordered.isNotEmpty && ordered.last == target.label) {
        continue;
      }
      ordered.add(target.label);
    }
    return ordered;
  }

  String _normalizedLabel(String? label) =>
      (label ?? '').replaceAll(RegExp(r'\s+'), ' ').trim();
}

class _AccessibilityTarget {
  const _AccessibilityTarget({
    required this.label,
    required this.rect,
    required this.priority,
  });

  final String label;
  final Rect rect;
  final int priority;
}
