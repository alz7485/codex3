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
    from .ui import InteractionBubble, Mascot, character_pixmap, create_application
    from .core import Notice
    from .characters import CHARACTERS

    app = create_application()
    assets = Path(__file__).parent / 'assets'
    images = ['app/yohaku.png', 'app/yohaku.ico', 'characters/front_reactions.png', 'characters/holding_poses.png', 'characters/mail_poses.png', 'characters/calendar_poses.png']
    images += [f'characters/{key.lower()}_motion.png' for key in CHARACTERS]
    for name in images:
        if QPixmap(str(assets/name)).isNull():
            raise ValueError('Bundled image cannot be decoded')
    for name in ('default_dialogue', 'personality_wording_v1', 'debtor_wording_v1', 'debtor_style_v1', 'gambler_wording_v1'):
        json.loads((assets/'dialogue'/f'{name}.json').read_text(encoding='utf-8'))
    json.loads((assets/'characters/motion_layout.json').read_text(encoding='utf-8'))
    document = defaults()
    rendered = 0
    for character in CHARACTERS:
        widget = Mascot(character=character)
        try:
            for frame in (0, 16, 24, 27):
                widget.frame_index = frame
                if widget.grab().isNull():
                    raise ValueError('Character rendering failed')
                rendered += 1
        finally:
            widget.hide(); widget.deleteLater()
    # Render all nine added prop poses independently of user files/settings.
    from PySide6.QtWidgets import QStyle
    from .props import prop_frame
    prop_rendered = 0
    for character in CHARACTERS:
        reference = character_pixmap(character)
        for kind in ('file', 'mail', 'calendar'):
            icon = app.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            if prop_frame(character, reference, kind, icon).isNull():
                raise ValueError('Prop rendering failed')
            prop_rendered += 1
    bubble = InteractionBubble()
    try:
        for notice in (Notice('', '表示の確認'), Notice('', '17:00にメールの確認', True, kind='notification', styles=[dict(start=0,length=5,bold=True,color='#28744f')])):
            bubble.display(notice)
            if bubble.grab().isNull():
                raise ValueError('Bubble rendering failed')
    finally:
        bubble.hide(); bubble.deleteLater(); app.processEvents()
    # Exercise the added libraries from the packaged EXE using disposable files,
    # without touching user settings, user documents, printers or Outlook.
    import tempfile
    from datetime import datetime
    import pyzipper
    from PySide6.QtCore import QFile, QIODevice, QSize
    from PySide6.QtGui import QPainter, QPdfWriter
    from PySide6.QtPdf import QPdfDocument
    from .file_drop import defaults as drop_defaults, execute
    from .pdf_print import print_pdf  # Also load the frozen QtPrintSupport library.
    with tempfile.TemporaryDirectory(prefix='yohaku-bundle-') as temporary:
        root = Path(temporary); archive_path = root/'sample.zip'; output = root/'output'; output.mkdir()
        with pyzipper.AESZipFile(archive_path, 'w', encryption=pyzipper.WZ_AES) as archive:
            archive.setpassword(b'check10'); archive.writestr('sample.txt', b'Yohaku')
        rule = drop_defaults()['rules'][1]; rule.update(destination=str(output), password_template='check{month}')
        result = execute('move_extract', archive_path, rule, datetime(2026, 10, 1))
        if (Path(result['extracted'])/'sample.txt').read_bytes() != b'Yohaku':
            raise ValueError('Archive operation failed')
        from .file_destinations import DestinationStore
        from .destination_editor import DestinationEditor
        targets=DestinationStore(root/'file_destinations.json')
        targets.save(dict(schema_version=1,destinations=[dict(id='sample',name='提出用',path=str(output))]))
        staged_bubble=InteractionBubble();destination_editor=DestinationEditor(targets)
        try:
            for stage in ('action','destination','paper'):
                staged_bubble.show_drop_stage(root/'sample.pdf',stage,targets.data['destinations'])
                if staged_bubble.grab().isNull():raise ValueError('Drop stage rendering failed')
            if destination_editor.grab().isNull():raise ValueError('Destination editor rendering failed')
        finally:staged_bubble.hide();destination_editor.hide()
        pdf = root/'sample.pdf'; writer = QPdfWriter(str(pdf)); painter = QPainter(writer)
        painter.drawText(30, 100, 'Yohaku'); painter.end(); del writer
        from .shelf import ShelfStore
        shelf=ShelfStore(root/'shelf.json');shelf.set_period('forever',datetime.now().astimezone())
        shelf_id=shelf.add(pdf,datetime.now().astimezone());shelf_bubble=InteractionBubble()
        try:
            shelf_bubble.show_shelf(shelf.data['items'])
            if shelf_bubble.grab().isNull():raise ValueError('Shelf rendering failed')
            shelf.remove(shelf_id)
            if not pdf.exists():raise ValueError('Shelf changed a document')
        finally:shelf_bubble.hide()
        pdf_document = QPdfDocument()
        pdf_device = QFile(str(pdf))
        try:
            if not pdf_device.open(QIODevice.OpenModeFlag.ReadOnly):
                raise ValueError('PDF read failed')
            pdf_document.load(pdf_device)
            if pdf_document.status() != QPdfDocument.Status.Ready or pdf_document.render(0, QSize(128, 128)).isNull():
                raise ValueError('PDF rendering failed')
        finally:
            pdf_document.close()
            pdf_device.close()
    return {'version': VERSION, 'python': platform.python_version(), 'qt': qVersion(),
            'platform': sys.platform, 'success': True, 'character_frames_rendered': rendered,
            'topics': len(document['rules']), 'voices': len(document['phrases']),
            'encrypted_zip_checked': True, 'pdf_render_checked': True, 'prop_poses_rendered': prop_rendered, 'drop_stages_rendered': 3, 'destination_editor_checked': True, 'shelf_launcher_checked': True}


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
