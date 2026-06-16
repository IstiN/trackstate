import 'dart:ui';

class ColorBlindnessFilters {
  static ColorFilter grayscale() {
    return const ColorFilter.matrix(<double>[
      0.2126,
      0.7152,
      0.0722,
      0,
      0,
      0.2126,
      0.7152,
      0.0722,
      0,
      0,
      0.2126,
      0.7152,
      0.0722,
      0,
      0,
      0,
      0,
      0,
      1,
      0,
    ]);
  }

  static ColorFilter protanopia() {
    return const ColorFilter.matrix(<double>[
      0.56667,
      0.43333,
      0,
      0,
      0,
      0.55833,
      0.44167,
      0,
      0,
      0,
      0,
      0.24167,
      0.75833,
      0,
      0,
      0,
      0,
      0,
      1,
      0,
    ]);
  }
}
