"""Render the actual front-view sprites and JSON click-reaction dialogue."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile

from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from companion.core import CHARACTERS, Engine, Settings
from companion.metadata import VERSION
from companion.ui import Mascot, create_application


def main():
    app = create_application()
    board = QPixmap(1280, 1000)
    board.fill(QColor('#edf1ea'))
    p = QPainter(board)

    def text(x, y, value, size=15, bold=False):
        font = QFont(app.font())
        font.setPixelSize(size)
        font.setBold(bold)
        p.setFont(font)
        p.setPen(QColor('#344f3f'))
        p.drawText(x, y, value)

    text(36, 38, f'Y O H A K U  /  v{VERSION}', 14, True)
    text(36, 81, 'こちらを向いて、気持ちをひとつ。', 30, True)
    text(36, 112, '正面と連打への反応 / ペンギンは翼2本 / お茶ねこの目を少し猫らしく。', 17)
    for x, caption in zip((265, 505, 745, 985), ('正面', 'まばたき', '4回で困る', '7回で少し怒る')):
        text(x, 150, caption, 16, True)
    with tempfile.TemporaryDirectory() as temporary:
        for row, (character, name) in enumerate(CHARACTERS.items()):
            y = 175 + row * 195
            engine = Engine(Settings(character=character), Path(temporary) / 'history.json', choose=lambda items: items[0])
            mascot = Mascot(130, character=character)
            mascot.show()
            app.processEvents()
            text(36, y + 57, character + '  ' + name, 18, True)
            for column, frame in enumerate((24, 25, 26, 27)):
                mascot.frame_index = frame
                mascot.previous_frame = None
                p.drawPixmap(245 + column * 240, y, mascot.grab())
            for index in range(7):
                notice = engine.click_reaction(index * .2)
                if index == 3: concern = notice.text
            text(280, y + 152, concern, 15)
            text(280, y + 177, notice.text, 15)
            mascot.hide()
    text(36, 986, '反応の本文をクリックして閉じるまで左クリックを停止 / 右クリックは使用可能 / 会話編集でセリフ・判定条件を変更', 14)
    p.end()
    board.save(str(Path(__file__).parent / 'docs/front-reactions.png'))
    print('Rendered docs/front-reactions.png')


if __name__ == '__main__':
    main()
