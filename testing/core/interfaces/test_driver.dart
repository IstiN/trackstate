import '../models/action_availability.dart';

abstract interface class TestDriver {
  Future<void> tapText(String text, {Pattern? within});

  Future<void> tapSemanticsLabel(Pattern label, {Pattern? within});

  bool hasText(String text, {Pattern? within});

  bool hasSemanticsLabel(Pattern label, {Pattern? within});

  ActionAvailability getActionAvailability(String label, {Pattern? within});

  bool hasAnyMessage(Iterable<Pattern> patterns, {Pattern? within});
}
