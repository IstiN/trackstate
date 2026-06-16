class LocalizedLabelResolution {
  const LocalizedLabelResolution({
    required this.displayName,
    required this.usedFallback,
    this.requestedLocale,
    this.fallbackLocale,
  });

  final String displayName;
  final bool usedFallback;
  final String? requestedLocale;
  final String? fallbackLocale;
}

mixin LocalizedLabelResolver {
  String get name;
  Map<String, String> get localizedLabels;

  String label([String? locale]) =>
      locale == null ? name : localizedLabels[locale] ?? name;

  LocalizedLabelResolution resolveLabel({
    String? locale,
    String? defaultLocale,
  }) {
    final requestedLocale = locale?.trim();
    if (requestedLocale != null && requestedLocale.isNotEmpty) {
      final requestedLabel = localizedLabels[requestedLocale]?.trim();
      if (requestedLabel != null && requestedLabel.isNotEmpty) {
        return LocalizedLabelResolution(
          displayName: requestedLabel,
          usedFallback: false,
          requestedLocale: requestedLocale,
        );
      }
      final fallbackLocale = defaultLocale?.trim();
      final fallbackLabel = fallbackLocale == null || fallbackLocale.isEmpty
          ? null
          : localizedLabels[fallbackLocale]?.trim();
      if (fallbackLocale != null &&
          fallbackLocale.isNotEmpty &&
          fallbackLocale != requestedLocale &&
          fallbackLabel != null &&
          fallbackLabel.isNotEmpty) {
        return LocalizedLabelResolution(
          displayName: fallbackLabel,
          usedFallback: true,
          requestedLocale: requestedLocale,
          fallbackLocale: fallbackLocale,
        );
      }
      return LocalizedLabelResolution(
        displayName: name,
        usedFallback: true,
        requestedLocale: requestedLocale,
        fallbackLocale: fallbackLocale,
      );
    }

    final fallbackLocale = defaultLocale?.trim();
    final defaultLabel = fallbackLocale == null || fallbackLocale.isEmpty
        ? null
        : localizedLabels[fallbackLocale]?.trim();
    return LocalizedLabelResolution(
      displayName: defaultLabel == null || defaultLabel.isEmpty
          ? name
          : defaultLabel,
      usedFallback: false,
      requestedLocale: fallbackLocale,
    );
  }
}

List<String> resolveEffectiveSupportedLocales(
  String defaultLocale,
  List<String> supportedLocales,
) {
  final locales = <String>[];
  final normalizedDefaultLocale = defaultLocale.trim();
  if (normalizedDefaultLocale.isNotEmpty) {
    locales.add(normalizedDefaultLocale);
  }
  for (final locale in supportedLocales) {
    final normalized = locale.trim();
    if (normalized.isEmpty || locales.contains(normalized)) {
      continue;
    }
    locales.add(normalized);
  }
  return locales;
}
