import 'dart:convert';
import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';
import 'package:trackstate/data/repositories/trackstate_runtime.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/runtime_startup_probe.dart';
import '../../core/interfaces/runtime_ui_probe.dart';
import '../../core/models/runtime_startup_observation.dart';
import '../../core/models/runtime_ui_observation.dart';
import 'runtime_define_override_probe_stub.dart'
    if (dart.library.io) 'runtime_define_override_probe_io.dart'
    as runtime_define_override_probe;

class FlutterRuntimeStartupProbe implements RuntimeStartupProbe {
  const FlutterRuntimeStartupProbe();

  @override
  RuntimeStartupObservation inspectDefaultStartup() {
    final repository = createTrackStateRepository();
    return RuntimeStartupObservation(
      configuredRuntimeName: configuredTrackStateRuntimeName,
      configuredRuntime: configuredTrackStateRuntime,
      repositoryType: repository.runtimeType.toString(),
      usesLocalPersistence: repository.usesLocalPersistence,
      supportsGitHubAuth: repository.supportsGitHubAuth,
    );
  }

  @override
  Future<RuntimeOverrideObservation> inspectLocalGitOverrideAttempt() {
    return runtime_define_override_probe.inspectLocalGitOverrideAttempt();
  }
}

class FlutterRuntimeUiProbe implements RuntimeUiProbe {
  const FlutterRuntimeUiProbe();

  @override
  Future<RuntimeUiObservation> inspectHostedRuntimeExperience(
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    try {
      final repository = createTrackStateRepository(client: _mockSetupClient());
      await tester.pumpWidget(
        TrackStateApp(repository: repository),
      );

      final repositoryAccess = find.bySemanticsLabel(RegExp('Connect GitHub'));
      await _pumpUntilVisible(tester, repositoryAccess);
      await tester.tap(repositoryAccess.first);
      await tester.pumpAndSettle();

      final connectGitHubDialog = find.text('Connect GitHub');
      await _pumpUntilVisible(tester, connectGitHubDialog);

      return RuntimeUiObservation(
        repositoryType: repository.runtimeType.toString(),
        usesLocalPersistence: repository.usesLocalPersistence,
        supportsGitHubAuth: repository.supportsGitHubAuth,
        repositoryAccessVisible: repositoryAccess.evaluate().isNotEmpty,
        connectGitHubDialogVisible: connectGitHubDialog.evaluate().isNotEmpty,
        fineGrainedTokenVisible: find
            .text('Fine-grained token')
            .evaluate()
            .isNotEmpty,
        fineGrainedTokenHelperVisible: find
            .text('Needs Contents: read/write. Stored only on this device if remembered.')
            .evaluate()
            .isNotEmpty,
        rememberOnThisBrowserVisible: find
            .text('Remember on this browser')
            .evaluate()
            .isNotEmpty,
        localRuntimeMessagingVisible:
            find.text('Local Git runtime').evaluate().isNotEmpty ||
            find
                .textContaining('GitHub tokens are not used in this runtime')
                .evaluate()
                .isNotEmpty,
      );
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    }
  }
}

http.Client _mockSetupClient() {
  return MockClient((request) async {
    final path = request.url.path;
    if (path.endsWith('/git/trees/main')) {
      expect(request.url.queryParameters['recursive'], '1');
      return http.Response(jsonEncode(_treeResponse), 200);
    }
    final entry = _contentResponses[path];
    if (entry != null) {
      return http.Response(
        jsonEncode({
          'content': base64Encode(utf8.encode(entry)),
          'sha': 'test-sha',
        }),
        200,
      );
    }
    return http.Response('', 404);
  });
}

const _treeResponse = {
  'tree': [
    {'path': 'DEMO/project.json', 'type': 'blob'},
    {'path': 'DEMO/config/statuses.json', 'type': 'blob'},
    {'path': 'DEMO/config/issue-types.json', 'type': 'blob'},
    {'path': 'DEMO/config/fields.json', 'type': 'blob'},
    {'path': 'DEMO/DEMO-1/main.md', 'type': 'blob'},
    {'path': 'DEMO/DEMO-1/acceptance_criteria.md', 'type': 'blob'},
  ],
};

const _contentResponses = {
  '/repos/trackstate/trackstate/contents/DEMO/project.json':
      '{"key":"DEMO","name":"Demo Project"}',
  '/repos/trackstate/trackstate/contents/DEMO/config/statuses.json':
      '[{"name":"To Do"},{"name":"In Progress"},{"name":"Done"}]',
  '/repos/trackstate/trackstate/contents/DEMO/config/issue-types.json':
      '[{"name":"Epic"},{"name":"Story"}]',
  '/repos/trackstate/trackstate/contents/DEMO/config/fields.json':
      '[{"name":"Summary"},{"name":"Priority"}]',
  '/repos/trackstate/trackstate/contents/DEMO/DEMO-1/main.md':
      '---\nkey: DEMO-1\nproject: DEMO\nissueType: Story\nstatus: In Progress\npriority: High\nsummary: Hosted runtime sample issue\nassignee: demo-user\nreporter: demo-admin\nlabels:\n  - hosted\ncomponents:\n  - web\nparent: null\nepic: null\nupdated: 2026-05-05T00:00:00Z\n---\n\n# Description\n\nLoaded through the hosted setup repository.\n',
  '/repos/trackstate/trackstate/contents/DEMO/DEMO-1/acceptance_criteria.md':
      '- Verify GitHub runtime startup.\n- Keep Local Git disabled by default.\n',
};

Future<void> _pumpUntilVisible(
  WidgetTester tester,
  Finder finder, {
  Duration timeout = const Duration(seconds: 5),
  Duration step = const Duration(milliseconds: 100),
}) async {
  final maxAttempts = timeout.inMilliseconds ~/ step.inMilliseconds;
  for (var attempt = 0; attempt < maxAttempts; attempt++) {
    await tester.pump(step);
    if (finder.evaluate().isNotEmpty) {
      return;
    }
  }
  throw TestFailure('Timed out waiting for the expected UI element.');
}
