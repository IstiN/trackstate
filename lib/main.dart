import 'package:flutter/material.dart';

import 'data/repositories/trackstate_repository.dart';
import 'platform/window_setup.dart';
import 'ui/features/tracker/views/trackstate_app.dart';

const bool _useDemoRepositoryForAccessibility = bool.fromEnvironment(
  'TRACKSTATE_USE_DEMO_REPOSITORY',
);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initWindow();
  runApp(
    _useDemoRepositoryForAccessibility
        ? const TrackStateApp(repository: DemoTrackStateRepository())
        : const TrackStateApp(),
  );
}
