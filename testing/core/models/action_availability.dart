class ActionAvailability {
  const ActionAvailability({
    required this.label,
    required this.visible,
    required this.enabled,
  });

  final String label;
  final bool visible;
  final bool enabled;

  bool get isUnavailable => !visible || !enabled;

  String describe() => '$label visible=$visible, enabled=$enabled';
}
