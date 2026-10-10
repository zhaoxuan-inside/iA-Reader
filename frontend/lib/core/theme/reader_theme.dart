import 'package:flutter/material.dart';

/// AI Reader 核心视觉主题与设计 Token
/// 严格对标 DESIGN.md (iA Writer 极简主义哲学、排版优先与单一强调色)
class ReaderTheme {
  // --- 亮色模式 (Day / Pure Paper) ---
  static const Color lightBgCanvas = Color(0xFFFAFAFA);       // 纸张纯净画布
  static const Color lightBgSurface = Color(0xFFFFFFFF);      // 面板与卡片底色
  static const Color lightTextPrimary = Color(0xFF111827);    // 高对比正文
  static const Color lightTextSecondary = Color(0xFF6B7280);  // 次要元数据、极简页眉
  static const Color lightTextMuted = Color(0xFF9CA3AF);      // 失焦弱化与微线
  static const Color lightBorderSubtle = Color(0xFFE5E7EB);   // 1px 极细微线
  static const Color lightAccentFocus = Color(0xFF007AFF);    // iA 经典光标蓝
  static const Color lightHighlightMark = Color(0x66FEF08A);  // 40% 黄色荧光笔

  // --- 暗色模式 (Night / Matte Dark) ---
  static const Color darkBgCanvas = Color(0xFF121214);        // 哑光深炭黑
  static const Color darkBgSurface = Color(0xFF18181B);       // 柔和暗色面板
  static const Color darkTextPrimary = Color(0xFFF4F4F5);     // 护眼暖白
  static const Color darkTextSecondary = Color(0xFFA1A1AA);   // 暗色冷灰元数据
  static const Color darkTextMuted = Color(0xFF52525B);       // 失焦弱化
  static const Color darkBorderSubtle = Color(0xFF27272A);    // 极暗微线
  static const Color darkAccentFocus = Color(0xFF38BDF8);     // 明晰天青蓝
  static const Color darkHighlightMark = Color(0x4DCA8A04);   // 30% 暗调琥珀黄

  // --- 排版度量常数 (Typography Metrics) ---
  static const double readingGoldenWidth = 700.0; // 黄金版心定宽 (680~720px 扫视舒适区)
  static const double bodyLineHeight = 1.72;      // iA 级黄金呼吸感行高
  static const double paragraphSpacing = 22.0;    // 自然舒适的段间留白
  static const double focusDimOpacity = 0.65;     // Focus Mode 非焦点段落柔和透明度

  // --- 字体族配置优先序列 ---
  static const List<String> serifFontFamilyFallback = [
    'iA Writer Duo',
    'Source Han Serif',
    'Noto Serif CJK SC',
    'Songti SC',
    'Merriweather',
    'Georgia',
    'serif',
  ];

  static const List<String> monoFontFamilyFallback = [
    'iA Writer Mono',
    'JetBrains Mono',
    'SF Mono',
    'Menlo',
    'monospace',
  ];

  static const List<String> sansFontFamilyFallback = [
    'Inter',
    'SF Pro Text',
    'PingFang SC',
    'Helvetica Neue',
    'sans-serif',
  ];

  // --- 动画常数 ---
  static const Duration focusTransitionDuration = Duration(milliseconds: 220);
  static const Duration chromeFadeDuration = Duration(milliseconds: 300);
  static const Duration drawerSlideDuration = Duration(milliseconds: 240);

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
      fontFamilyFallback: serifFontFamilyFallback,
      textTheme: const TextTheme(
        bodyLarge: TextStyle(
          fontSize: 18.5,
          height: bodyLineHeight,
          letterSpacing: 0.15,
          color: lightTextPrimary,
          fontWeight: FontWeight.w400,
        ),
        bodyMedium: TextStyle(
          fontSize: 16.0,
          height: bodyLineHeight,
          letterSpacing: 0.1,
          color: lightTextPrimary,
        ),
        labelSmall: TextStyle(
          fontSize: 12.0,
          color: lightTextSecondary,
          letterSpacing: 0.3,
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
      fontFamilyFallback: serifFontFamilyFallback,
      textTheme: const TextTheme(
        bodyLarge: TextStyle(
          fontSize: 18.5,
          height: bodyLineHeight,
          letterSpacing: 0.15,
          color: darkTextPrimary,
          fontWeight: FontWeight.w400,
        ),
        bodyMedium: TextStyle(
          fontSize: 16.0,
          height: bodyLineHeight,
          letterSpacing: 0.1,
          color: darkTextPrimary,
        ),
        labelSmall: TextStyle(
          fontSize: 12.0,
          color: darkTextSecondary,
          letterSpacing: 0.3,
        ),
      ),
    );
  }
}
