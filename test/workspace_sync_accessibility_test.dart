import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../testing/components/screens/settings_screen_robot.dart';
import '../testing/core/utils/color_contrast.dart';
import '../testing/tests/TS-716/support/ts716_workspace_sync_accessibility_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'workspace sync error state exposes descriptive semantics, AA contrast, and retry-first keyboard recovery order',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final repository = Ts716WorkspaceSyncAccessibilityRepository();

      try {
        await robot.pumpApp(
          repository: repository,
          sharedPreferences: const <String, Object>{
            Ts716WorkspaceSyncAccessibilityRepository.hostedTokenKey:
                Ts716WorkspaceSyncAccessibilityRepository.hostedTokenValue,
          },
        );

        final pill = find.byKey(const ValueKey('workspace-sync-pill'));
        await _pumpUntil(
          tester,
          condition: () =>
              pill.evaluate().isNotEmpty &&
              find
                  .text(
                    Ts716WorkspaceSyncAccessibilityRepository.topBarStatusLabel,
                    findRichText: true,
                  )
                  .evaluate()
                  .isNotEmpty &&
              find
                  .textContaining(
                    'This repository session is read-only',
                    findRichText: true,
                  )
                  .evaluate()
                  .isNotEmpty,
        );

        final semanticsLabel = tester.getSemantics(pill.first).label;
        expect(
          _hasDescriptiveSyncErrorSemantics(semanticsLabel),
          isTrue,
          reason:
              'Expected the sync pill semantics to include sync/error context, but got "$semanticsLabel".',
        );

        final background = robot.decoratedContainerBackgroundColor(pill);
        expect(background, isNotNull);
        expect(
          contrastRatio(
            robot.renderedTextColorWithin(
              pill,
              Ts716WorkspaceSyncAccessibilityRepository.topBarStatusLabel,
            ),
            background!,
          ),
          greaterThanOrEqualTo(4.5),
        );

        await tester.tap(pill.first, warnIfMissed: false);
        await tester.pumpAndSettle();

        final retryAction = robot.actionButton(
          Ts716WorkspaceSyncAccessibilityRepository.retryLabel,
        );
        final reconnectAction = robot.actionButton(
          Ts716WorkspaceSyncAccessibilityRepository.reconnectLabel,
        );

        await tester.ensureVisible(retryAction);
        await tester.ensureVisible(reconnectAction);
        await robot.clearFocus();

        expect(
          await robot.collectFocusOrder(
            candidates: <String, Finder>{
              Ts716WorkspaceSyncAccessibilityRepository.retryLabel: retryAction,
              Ts716WorkspaceSyncAccessibilityRepository.reconnectLabel:
                  reconnectAction,
            },
            tabs: 20,
          ),
          containsAllInOrder(const <String>[
            Ts716WorkspaceSyncAccessibilityRepository.retryLabel,
            Ts716WorkspaceSyncAccessibilityRepository.reconnectLabel,
          ]),
        );
      } finally {
        semantics.dispose();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );
}

bool _hasDescriptiveSyncErrorSemantics(String label) {
  final normalized = label.toLowerCase();
  return normalized.contains('sync') &&
      normalized.contains('attention needed') &&
      (normalized.contains('error') || normalized.contains('read-only'));
}

Future<void> _pumpUntil(
  WidgetTester tester, {
  required bool Function() condition,
  Duration timeout = const Duration(seconds: 5),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (condition()) {
      return;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
  expect(
    condition(),
    isTrue,
    reason: 'Timed out waiting for sync error state.',
  );
}
