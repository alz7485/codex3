"""Render new personality lines using the actual speech bubble widgets."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6.QtGui import QColor,QFont,QPainter,QPixmap
from companion.core import Notice
from companion.dialogue import ADDED_VOICE_NAMES,defaults
from companion.metadata import VERSION
from companion.ui import InteractionBubble,Mascot,create_application


def main():
    app=create_application();document=defaults()
    board=QPixmap(1120,700);board.fill(QColor('#e7ede6'));p=QPainter(board);widgets=[]
    def text(x,y,value,size=14,bold=False):
        font=QFont(app.font());font.setPixelSize(size);font.setBold(bold)
        p.setFont(font);p.setPen(QColor('#344f3f'));p.drawText(x,y,value)
    text(40,36,f'Yohaku / v{VERSION}',12,True)
    text(40,80,'同じ相棒に、違う話し方を。',28,True)
    text(40,115,'設定 → キャラの性格 / 見た目とは別に、7種類から選べます。')
    for i,voice in enumerate(ADDED_VOICE_NAMES):
        x=35+i*365;text(x,167,voice,18,True)
        for y,key,caption in ((205,'call','呼びかけ'),(315,'chat','普段の一言'),(430,'click_concern','連続クリックへの反応')):
            text(x,y,caption,12)
            bubble=InteractionBubble();bubble.display(Notice('',document['phrases'][voice]['smalltalk' if voice=='孤高のギャンブラー' and key=='chat' else key][0]))
            app.processEvents();p.drawPixmap(x,y+12,bubble.grab());widgets.append(bubble)
        mascot=Mascot(72,character='ABE'[i]);mascot.frame_index=24;mascot.show();app.processEvents()
        p.drawPixmap(x+235,570,mascot.grab());widgets.append(mascot)
    text(40,676,'実装ウィジェットによるセリフの表示例 / 7性格、合計1,519件 / Windows実機では未検証',12)
    p.end();board.save(str(Path(__file__).parent/'docs/personality-examples.png'))
    for widget in widgets:widget.hide()
    print('Rendered personality-examples.png')


if __name__=='__main__':main()
