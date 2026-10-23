"""Render the real draggable widgets with synthetic message content."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
from unittest.mock import patch

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from companion.core import Notice, Settings, save_json
from companion.metadata import VERSION
from companion.ui import Controller, create_application
from dataclasses import asdict


def main():
    with tempfile.TemporaryDirectory(prefix='yohaku-drag-') as temporary, patch.dict(os.environ, {'LOCALAPPDATA': temporary}):
        save_json(Path(temporary) / 'Yohaku/settings.json', asdict(Settings(
            context_enabled=False, mail_enabled=False, animation=False, quiet_start='00:00', quiet_end='00:00')))
        app = create_application()
        controller = Controller(app)
        controller.panel.hide()
        board = QPixmap(1240, 830)
        board.fill(QColor('#e7ede6'))
        painter = QPainter(board)

        def text(x, y, value, size=14, bold=False):
            font = QFont(app.font())
            font.setPixelSize(size)
            font.setBold(bold)
            painter.setFont(font)
            painter.setPen(QColor('#344f3f'))
            painter.drawText(x, y, value)

        text(40, 42, f'Y O H A K U  /  v{VERSION}', 13, True)
        text(40, 90, '好きな場所に。言葉は、そのまま。', 30, True)
        text(40, 125, 'ドラッグで移動・位置を保存。左クリックで一言、右クリックで呼び出し。', 16)
        with patch.object(controller, 'resident_area', return_value=QRect(0, 0, 380, 560)):
            for index, (caption, point) in enumerate((
                ('01  通常メッセージは本文だけ', QPoint(215, 420)),
                ('02  上端では吹き出しを下へ', QPoint(145, 22)),
                ('03  右クリックの5択はそのまま', QPoint(215, 420)),
            )):
                left = 35 + index * 400
                text(left + 5, 175, caption, 16, True)
                painter.fillRect(QRect(left, 197, 380, 560), QColor('#f3f6f1'))
                if index == 2:
                    controller.bubble.open_choices('お呼びですか？', '余白ノート')
                else:
                    controller.bubble.display(Notice('', '少しだけ、目に白紙の時間を。\nひと息ついてから、続きをどうぞ。'))
                controller.drag_character(point)
                app.processEvents()
                painter.drawPixmap(left + controller.bubble.x(), 197 + controller.bubble.y(), controller.bubble.grab())
                painter.drawPixmap(left + controller.resident.x(), 197 + controller.resident.y(), controller.resident.grab())
        text(40, 801, '実装ウィジェットの描画 / メッセージは表示例 / Windows実機の描画は未検証', 12)
        painter.end()
        board.save(str(Path(__file__).parent / 'docs/draggable-preview.png'))
        controller.shutdown()
        controller.resident.hide()
        controller.bubble.hide()
        controller.tray.hide()
    print('Rendered draggable-preview.png')


if __name__ == '__main__':
    main()
