import 'dart:ui' show Rect;

abstract class SettingsProviderDriver {
  Future<void> launchApp();

  void resetView();

  Future<void> tapLabeledElement(String label);

  Future<void> enterTextIntoField(String label, String text);

  Future<void> scrollBodyBy(double dy);

  bool isTextVisible(String text);

  int visibleTextCount(String text);

  bool isSelected(String label);

  Rect? rectForText(String text);

  String? textFieldValue(String label);

  bool isTextFieldReadOnly(String label);
}
