"""Capture actual preset, isolated preview and whole-history search widgets."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from companion.activity import FileHistory, FileObservation
from companion.core import Settings
from companion.dialogue import DialogueStore
from companion.metadata import VERSION
from companion.preview import PreviewWindow
from companion.ui import HistoryWindow, Panel, create_application


def main():
    app = create_application()
    destination = Path(__file__).parent / 'docs'
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        dialogue = DialogueStore(root / 'dialogue.json')
        settings = Settings(interval=30, comfort_preset='restrained', walking=False)
        panel = Panel(settings, dialogue)
        panel.set_page(1)
        panel.show()
        preview = PreviewWindow(settings, dialogue)
        preview.selector.setCurrentIndex(preview.selector.findData('click_angry'))
        preview.show()
        app.processEvents()
        board = QPixmap(1540, 920)
        board.fill(QColor('#e7ede6'))
        painter = QPainter(board)
        font = QFont(app.font()); font.setPixelSize(25); font.setBold(True)
        painter.setFont(font); painter.setPen(QColor('#344f3f'))
        painter.drawText(32, 45, f'YOHAKU v{VERSION} / 距離感を選んで、表情を試す。')
        painter.drawPixmap(24, 80, panel.grab())
        painter.drawPixmap(978, 80, preview.grab())
        font.setPixelSize(15); font.setBold(False); painter.setFont(font)
        painter.drawText(32, 887, '実装画面の描画 / プレビューは本番の通知・履歴・連打判定を変更しません / Windows実機は未検証')
        painter.end()
        board.save(str(destination / 'comfort-preview.png'))
        history = FileHistory(root / 'files.sqlite3')
        now = datetime.now().astimezone()
        history.append([FileObservation(f'C:/work/{folder}/予算.xlsx', '予算.xlsx', 'Excel', now - timedelta(days=days))
                        for folder, days in (('本社', 0), ('支店', 1), ('営業部', 14))], now)
        window = HistoryWindow()
        window.resize(1180, 680)
        window.search_edit.setText('予算')
        window.set_records(history.search('予算', now), '記録オフ · 保存済みの全履歴から検索（表示例）', query='予算')
        window.show()
        app.processEvents()
        window.grab().save(str(destination / 'history-search.png'))
        preview.hide(); panel.hide(); window.hide()
    print('Rendered comfort-preview.png and history-search.png')


if __name__ == '__main__':
    main()
