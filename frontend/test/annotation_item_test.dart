// 标注模型测试（task_13 D1/D2：样式分类 + 调色板）
import 'package:flutter_test/flutter_test.dart';
import 'package:ai_reader_frontend/features/annotation/domain/annotation_item.dart';

void main() {
  group('AnnotationStyle 分类', () {
    test('七种内容样式 + 边注样式 key 往返', () {
      const styles = [
        AnnotationStyle.highlight,
        AnnotationStyle.halfHighlight,
        AnnotationStyle.underline,
        AnnotationStyle.wavy,
        AnnotationStyle.strike,
        AnnotationStyle.bold,
        AnnotationStyle.italic,
        AnnotationStyle.marginNote,
      ];
      for (final s in styles) {
        expect(AnnotationStyle.fromKey(s.key), s, reason: '${s.key} 应可往返');
      }
      expect(AnnotationStyle.fromKey('mystery'), AnnotationStyle.unknown);
    });

    test('样式分组完备：背景/线条/字型三类覆盖全部内容样式', () {
      final contentStyles = annotationStyleGroups.values.expand((x) => x).toSet();
      expect(contentStyles, containsAll([
        AnnotationStyle.highlight,
        AnnotationStyle.halfHighlight,
        AnnotationStyle.underline,
        AnnotationStyle.wavy,
        AnnotationStyle.strike,
        AnnotationStyle.bold,
        AnnotationStyle.italic,
      ]));
    });
  });

  group('annotationColorPalette', () {
    test('6 色且十六进制合法', () {
      expect(annotationColorPalette.length, 6);
      for (final c in annotationColorPalette) {
        expect(RegExp(r'^#[0-9A-Fa-f]{6}$').hasMatch(c.hex), isTrue, reason: c.hex);
        expect(c.label, isNotEmpty);
      }
      expect(annotationColorPalette.first.hex, '#CA8A04', reason: '默认琥珀');
    });
  });

  group('AnnotationItem.fromListRow', () {
    test('真实后端行（anchor_json 字符串）解析区间与样式', () {
      final item = AnnotationItem.fromListRow({
        'id': 7,
        'book_id': 1,
        'section_id': 2,
        'color': '#34C759',
        'style': 'wavy',
        'note_text': null,
        'anchor_json': '{"paragraph_id":"p2","section_id":2,"start":3,"end":9}',
      });
      expect(item.paragraphId, 'p2');
      expect(item.startOffset, 3);
      expect(item.endOffset, 9);
      expect(item.style, AnnotationStyle.wavy);
      expect(item.colorHex, '#34C759');
      expect(item.hasRange, isTrue);
    });

    test('mock 行（anchor Map + 顶层 paragraph_id）解析', () {
      final item = AnnotationItem.fromListRow({
        'id': 'annot_1',
        'book_id': 1,
        'paragraph_id': 'p3',
        'style': 'margin_note',
        'note_text': '人工批注内容',
        'color': '#007AFF',
        'anchor': {'paragraph_id': 'p3', 'start': 0, 'end': 4},
      });
      expect(item.paragraphId, 'p3');
      expect(item.style, AnnotationStyle.marginNote);
      expect(item.noteText, '人工批注内容');
    });
  });
}
