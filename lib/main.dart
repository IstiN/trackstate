import 'package:flutter/material.dart';

import 'data/repositories/trackstate_repository.dart';
import 'ui/features/tracker/views/trackstate_app.dart';

const bool _useDemoRepositoryForAccessibility = bool.fromEnvironment(
  'TRACKSTATE_USE_DEMO_REPOSITORY',
);

void main() {
  runApp(
    _useDemoRepositoryForAccessibility
        ? const TrackStateApp(repository: DemoTrackStateRepository())
        : const TrackStateApp(),
  );
}
