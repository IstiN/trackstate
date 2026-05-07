import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
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
  const FlutterRuntimeUiProbe({
    required WidgetTester tester,
    required this.createRepository,
  }) : _tester = tester;

  final WidgetTester _tester;
  final TrackStateRepository Function() createRepository;

  @override
  Future<RuntimeUiObservation> inspectHostedRuntimeExperience() async {
    final tester = _tester;
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    try {
      final repository = createRepository();
      await tester.pumpWidget(TrackStateApp(repository: repository));

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
            .text(
              'Needs Contents: read/write. Stored only on this device if remembered.',
            )
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
