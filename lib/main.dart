import 'package:flutter/material.dart';

import 'data/repositories/trackstate_repository.dart';
import 'ui/features/tracker/views/trackstate_app.dart';
import 'ui/core/trackstate_theme.dart';
import 'ts926_accessibility_boundary_probe.dart';

const bool _useDemoRepositoryForAccessibility = bool.fromEnvironment(
  'TRACKSTATE_USE_DEMO_REPOSITORY',
);

void main() {
  runApp(_Ts926RenderedProbeApp(child: _useDemoRepositoryForAccessibility
        ? const TrackStateApp(repository: DemoTrackStateRepository())
        : const TrackStateApp(),));
}

class _Ts926RenderedProbeApp extends StatelessWidget {
  const _Ts926RenderedProbeApp({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned.fill(child: child),
        Positioned(
          top: 24,
          left: 24,
          child: const Directionality(
            textDirection: TextDirection.ltr,
            child: _Ts926ProbeOverlay(),
          ),
        ),
      ],
    );
  }
}

class _Ts926ProbeOverlay extends StatelessWidget {
  const _Ts926ProbeOverlay();

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: TrackStateTheme.light(),
      child: const Material(
        color: Colors.transparent,
        child: Ts926ProbeSurface(),
      ),
    );
  }
}
