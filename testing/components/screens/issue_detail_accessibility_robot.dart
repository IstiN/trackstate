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
    final rootLabel = 'Issue detail $issueKey';
    return _screenReaderTargets(
      issueKey,
      rootLabel,
    ).map((target) => target.label).toList();
  }

  @override
  List<String> semanticsLabelsInIssueDetailTraversal(String issueKey) {
    final rootLabel = 'Issue detail $issueKey';
    return _dedupeConsecutive(
      _screenReaderTargets(
        issueKey,
        rootLabel,
      ).map((target) => target.label).toList(),
    );
  }

  @override
  List<String> commentActionLabels(String issueKey) {
    final rootLabel = 'Issue detail $issueKey';
    final targets = _screenReaderTargets(issueKey, rootLabel);
    final commentsIndex = targets.indexWhere(
      (target) => target.label == 'Comments',
    );
    if (commentsIndex == -1) {
      return const [];
    }
    return targets
        .skip(commentsIndex + 1)
        .where((target) => target.isButton)
        .map((target) => target.label)
        .toList();
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

  List<_SemanticsTarget> _screenReaderTargets(
    String issueKey,
    String rootLabel,
  ) {
    final rootNode = tester.getSemantics(_issueDetail(issueKey).first);
    final targets = <_SemanticsTarget>[];

    void visit(SemanticsNode node) {
      final children = node.debugListChildrenInOrder(
        DebugSemanticsDumpOrder.traversalOrder,
      );
      final label = _normalizedLabel(node.label);
      if (label.isNotEmpty &&
          label != rootLabel &&
          !node.isInvisible &&
          !node.isMergedIntoParent &&
          !_isMergedContainerLabel(label, children) &&
          (_isScreenReaderTarget(node) || children.isEmpty)) {
        targets.add(
          _SemanticsTarget(
            label: label,
            isButton: node.flagsCollection.isButton,
          ),
        );
      }
      for (final child in children) {
        visit(child);
      }
    }

    visit(rootNode);
    return targets;
  }

  bool _isScreenReaderTarget(SemanticsNode node) {
    return node.flagsCollection.isButton;
  }

  bool _isMergedContainerLabel(String label, List<SemanticsNode> children) {
    if (children.isEmpty) {
      return false;
    }

    var matchedChildLabels = 0;
    for (final child in children) {
      final childLabel = _normalizedLabel(child.label);
      if (childLabel.isEmpty ||
          childLabel == label ||
          !label.contains(childLabel)) {
        continue;
      }
      matchedChildLabels += 1;
      if (matchedChildLabels >= 2) {
        return true;
      }
    }
    return false;
  }

  List<String> _dedupeConsecutive(List<String> labels) {
    final ordered = <String>[];
    for (final label in labels) {
      if (ordered.isNotEmpty && ordered.last == label) {
        continue;
      }
      ordered.add(label);
    }
    return ordered;
  }

  String _normalizedLabel(String? label) =>
      (label ?? '').replaceAll(RegExp(r'\s+'), ' ').trim();
}

class _SemanticsTarget {
  const _SemanticsTarget({required this.label, required this.isButton});

  final String label;
  final bool isButton;
}
