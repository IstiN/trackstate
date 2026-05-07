import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/test_driver.dart';
import '../../core/models/action_availability.dart';

class WidgetTestDriver implements TestDriver {
  const WidgetTestDriver(this.tester);

  final WidgetTester tester;

  Future<void> pumpApp(Widget widget) async {
    await tester.pumpWidget(widget);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> tapSemanticsLabel(Pattern label) async {
    await tester.tap(find.bySemanticsLabel(label).first);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> tapText(String text) async {
    await tester.tap(find.text(text).first);
    await tester.pumpAndSettle();
  }

  @override
  bool hasText(String text) => find.text(text).evaluate().isNotEmpty;

  @override
  bool hasSemanticsLabel(Pattern label) =>
      find.bySemanticsLabel(label).evaluate().isNotEmpty;

  @override
  ActionAvailability getActionAvailability(String label) {
    final action = _findActionControl(label);
    if (action.evaluate().isEmpty) {
      return ActionAvailability(label: label, visible: false, enabled: false);
    }

    final enabled = _isActionEnabled(action.first);
    return ActionAvailability(label: label, visible: true, enabled: enabled);
  }

  @override
  bool hasAnyMessage(Iterable<Pattern> patterns) {
    for (final pattern in patterns) {
      final message = find.byWidgetPredicate((widget) {
        if (widget is Text) {
          final text = widget.data ?? widget.textSpan?.toPlainText();
          return text != null && _matchesPattern(text, pattern);
        }
        if (widget is SelectableText) {
          final text = widget.data ?? widget.textSpan?.toPlainText();
          return text != null && _matchesPattern(text, pattern);
        }
        if (widget is Tooltip) {
          final message = widget.message;
          return message != null && _matchesPattern(message, pattern);
        }
        return false;
      });
      if (message.evaluate().isNotEmpty) {
        return true;
      }
    }
    return false;
  }

  Finder _findActionControl(String label) {
    return find.byWidgetPredicate(
      (widget) =>
          widget is Semantics &&
          widget.properties.button == true &&
          widget.properties.label == label,
      description: 'button semantics labeled $label',
    );
  }

  bool _isActionEnabled(Finder action) {
    final filledButton = find.descendant(
      of: action,
      matching: find.byType(FilledButton),
    );
    if (filledButton.evaluate().isNotEmpty) {
      return tester.widget<FilledButton>(filledButton.first).onPressed != null;
    }

    final iconButton = find.descendant(
      of: action,
      matching: find.byType(IconButton),
    );
    if (iconButton.evaluate().isNotEmpty) {
      return tester.widget<IconButton>(iconButton.first).onPressed != null;
    }

    final inkWell = find.descendant(of: action, matching: find.byType(InkWell));
    if (inkWell.evaluate().isNotEmpty) {
      return tester.widget<InkWell>(inkWell.first).onTap != null;
    }

    return false;
  }

  bool _matchesPattern(String value, Pattern pattern) {
    if (pattern is RegExp) {
      return pattern.hasMatch(value);
    }
    return value.contains(pattern.toString());
  }
}
