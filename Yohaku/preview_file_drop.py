"""Render the actual staged choices and named destination editor, without jobs."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
from PySide6.QtGui import QColor,QFont,QPainter,QPixmap
from companion.ui import InteractionBubble,Mascot,create_application
from companion.file_destinations import DestinationStore
from companion.destination_editor import DestinationEditor
from companion.metadata import VERSION

def main():
    app=create_application();board=QPixmap(1480,650);board.fill(QColor('#e7ede6'));p=QPainter(board);widgets=[]
    font=QFont(app.font());font.setPixelSize(19);p.setFont(font);p.setPen(QColor('#344f3f'))
    p.drawText(25,35,f'Yohaku v{VERSION} / 吹き出しで順番に選ぶ')
    rows=[dict(id='submit',name='提出用',path='C:\\Yohaku\\提出用'),dict(id='archive',name='保管用',path='D:\\保管')]
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary);pdf=root/'資料.pdf';pdf.touch();folder=root/'資料フォルダー';folder.mkdir()
        for index,(title,path,stage,key) in enumerate([('PDFを渡す',pdf,'action','A'),('移動する → 移動先を選ぶ',pdf,'destination','B'),('印刷する → 用紙を選ぶ',pdf,'paper','E'),('その他のファイル・フォルダー',folder,'action','A')]):
            x=25+index*365;p.drawText(x,85,title)
            bubble=InteractionBubble();bubble.show_drop_stage(path,stage,rows);app.processEvents();p.drawPixmap(x,108,bubble.grab());widgets.append(bubble)
            mascot=Mascot(100,character=key);mascot.prop_animation_enabled=False;mascot.hold_item(path);mascot.show();app.processEvents();p.drawPixmap(x+210,112+bubble.height(),mascot.grab());widgets.append(mascot)
        p.drawText(25,610,'移動先を編集する → 吹き出しを閉じて編集画面へ。PDFは選択した用紙で既定プリンターへ印刷。')
        p.end();board.save(str(Path(__file__).parent/'docs/file-drop.png'))
        store=DestinationStore(root/'file_destinations.json');store.data=dict(schema_version=1,destinations=rows)
        editor=DestinationEditor(store);editor.show();app.processEvents();editor.grab().save(str(Path(__file__).parent/'docs/file-drop-settings.png'));editor.hide()
    for w in widgets:w.hide()

if __name__=='__main__':main()
