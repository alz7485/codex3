"""Real widgets with synthetic resource values; does not collect PC data."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from companion.core import Engine, Notice, Settings
from companion.dialogue_editor import DialogueEditor
from companion.metadata import VERSION
from companion.ui import InteractionBubble, Mascot, create_application


def main():
    app = create_application()
    destination = Path(__file__).parent / 'docs'
    with TemporaryDirectory(prefix='yohaku-resource-preview-') as temporary:
        engine = Engine(Settings(), Path(temporary)/'history.json', choose=lambda values:values[0])
        engine.context = {'cpu_percent':87, 'memory_percent':92}
        board = QPixmap(1120, 480)
        board.fill(QColor('#e7ede6'))
        painter = QPainter(board)
        widgets = []

        def text(x, y, value, size=14, bold=False):
            font = QFont(app.font()); font.setPixelSize(size); font.setBold(bold)
            painter.setFont(font); painter.setPen(QColor('#344f3f'))
            painter.drawText(x, y, value)

        text(40, 38, f'Yohaku / v{VERSION}', 12, True)
        text(40, 82, 'PCの忙しさも、ひとことに。', 28, True)
        text(40, 117, 'CPU・メモリは通常会話の話題。しきい値とセリフは編集できます。')
        for x, character, topic, caption in ((40,'A','cpu_high','CPU：直近約1分の平均'),
                                               (600,'B','memory_high','メモリ：PC全体の物理RAM')):
            engine.settings.character = character
            text(x, 158, caption, 16, True)
            bubble = InteractionBubble()
            bubble.display(Notice('', engine.phrase(topic)))
            mascot = Mascot(90, character=character); mascot.frame_index = 4; mascot.show()
            app.processEvents()
            painter.drawPixmap(x, 182, bubble.grab())
            painter.drawPixmap(x+230, 190+bubble.height(), mascot.grab())
            widgets.extend((bubble, mascot))
        text(40, 451, '合成データによる表示例 / 使用率は保存しません / Windows実機では未検証', 12)
        painter.end()
        board.save(str(destination/'resource-messages.png'))
        editor = DialogueEditor(engine.dialogue)
        editor.path_label.setText(r'保存先：%LOCALAPPDATA%\Yohaku\dialogue.json')
        editor.tabs.setCurrentIndex(1)
        editor.rule_list.setCurrentRow(next(i for i,r in enumerate(editor.draft['rules']) if r['id']=='cpu_high'))
        editor.resize(1020, 920)
        editor.show(); app.processEvents()
        editor.rule_list.scrollToItem(editor.rule_list.currentItem())
        app.processEvents()
        editor.grab().save(str(destination/'resource-rules.png'))
        editor.hide()
        for widget in widgets: widget.hide()
    print('Rendered resource-messages.png and resource-rules.png')


if __name__ == '__main__':
    main()
