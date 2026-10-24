"""Capture the implemented ratio editor with bundled default conditions."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
from companion.ui import create_application
from companion.dialogue import DialogueStore
from companion.dialogue_editor import DialogueEditor


def main():
    app=create_application()
    with tempfile.TemporaryDirectory() as temporary:
        editor=DialogueEditor(DialogueStore(Path(temporary)/'dialogue.json'))
        editor.resize(1160,820);editor.show()
        row=next(i for i,r in enumerate(editor.draft['rules']) if r['id']=='active_ratio_high')
        editor.tabs.setCurrentIndex(1);editor.rule_list.setCurrentRow(row);app.processEvents()
        editor.grab().save(str(Path(__file__).parent/'docs/ratio-condition.png'))
        editor.dirty=False;editor.hide()
    print('Rendered ratio-condition.png')


if __name__=='__main__':main()
