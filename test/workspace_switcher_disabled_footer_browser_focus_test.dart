import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_focusable_control_logic.dart';

void main() {
  test(
    'desktop web workspace switcher keeps the disabled Save and switch footer in the browser tab order',
    () {
      final trackStateAppSource = File(
        '${Directory.current.path}/lib/ui/features/tracker/views/trackstate_app.dart',
      ).readAsStringSync();

      expect(
        trackStateAppSource,
        contains('focusTargetId: _workspaceSwitcherSaveFocusId'),
      );
      expect(trackStateAppSource, contains('focusableWhenDisabled: true'));
      expect(
        trackStateAppSource,
        isNot(contains('_WorkspaceSwitcherDisabledFooterButton(')),
        reason:
            'The footer must stay on the shared browser-focus bridge path so '
            'disabled Save and switch actions still export a tabbable native '
            'focus target on web.',
      );

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
}
