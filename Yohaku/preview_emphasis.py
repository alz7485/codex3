"""Render the actual emphasis and selection-based notification editor."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6.QtGui import QColor,QFont,QPainter,QPixmap
from companion.core import Notice
from companion.ui import InteractionBubble,create_application


def main():
    app=create_application();board=QPixmap(1110,700);board.fill(QColor('#e7ede6'));p=QPainter(board)
    font=QFont(app.font());font.setPixelSize(19);p.setFont(font);p.setPen(QColor('#344f3f'))
    p.drawText(28,35,'時刻と重要な言葉を見やすく。通知の文字も選んで装飾できます。')
    widgets=[]
    rows=[('予定の確認',Notice('','今日の予定です。\n13:30–14:00 打ち合わせ\n17:00–17:30 振り返り',kind='calendar')),
          ('新着メール',Notice('','メールが届きました。',True,kind='notification')),
          ('ユーザー登録通知',Notice('','提出を17:00までにお願いします。',True,kind='reminder',styles=[dict(start=0,length=2,bold=True,color='#b0443a')]))]
    for i,(title,notice) in enumerate(rows):
        x=25+i*365;p.drawText(x,85,title);b=InteractionBubble();b.display(notice);app.processEvents();p.drawPixmap(x,105,b.grab());widgets.append(b)
    b=InteractionBubble();b.show_one_shot_form();b.reminder_message.set_message('提出を忘れずに。',[dict(start=0,length=2,bold=True,color='#7650a3')]);app.processEvents()
    p.drawText(28,330,'単発通知の編集（文字を選択して太字・色を変更）');p.drawPixmap(28,350,b.grab());widgets.append(b)
    p.drawText(400,405,'本文はそのまま、装飾は範囲ごとにJSONへ保存。')
    p.drawText(400,445,'青・緑・赤・紫・橙・黒から指定できます。')
    p.drawText(400,485,'登録通知と、吹き出しの単発通知の両方に対応。')
    p.end();board.save(str(Path(__file__).parent/'docs/message-emphasis.png'))
    for b in widgets:b.hide()

if __name__=='__main__':main()
