import 'package:flutter/material.dart';

import 'data/repositories/trackstate_repository.dart';
import 'ui/features/tracker/views/trackstate_app.dart';
import 'ts936_probe_surface.dart';

const bool _useDemoRepositoryForAccessibility = bool.fromEnvironment(
  'TRACKSTATE_USE_DEMO_REPOSITORY',
);

void main() {
  runApp(_Ts908RenderedProbeApp(child: _useDemoRepositoryForAccessibility
        ? const TrackStateApp(repository: DemoTrackStateRepository())
        : const TrackStateApp(),));
}

class _Ts908RenderedProbeApp extends StatelessWidget {
  const _Ts908RenderedProbeApp({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    assert(() {
      debugPrint(
        'Accessibility probe preserved original app entrypoint: ${child.runtimeType}',
      );
      return true;
    }());
    return MaterialApp(
      title: 'TrackState.AI',
      home: Scaffold(
        body: Align(
          alignment: Alignment.topLeft,
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: const Ts908ProbeSurface(),
          ),
        ),
      ),
    );
  }
}
