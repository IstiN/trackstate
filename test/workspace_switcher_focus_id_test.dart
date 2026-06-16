import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app_types.dart';

void main() {
  group('workspaceSwitcherActionFocusId', () {
    test('composes focus id from workspace and action', () {
      expect(
        workspaceSwitcherActionFocusId('ws-1', 'edit'),
        'trackstate-workspace-switcher-edit-ws-1',
      );
    });

    test('handles workspace id with special characters', () {
      expect(
        workspaceSwitcherActionFocusId('my/workspace', 'delete'),
        'trackstate-workspace-switcher-delete-my/workspace',
      );
    });
  });
}
