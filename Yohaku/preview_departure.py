"""Preview the real departure settings and explicit attendance-site action."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from datetime import datetime, timezone
from pathlib import Path
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QScrollArea
from companion.core import Notice, Settings
from companion.departure import departure_body
from companion.metadata import VERSION
from companion.ui import Panel, InteractionBubble, Mascot, create_application


def main():
    app = create_application()
    settings = Settings(departure_enabled=True, attendance_url='https://attendance.example.test/input')
    panel = Panel(settings)
    panel.set_page(1)
    panel.resize(920, 740)
    panel.show()
    app.processEvents()
    for scroll in panel.findChildren(QScrollArea):
        if scroll.isAncestorOf(panel.departure_time):
            scroll.ensureWidgetVisible(panel.departure_time.parentWidget(), 0, 5)
    app.processEvents()
    now = datetime(2026, 10, 23, 17, 0, tzinfo=timezone.utc)
    bubble = InteractionBubble()
    bubble.show_departure(Notice('退勤前のお知らせ', departure_body(settings.departure_message, now, 8.5 * 3600), True, 'notice', 'departure'), True)
    mascot = Mascot(100)
    mascot.frame_index = 3
    mascot.show()
    app.processEvents()
    board = QPixmap(1360, 940)
    board.fill(QColor('#e7ede6'))
    painter = QPainter(board)
    def text(x, y, value, size=15, bold=False):
        font = QFont(app.font())
        font.setPixelSize(size)
        font.setBold(bold)
        painter.setFont(font)
        painter.setPen(QColor('#344f3f'))
        painter.drawText(x, y, value)
    text(35, 42, f'Yohaku  /  v{VERSION}', 13, True)
    text(35, 88, '帰る前に、ひと声。', 30, True)
    text(35, 123, '初期17:00。メッセージとPC起動時間を知らせ、勤怠サイトへ進むか選びます。', 16)
    painter.drawPixmap(35, 155, panel.grab())
    text(985, 195, '指定した時刻に、お知らせ', 18, True)
    painter.drawPixmap(985, 225, bubble.grab())
    painter.drawPixmap(1195, 235 + bubble.height(), mascot.grab())
    text(985, 680, 'URLは利用者が設定で入力。', 15)
    text(985, 712, '開くときだけブラウザーを起動。', 14)
    text(985, 744, '入力・送信は行いません。', 14)
    text(35, 920, '実装UIの表示例 / URL・PC起動時間は合成データ / Windows実機は未検証', 12)
    painter.end()
    board.save(str(Path(__file__).parent / 'docs/departure-preview.png'))
    panel.hide()
    bubble.hide()
    mascot.hide()
    print('Rendered departure-preview.png')


if __name__ == '__main__': main()
