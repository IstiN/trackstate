import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/trackstate_runtime_service_factory.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'hosted runtime onboarding GitHub access elements render during startup',
    (tester) async {
      final service = createTrackStateRuntimeUiService(tester);
      final observation = await service.inspectHostedRuntimeExperience();

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
    },
  );
}
