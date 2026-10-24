"""Render the real bubble UI with synthetic once-only notification content."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6.QtCore import QDate,QTime
from PySide6.QtGui import QColor,QFont,QPainter,QPixmap
from companion.ui import InteractionBubble,create_application
from companion.metadata import VERSION


def main():
    app=create_application()
    menu=InteractionBubble();menu.open_choices('お呼びですか？')
    form=InteractionBubble();form.show_one_shot_form()
    form.reminder_date.setDate(QDate.currentDate().addDays(1));form.reminder_time.setTime(QTime(15,0))
    form.reminder_message.setPlainText('会議資料を確認する')
    form.resize_text();app.processEvents()
    height=max(menu.height(),form.height())+220
    board=QPixmap(1000,height);board.fill(QColor('#e7ede6'));p=QPainter(board)
    def text(x,y,value,size=14,bold=False):
        font=QFont(app.font());font.setPixelSize(size);font.setBold(bold)
        p.setFont(font);p.setPen(QColor('#344f3f'));p.drawText(x,y,value)
    text(40,36,f'Yohaku / v{VERSION}',12,True)
    text(40,80,'ちょっとした用事も、吹き出しで。',26,True)
    text(40,117,'日付・時間・内容を入力して、一度だけのお知らせを登録します。')
    for x,bubble,title in ((50,menu,'呼び出し：5つの選択肢'),(580,form,'通知を設定する')):
        text(x,158,title,15,True);p.drawPixmap(x,178,bubble.grab())
    text(40,height-18,'実装画面による表示例 / 通知内容は合成データ / Windows実機では未検証',12)
    p.end();board.save(str(Path(__file__).parent/'docs/one-shot-reminder.png'))
    menu.hide();form.hide();print('Rendered one-shot-reminder.png')


if __name__=='__main__':main()
