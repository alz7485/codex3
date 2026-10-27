"""Render the actual pickup and reminder-input widgets for documentation."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from PySide6.QtGui import QPixmap,QPainter,QColor,QFont
from companion.ui import Resident,create_application
from companion.characters import CHARACTERS

app=create_application();board=QPixmap(1050,680);board.fill(QColor('#e7ede6'))
p=QPainter(board);font=QFont(app.font());font.setPixelSize(22);p.setFont(font);p.setPen(QColor('#344f3f'))
p.drawText(28,40,'ドラッグ中はつままれた姿、通知の入力中はメモを取る姿。')
widgets=[]
for column,(key,name) in enumerate(CHARACTERS.items()):
    x=column*340+65;p.drawText(x,88,name)
    for row,kind in enumerate(('pickup','notes')):
        actor=Resident(key);actor.setFixedSize(190,190);actor.prop_animation_enabled=False
        actor.dragging=kind=='pickup'
        if kind=='notes':actor.take_notes()
        p.drawPixmap(x,105+row*270,actor.grab());widgets.append(actor)
    p.drawText(x,325,'ドラッグ中')
    p.drawText(x,595,'通知を入力中')
font.setPixelSize(16);p.setFont(font)
p.drawText(28,650,'メモは鉛筆とまばたきが動きます。入力を閉じると元の姿へ戻ります。')
p.end();board.save(str(Path(__file__).parent/'docs/action-poses.png'))
for widget in widgets:widget.hide();widget.deleteLater()
