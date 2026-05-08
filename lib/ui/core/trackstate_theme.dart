import 'package:flutter/material.dart';

class TrackStateColors extends ThemeExtension<TrackStateColors> {
  const TrackStateColors({
    required this.primary,
    required this.primarySoft,
    required this.secondary,
    required this.secondarySoft,
    required this.accent,
    required this.accentSoft,
    required this.page,
    required this.surface,
    required this.surfaceAlt,
    required this.text,
    required this.muted,
    required this.border,
    required this.success,
    required this.warning,
    required this.error,
    required this.info,
    required this.shadow,
  });

  final Color primary;
  final Color primarySoft;
  final Color secondary;
  final Color secondarySoft;
  final Color accent;
  final Color accentSoft;
  final Color page;
  final Color surface;
  final Color surfaceAlt;
  final Color text;
  final Color muted;
  final Color border;
  final Color success;
  final Color warning;
  final Color error;
  final Color info;
  final Color shadow;

  static const light = TrackStateColors(
    primary: Color(0xFFB24328),
    primarySoft: Color(0xFFF2D2C4),
    secondary: Color(0xFF6D7F4F),
    secondarySoft: Color(0xFFE7EED8),
    accent: Color(0xFFD9A21B),
    accentSoft: Color(0xFFFFF1CF),
    page: Color(0xFFFAF8F4),
    surface: Color(0xFFFFFFFF),
    surfaceAlt: Color(0xFFF1E4D5),
    text: Color(0xFF2D2A26),
    muted: Color(0xFF6B6D63),
    border: Color(0xFFE5D3B8),
    success: Color(0xFF3BBE60),
    warning: Color(0xFFC1B341),
    error: Color(0xFFC25742),
    info: Color(0xFF5A5F18),
    shadow: Color(0x1F2D2A26),
  );

  static const dark = TrackStateColors(
    primary: Color(0xFFE8A085),
    primarySoft: Color(0xFF3E2A25),
    secondary: Color(0xFF9CD648),
    secondarySoft: Color(0xFF26301F),
    accent: Color(0xFFF2B538),
    accentSoft: Color(0xFF3A311C),
    page: Color(0xFF111413),
    surface: Color(0xFF1B1E1D),
    surfaceAlt: Color(0xFF242827),
    text: Color(0xFFFAF8F4),
    muted: Color(0xFFB5A498),
    border: Color(0xFF454540),
    success: Color(0xFF8CB85A),
    warning: Color(0xFFF7C966),
    error: Color(0xFFE8A085),
    info: Color(0xFFE7EED8),
    shadow: Color(0x442D2A26),
  );

  @override
  TrackStateColors copyWith({
    Color? primary,
    Color? primarySoft,
    Color? secondary,
    Color? secondarySoft,
    Color? accent,
    Color? accentSoft,
    Color? page,
    Color? surface,
    Color? surfaceAlt,
    Color? text,
    Color? muted,
    Color? border,
    Color? success,
    Color? warning,
    Color? error,
    Color? info,
    Color? shadow,
  }) {
    return TrackStateColors(
      primary: primary ?? this.primary,
      primarySoft: primarySoft ?? this.primarySoft,
      secondary: secondary ?? this.secondary,
      secondarySoft: secondarySoft ?? this.secondarySoft,
      accent: accent ?? this.accent,
      accentSoft: accentSoft ?? this.accentSoft,
      page: page ?? this.page,
      surface: surface ?? this.surface,
      surfaceAlt: surfaceAlt ?? this.surfaceAlt,
      text: text ?? this.text,
      muted: muted ?? this.muted,
      border: border ?? this.border,
      success: success ?? this.success,
      warning: warning ?? this.warning,
      error: error ?? this.error,
      info: info ?? this.info,
      shadow: shadow ?? this.shadow,
    );
  }

  @override
  TrackStateColors lerp(ThemeExtension<TrackStateColors>? other, double t) {
    if (other is! TrackStateColors) return this;
    return TrackStateColors(
      primary: Color.lerp(primary, other.primary, t)!,
      primarySoft: Color.lerp(primarySoft, other.primarySoft, t)!,
      secondary: Color.lerp(secondary, other.secondary, t)!,
      secondarySoft: Color.lerp(secondarySoft, other.secondarySoft, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      accentSoft: Color.lerp(accentSoft, other.accentSoft, t)!,
      page: Color.lerp(page, other.page, t)!,
      surface: Color.lerp(surface, other.surface, t)!,
      surfaceAlt: Color.lerp(surfaceAlt, other.surfaceAlt, t)!,
      text: Color.lerp(text, other.text, t)!,
      muted: Color.lerp(muted, other.muted, t)!,
      border: Color.lerp(border, other.border, t)!,
      success: Color.lerp(success, other.success, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
      error: Color.lerp(error, other.error, t)!,
      info: Color.lerp(info, other.info, t)!,
      shadow: Color.lerp(shadow, other.shadow, t)!,
    );
  }
}

class TrackStateTheme {
  static ThemeData light() => _theme(Brightness.light, TrackStateColors.light);
  static ThemeData dark() => _theme(Brightness.dark, TrackStateColors.dark);

  static ThemeData _theme(Brightness brightness, TrackStateColors colors) {
    final scheme = ColorScheme(
      brightness: brightness,
      primary: colors.primary,
      onPrimary: const Color(0xFFFAF8F4),
      secondary: colors.secondary,
      onSecondary: colors.text,
      error: colors.error,
      onError: const Color(0xFFFAF8F4),
      surface: colors.surface,
      onSurface: colors.text,
    );
    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: colors.page,
      fontFamily: 'Inter',
      extensions: [colors],
      textTheme: TextTheme(
        displayLarge: TextStyle(
          fontSize: 48,
          fontWeight: FontWeight.w700,
          height: 1.1,
          letterSpacing: -0.96,
          color: colors.text,
        ),
        headlineLarge: TextStyle(
          fontSize: 32,
          fontWeight: FontWeight.w700,
          height: 1.15,
          letterSpacing: -0.64,
          color: colors.text,
        ),
        headlineMedium: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w600,
          height: 1.3,
          color: colors.text,
        ),
        titleMedium: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          color: colors.text,
        ),
        bodyLarge: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w400,
          height: 1.6,
          color: colors.text,
        ),
        bodyMedium: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w400,
          height: 1.5,
          color: colors.text,
        ),
        labelLarge: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: colors.text,
        ),
        labelSmall: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w500,
          letterSpacing: .33,
          color: colors.muted,
        ),
      ),
      focusColor: colors.primarySoft,
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: colors.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: colors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: colors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: colors.primary, width: 2),
        ),
      ),
    );
  }
}

extension TrackStateThemeContext on BuildContext {
  TrackStateColors get ts => Theme.of(this).extension<TrackStateColors>()!;
}
