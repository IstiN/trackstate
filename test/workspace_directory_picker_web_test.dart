@TestOn('browser')
library;

import 'dart:js_interop';
import 'dart:js_interop_unsafe';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/browser_local_workspace_repository.dart';
import 'package:trackstate/ui/features/tracker/services/workspace_directory_picker_web.dart';

void main() {
  late BrowserDirectoryAccessRequester originalRequester;

  setUp(() async {
    originalRequester = browserDirectoryAccessRequester;
    await clearRememberedBrowserLocalWorkspaceSelections();
  });

  tearDown(() async {
    browserDirectoryAccessRequester = originalRequester;
    await clearRememberedBrowserLocalWorkspaceSelections();
  });

  test(
    'browser workspace picker preserves the saved target after browser access is granted',
    () async {
      var calls = 0;
      browserDirectoryAccessRequester =
          ({String? confirmButtonText, String? initialDirectory}) async {
            calls += 1;
            expect(confirmButtonText, isNull);
            expect(initialDirectory, '/tmp/demo');
            return JSObject()
              ..['kind'] = 'directory'.toJS
              ..['name'] = 'demo'.toJS;
          };

      final selectedPath = await pickWorkspaceDirectory(
        initialDirectory: '/tmp/demo',
      );

      expect(calls, 1);
      expect(selectedPath, '/tmp/demo');
    },
  );

  test(
    'browser workspace picker returns null when the browser directory prompt is canceled',
    () async {
      browserDirectoryAccessRequester =
          ({String? confirmButtonText, String? initialDirectory}) async {
            throw const _AbortError();
          };

      final selectedPath = await pickWorkspaceDirectory(
        initialDirectory: '/tmp/demo',
      );

      expect(selectedPath, isNull);
    },
  );

  test(
    'browser workspace picker rejects a handle whose directory name does not match the saved workspace target',
    () async {
      browserDirectoryAccessRequester =
          ({String? confirmButtonText, String? initialDirectory}) async {
            return <String, Object?>{'name': 'wrong-directory'};
          };

      await expectLater(
        pickWorkspaceDirectory(initialDirectory: '/tmp/demo'),
        throwsA(
          isA<Exception>().having(
            (error) => error.toString(),
            'message',
            'Selected directory does not match the saved workspace configuration.',
          ),
        ),
      );
    },
  );

  test(
    'browser local repository restores a saved directory handle after a reload',
    () async {
      final directoryHandle = JSObject()
        ..['kind'] = 'directory'.toJS
        ..['name'] = 'trackstate-demo'.toJS;

      await rememberBrowserLocalWorkspaceSelection(
        workspacePath: '/tmp/trackstate-demo',
        selection: directoryHandle,
      );
      await clearRememberedBrowserLocalWorkspaceSelections(
        clearPersisted: false,
      );

      final repository = await openBrowserLocalWorkspaceRepository(
        repositoryPath: '/tmp/trackstate-demo',
        defaultBranch: 'main',
        writeBranch: 'main',
      );

      expect(repository, isNotNull);
    },
  );
}

class _AbortError implements Exception {
  const _AbortError();

  @override
  String toString() => 'AbortError: The user aborted a request.';
}
