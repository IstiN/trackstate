import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/core/trackstate_icons.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../core/models/issue_detail_icon_observation.dart';
import '../../core/models/issue_detail_row_style_observation.dart';
import '../../core/models/issue_detail_text_contrast_observation.dart';
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

  @override
  Future<void> selectCollaborationTab(String issueKey, String label) async {
    final tab = _collaborationTab(issueKey, label);
    await tester.ensureVisible(tab.first);
    await tester.tap(tab.first, warnIfMissed: false);
    await tester.pumpAndSettle();
  }

  @override
  Future<List<String>> collectForwardCollaborationTabFocusOrder(
    String issueKey,
  ) async {
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pump();

    final candidates = <String, Finder>{
      for (final label in const [
        'Detail',
        'Comments',
        'Attachments',
        'History',
      ])
        label: _collaborationTab(issueKey, label),
    };

    final order = <String>[];
    for (var index = 0; index < 18; index += 1) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
      final label = _focusedLabel(candidates);
      if (label != null) {
        order.add(label);
        break;
      }
    }

    for (var index = 0; index < 6; index += 1) {
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
      await tester.pump();
      final label = _focusedLabel(candidates);
      if (label != null && (order.isEmpty || order.last != label)) {
        order.add(label);
      }
      if (order.length == 4) {
        break;
      }
    }

    return order;
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
  List<String> buttonLabelsInIssueDetail(String issueKey) {
    final rootLabel = 'Issue detail $issueKey';
    return _screenReaderTargets(
      issueKey,
      rootLabel,
    ).where((target) => target.isButton).map((target) => target.label).toList();
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

  @override
  IssueDetailTextContrastObservation observeDecoratedRowTextContrast(
    String issueKey, {
    required String rowAnchorText,
    required String text,
  }) {
    final row = _decoratedRow(issueKey, rowAnchorText);
    final foreground = _renderedTextColorWithin(row, text);
    final background = _renderedContainerBackground(row);
    return IssueDetailTextContrastObservation(
      text: text,
      foregroundHex: _rgbHex(foreground),
      backgroundHex: _rgbHex(background),
      contrastRatio: contrastRatio(foreground, background),
    );
  }

  @override
  IssueDetailRowStyleObservation observeDecoratedRowStyle(
    String issueKey, {
    required String rowAnchorText,
  }) {
    final row = _decoratedRow(issueKey, rowAnchorText);
    final background = _renderedContainerBackground(row);
    final border = _renderedContainerBorder(row);
    final colors = _trackStateColors(issueKey);
    return IssueDetailRowStyleObservation(
      anchorText: rowAnchorText,
      backgroundHex: _rgbHex(background),
      expectedBackgroundHex: _rgbHex(colors.surfaceAlt),
      borderHex: _rgbHex(border),
      expectedBorderHex: _rgbHex(colors.border),
    );
  }

  @override
  IssueDetailIconObservation observeDecoratedRowIcon(
    String issueKey, {
    required String rowAnchorText,
    required String semanticLabel,
  }) {
    final row = _decoratedRow(issueKey, rowAnchorText);
    final icon = _trackStateIconWithin(row, semanticLabel);
    final widget = tester.widget<TrackStateIcon>(icon);
    final colors = _trackStateColors(issueKey);
    final foreground = widget.color ?? colors.text;
    final background = _renderedContainerBackground(row);
    return IssueDetailIconObservation(
      semanticLabel: semanticLabel,
      glyphName: widget.glyph.name,
      filled: widget.filled,
      foregroundHex: _rgbHex(foreground),
      expectedForegroundHex: _rgbHex(colors.text),
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

  Finder _collaborationTab(String issueKey, String label) {
    final semantics = find.descendant(
      of: _issueDetail(issueKey),
      matching: find.byWidgetPredicate((widget) {
        if (widget is! Semantics) {
          return false;
        }
        return widget.properties.label == label &&
            widget.properties.button == true;
      }, description: 'collaboration tab $label'),
    );
    if (semantics.evaluate().isNotEmpty) {
      return semantics;
    }

    return find.descendant(
      of: _issueDetail(issueKey),
      matching: find.ancestor(
        of: find.text(label, findRichText: true),
        matching: find.byType(TextButton),
      ),
    );
  }

  String? _focusedLabel(Map<String, Finder> candidates) {
    final focusedSemantics = find.semantics.byPredicate(
      (node) => node.getSemanticsData().flagsCollection.isFocused,
      describeMatch: (_) => 'focused semantics node',
    );
    if (focusedSemantics.evaluate().isEmpty) {
      return null;
    }

    for (final entry in candidates.entries) {
      final exactFocusedMatch = find.semantics.byPredicate(
        (node) =>
            node.getSemanticsData().flagsCollection.isFocused &&
            _normalizedLabel(node.label) == entry.key,
        describeMatch: (_) => 'focused semantics labeled ${entry.key}',
      );
      if (exactFocusedMatch.evaluate().isNotEmpty) {
        return entry.key;
      }

      final matches = entry.value.evaluate().length;
      if (matches == 0) {
        continue;
      }
      for (var index = 0; index < matches; index += 1) {
        final candidateSemantics = _semanticsFinderFor(entry.value.at(index));
        final ownsFocusedNode = find.semantics.descendant(
          of: candidateSemantics,
          matching: focusedSemantics,
          matchRoot: true,
        );
        if (ownsFocusedNode.evaluate().isNotEmpty) {
          return entry.key;
        }
      }
    }
    return null;
  }

  FinderBase<SemanticsNode> _semanticsFinderFor(Finder finder) {
    final semanticsId = tester.getSemantics(finder).id;
    return find.semantics.byPredicate(
      (node) => node.id == semanticsId,
      describeMatch: (_) => 'semantics node for $finder',
    );
  }

  Finder _decoratedRow(String issueKey, String anchorText) {
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
      }, description: 'decorated issue detail row'),
    );

    Finder? bestMatch;
    double? smallestArea;
    final anchorTexts = find.descendant(
      of: _issueDetail(issueKey),
      matching: find.text(anchorText, findRichText: true),
    );
    final anchorCount = anchorTexts.evaluate().length;
    for (var anchorIndex = 0; anchorIndex < anchorCount; anchorIndex++) {
      final anchor = anchorTexts.at(anchorIndex);
      final ancestors = find.ancestor(
        of: anchor,
        matching: decoratedContainers,
      );
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
        'No decorated issue-detail row found for "$anchorText" in issue detail $issueKey.',
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
    return _renderedContainerBackground(scope);
  }

  Color _renderedContainerBackground(Finder scope) {
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

  Color _renderedContainerBorder(Finder scope) {
    for (final element in scope.evaluate()) {
      final widget = element.widget;
      if (widget is! Container) {
        continue;
      }
      final decoration = widget.decoration;
      if (decoration is! BoxDecoration) {
        continue;
      }
      final border = decoration.border;
      if (border is Border) {
        return border.top.color;
      }
    }
    throw StateError('No rendered container border found within $scope.');
  }

  Finder _trackStateIconWithin(Finder scope, String semanticLabel) {
    final icon = find.descendant(
      of: scope,
      matching: find.byWidgetPredicate((widget) {
        if (widget is! TrackStateIcon) {
          return false;
        }
        return widget.semanticLabel == semanticLabel;
      }, description: 'TrackStateIcon labeled $semanticLabel'),
    );

    if (icon.evaluate().isEmpty) {
      throw StateError(
        'No icon semantics labeled "$semanticLabel" found within $scope.',
      );
    }
    return icon.first;
  }

  TrackStateColors _trackStateColors(String issueKey) {
    final element = _issueDetail(issueKey).first.evaluate().single;
    return Theme.of(element).extension<TrackStateColors>() ??
        TrackStateColors.light;
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
