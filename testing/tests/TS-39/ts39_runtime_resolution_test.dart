import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/services/trackstate_runtime_service.dart';
import '../../frameworks/flutter/runtime_probes.dart';

void main() {
  const service = TrackStateRuntimeService(
    startupProbe: FlutterRuntimeStartupProbe(),
    uiProbe: FlutterRuntimeUiProbe(),
  );

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'default startup resolves the hosted GitHub runtime without auto-detection',
    () {
      final startup = service.inspectStartupResolution();
      final localOverride = service.inspectLocalGitOverrideAttempt();

      expect(startup.matchesHostedRuntime, isTrue);
      expect(startup.configuredRuntimeName, 'github');
      expect(startup.repositoryType, 'SetupTrackStateRepository');
      expect(startup.usesLocalPersistence, isFalse);
      expect(startup.supportsGitHubAuth, isTrue);

      if (kIsWeb) {
        expect(localOverride.isBlocked, isTrue);
        expect(
          localOverride.blockedReason,
          contains('The local Git runtime is not available in web builds.'),
        );
      } else {
        expect(localOverride.matchesLocalRuntime, isTrue);
        expect(localOverride.repositoryType, isNot(startup.repositoryType));
      }
    },
  );

  testWidgets('hosted runtime presents GitHub repository access to the user', (
    tester,
  ) async {
    final observation = await service.inspectHostedRuntimeExperience(tester);

    expect(observation.matchesHostedRuntimeExperience, isTrue);
    expect(observation.repositoryAccessVisible, isTrue);
    expect(observation.connectGitHubDialogVisible, isTrue);
    expect(observation.fineGrainedTokenVisible, isTrue);
    expect(observation.fineGrainedTokenHelperVisible, isTrue);
    expect(observation.rememberOnThisBrowserVisible, isTrue);
    expect(observation.localRuntimeMessagingVisible, isFalse);
  });
}
