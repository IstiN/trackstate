import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/ts39_runtime_service_factory.dart';

void main() {
  final service = createTrackStateRuntimeService();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'default startup resolves the hosted GitHub runtime without auto-detection',
    () async {
      final startup = service.inspectStartupResolution();
      final localOverride = await service.inspectLocalGitOverrideAttempt();

      expect(startup.matchesHostedRuntime, isTrue);
      expect(startup.configuredRuntimeName, 'github');
      expect(startup.repositoryType, 'SetupTrackStateRepository');
      expect(startup.usesLocalPersistence, isFalse);
      expect(startup.supportsGitHubAuth, isTrue);

      if (kIsWeb) {
        expect(localOverride.isBlocked, isTrue);
        expect(localOverride.blockedReason, contains('IO test subprocess'));
      } else {
        expect(localOverride.matchesLocalRuntime, isTrue);
        expect(localOverride.configuredRuntimeName, 'local-git');
        expect(localOverride.repositoryType, 'LocalTrackStateRepository');
      }
    },
  );

  testWidgets('hosted runtime presents GitHub repository access to the user', (
    tester,
  ) async {
    final observation = await service.inspectHostedRuntimeExperience(tester);

    expect(observation.matchesHostedRuntimeExperience, isTrue);
    expect(observation.repositoryType, 'SetupTrackStateRepository');
    expect(observation.usesLocalPersistence, isFalse);
    expect(observation.supportsGitHubAuth, isTrue);
    expect(observation.repositoryAccessVisible, isTrue);
    expect(observation.connectGitHubDialogVisible, isTrue);
    expect(observation.fineGrainedTokenVisible, isTrue);
    expect(observation.fineGrainedTokenHelperVisible, isTrue);
    expect(observation.rememberOnThisBrowserVisible, isTrue);
    expect(observation.localRuntimeMessagingVisible, isFalse);
  });
}
