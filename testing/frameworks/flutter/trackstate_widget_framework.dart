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
  Future<void> launchApp() async {
    const repository = DemoTrackStateRepository();
    const size = Size(1440, 960);
    SharedPreferences.setMockInitialValues({});
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;

    await tester.pumpWidget(TrackStateApp(repository: repository));
    await tester.pumpAndSettle();
  }

  @override
  void resetView() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  }

  @override
  Future<void> tapLabeledElement(String label) async {
    final finder = _labeledElement(label);
    await tester.ensureVisible(finder.first);
    await tester.tap(finder.first);
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
    for (final finder in [_semanticsFinder(label), _textFinder(label)]) {
      final matches = finder.evaluate().toList();
      for (var index = 0; index < matches.length; index++) {
        final semantics = tester.getSemantics(finder.at(index));
        final flags = semantics.flagsCollection;
        final hasSelectionState =
            flags.hasCheckedState || flags.hasSelectedState;
        if (!hasSelectionState) {
          continue;
        }
        if (flags.isChecked || flags.isSelected) {
          return true;
        }
      }
    }
    return false;
  }

  @override
  Rect? rectForText(String text) {
    final finder = _textFinder(text);
    if (finder.evaluate().isEmpty) {
      return null;
    }
    return tester.getRect(finder.first);
  }

  Finder _labeledElement(String label) {
    final semanticsFinder = _semanticsFinder(label);
    if (semanticsFinder.evaluate().isNotEmpty) {
      return semanticsFinder;
    }
    return _textFinder(label);
  }

  Finder _semanticsFinder(String label) =>
      find.bySemanticsLabel(RegExp(RegExp.escape(label)));

  Finder _textFinder(String text) => find.text(text);
}
