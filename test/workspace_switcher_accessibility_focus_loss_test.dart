import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  group('workspace switcher accessibility focus loss', () {
    test('compact switcher does not close from accessibility focus loss', () {
      expect(
        shouldCloseDesktopWorkspaceSwitcherOnAccessibilityFocusLoss(
          compact: true,
          isWeb: false,
        ),
        isFalse,
      );
    });

    test('desktop native switcher still closes from accessibility focus loss', () {
      expect(
        shouldCloseDesktopWorkspaceSwitcherOnAccessibilityFocusLoss(
          compact: false,
          isWeb: false,
        ),
        isTrue,
      );
    });

    test('desktop web switcher ignores accessibility focus loss', () {
      expect(
        shouldCloseDesktopWorkspaceSwitcherOnAccessibilityFocusLoss(
          compact: false,
          isWeb: true,
        ),
        isFalse,
      );
    });
  });
}
