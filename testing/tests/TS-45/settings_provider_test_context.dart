import 'package:flutter_test/flutter_test.dart';

import '../../components/pages/settings_provider_page.dart';
import '../../frameworks/flutter/trackstate_widget_framework.dart';

SettingsProviderPage createSettingsProviderPage(WidgetTester tester) {
  return SettingsProviderPage(TrackStateWidgetFramework(tester));
}
