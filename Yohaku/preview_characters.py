"""Render the approved new characters using the actual runtime frames and speech UI."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from companion.characters import CHARACTERS
from companion.core import Notice, Settings
from companion.dialogue import DialogueStore, defaults
from companion.metadata import VERSION
from companion.ui import InteractionBubble, Mascot, Panel, create_application
import tempfile


def main():
    app = create_application()
    board = QPixmap(1440, 850)
    board.fill(QColor('#e7ede6'))
    painter = QPainter(board)
    widgets = []

    def text(x, y, value, size=16, bold=False):
        font = QFont(app.font()); font.setPixelSize(size); font.setBold(bold)
        painter.setFont(font); painter.setPen(QColor('#344f3f')); painter.drawText(x, y, value)

    text(36, 36, f'Yohaku / v{VERSION}', 13, True)
    text(36, 80, '3体の相棒。7つの話し方。', 30, True)
    text(36, 114, 'つづり・ビット・ペンギー / 全7性格のセリフはそのまま', 17)
    for column, (key, profile) in enumerate(defaults()['profiles'].items()):
        left = 25 + column * 470
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor('#f9fbf6'))
        painter.drawRoundedRect(QRectF(left, 140, 450, 465), 18, 18)
        text(left + 22, 180, CHARACTERS[key], 25, True)
        text(left + 22, 212, profile['voice'], 18)
        bubble = InteractionBubble(); bubble.display(Notice('', profile['tagline']))
        app.processEvents(); painter.drawPixmap(left + 22, 232, bubble.grab()); widgets.append(bubble)
        for x, frame, caption in ((left + 25, 24, '正面'), (left + 140, 16, '歩行'),
                                  (left + 245, 26, '困る'), (left + 345, 27, '怒る')):
            mascot = Mascot(88, character=key); mascot.frame_index = frame; mascot.show()
            app.processEvents(); painter.drawPixmap(x, 385, mascot.grab()); widgets.append(mascot)
            text(x + 27, 500, caption, 13)
        text(left + 22, 550, '28コマ / まばたき・表情・歩行8コマ', 15)
        text(left + 22, 580, '足元と中央をそろえて表示', 14)
    text(36, 650, '静かな時間・設定画面を開いている間も歩行。吹き出しの操作中は立ち止まります。', 17)
    for index, (key, name) in enumerate(CHARACTERS.items()):
        x = 150 + index * 470
        mascot = Mascot(72, character=key); mascot.frame_index = 24; mascot.show()
        app.processEvents(); painter.drawPixmap(x + 30, 674, mascot.grab()); widgets.append(mascot)
        text(x + 40, 776, name, 15, True)
    text(36, 825, '実装ウィジェットの表示例 / 画像はローカル素材 / 音声なし・外部AIなし', 13)
    painter.end()
    destination = Path(__file__).parent/'docs'
    board.save(str(destination/'new-characters.png'))
    with tempfile.TemporaryDirectory() as temporary:
        panel = Panel(Settings(character='A'), DialogueStore(Path(temporary)/'dialogue.json'))
        panel.set_page(1); panel.show(); app.processEvents()
        panel.grab().save(str(destination/'settings.png')); panel.hide()
    for widget in widgets:
        widget.hide()
    print('Rendered new-characters.png and settings.png')


if __name__ == '__main__':
    main()
