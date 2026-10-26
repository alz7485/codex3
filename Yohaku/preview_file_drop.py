"""Render the actual drop-choice bubbles and limited-rule editor."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from companion.file_drop import FileDropStore, defaults
from companion.file_drop_editor import FileDropEditor
from companion.metadata import VERSION
from companion.ui import InteractionBubble, Mascot, create_application


def main():
    app = create_application(); board = QPixmap(1180, 740); board.fill(QColor('#e7ede6'))
    painter = QPainter(board); widgets = []
    def text(x, y, value, size=16, bold=False):
        font = QFont(app.font()); font.setPixelSize(size); font.setBold(bold)
        painter.setFont(font); painter.setPen(QColor('#344f3f')); painter.drawText(x, y, value)
    text(36, 38, f'Yohaku / v{VERSION}', 13, True)
    text(36, 85, 'ファイルを渡して、処理を選ぶ。', 29, True)
    text(36, 121, '通常は移動、PDFは移動・印刷、ZIPは移動して解凍。選ぶまで実行しません。', 16)
    rules = defaults()['rules']
    for index, (filename, rule, character) in enumerate((('報告書.xlsx', rules[2], 'A'), ('資料.pdf', rules[0], 'B'), ('届いた資料.zip', rules[1], 'E'))):
        x = 30 + index*385; rule['destination'] = 'C:\\Yohaku\\受け取り'
        text(x, 178, filename, 19, True)
        bubble = InteractionBubble(); bubble.show_drop_choices(Path(filename), rule)
        app.processEvents(); painter.drawPixmap(x, 198, bubble.grab()); widgets.append(bubble)
        mascot = Mascot(82, character=character); mascot.frame_index = 24; mascot.show(); app.processEvents()
        painter.drawPixmap(x+230, 198+bubble.height(), mascot.grab()); widgets.append(mascot)
    text(36, 659, 'ZIPのパスワード例：固定部分{month} → 1月は固定部分01、10月は固定部分10', 16)
    text(36, 697, '実装ウィジェットの表示例 / JSONと専用画面で編集 / バッチ・外部コマンドを登録する機能はありません', 13)
    painter.end(); board.save(str(Path(__file__).parent/'docs/file-drop.png'))
    with tempfile.TemporaryDirectory() as temporary:
        store = FileDropStore(Path(temporary)/'file_drop_settings.json'); store.data = defaults()
        store.data['rules'][1]['destination'] = 'C:\\Yohaku\\受け取り'
        store.data['rules'][1]['password_template'] = 'example{month}'
        editor = FileDropEditor(store); editor.selector.setCurrentIndex(1); editor.show(); app.processEvents()
        editor.grab().save(str(Path(__file__).parent/'docs/file-drop-settings.png')); editor.hide()
    for widget in widgets: widget.hide()
    print('Rendered file-drop.png and file-drop-settings.png')


if __name__ == '__main__': main()
