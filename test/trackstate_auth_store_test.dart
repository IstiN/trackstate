import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'workspace-scoped tokens stay isolated across branch-distinct workspaces',
    () async {
      const store = SharedPreferencesTrackStateAuthStore();

      await store.saveToken(
        'feature-a-token',
        workspaceId: 'hosted:trackstate/trackstate@main:feature/a',
      );
      await store.saveToken(
        'feature-b-token',
        workspaceId: 'hosted:trackstate/trackstate@main:feature/b',
      );
      await store.saveToken(
        'legacy-token',
        repository: 'trackstate/trackstate',
      );

      expect(
        await store.readToken(
          workspaceId: 'hosted:trackstate/trackstate@main:feature/a',
        ),
        'feature-a-token',
      );
      expect(
        await store.readToken(
          workspaceId: 'hosted:trackstate/trackstate@main:feature/b',
        ),
        'feature-b-token',
      );
      expect(
        await store.readToken(repository: 'trackstate/trackstate'),
        'legacy-token',
      );
    },
  );

  test(
    'migrateLegacyRepositoryToken moves the stored token into workspace scope',
    () async {
      const store = SharedPreferencesTrackStateAuthStore();
      await store.saveToken(
        'legacy-token',
        repository: 'trackstate/trackstate',
      );

      final migratedToken = await store.migrateLegacyRepositoryToken(
        repository: 'trackstate/trackstate',
        workspaceId: 'hosted:trackstate/trackstate@main',
      );

      expect(migratedToken, 'legacy-token');
      expect(
        await store.readToken(workspaceId: 'hosted:trackstate/trackstate@main'),
        'legacy-token',
      );
      expect(
        await store.readToken(repository: 'trackstate/trackstate'),
        isNull,
      );
    },
  );

  test(
    'moveToken re-scopes a workspace token when a workspace identity changes',
    () async {
      const store = SharedPreferencesTrackStateAuthStore();
      await store.saveToken(
        'workspace-token',
        workspaceId: 'hosted:trackstate/trackstate@main',
      );

      await store.moveToken(
        fromWorkspaceId: 'hosted:trackstate/trackstate@main',
        toWorkspaceId: 'hosted:trackstate/trackstate@main:release',
      );

      expect(
        await store.readToken(workspaceId: 'hosted:trackstate/trackstate@main'),
        isNull,
      );
      expect(
        await store.readToken(
          workspaceId: 'hosted:trackstate/trackstate@main:release',
        ),
        'workspace-token',
      );
    },
  );
}
