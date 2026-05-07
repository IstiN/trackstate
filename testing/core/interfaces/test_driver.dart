import '../models/action_availability.dart';

abstract interface class TestDriver {
  Future<void> tapText(String text);

  Future<void> tapSemanticsLabel(Pattern label);

  bool hasText(String text);

  bool hasSemanticsLabel(Pattern label);

  ActionAvailability getActionAvailability(String label);

  bool hasAnyMessage(Iterable<Pattern> patterns);
}
