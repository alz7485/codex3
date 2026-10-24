"""Real history links and calendar buttons, using only synthetic names and dates."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6.QtGui import QColor,QFont,QPainter,QPixmap
from companion.ui import InteractionBubble,Mascot,create_application
from companion.metadata import VERSION


def main():
    app=create_application();board=QPixmap(1120,570);board.fill(QColor('#e7ede6'));p=QPainter(board)
    def text(x,y,value,size=14,bold=False):
        font=QFont(app.font());font.setPixelSize(size);font.setBold(bold);p.setFont(font);p.setPen(QColor('#344f3f'));p.drawText(x,y,value)
    text(40,38,f'Yohaku / v{VERSION}',12,True);text(40,82,'まずは、吹き出しで。',28,True)
    text(40,118,'日付選択や検索が必要になったら、管理画面へ。')
    history=InteractionBubble();history.show_file_history('今日のファイル起動履歴は、こちらです。',[
        ('予算.xlsx','C:/work/予算.xlsx'),('打合せメモ.docx','C:/work/打合せメモ.docx'),('日報.xlsx','C:/work/日報.xlsx')])
    calendar=InteractionBubble();calendar.content('calendar','','このあとの予定はこちらです。\n\n14:00–14:30  [未承諾] 予定あり\n15:00–15:30  予定あり')
    widgets=[history,calendar]
    for x,bubble,caption in ((40,history,'今日開いたファイル'),(600,calendar,'予定からOutlookへ')):
        text(x,158,caption,16,True);mascot=Mascot(90,character='A');mascot.frame_index=2;mascot.show();app.processEvents()
        p.drawPixmap(x,182,bubble.grab());p.drawPixmap(x+230,190+bubble.height(),mascot.grab());widgets.append(mascot)
    text(40,540,'実装画面による表示例 / ファイル名・予定は合成データ / Windows実機では未検証',12)
    p.end();board.save(str(Path(__file__).parent/'docs/conversation-navigation.png'))
    for widget in widgets:widget.hide()
    print('Rendered conversation-navigation.png')


if __name__=='__main__':main()
