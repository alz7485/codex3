"""Explicit bundle smoke check without Controller, user data or Outlook."""
import json
from pathlib import Path
import platform
import sys

from .metadata import VERSION


def check_bundle():
    from PySide6.QtCore import qVersion
    from PySide6.QtGui import QPixmap
    from .dialogue import defaults
    from .ui import InteractionBubble, Mascot, create_application
    from .core import Notice

    app = create_application()
    assets = Path(__file__).parent / 'assets'
    images = ['app/yohaku.png', 'app/yohaku.ico', 'characters/front_reactions.png', 'characters/f_front.png']
    images += [f'characters/{key}{suffix}.png' for key in 'abef' for suffix in ('', '_motion')]
    for name in images:
        if QPixmap(str(assets/name)).isNull():
            raise ValueError('Bundled image cannot be decoded')
    for name in ('default_dialogue', 'personality_wording_v1', 'debtor_wording_v1', 'debtor_style_v1'):
        json.loads((assets/'dialogue'/f'{name}.json').read_text(encoding='utf-8'))
    json.loads((assets/'characters/motion_layout.json').read_text(encoding='utf-8'))
    document = defaults()
    rendered = 0
    for character in 'ABEF':
        widget = Mascot(character=character)
        try:
            for frame in (0, 16, 24, 27):
                widget.frame_index = frame
                if widget.grab().isNull():
                    raise ValueError('Character rendering failed')
                rendered += 1
        finally:
            widget.hide(); widget.deleteLater()
    bubble = InteractionBubble()
    try:
        for notice in (Notice('', '表示の確認'), Notice('', '通知の確認', True, kind='notification')):
            bubble.display(notice)
            if bubble.grab().isNull():
                raise ValueError('Bubble rendering failed')
    finally:
        bubble.hide(); bubble.deleteLater(); app.processEvents()
    return {'version': VERSION, 'python': platform.python_version(), 'qt': qVersion(),
            'platform': sys.platform, 'success': True, 'character_frames_rendered': rendered,
            'topics': len(document['rules']), 'voices': len(document['phrases'])}


def run(output):
    try:
        result = check_bundle()
    except Exception as error:
        # Do not put exception messages, file paths or user content in reports.
        result = {'version': VERSION, 'success': False, 'error_type': type(error).__name__}
    try:
        Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n',
                                encoding='utf-8', newline='\n')
    except OSError:
        return 2
    return 0 if result['success'] else 1
