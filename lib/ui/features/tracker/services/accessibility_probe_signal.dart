import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'accessibility_probe_signal_stub.dart'
    if (dart.library.js_interop) 'accessibility_probe_signal_web.dart'
    as platform;

void publishAccessibilityContrastProbeSignal({
  required String text,
  required String semanticsLabel,
  required Color foreground,
  required Color background,
  double threshold = 4.5,
}) {
  platform.publishAccessibilityContrastProbeSignal(
    text: text,
    semanticsLabel: semanticsLabel,
    contrastRatio: _contrastRatio(foreground, background),
    threshold: threshold,
    foregroundHex: _hexColor(foreground),
    backgroundHex: _hexColor(background),
  );
}

double _contrastRatio(Color foreground, Color background) {
  final foregroundLuminance = _relativeLuminance(foreground);
  final backgroundLuminance = _relativeLuminance(background);
  final lighter = math.max(foregroundLuminance, backgroundLuminance);
  final darker = math.min(foregroundLuminance, backgroundLuminance);
  return (lighter + 0.05) / (darker + 0.05);
}

double _relativeLuminance(Color color) {
  double channel(double value) {
    if (value <= 0.03928) {
      return value / 12.92;
    }

    return math.pow((value + 0.055) / 1.055, 2.4).toDouble();
  }

  return 0.2126 * channel(color.r) +
      0.7152 * channel(color.g) +
      0.0722 * channel(color.b);
}

String _hexColor(Color color) {
  String channel(int value) => value.toRadixString(16).padLeft(2, '0');
  return '#${channel((color.r * 255).round() & 0xff)}'
      '${channel((color.g * 255).round() & 0xff)}'
      '${channel((color.b * 255).round() & 0xff)}';
}
