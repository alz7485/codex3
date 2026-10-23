"""Render the real speech flow and dedicated history window, using synthetic data."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from datetime import datetime, timedelta
from pathlib import Path
import shutil
import subprocess
import tempfile

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from companion.core import Notice
from companion.ui import HistoryWindow, InteractionBubble, Mascot, create_application


def main(export_gif=False):
    app = create_application()
    destination = Path(__file__).parent / 'docs'
    destination.mkdir(exist_ok=True)
    now = datetime.now().astimezone() - timedelta(days=1)
    rows = [('予算.xlsx', 'C:\\work\\営業部\\予算.xlsx', 'Excel', now.isoformat()),
            ('予算.xlsx', 'C:\\work\\総務部\\予算.xlsx', 'Excel', (now - timedelta(minutes=30)).isoformat()),
            ('議事録.docx', 'C:\\work\\会議\\議事録.docx', 'Word', (now - timedelta(hours=1)).isoformat())]
    history = HistoryWindow()
    history.resize(1000, 580)
    history.calendar.setSelectedDate(QDate(now.year, now.month, now.day))
    history.set_records(rows, '記録オン · 表示例（合成データ） · 過去3か月')
    history.show()
    bubbles = [InteractionBubble() for _ in range(3)]
    bubbles[0].open_choices('お呼びですか？', '余白ノート')
    bubbles[1].open_choices(name='余白ノート')
    bubbles[1].display(Notice('余白ノート', '操作が続いていますね。\nそろそろ、目に白紙の時間をどうぞ。'))
    bubbles[2].open_choices(name='余白ノート')
    bubbles[2].content('calendar', '余白ノート', 'このあとの予定はこちらです。\n\n14:00–14:30  [未承諾] 予定あり\n15:00–15:30  予定あり\n\n件名は隠しておきますね。')
    mascot = Mascot(90, character='A')
    mascot.frame_index = 2
    mascot.show()
    app.processEvents()
    history.grab().save(str(destination / 'history-calendar.png'))

    board = QPixmap(1400, 1480)
    board.fill(QColor('#e7ede6'))
    painter = QPainter(board)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    def text(x, y, value, size=14, bold=False, color='#344f3f'):
        font = QFont(app.font())
        font.setPixelSize(size)
        font.setBold(bold)
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(x, y, value)

    text(65, 48, 'Y O H A K U  /  v0.11.0', 12, True)
    text(65, 99, '左で一言。右で呼び出し。', 30, True)
    text(65, 135, '予定は淡い黄、新着通知は淡い青。履歴と設定は専用画面へ。', 17)
    for i, caption in enumerate(('01  右クリックで呼び出し', '02  左クリックで一言', '03  予定を聞く')):
        x = 65 + i * 440
        text(x, 186, caption, 17, True)
        painter.drawPixmap(x, 210, bubbles[i].grab())
        painter.drawPixmap(x + 228, 216 + bubbles[i].height(), mascot.grab())
    text(65, 815, '04  ファイル起動履歴を見る → 専用の画面へ', 20, True)
    painter.drawPixmap(65, 840, history.grab())
    text(1060, 905, 'ファイル履歴', 21, True)
    text(1060, 949, 'カレンダーで日付を選択。', 14)
    text(1060, 980, 'ファイル名と保存先を一覧で。', 14)
    text(1060, 1035, '吹き出しの4択から開きます。', 13)
    text(1060, 1066, '記録の設定も、この画面から。', 13)
    text(65, 1445, '実装画面によるプレビュー / 予定とファイル履歴は合成データです。Windows実機では未検証です。', 13, color='#65786a')
    painter.end()
    board.save(str(destination / 'speech-flow.png'))
    board.save(str(destination / 'interaction-preview.png'))

    click_preview = QPixmap(560, 650)
    click_preview.fill(QColor('#e7ede6'))
    painter = QPainter(click_preview)
    text(40, 51, 'キャラを右クリックすると', 23, True)
    painter.drawPixmap(100, 95, bubbles[0].grab())
    painter.drawPixmap(328, 101 + bubbles[0].height(), mascot.grab())
    text(40, 591, '問いかけの下に、4つの選択肢を1行ずつ。', 14)
    text(40, 624, 'v0.11.0 / 実装画面のプレビュー', 12, color='#65786a')
    painter.end()
    click_preview.save(str(destination / 'click-menu.png'))

    if export_gif and shutil.which('ffmpeg'):
        with tempfile.TemporaryDirectory(prefix='yohaku-speech-') as tmp:
            bubble = bubbles[0]
            for index in range(90):
                if index < 25:
                    bubble.open_choices('お呼びですか？', '余白ノート')
                    caption = '右クリックで呼び出し＋4択。'
                elif index < 50:
                    bubble.display(Notice('余白ノート', '肩の力を抜きましょう。\nひと息つくのも、仕事のうちです。'))
                    caption = '左クリックで、一言。'
                elif index < 70:
                    bubble.content('calendar', '余白ノート', 'このあとの予定はこちらです。\n\n14:00–14:30  [未承諾] 予定あり\n15:00–15:30  予定あり')
                    caption = '予定も、同じ吹き出しで。'
                else:
                    bubble.content('activity', '余白ノート', '履歴を開きました。\n日付を選んで、振り返ってみましょう。')
                    caption = '履歴だけ、専用の画面が開きます。'
                mascot.frame_index = 1 if index % 45 in (40, 41) else (2 if index < 50 else 0)
                app.processEvents()
                canvas = QPixmap(960, 820)
                canvas.fill(QColor('#e7ede6'))
                painter = QPainter(canvas)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                text(40, 46, 'Y O H A K U  /  v0.11.0', 12, True)
                text(40, 95, caption, 25, True)
                painter.drawPixmap(580, 163, bubble.grab())
                painter.drawPixmap(805, 169 + bubble.height(), mascot.grab())
                if index >= 70:
                    text(40, 170, 'ファイル履歴の専用ウィンドウ', 16, True)
                    painter.drawPixmap(40, 190, history.grab().scaled(510, 320, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                else:
                    text(40, 255, '普段の吹き出しの中に', 20, True)
                    text(40, 295, 'キャラの問いかけと、4つの選択肢。', 17)
                    text(40, 350, '予定を聞く', 16)
                    text(40, 385, 'ファイル起動履歴を見る', 16)
                    text(40, 420, '設定を開く', 16)
                    text(40, 455, '非表示にする', 16)
                text(40, 780, '実装画面を使用 / 予定と履歴は合成データです。', 12, color='#65786a')
                painter.end()
                canvas.save(str(Path(tmp) / f'frame_{index:03d}.png'))
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-threads', '1', '-filter_complex_threads', '1', '-framerate', '10', '-i', str(Path(tmp) / 'frame_%03d.png'), '-filter_complex', '[0:v]split[a][b];[a]palettegen=max_colors=192[p];[b][p]paletteuse=dither=bayer:bayer_scale=3', '-loop', '0', str(destination / 'animation-preview.gif')], check=True)
    for bubble in bubbles:
        bubble.hide()
    history.hide()
    mascot.hide()
    print('Rendered speech-flow.png, history-calendar.png, interaction-preview.png' + (' and animation-preview.gif' if export_gif else ''))


if __name__ == '__main__':
    main()
