import 'package:flutter_test/flutter_test.dart';

import '../../../components/services/legacy_hosted_workspace_migration_service.dart';
import '../../../core/interfaces/legacy_hosted_workspace_migration_probe.dart';
import '../../../frameworks/flutter/legacy_hosted_workspace_migration_widget_driver.dart';

LegacyHostedWorkspaceMigrationProbe
createTs665LegacyHostedWorkspaceMigrationProbe(WidgetTester tester) {
  return LegacyHostedWorkspaceMigrationService(
    driver: LegacyHostedWorkspaceMigrationWidgetDriver(tester),
  );
}
