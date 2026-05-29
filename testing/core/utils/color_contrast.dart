import 'dart:math' as math;

import 'package:flutter/material.dart';

double contrastRatio(Color foreground, Color background) {
  final effectiveForeground = compositeForegroundOverBackground(
    foreground,
    background,
  );
  final lighter = _relativeLuminance(effectiveForeground);
  final darker = _relativeLuminance(background);
  final maxValue = lighter > darker ? lighter : darker;
  final minValue = lighter > darker ? darker : lighter;
  return (maxValue + 0.05) / (minValue + 0.05);
}

Color compositeForegroundOverBackground(Color foreground, Color background) {
  if (foreground.a >= 1) {
    return foreground;
  }
  final alpha = foreground.a.clamp(0, 1).toDouble();
  return Color.fromRGBO(
    _compositeChannel(foreground.r, background.r, alpha),
    _compositeChannel(foreground.g, background.g, alpha),
    _compositeChannel(foreground.b, background.b, alpha),
    1,
  );
}

int _compositeChannel(double foreground, double background, double alpha) {
  final value = (foreground * alpha) + (background * (1 - alpha));
  final normalized = (value * 255).round();
  return normalized.clamp(0, 255);
}

double _relativeLuminance(Color color) {
  double channel(double normalized) {
    if (normalized <= 0.03928) {
      return normalized / 12.92;
    }
    return math.pow((normalized + 0.055) / 1.055, 2.4).toDouble();
  }

  return 0.2126 * channel(color.r) +
      0.7152 * channel(color.g) +
      0.0722 * channel(color.b);
}
