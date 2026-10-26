import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap,QPainter,QColor,QFont
from companion.ui import create_application,Mascot
from companion.characters import CHARACTERS
app=create_application()
with tempfile.TemporaryDirectory() as temp:
 folder=Path(temp)/'資料';folder.mkdir();file=Path(temp)/'報告.pdf';file.touch()
 board=QPixmap(1060,1000);board.fill(QColor('#e7ede6'));p=QPainter(board)
 font=QFont(app.font());font.setPixelSize(19);p.setFont(font);p.setPen(QColor('#344f3f'))
 widgets=[]
 for i,(key,name) in enumerate(CHARACTERS.items()):
  x=40+i*345;p.drawText(x,35,name)
  for row,kind in enumerate(('file','folder','mail','calendar')):
   w=Mascot(200,character=key); w.prop_animation_enabled=False
   if kind=='calendar':w.check_calendar()
   elif kind=='mail':w.raise_mail()
   else:w.hold_item(folder if kind=='folder' else file)
   w.show();app.processEvents();p.drawPixmap(x,65+row*230,w.grab());p.drawText(x+205,165+row*230,{'file':'PDF','folder':'フォルダ','mail':'新着メール','calendar':'予定の確認'}[kind]);widgets.append(w)
 p.end();board.save(str(Path(__file__).parent/'docs/prop-poses.png'))
 for w in widgets:w.hide()
