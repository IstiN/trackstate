import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/core/trackstate_icons.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../core/models/issue_detail_icon_observation.dart';
import '../../core/models/issue_detail_row_style_observation.dart';
import '../../core/models/issue_detail_theme_tokens.dart';
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
  Future<void> enterCommentComposerText(String issueKey, String text) async {
    final field = _commentComposerField(issueKey);
    await tester.ensureVisible(field.first);
    await tester.tap(field.first, warnIfMissed: false);
    await tester.pump();
    await tester.enterText(field.first, text);
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
    final visitedLabels = <String>{};
    for (var index = 0; index < 18; index += 1) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
      final label = _focusedLabel(candidates);
      if (label != null) {
        order.add(label);
        visitedLabels.add(label);
        break;
      }
    }

    for (var index = 0; index < candidates.length * 2; index += 1) {
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
      await tester.pump();
      final label = _focusedLabel(candidates);
      if (label != null) {
        order.add(label);
        visitedLabels.add(label);
      }
      if (visitedLabels.length == candidates.length) {
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
  bool showsAttachmentsRestrictionCallout(
    String issueKey, {
    required String title,
    required String message,
  }) => _attachmentsRestrictionCallout(
    issueKey,
    title: title,
    message: message,
  ).evaluate().isNotEmpty;

  @override
  bool attachmentsRestrictionCalloutShowsText(
    String issueKey, {
    required String title,
    required String message,
    required String text,
  }) {
    final callout = _attachmentsRestrictionCallout(
      issueKey,
      title: title,
      message: message,
    );
    if (callout.evaluate().isEmpty) {
      return false;
    }
    return find
        .descendant(of: callout, matching: find.text(text, findRichText: true))
        .evaluate()
        .isNotEmpty;
  }

  @override
  bool attachmentsRestrictionCalloutIsInline(
    String issueKey, {
    required String tabLabel,
    required String title,
    required String message,
  }) {
    final callout = _attachmentsRestrictionCallout(
      issueKey,
      title: title,
      message: message,
    );
    final tab = _collaborationTab(issueKey, tabLabel);
    if (callout.evaluate().isEmpty || tab.evaluate().isEmpty) {
      return false;
    }
    final tabBottom = tester.getBottomLeft(tab.first).dy;
    final calloutTop = tester.getTopLeft(callout.first).dy;
    return calloutTop > tabBottom;
  }

  @override
  bool showsAttachmentRow(String issueKey, String attachmentName) =>
      _attachmentRow(issueKey, attachmentName).evaluate().isNotEmpty;

  @override
  bool attachmentRowIsBelowAttachmentsRestrictionCallout(
    String issueKey, {
    required String title,
    required String message,
    required String attachmentName,
  }) {
    final callout = _attachmentsRestrictionCallout(
      issueKey,
      title: title,
      message: message,
    );
    final attachmentRow = _attachmentRow(issueKey, attachmentName);
    if (callout.evaluate().isEmpty || attachmentRow.evaluate().isEmpty) {
      return false;
    }
    final calloutBottom = tester.getBottomLeft(callout.first).dy;
    final rowTop = tester.getTopLeft(attachmentRow.first).dy;
    return rowTop > calloutBottom;
  }

  @override
  bool showsAttachmentsRestrictionAction(
    String issueKey, {
    required String title,
    required String message,
    required String actionLabel,
  }) {
    final action = _attachmentsRestrictionAction(
      issueKey,
      title: title,
      message: message,
      actionLabel: actionLabel,
    );
    return action.evaluate().isNotEmpty;
  }

  @override
  Future<void> tapAttachmentsRestrictionAction(
    String issueKey, {
    required String title,
    required String message,
    required String actionLabel,
  }) async {
    final action = _attachmentsRestrictionAction(
      issueKey,
      title: title,
      message: message,
      actionLabel: actionLabel,
    );
    if (action.evaluate().isEmpty) {
      throw StateError(
        'No "$actionLabel" action was rendered inside the "$title" restriction callout for issue detail $issueKey.',
      );
    }
    await tester.ensureVisible(action.first);
    await tester.tap(action.first, warnIfMissed: false);
    await tester.pumpAndSettle();
  }

  @override
  String? commentComposerPlaceholderText(String issueKey) {
    final decoration = _commentComposerDecoration(issueKey);
    final placeholder = decoration.hintText?.trim();
    if (placeholder == null || placeholder.isEmpty) {
      return null;
    }
    return placeholder;
  }

  @override
  String? readCommentComposerText(String issueKey) {
    final field = _commentComposerField(issueKey);
    final widget = tester.widget<TextField>(field.first);
    final controller = widget.controller;
    if (controller != null) {
      return controller.text;
    }

    final editableText = find.descendant(
      of: field.first,
      matching: find.byType(EditableText),
    );
    if (editableText.evaluate().isNotEmpty) {
      return tester.widget<EditableText>(editableText.first).controller.text;
    }

    return null;
  }

  @override
  IssueDetailThemeTokens themeTokens(String issueKey) {
    final colors = _trackStateColors(issueKey);
    return IssueDetailThemeTokens(
      textHex: _rgbHex(colors.text),
      mutedHex: _rgbHex(colors.muted),
      errorHex: _rgbHex(colors.error),
      surfaceAltHex: _rgbHex(colors.surfaceAlt),
      borderHex: _rgbHex(colors.border),
    );
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
  IssueDetailTextContrastObservation observeCommentComposerEnteredTextContrast(
    String issueKey, {
    required String text,
  }) {
    final foreground = _editableTextColor(_commentComposerField(issueKey));
    final background = _commentComposerBackgroundColor(issueKey);
    return IssueDetailTextContrastObservation(
      text: text,
      foregroundHex: _rgbHex(foreground),
      backgroundHex: _rgbHex(background),
      contrastRatio: contrastRatio(foreground, background),
    );
  }

  @override
  IssueDetailTextContrastObservation observeCommentComposerPlaceholderContrast(
    String issueKey,
  ) {
    final placeholder = commentComposerPlaceholderText(issueKey);
    if (placeholder == null) {
      throw StateError(
        'No comment composer placeholder (hintText) was rendered for issue detail $issueKey.',
      );
    }
    final field = _commentComposerField(issueKey);
    final foreground = _renderedTextColorWithin(field, placeholder);
    final background = _commentComposerBackgroundColor(issueKey);
    return IssueDetailTextContrastObservation(
      text: placeholder,
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

  Finder _commentComposerField(String issueKey) {
    final field = find.descendant(
      of: _issueDetail(issueKey),
      matching: find.byWidgetPredicate((widget) {
        return widget is TextField &&
            widget.decoration?.labelText == 'Comments';
      }, description: 'comment composer text field'),
    );
    if (field.evaluate().isEmpty) {
      throw StateError(
        'No comment composer TextField labeled "Comments" was rendered in issue detail $issueKey.',
      );
    }
    return field.first;
  }

  Finder _attachmentsRestrictionCallout(
    String issueKey, {
    required String title,
    required String message,
  }) => find.ancestor(
    of: find.descendant(
      of: _issueDetail(issueKey),
      matching: find.text(title, findRichText: true),
    ),
    matching: find.byWidgetPredicate((widget) {
      if (widget is! Semantics) {
        return false;
      }
      final label = widget.properties.label ?? '';
      return label.contains(title) && label.contains(message);
    }, description: 'attachments restriction callout "$title"'),
  );

  Finder _attachmentsRestrictionAction(
    String issueKey, {
    required String title,
    required String message,
    required String actionLabel,
  }) {
    final callout = _attachmentsRestrictionCallout(
      issueKey,
      title: title,
      message: message,
    );
    if (callout.evaluate().isEmpty) {
      return find.byWidgetPredicate(
        (_) => false,
        description: 'missing attachments restriction action "$actionLabel"',
      );
    }
    final outlinedButton = find.descendant(
      of: callout,
      matching: find.widgetWithText(OutlinedButton, actionLabel),
    );
    if (outlinedButton.evaluate().isNotEmpty) {
      return outlinedButton.first;
    }
    final filledButton = find.descendant(
      of: callout,
      matching: find.widgetWithText(FilledButton, actionLabel),
    );
    if (filledButton.evaluate().isNotEmpty) {
      return filledButton.first;
    }
    return find.descendant(
      of: callout,
      matching: find.text(actionLabel, findRichText: true),
    );
  }

  Finder _attachmentRow(String issueKey, String attachmentName) =>
      find.descendant(
        of: _issueDetail(issueKey),
        matching: find.byWidgetPredicate((widget) {
          if (widget is! Semantics) {
            return false;
          }
          final label = widget.properties.label ?? '';
          return label.contains(attachmentName);
        }, description: 'attachment row for $attachmentName'),
      );

  InputDecoration _commentComposerDecoration(String issueKey) {
    final field = tester.widget<TextField>(_commentComposerField(issueKey));
    final decoration = field.decoration;
    if (decoration == null) {
      throw StateError(
        'The comment composer TextField in issue detail $issueKey did not expose an InputDecoration.',
      );
    }
    return decoration;
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

  Color _editableTextColor(Finder textField) {
    final editable = find.descendant(
      of: textField,
      matching: find.byType(EditableText),
    );
    if (editable.evaluate().isEmpty) {
      throw StateError('No EditableText found within $textField.');
    }
    return tester.widget<EditableText>(editable.first).style.color ??
        TrackStateColors.light.text;
  }

  Color _commentComposerBackgroundColor(String issueKey) {
    final field = _commentComposerField(issueKey);
    final element = field.evaluate().single;
    final widget = element.widget as TextField;
    final theme = Theme.of(element);
    return widget.decoration?.fillColor ??
        theme.inputDecorationTheme.fillColor ??
        (theme.extension<TrackStateColors>()?.surface ??
            TrackStateColors.light.surface);
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
