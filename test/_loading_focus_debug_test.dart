import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../testing/fixtures/loading_state_visual_quality_screen_fixture.dart';

void main() {
  testWidgets('debug loading focus', (tester) async {
    final semantics = tester.ensureSemantics();
    final screen = await launchLoadingStateVisualQualityFixture(tester);
    await screen.openJqlSearch();

    Finder focusedSemantics() => find.semantics.byPredicate(
      (node) => node.getSemanticsData().flagsCollection.isFocused,
      describeMatch: (_) => 'focused semantics node',
    );

    Future<void> dump(String prefix) async {
      final labels = <String>[];
      for (final node in focusedSemantics().evaluate()) {
        labels.add(node.getSemanticsData().label);
      }
      // ignore: avoid_print
      print('$prefix => ${labels.join(' | ')}');
    }

    await tester.tap(find.byType(TextField).last);
    await tester.pump();
    await dump('initial');
    for (var i = 0; i < 20; i++) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
      await dump('tab $i');
    }

    screen.dispose();
    semantics.dispose();
  });
}
