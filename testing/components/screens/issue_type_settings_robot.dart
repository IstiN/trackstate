import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'settings_screen_robot.dart';

class IssueTypeSettingsRobot {
  IssueTypeSettingsRobot(this.tester, this.settingsRobot);

  final WidgetTester tester;
  final SettingsScreenRobot settingsRobot;

  static const iconPickerLabels = <String>[
    'Epic',
    'Story',
    'Sub-task',
    'Hierarchy',
    'Settings',
    'Issue',
  ];

  Finder get issueTypesTab => settingsRobot.issueTypesCard;
  Finder get saveSettingsButton => find.bySemanticsLabel('Save settings');
  Finder get editorSaveButton => find.widgetWithText(FilledButton, 'Save');
  Finder get editorCancelButton => find.widgetWithText(TextButton, 'Cancel');

  Finder issueTypeTile(String issueTypeName) => find.descendant(
    of: settingsRobot.settingsAdminSection,
    matching: find.ancestor(
      of: find.text(issueTypeName),
      matching: find.byType(ListTile),
    ),
  );

  Finder editIssueTypeButton(String issueTypeName) => find.descendant(
    of: issueTypeTile(issueTypeName),
    matching: find.widgetWithText(TextButton, 'Edit'),
  );

  Finder textField(String label) => find.byWidgetPredicate(
    (widget) =>
        widget is TextFormField &&
        find
            .descendant(of: find.byWidget(widget), matching: find.text(label))
            .evaluate()
            .isNotEmpty,
    description: 'TextFormField("$label")',
  );

  Finder dropdownField(String label) => find.byWidgetPredicate(
    (widget) =>
        widget is DropdownButtonFormField<String> &&
        find
            .descendant(of: find.byWidget(widget), matching: find.text(label))
            .evaluate()
            .isNotEmpty,
    description: 'DropdownButtonFormField("$label")',
  );

  Future<void> openIssueTypesTab() async {
    await tester.tap(issueTypesTab);
    await tester.pumpAndSettle();
  }

  Future<void> openIssueTypeEditor(String issueTypeName) async {
    final button = editIssueTypeButton(issueTypeName);
    await tester.ensureVisible(button.first);
    await tester.tap(button.first, warnIfMissed: false);
    await tester.pumpAndSettle();
  }

  Future<void> enterTextFieldValue(String label, String value) async {
    final field = textField(label);
    await tester.ensureVisible(field);
    await tester.tap(field);
    await tester.pump();
    await tester.enterText(field, value);
    await tester.pumpAndSettle();
  }

  Future<void> saveEditor() async {
    await tester.ensureVisible(editorSaveButton);
    await tester.tap(editorSaveButton);
    await tester.pumpAndSettle();
  }

  Future<void> saveSettings() async {
    await tester.ensureVisible(saveSettingsButton);
    await tester.tap(saveSettingsButton);
    await tester.pumpAndSettle();
  }

  String readTextFieldValue(String label) {
    final widget = tester.widget<TextFormField>(textField(label));
    return widget.controller?.text ?? widget.initialValue ?? '';
  }

  bool issueTypeSubtitleContains(String issueTypeName, String value) {
    final subtitle = find.descendant(
      of: issueTypeTile(issueTypeName),
      matching: find.textContaining(value, findRichText: true),
    );
    return subtitle.evaluate().isNotEmpty;
  }

  bool showsText(String value) => find.text(value).evaluate().isNotEmpty;

  List<String> visibleTexts() {
    return tester
        .widgetList<Text>(find.byType(Text))
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList(growable: false);
  }

  String visibleTextSnapshot({int limit = 24}) {
    final unique = <String>{};
    for (final value in visibleTexts()) {
      unique.add(value.trim());
      if (unique.length == limit) {
        break;
      }
    }
    return unique.isEmpty ? '<none>' : unique.join(' | ');
  }

  List<String> describeIconInputControls() {
    final descriptions = <String>[];
    final iconTextFieldCount = textField('Icon').evaluate().length;
    final iconDropdownCount = dropdownField('Icon').evaluate().length;
    if (iconTextFieldCount > 0) {
      descriptions.add('editable text field x$iconTextFieldCount');
    }
    if (iconDropdownCount > 0) {
      descriptions.add('dropdown field x$iconDropdownCount');
    }
    return descriptions;
  }

  Future<bool> openIconPicker() async {
    final dropdown = dropdownField('Icon');
    if (dropdown.evaluate().isNotEmpty) {
      await tester.ensureVisible(dropdown.first);
      await tester.tap(dropdown.first, warnIfMissed: false);
      await tester.pumpAndSettle();
      return true;
    }

    final field = textField('Icon');
    if (field.evaluate().isNotEmpty) {
      await tester.ensureVisible(field.first);
      await tester.tap(field.first, warnIfMissed: false);
      await tester.pumpAndSettle();
    }

    return false;
  }

  List<String> readDropdownOptions(String label) {
    final field = dropdownField(label);
    if (field.evaluate().isEmpty) {
      return const [];
    }

    final dropdownButton = find.descendant(
      of: field.first,
      matching: find.byType(DropdownButton<String>),
    );
    if (dropdownButton.evaluate().isEmpty) {
      return const [];
    }

    final dropdown = tester.widget<DropdownButton<String>>(
      dropdownButton.first,
    );
    final optionTexts = <String>[];
    for (final item in dropdown.items ?? const <DropdownMenuItem<String>>[]) {
      final text = _widgetText(item.child);
      if (text == null || optionTexts.contains(text)) {
        continue;
      }
      optionTexts.add(text);
    }
    return optionTexts;
  }

  String? _widgetText(Widget? widget) {
    if (widget == null) {
      return null;
    }
    if (widget is Text) {
      final text = widget.data?.trim() ?? widget.textSpan?.toPlainText().trim();
      return text == null || text.isEmpty ? null : text;
    }
    if (widget is RichText) {
      final text = widget.text.toPlainText().trim();
      return text.isEmpty ? null : text;
    }
    if (widget is Semantics) {
      final label = widget.properties.label?.trim();
      if (label != null && label.isNotEmpty) {
        return label;
      }
      return _widgetText(widget.child);
    }
    if (widget is SingleChildRenderObjectWidget) {
      return _widgetText(widget.child);
    }
    if (widget is MultiChildRenderObjectWidget) {
      for (final child in widget.children) {
        final text = _widgetText(child);
        if (text != null) {
          return text;
        }
      }
    }
    return null;
  }
}
