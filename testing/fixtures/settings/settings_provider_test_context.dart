import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/pages/settings_provider_page.dart';
import '../../frameworks/flutter/trackstate_widget_framework.dart';

SettingsProviderPage createSettingsProviderPage(
  WidgetTester tester, {
  TrackStateRepository repository = const DemoTrackStateRepository(),
  Map<String, Object> sharedPreferences = const {},
}) {
  return SettingsProviderPage(
    TrackStateWidgetFramework(tester),
    repository: repository,
    sharedPreferences: sharedPreferences,
  );
}
