import 'package:flutter/material.dart';

/// AI Reader 核心视觉主题与设计 Token
/// 严格对标 DESIGN.md (iA Writer 极简主义、排版优先与单一强调色)
class ReaderTheme {
  // --- 亮色模式 (Day / Pure Paper) ---
  static const Color lightBgCanvas = Color(0xFFFAFAFA);
  static const Color lightBgSurface = Color(0xFFFFFFFF);
  static const Color lightTextPrimary = Color(0xFF111827);
  static const Color lightTextSecondary = Color(0xFF6B7280);
  static const Color lightTextMuted = Color(0xFF9CA3AF);
  static const Color lightBorderSubtle = Color(0xFFE5E7EB);
  static const Color lightAccentFocus = Color(0xFF007AFF); // iA 经典光标蓝
  static const Color lightHighlightMark = Color(0x66FEF08A); // 40% 黄色高亮

  // --- 暗色模式 (Night / Matte Dark) ---
  static const Color darkBgCanvas = Color(0xFF121214);
  static const Color darkBgSurface = Color(0xFF18181B);
  static const Color darkTextPrimary = Color(0xFFF4F4F5);
  static const Color darkTextSecondary = Color(0xFFA1A1AA);
  static const Color darkTextMuted = Color(0xFF52525B);
  static const Color darkBorderSubtle = Color(0xFF27272A);
  static const Color darkAccentFocus = Color(0xFF38BDF8); // 明晰天青蓝
  static const Color darkHighlightMark = Color(0x4DCA8A04); // 30% 暗调琥珀黄

  // --- 排版度量常数 ---
  static const double readingGoldenWidth = 700.0; // 黄金版心定宽 (680~720px)
  static const double bodyLineHeight = 1.68;      // 黄金行高
  static const double paragraphSpacing = 16.0;    // 段落间距
  static const double focusDimOpacity = 0.65;     // Focus Mode 非焦点段落柔和透明度

  // --- 动画常数 ---
  static const Duration focusTransitionDuration = Duration(milliseconds: 200);
  static const Duration chromeFadeDuration = Duration(milliseconds: 300);

  /// 亮色 ThemeData
  static ThemeData get lightTheme {
    return ThemeData(
      brightness: Brightness.light,
      scaffoldBackgroundColor: lightBgCanvas,
      colorScheme: const ColorScheme.light(
        primary: lightAccentFocus,
        surface: lightBgSurface,
        onSurface: lightTextPrimary,
        outline: lightBorderSubtle,
      ),
      fontFamily: 'Source Han Serif',
      textTheme: const TextTheme(
        bodyLarge: TextStyle(
          fontSize: 18.0,
          height: bodyLineHeight,
          color: lightTextPrimary,
          fontWeight: FontWeight.normal,
        ),
        bodyMedium: TextStyle(
          fontSize: 16.0,
          height: bodyLineHeight,
          color: lightTextPrimary,
        ),
        labelSmall: TextStyle(
          fontSize: 12.0,
          color: lightTextSecondary,
          letterSpacing: 0.2,
        ),
      ),
    );
  }

  /// 暗色 ThemeData
  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: darkBgCanvas,
      colorScheme: const ColorScheme.dark(
        primary: darkAccentFocus,
        surface: darkBgSurface,
        onSurface: darkTextPrimary,
        outline: darkBorderSubtle,
      ),
      fontFamily: 'Source Han Serif',
      textTheme: const TextTheme(
        bodyLarge: TextStyle(
          fontSize: 18.0,
          height: bodyLineHeight,
          color: darkTextPrimary,
          fontWeight: FontWeight.normal,
        ),
        bodyMedium: TextStyle(
          fontSize: 16.0,
          height: bodyLineHeight,
          color: darkTextPrimary,
        ),
        labelSmall: TextStyle(
          fontSize: 12.0,
          color: darkTextSecondary,
          letterSpacing: 0.2,
        ),
      ),
    );
  }
}
