import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class WidgetTestDriver {
  const WidgetTestDriver(this.tester);

  final WidgetTester tester;

  Future<void> pumpApp(Widget widget) async {
    await tester.pumpWidget(widget);
    await tester.pumpAndSettle();
  }

  Future<void> tapSemanticsLabel(Pattern label) async {
    await tester.tap(find.bySemanticsLabel(label).first);
    await tester.pumpAndSettle();
  }

  Future<void> tapText(String text) async {
    await tester.tap(find.text(text).first);
    await tester.pumpAndSettle();
  }

  bool hasText(String text) => find.text(text).evaluate().isNotEmpty;

  bool hasSemanticsLabel(Pattern label) =>
      find.bySemanticsLabel(label).evaluate().isNotEmpty;

  bool isFilledButtonEnabled(String label) {
    final button = find.widgetWithText(FilledButton, label);
    if (button.evaluate().isEmpty) {
      return false;
    }
    return tester.widget<FilledButton>(button.first).onPressed != null;
  }

  bool hasLabeledControl(String label) {
    final exactLabel = RegExp('^${RegExp.escape(label)}\$');
    return hasText(label) || hasSemanticsLabel(exactLabel);
  }
}
