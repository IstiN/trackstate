@TestOn('browser')
library;

import 'dart:js_interop';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/browser_local_workspace_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

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
      expect(repository, isA<ProviderBackedTrackStateRepository>());
      final providerRepository =
          repository! as ProviderBackedTrackStateRepository;
      expect(providerRepository.usesLocalPersistence, isTrue);
      expect(providerRepository.providerAdapter.repositoryLabel, '/tmp/demo');
      expect(providerRepository.providerAdapter.dataRef, 'main');
      expect(
        await providerRepository.providerAdapter.resolveWriteBranch(),
        'main',
      );
      final branch = await providerRepository.providerAdapter.getBranch('main');
      expect(
        branch,
        isA<RepositoryBranch>()
            .having((repositoryBranch) => repositoryBranch.name, 'name', 'main')
            .having(
              (repositoryBranch) => repositoryBranch.exists,
              'exists',
              isTrue,
            )
            .having(
              (repositoryBranch) => repositoryBranch.isCurrent,
              'isCurrent',
              isTrue,
            ),
      );
    },
  );
}

extension type _FakeDirectoryHandle._(JSObject _) implements JSObject {
  external factory _FakeDirectoryHandle({String kind, String name});
}
