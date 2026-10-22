"""Render the real conversation editor with bundled data and a sample save path."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from tempfile import TemporaryDirectory
from companion.dialogue import DialogueStore
from companion.dialogue_editor import DialogueEditor
from companion.ui import create_application


def main():
    app = create_application()
    with TemporaryDirectory(prefix='yohaku-editor-preview-') as temporary:
        editor = DialogueEditor(DialogueStore(Path(temporary) / 'dialogue.json'))
        editor.path_label.setText(r'保存先：%LOCALAPPDATA%\Yohaku\dialogue.json')
        editor.show()
        destination = Path(__file__).parent / 'docs'
        for index, name in enumerate(('dialogue-editor', 'dialogue-rules', 'dialogue-options')):
            editor.tabs.setCurrentIndex(index)
            if index == 1:
                editor.rule_list.setCurrentRow(next(i for i, rule in enumerate(editor.draft['rules']) if rule['id'] == 'before_meeting'))
            app.processEvents()
            editor.grab().save(str(destination / (name + '.png')))
        editor.hide()
    print('Rendered 3 conversation editor tabs.')


if __name__ == '__main__':
    main()
