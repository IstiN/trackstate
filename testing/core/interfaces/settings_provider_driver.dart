import 'dart:ui' show Rect;

abstract class SettingsProviderDriver {
  Future<void> launchApp();

  void resetView();

  Future<void> tapLabeledElement(String label);

  Future<void> scrollBodyBy(double dy);

  bool isTextVisible(String text);

  int visibleTextCount(String text);

  bool isSelected(String label);

  Rect? rectForText(String text);
}
