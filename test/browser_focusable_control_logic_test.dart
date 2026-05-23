import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_focusable_control_logic.dart';

void main() {
  test(
    'disabled controls can remain tabbable for browser focus traps',
    () {
      expect(
        resolveBrowserFocusableControlDomConfig(
          enabled: false,
          focusableWhenDisabled: true,
          explicitTabIndex: null,
        ),
        isA<BrowserFocusableControlDomConfig>()
            .having((config) => config.tabIndex, 'tabIndex', 0)
            .having((config) => config.ariaDisabled, 'ariaDisabled', 'true'),
      );
    },
  );

  test('disabled controls stay out of tab order by default', () {
    expect(
      resolveBrowserFocusableControlDomConfig(
        enabled: false,
        focusableWhenDisabled: false,
        explicitTabIndex: null,
      ),
      isA<BrowserFocusableControlDomConfig>()
          .having((config) => config.tabIndex, 'tabIndex', -1)
          .having((config) => config.ariaDisabled, 'ariaDisabled', 'true'),
    );
  });
}
