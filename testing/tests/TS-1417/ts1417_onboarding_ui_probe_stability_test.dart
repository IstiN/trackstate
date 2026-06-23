import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/trackstate_runtime_service_factory.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('onboarding UI widget hierarchy is stable for automated probes', (
    tester,
  ) async {
    final service = createTrackStateRuntimeUiService(tester);
    final observation = await service.inspectHostedRuntimeStability();

    expect(observation.isStableForAutomatedProbes, isTrue);
    expect(observation.connectGitHubElementCount, greaterThan(0));
    expect(observation.connectGitHubStableAcrossPumps, isTrue);
    expect(observation.fineGrainedTokenElementCount, 1);
    expect(observation.fineGrainedTokenStableAcrossPumps, isTrue);
    expect(observation.fineGrainedTokenHelperElementCount, 1);
    expect(observation.fineGrainedTokenHelperStableAcrossPumps, isTrue);
    expect(observation.rememberOnThisBrowserElementCount, 1);
    expect(observation.rememberOnThisBrowserStableAcrossPumps, isTrue);
  });
}
