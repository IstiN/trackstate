import 'dart:ui' show Rect;

import 'package:trackstate/data/repositories/trackstate_repository.dart';

abstract class SettingsProviderDriver {
  Future<void> launchApp({
    required TrackStateRepository repository,
    Map<String, Object> sharedPreferences = const {},
  });

  void resetView();

  Future<void> tapLabeledElement(String label);

  Future<void> enterTextIntoField(String label, String text);
  Future<void> scrollBodyBy(double dy);

  bool isTextVisible(String text);

  int visibleTextCount(String text);

  bool isSelected(String label);

  Rect? rectForText(String text);

  List<String> visibleTexts();
  String? textFieldValue(String label);

  bool isTextFieldReadOnly(String label);

  List<String> visibleProviderLabels();

  bool isProviderSelected(String label);

  Rect? rectForProviderLabel(String label);
}
