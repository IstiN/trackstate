@TestOn('browser')
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';
import 'package:web/web.dart' as web;

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'desktop web workspace switcher keeps the disabled Save and switch footer in the browser tab order',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        const TrackStateApp(repository: DemoTrackStateRepository()),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const ValueKey('workspace-switcher-trigger')));
      await tester.pumpAndSettle();

      expect(find.text('Save and switch'), findsOneWidget);

      final element = web.document.querySelector(
        'button[data-trackstate-browser-focus-id="trackstate-workspace-switcher-save"]',
      );

      expect(
        element,
        isA<web.HTMLButtonElement>(),
        reason:
            'The visible disabled footer action must still export a browser-owned '
            'focus target so desktop Tab traversal can reach it instead of '
            'escaping the workspace switcher.',
      );

      final button = element! as web.HTMLButtonElement;
      expect(button.tabIndex, 0);
      expect(button.getAttribute('aria-disabled'), 'true');
      expect(button.disabled, isFalse);
    },
  );
}
