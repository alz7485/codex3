"""Render actual bubbles for normal remarks, calendar reminders and new Outlook mail."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6.QtGui import QColor,QFont,QPainter,QPixmap
from companion.core import Notice
from companion.ui import InteractionBubble,Mascot,create_application


def main():
    app=create_application()
    board=QPixmap(1260,640);board.fill(QColor('#e7ede6'))
    painter=QPainter(board)
    def text(x,y,value,size=14,bold=False):
        font=QFont(app.font());font.setPixelSize(size);font.setBold(bold)
        painter.setFont(font);painter.setPen(QColor('#344f3f'));painter.drawText(x,y,value)
    text(40,44,'Y O H A K U  /  v0.9.0',13,True)
    text(40,92,'一言、予定、新着。色でも見分けられる。',29,True)
    notices=[Notice('余白ノート','定時まであと約2時間です。\n今日の区切りを考えておきますか。'),
             Notice('予定まで あと10分','そろそろ会議です。\n余白も、持ち物にどうぞ。',True,'notice','calendar'),
             Notice('新着通知 · Outlook','Outlookに1件、新着です。\n読む時間にも余白をどうぞ。',True,'notice','notification')]
    widgets=[]
    for index,(caption,notice) in enumerate(zip(('左クリック / 10分ごとの会話','予定のお知らせ','受信を検知したらすぐ通知'),notices)):
        x=40+index*410;text(x,150,caption,16,True)
        bubble=InteractionBubble();bubble.display(notice)
        mascot=Mascot(100);mascot.frame_index=2 if index==0 else 3;mascot.show();app.processEvents()
        painter.drawPixmap(x,178,bubble.grab());painter.drawPixmap(x+222,186+bubble.height(),mascot.grab())
        widgets.extend((bubble,mascot))
    text(40,565,'右クリックの呼び出し：予定を聞く / ファイル起動履歴を見る / 設定を開く / 非表示にする',15)
    text(40,608,'実装ウィジェットによる表示例 / 予定・メールは合成データ / Windows・実Outlookは未検証',13)
    painter.end();board.save(str(Path(__file__).parent/'docs/notification-colors.png'))
    for widget in widgets:widget.hide()
    print('Rendered notification-colors.png')


if __name__=='__main__':main()
