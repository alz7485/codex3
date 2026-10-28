"""Render system-speech examples without PC/Outlook watchers or user data."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor,QFont,QPainter,QPixmap
from companion.core import Notice
from companion.dialogue import DialogueStore,VOICE_NAMES
from companion.dialogue_editor import DialogueEditor
from companion.system_dialogue import render_system_phrase
from companion.ui import InteractionBubble,create_application


def capture(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);app=create_application()
    scene=QPixmap(1060,1050);scene.fill(QColor('#edf2ef'));p=QPainter(scene)
    p.setFont(QFont(app.font().family(),15));p.setPen(QColor('#344e44'));p.drawText(28,38,'操作案内にも、その性格の声を。')
    for n,voice in enumerate(VOICE_NAMES):
        bubble=InteractionBubble();bubble.setFixedWidth(460)
        text=render_system_phrase(voice,'one_shot_saved',replacements={'when':'2026/10/29 17:00'})
        text+='\n\n'+render_system_phrase(voice,'growth_level',replacements={'level':2})
        bubble.display(Notice('',text,True,kind='notification'));bubble.timer.stop();app.processEvents()
        x=28+(n%2)*520;y=78+(n//2)*240
        p.setFont(QFont(app.font().family(),12));p.setPen(QColor('#344e44'));p.drawText(x,y,voice)
        p.drawPixmap(x,y+14,bubble.grab());bubble.hide();bubble.deleteLater()
    p.end();scene.save(str(output/'system-voices.png'))
    with TemporaryDirectory(prefix='yohaku-system-preview-') as temporary:
        editor=DialogueEditor(DialogueStore(Path(temporary)/'dialogue.json'))
        editor.voice.setCurrentText('馴れ馴れしい関西弁')
        for n in range(editor.phrase_topics.count()):
            if editor.phrase_topics.item(n).data(Qt.ItemDataRole.UserRole)=='one_shot_saved':editor.phrase_topics.setCurrentRow(n);break
        editor.show();app.processEvents();editor.grab().save(str(output/'system-editor.png'));editor.hide();editor.deleteLater()
    print(output)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='docs/system-preview');capture(parser.parse_args().output)
