import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  test(
    'web inactive row summary stays inert when a separate Open action is shown',
    () {
      expect(
        shouldActivateBrowserWorkspaceSwitcherRowSummary(
          isWeb: true,
          isActive: false,
          showOpenAction: true,
          hasSelectionAction: true,
        ),
        isFalse,
      );
    },
  );

  test('native inactive row summary can still activate selection', () {
    expect(
      shouldActivateBrowserWorkspaceSwitcherRowSummary(
        isWeb: false,
        isActive: false,
        showOpenAction: true,
        hasSelectionAction: true,
      ),
      isTrue,
    );
  });

  test('rows without a selection action stay inert', () {
    expect(
      shouldActivateBrowserWorkspaceSwitcherRowSummary(
        isWeb: true,
        isActive: true,
        showOpenAction: false,
        hasSelectionAction: false,
      ),
      isFalse,
    );
  });
}
