import 'package:flutter_test/flutter_test.dart';

import '../models/runtime_ui_observation.dart';

abstract class RuntimeUiProbe {
  Future<RuntimeUiObservation> inspectHostedRuntimeExperience(
    WidgetTester tester,
  );
}
