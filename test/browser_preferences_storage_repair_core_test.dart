import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/services/browser_preferences_storage_repair_core.dart';

void main() {
  test(
    'repairs raw preloaded workspace state and repository token values into shared_preferences web format',
    () {
      final rawWorkspaceState = jsonEncode({
        'activeWorkspaceId': 'hosted:istin/trackstate-setup@main',
        'migrationComplete': true,
        'profiles': [
          {
            'id': 'hosted:istin/trackstate-setup@main',
            'displayName': '',
            'targetType': 'hosted',
            'target': 'IstiN/trackstate-setup',
            'defaultBranch': 'main',
            'writeBranch': 'main',
          },
        ],
      });
      final storage = _FakeBrowserPreferencesStorage({
        'trackstate.workspaceProfiles.state': rawWorkspaceState,
        'flutter.trackstate.workspaceProfiles.state': rawWorkspaceState,
        'trackstate.githubToken.IstiN.trackstate-setup': 'test-token',
        'flutter.trackstate.githubToken.IstiN.trackstate-setup': 'test-token',
      });

      repairBrowserPreferencesStorageEntries(storage);

      expect(
        storage.values['flutter.trackstate.workspaceProfiles.state'],
        jsonEncode(rawWorkspaceState),
      );
      expect(
        storage.values['flutter.trackstate.githubToken.IstiN.trackstate-setup'],
        jsonEncode('test-token'),
      );
    },
  );
}

class _FakeBrowserPreferencesStorage implements BrowserPreferencesStorage {
  _FakeBrowserPreferencesStorage(this.values);

  final Map<String, String> values;

  @override
  Iterable<String> get keys => values.keys;

  @override
  void remove(String key) {
    values.remove(key);
  }

  @override
  String? read(String key) => values[key];

  @override
  void write(String key, String value) {
    values[key] = value;
  }
}
