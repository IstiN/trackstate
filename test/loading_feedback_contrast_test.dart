import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

import '../testing/core/utils/color_contrast.dart';

void main() {
  test('loading feedback theme tokens keep WCAG AA contrast in both themes', () {
    for (final entry in <({String name, TrackStateColors colors})>[
      (name: 'light', colors: TrackStateColors.light),
      (name: 'dark', colors: TrackStateColors.dark),
    ]) {
      expect(
        contrastRatio(
          entry.colors.loadingFeedbackForeground,
          entry.colors.loadingFeedbackBackground,
        ),
        greaterThanOrEqualTo(4.5),
        reason:
            '${entry.name} theme loading feedback must stay at or above 4.5:1.',
      );
    }
  });
}
