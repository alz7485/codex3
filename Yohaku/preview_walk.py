"""Export the actual walking renderer for visual review, without Controller."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6.QtGui import QPixmap,QPainter,QColor,QFont
from companion.ui import Resident,create_application
from companion.characters import CHARACTERS

app=create_application();board=QPixmap(1050,640);board.fill(QColor('#e7ede6'))
p=QPainter(board);font=QFont(app.font());font.setPixelSize(21);p.setFont(font);p.setPen(QColor('#344f3f'))
p.drawText(25,38,'左右の足を交互に踏み出す歩行（同じ向きの半周期違い）')
actors=[]
for col,(key,name) in enumerate(CHARACTERS.items()):
    actor=Resident(key);actor.setFixedSize(210,210);actors.append(actor)
    x=col*340+60;p.drawText(x,78,name)
    for row,index in enumerate((16,20)):
        actor.frame_index=index;actor.previous_frame=None
        p.drawPixmap(x,90+row*260,actor.grab())
        p.drawText(x,318+row*260,'右足の踏み出し' if row==0 else '左足の踏み出し')
p.end();board.save(str(Path(__file__).parent/'docs/walk-alternation.png'))
for actor in actors:actor.hide();actor.deleteLater()
