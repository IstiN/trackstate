import 'dart:math' as math;

import 'package:flutter/material.dart';

double contrastRatio(Color foreground, Color background) {
  final lighter = _relativeLuminance(foreground);
  final darker = _relativeLuminance(background);
  final maxValue = lighter > darker ? lighter : darker;
  final minValue = lighter > darker ? darker : lighter;
  return (maxValue + 0.05) / (minValue + 0.05);
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
