"""Render current history and adaptive speech using disposable example data."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from datetime import datetime
from pathlib import Path
from PySide6.QtGui import QColor,QFont,QPainter,QPixmap
from companion.core import Notice
from companion.ui import HistoryWindow,InteractionBubble,create_application
app=create_application();now=datetime.now().astimezone()
rows=[(f'資料_{i:02d}.xlsx',f'C:\\資料\\資料_{i:02d}.xlsx','Excel',now.isoformat()) for i in range(1,41)]
window=HistoryWindow();window.set_records(rows,'表示例（合成データ）');window.show();app.processEvents()
board=QPixmap(1560,1110);board.fill(QColor('#e7ede6'));p=QPainter(board);font=QFont(app.font());font.setPixelSize(18);p.setFont(font);p.setPen(QColor('#344f3f'))
p.drawText(20,30,'履歴の行間を詰め、内容が多い吹き出しは高さを広げる。')
p.drawPixmap(20,55,window.grab())
links=InteractionBubble();links.resize_text(700);links.show_file_history('今日のファイル履歴はこちらです。',[(r[0],r[1]) for r in rows]);app.processEvents();p.drawPixmap(1220,55,links.grab())
calendar=InteractionBubble();calendar.resize_text(600);calendar.display(Notice('','このあとの予定です。\n'+'\n'.join(f'{i:02d}:00–{i:02d}:30 予定あり' for i in range(8,21)),kind='calendar'));app.processEvents();p.drawPixmap(20,710,calendar.grab())
short=InteractionBubble();short.display(Notice('','短いメッセージはコンパクトに。'));app.processEvents();p.drawPixmap(400,710,short.grab())
p.end();board.save(str(Path(__file__).parent/'docs/compact-history.png'))
for w in (window,links,calendar,short):w.hide()
