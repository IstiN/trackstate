import 'package:flutter/material.dart';

import 'data/repositories/trackstate_repository.dart';
import 'ui/features/tracker/views/trackstate_app.dart';
import 'ts924_probe_surface.dart';

const bool _useDemoRepositoryForAccessibility = bool.fromEnvironment(
  'TRACKSTATE_USE_DEMO_REPOSITORY',
);

void main() {
  runApp(_Ts924RenderedProbeApp(child: _useDemoRepositoryForAccessibility
        ? const TrackStateApp(repository: DemoTrackStateRepository())
        : const TrackStateApp(),));
}

class _Ts924RenderedProbeApp extends StatelessWidget {
  const _Ts924RenderedProbeApp({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        child,
        Positioned(
          top: 24,
          left: 24,
          child: Directionality(
            textDirection: TextDirection.ltr,
            child: _Ts924ProbeOverlay(),
          ),
        ),
      ],
    );
  }
}

class _Ts924ProbeOverlay extends StatelessWidget {
  const _Ts924ProbeOverlay();

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: ThemeData(useMaterial3: true),
      child: Material(
        color: Colors.transparent,
        child: const Ts924ProbeSurface(),
      ),
    );
  }
}
