import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/settings_provider_driver.dart';

class TrackStateWidgetFramework implements SettingsProviderDriver {
  TrackStateWidgetFramework(this.tester);

  final WidgetTester tester;

  @override
  Future<void> launchApp({
    required TrackStateRepository repository,
    Map<String, Object> sharedPreferences = const {},
  }) async {
    const size = Size(1440, 960);
    SharedPreferences.setMockInitialValues(sharedPreferences);
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;

    await tester.pumpWidget(
      TrackStateApp(key: UniqueKey(), repository: repository),
    );
    await tester.pumpAndSettle();
  }

  @override
  void resetView() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  }

  @override
  Future<void> tapLabeledElement(String label) async {
    final finder = _bestTapTarget(label);
    await tester.ensureVisible(finder);
    await tester.tap(finder, warnIfMissed: false);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> enterTextIntoField(String label, String text) async {
    final finder = _textFieldFinder(label);
    await tester.ensureVisible(finder);
    await tester.tap(finder, warnIfMissed: false);
    await tester.pump();
    await tester.enterText(finder, text);
    await tester.pumpAndSettle();
  }

  @override
  Future<void> scrollBodyBy(double dy) async {
    final scrollableFinder = find.byType(SingleChildScrollView).first;
    await tester.drag(scrollableFinder, Offset(0, dy));
    await tester.pumpAndSettle();
  }

  @override
  bool isTextVisible(String text) => _textFinder(text).evaluate().isNotEmpty;

  @override
  int visibleTextCount(String text) => _textFinder(text).evaluate().length;

  @override
  bool isSelected(String label) {
    return _finderHasSelectedState(_semanticsFinder(label)) ||
        _finderHasSelectedState(_textFinder(label));
  }

  @override
  Rect? rectForText(String text) {
    final finder = _textFinder(text);
    if (finder.evaluate().isEmpty) {
      return null;
    }
    return tester.getRect(finder.first);
  }

  @override
  List<String> visibleTexts() {
    return tester
        .widgetList<Text>(find.byType(Text))
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList();
  }

  @override
  String? textFieldValue(String label) {
    final editableTextFinder = _editableTextFinder(label);
    if (editableTextFinder.evaluate().isEmpty) {
      return null;
    }
    final editableText = tester.widget<EditableText>(editableTextFinder.first);
    return editableText.controller.text;
  }

  @override
  bool isTextFieldReadOnly(String label) {
    final editableTextFinder = _editableTextFinder(label);
    if (editableTextFinder.evaluate().isEmpty) {
      return false;
    }
    final editableText = tester.widget<EditableText>(editableTextFinder.first);
    return editableText.readOnly;
  }

  @override
  List<String> visibleProviderLabels() {
    final controls = find.descendant(
      of: _repositoryAccessSection,
      matching: find.bySubtype<ButtonStyleButton>(),
    );
    final rows = <({String label, double top})>[];
    final matches = controls.evaluate().length;
    for (var index = 0; index < matches; index++) {
      final control = controls.at(index);
      rows.add((
        label: tester.getSemantics(control).label,
        top: tester.getRect(control).top,
      ));
    }
    rows.sort((left, right) => left.top.compareTo(right.top));
    return rows.map((row) => row.label).toList();
  }

  @override
  bool isProviderSelected(String label) {
    final providerSemantics = find.descendant(
      of: _repositoryAccessSection,
      matching: _semanticsFinder(label),
    );
    return _finderHasSelectedState(providerSemantics) ||
        _finderHasSelectedState(_providerControl(label));
  }

  @override
  Rect? rectForProviderLabel(String label) {
    final control = _providerControl(label);
    if (control.evaluate().isEmpty) {
      return null;
    }
    return tester.getRect(control.first);
  }

  Finder _bestTapTarget(String label) {
    final providerControl = _providerControl(label);
    if (providerControl.evaluate().isNotEmpty) {
      return providerControl.first;
    }

    final providerSemantics = find.descendant(
      of: _repositoryAccessSection,
      matching: _semanticsFinder(label),
    );
    if (providerSemantics.evaluate().isNotEmpty) {
      return providerSemantics.first;
    }

    final buttonFinder = find.ancestor(
      of: _textFinder(label),
      matching: find.bySubtype<ButtonStyleButton>(),
    );
    final candidates = [
      ...buttonFinder.evaluate().map((_) => buttonFinder),
      ..._semanticsFinder(label).evaluate().map((_) => _semanticsFinder(label)),
      ..._textFinder(label).evaluate().map((_) => _textFinder(label)),
    ];

    Finder? best;
    var bestTop = double.negativeInfinity;
    for (final finder in candidates) {
      final matches = finder.evaluate().length;
      for (var index = 0; index < matches; index++) {
        final candidate = finder.at(index);
        final rect = tester.getRect(candidate);
        if (rect.top >= bestTop) {
          bestTop = rect.top;
          best = candidate;
        }
      }
    }

    return best ?? _textFinder(label).first;
  }

  Finder _semanticsFinder(String label) =>
      find.bySemanticsLabel(RegExp(RegExp.escape(label)));

  Finder _textFinder(String text) => find.text(text);

  Finder get _repositoryAccessSection =>
      find.bySemanticsLabel(RegExp('Repository access'));

  Finder _providerControl(String label) => find.descendant(
    of: _repositoryAccessSection,
    matching: find.ancestor(
      of: _textFinder(label),
      matching: find.bySubtype<ButtonStyleButton>(),
    ),
  );

  bool _finderHasSelectedState(Finder finder) {
    final matches = finder.evaluate().toList();
    for (var index = 0; index < matches.length; index++) {
      final flags = tester.getSemantics(finder.at(index)).flagsCollection;
      if (flags.isChecked || flags.isSelected) {
        return true;
      }
    }
    return false;
  }

  Finder _textFieldFinder(String label) =>
      find.widgetWithText(TextFormField, label);

  Finder _editableTextFinder(String label) => find.descendant(
    of: _textFieldFinder(label),
    matching: find.byType(EditableText),
  );
}
