import 'package:flutter/material.dart';

import '../../../core/theme/reader_theme.dart';

/// 人工批注编辑浮层（task_13 D4）：iA 极简多行输入。
/// 由 main.dart 以 FrostedModal 承载居中弹出。
class NoteEditorPopover extends StatefulWidget {
  final String initialText;
  final ValueChanged<String> onSave;
  final VoidCallback onCancel;

  const NoteEditorPopover({
    Key? key,
    this.initialText = '',
    required this.onSave,
    required this.onCancel,
  }) : super(key: key);

  @override
  State<NoteEditorPopover> createState() => _NoteEditorPopoverState();
}

class _NoteEditorPopoverState extends State<NoteEditorPopover> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialText);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final borderColor = isDark ? ReaderTheme.darkBorderSubtle : ReaderTheme.lightBorderSubtle;
    final textColor = isDark ? ReaderTheme.darkTextPrimary : ReaderTheme.lightTextPrimary;
    final textSecondary = isDark ? ReaderTheme.darkTextSecondary : ReaderTheme.lightTextSecondary;
    final accent = isDark ? ReaderTheme.darkAccentFocus : ReaderTheme.lightAccentFocus;

    return Padding(
      padding: const EdgeInsets.all(18.0),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('人工批注',
              style: TextStyle(
                  fontFamily: 'iA Writer Mono',
                  fontSize: 13.0,
                  fontWeight: FontWeight.w600,
                  color: textColor,
                  letterSpacing: 0.5)),
          const SizedBox(height: 10.0),
          TextField(
            controller: _controller,
            maxLines: 6,
            minLines: 4,
            autofocus: true,
            style: TextStyle(fontFamily: 'iA Writer Mono', fontSize: 13.0, color: textColor, height: 1.6),
            decoration: InputDecoration(
              hintText: '写下你对这段内容的想法…',
              hintStyle: TextStyle(fontSize: 12.5, color: textSecondary),
              contentPadding: const EdgeInsets.all(12.0),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8.0),
                borderSide: BorderSide(color: borderColor, width: 0.8),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8.0),
                borderSide: BorderSide(color: accent, width: 1.0),
              ),
            ),
          ),
          const SizedBox(height: 12.0),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                onPressed: widget.onCancel,
                child: Text('取消', style: TextStyle(fontSize: 12.5, color: textSecondary)),
              ),
              const SizedBox(width: 8.0),
              TextButton(
                onPressed: () => widget.onSave(_controller.text.trim()),
                child: Text('保存批注',
                    style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                        color: accent)),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
