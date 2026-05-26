@TestOn('browser')
library;

import 'dart:js_interop';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/browser_local_workspace_repository.dart';

void main() {
  setUp(() async {
    await debugResetBrowserLocalWorkspaceSelectionCache(clearPersisted: true);
  });

  tearDown(() async {
    await debugResetBrowserLocalWorkspaceSelectionCache(clearPersisted: true);
  });

  test(
    'browser local workspace selection survives a simulated reload',
    () async {
      await rememberBrowserLocalWorkspaceSelection(
        workspacePath: '/tmp/demo',
        selection: _FakeDirectoryHandle(kind: 'directory', name: 'demo'),
      );

      await debugResetBrowserLocalWorkspaceSelectionCache();

      final repository = await openBrowserLocalWorkspaceRepository(
        repositoryPath: '/tmp/demo',
        defaultBranch: 'main',
        writeBranch: 'main',
      );

      expect(repository, isNotNull);
    },
  );
}

extension type _FakeDirectoryHandle._(JSObject _) implements JSObject {
  external factory _FakeDirectoryHandle({String kind, String name});
}
