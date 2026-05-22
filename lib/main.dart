import 'package:flutter/material.dart';

import 'data/repositories/trackstate_repository.dart';
import 'ui/features/tracker/views/trackstate_app.dart';
import 'ts925_probe_surface.dart';

const bool _useDemoRepositoryForAccessibility = bool.fromEnvironment(
  'TRACKSTATE_USE_DEMO_REPOSITORY',
);

void main() {
  runApp(const _Ts908RenderedProbeApp());
}

class _Ts908RenderedProbeApp extends StatelessWidget {
  const _Ts908RenderedProbeApp();

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: const [
        TrackStateApp(),
        Positioned(
          top: 24,
          left: 24,
          child: Directionality(
            textDirection: TextDirection.ltr,
            child: _Ts908ProbeOverlay(),
          ),
        ),
      ],
    );
  }
}

class _Ts908ProbeOverlay extends StatelessWidget {
  const _Ts908ProbeOverlay();

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: ThemeData(useMaterial3: true),
      child: const Material(
        color: Colors.transparent,
        child: Ts908ProbeSurface(),
      ),
    );
  }
}
