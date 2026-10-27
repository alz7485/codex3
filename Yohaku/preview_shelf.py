"""Render the native shelf widgets using only temporary sample paths."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
from datetime import datetime
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap,QPainter,QColor,QFont
from PySide6.QtWidgets import QComboBox,QLabel,QVBoxLayout,QWidget
from companion.ui import InteractionBubble,create_application
from companion.shelf import ShelfStore
app=create_application();board=QPixmap(1120,870);board.fill(QColor('#e7ede6'));p=QPainter(board)
font=QFont(app.font());font.setPixelSize(18);p.setFont(font);p.setPen(QColor('#344f3f'));p.drawText(25,35,'預けたものを、いつもの吹き出しから開く。')
widgets=[]
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp);file=root/'資料.xlsx';file.write_bytes(b'example');folder=root/'作業フォルダ';folder.mkdir()
 store=ShelfStore(root/'shelf.json');store.add(file,datetime.now().astimezone());store.add(folder,datetime.now().astimezone())
 examples=[('渡したときの先頭に追加',lambda b:b.show_drop_stage(file,'action')),
           ('呼び出しの先頭から見る',lambda b:b.open_choices()),
           ('アイコン付き一覧（ダブルクリックで開く）',lambda b:b.show_shelf(store.data['items']))]
 for i,(title,show) in enumerate(examples):
  x=25+i*365;p.drawText(x,88,title);b=InteractionBubble();show(b);app.processEvents();p.drawPixmap(x,110,b.grab());widgets.append(b)
 p.drawText(25,575,'保持期間：1日（朝5:00）／1週間（月曜0:00）／1ヶ月（1日0:00）／無期限')
 p.drawText(25,620,'ファイルの右クリック：フォルダを開く／削除')
 p.drawText(25,660,'フォルダの右クリック：削除のみ')
 p.drawText(25,715,'削除・期限切れで外すのは、この一覧の登録だけです。')
 p.drawText(25,755,'ファイルやフォルダ本体をコピー・移動・削除しません。')
p.end();board.save(str(Path(__file__).parent/'docs/shelf.png'))
for w in widgets:w.hide()
