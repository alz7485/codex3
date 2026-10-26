"""Drop gestures and explicit choice execution; all filesystem data is synthetic."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QPdfWriter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog, QSystemTrayIcon
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter

from companion.core import Notice, Settings, save_json
from companion.file_drop import defaults
from companion.file_drop_editor import FileDropEditor
from companion.pdf_print import print_pdf
from companion.ui import Controller, create_application


class FileDropUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        save_json(self.root/'Yohaku/settings.json', asdict(Settings(context_enabled=False, mail_enabled=False,
                                                                quiet_start='00:00', quiet_end='00:00')))
        with patch.dict(os.environ, LOCALAPPDATA=self.temporary.name), patch.object(QSystemTrayIcon, 'isSystemTrayAvailable', return_value=True):
            self.c = Controller(self.app)
        self.addCleanup(self.cleanup)
        for timer in (self.c.tick_timer, self.c.poll_timer, self.c.animation_timer, self.c.activity_timer, self.c.context_timer):
            timer.stop()
        self.output = self.root/'out'; self.output.mkdir()
        document = defaults()
        for rule in document['rules']: rule['destination'] = str(self.output)
        self.c.file_drop_service.store.save(document)
        self.c.panel.hide()

    def cleanup(self):
        self.wait_worker()
        c = self.c; c.shutdown(); c.tray.hide()
        for widget in (c.panel, c.resident, c.bubble, c.history_window): widget.hide()
        c.deleteLater(); self.app.processEvents()

    def wait_worker(self):
        import time
        deadline = time.monotonic()+5
        while self.c.file_drop_service.busy and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertFalse(self.c.file_drop_service.busy)

    def file(self, name, data=b'content'):
        path = self.root/name; path.write_bytes(data); return path

    def gesture(self, urls):
        mime = QMimeData(); mime.setUrls(urls)
        actions = Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
        enter = QDragEnterEvent(QPoint(40, 40), actions, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.c.resident.dragEnterEvent(enter)
        drop = QDropEvent(QPointF(40, 40), actions, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.c.resident.dropEvent(drop)
        return enter, drop

    def test_drop_does_not_execute_until_the_user_chooses_move_and_executes_only_once(self):
        source = self.file('資料.txt')
        enter, drop = self.gesture([QUrl.fromLocalFile(str(source))])
        self.assertTrue(enter.isAccepted()); self.assertTrue(drop.isAccepted())
        self.assertEqual(drop.dropAction(), Qt.DropAction.CopyAction)
        self.assertFalse(self.c.resident.drop_hover)
        self.assertTrue(source.exists()); self.assertEqual(list(self.output.iterdir()), [])
        self.assertEqual(self.c.bubble.current, 'file_drop'); self.assertFalse(self.c.bubble.timer.isActive())
        self.assertTrue(self.c.bubble.drop_buttons['move'].isVisible())
        self.assertFalse(self.c.bubble.drop_buttons['print_pdf'].isVisible())
        self.c.bubble.drop_buttons['move'].click(); self.c.file_drop_service.run('move')
        self.wait_worker()
        self.assertFalse(source.exists()); self.assertEqual((self.output/source.name).read_bytes(), b'content')
        self.assertIn('移動しました', self.c.bubble.text.text())

    def test_cancel_and_changed_file_do_not_move_and_pdf_print_uses_dialog(self):
        source = self.file('資料.pdf')
        self.c.file_drop_service.drop(source)
        self.assertTrue(self.c.bubble.drop_buttons['move'].isVisible())
        self.assertTrue(self.c.bubble.drop_buttons['print_pdf'].isVisible())
        self.c.bubble.drop_cancel.click(); self.c.file_drop_service.run('move')
        self.assertTrue(source.exists()); self.assertEqual(list(self.output.iterdir()), [])
        self.c.file_drop_service.drop(source); source.write_bytes(b'edited document')
        self.c.file_drop_service.run('move'); self.assertTrue(source.exists())
        self.assertIn('変更', self.c.bubble.text.text())
        self.c.file_drop_service.drop(source)
        with patch('companion.pdf_print.print_pdf', return_value=False) as printing:
            self.c.bubble.drop_buttons['print_pdf'].click(); printing.assert_called_once()
        self.assertTrue(source.exists()); self.assertIn('キャンセル', self.c.bubble.text.text())

    def test_remote_urls_multiple_files_folders_and_links_do_not_run(self):
        one = self.file('one.txt'); two = self.file('two.txt')
        for urls in ([QUrl('https://example.invalid/a.zip')], [QUrl('file:relative.txt')], [QUrl.fromLocalFile(str(one)), QUrl.fromLocalFile(str(two))]):
            enter, drop = self.gesture(urls)
            self.assertFalse(enter.isAccepted()); self.assertFalse(drop.isAccepted())
        self.c.file_drop_service.drop(self.output)
        self.assertIn('フォルダー', self.c.bubble.text.text())
        self.assertTrue(one.exists()); self.assertTrue(two.exists())

    def test_unconfigured_move_prompts_settings_and_editor_saves_month_template(self):
        self.c.file_drop_service.store.save(defaults())
        self.c.file_drop_service.drop(self.file('data.zip'))
        self.assertFalse(self.c.bubble.drop_buttons['move_extract'].isEnabled())
        self.c.bubble.drop_settings_button.click()
        editor = self.c.file_drop_service.editor
        self.assertIsInstance(editor, FileDropEditor)
        editor.selector.setCurrentIndex(1)
        self.assertEqual(editor.password.echoMode(), editor.password.EchoMode.Password)
        editor.folder.setText(str(self.output)); editor.password.setText('sample{month}'); editor.save()
        saved = json.loads((self.root/'Yohaku/file_drop_settings.json').read_text())
        self.assertEqual(saved['rules'][1]['password_template'], 'sample{month}')
        self.assertTrue(self.c.bubble.drop_buttons['move_extract'].isEnabled())
        editor.hide()

    def test_drop_choices_hold_while_mail_is_shown_inline_and_not_during_reminder_input(self):
        source = self.file('a.txt'); self.c.file_drop_service.drop(source)
        self.c.show_message(); self.c.tick()
        self.assertEqual(self.c.bubble.current, 'file_drop')
        self.c.settings.outlook_enabled = self.c.settings.mail_enabled = True
        self.c.mail_result(self.c.mail_generation, {'messages': [{'kind': 'mail'}]}, '')
        self.assertEqual(self.c.bubble.current, 'file_drop')
        self.assertTrue(self.c.bubble.drop_notice.isVisible())
        self.c.bubble.show_one_shot_form(); self.c.bubble.reminder_message.setPlainText('入力を保持')
        enter, drop = self.gesture([QUrl.fromLocalFile(str(source))])
        self.assertFalse(enter.isAccepted()); self.assertFalse(drop.isAccepted())
        self.assertEqual(self.c.bubble.reminder_message.toPlainText(), '入力を保持')

    def test_disabled_drop_and_quit_while_busy_are_respected(self):
        self.c.file_drop_service.store.data['enabled'] = False
        enter, drop = self.gesture([QUrl.fromLocalFile(str(self.file('a.txt')))])
        self.assertFalse(enter.isAccepted()); self.assertFalse(drop.isAccepted())
        self.c.file_drop_service.store.data['enabled'] = True
        self.c.pending_reaction = Notice('', '待って。', expression='angry')
        enter, drop = self.gesture([QUrl.fromLocalFile(str(self.root/'a.txt'))])
        self.assertFalse(enter.isAccepted()); self.assertFalse(drop.isAccepted())
        self.c.pending_reaction = None
        self.c.file_drop_service.busy = True
        try:
            with patch.object(self.app, 'quit') as quitting:
                self.c.request_quit(); quitting.assert_not_called()
            self.assertIn('処理中', self.c.panel.saved_label.text())
        finally: self.c.file_drop_service.busy = False

    def test_late_file_result_preserves_a_new_reminder_form(self):
        self.c.bubble.show_one_shot_form(); self.c.bubble.reminder_message.setPlainText('編集中の通知')
        self.c.file_drop_service.finished({'path': str(self.output/'moved.txt')}, '')
        self.assertEqual(self.c.bubble.current, 'one_shot')
        self.assertEqual(self.c.bubble.reminder_message.toPlainText(), '編集中の通知')
        self.assertIn('移動しました', self.c.bubble.inline_mail.text())
        self.assertFalse(self.c.bubble.timer.isActive())

    def test_pdf_parser_and_print_cancel_do_not_submit_a_job(self):
        path = self.root/'real.pdf'; writer = QPdfWriter(str(path)); painter = QPainter(writer)
        painter.drawText(50, 100, 'Synthetic document'); painter.end(); del writer
        with patch('companion.pdf_print.QPrintDialog.exec', return_value=QDialog.DialogCode.Rejected):
            self.assertFalse(print_pdf(path))
        self.assertTrue(path.exists())
        moved = path.with_name('after-cancel.pdf')
        path.rename(moved); moved.rename(path)  # The source must not stay locked on Windows.

    def test_closed_application_does_not_redisplay_a_late_result(self):
        self.c.file_drop_service.closed = True; self.c.bubble.hide()
        self.c.file_drop_service.finished({'path': str(self.output/'a.txt')}, '')
        self.assertFalse(self.c.bubble.isVisible())

    def test_sharing_hides_settings_and_rejects_an_open_print_dialog(self):
        dialog = QDialog(); dialog.show(); self.c.file_drop_service.print_dialog = dialog
        self.c.file_drop_service.show_editor()
        try:
            with patch.object(dialog, 'reject', wraps=dialog.reject) as rejected:
                self.c.share(); rejected.assert_called_once()
            self.assertFalse(dialog.isVisible())
            self.assertFalse(self.c.file_drop_service.editor.isVisible())
        finally:
            self.c.file_drop_service.print_dialog = None; dialog.hide()
            if self.c.hidden: self.c.share()

    def test_pdf_print_range_renders_only_selected_pages_to_a_synthetic_pdf_printer(self):
        from unittest.mock import Mock
        source = self.root/'two.pdf'; output = self.root/'printed.pdf'
        writer = QPdfWriter(str(source)); painter = QPainter(writer)
        painter.drawText(50, 100, 'First'); writer.newPage(); painter.drawText(50, 100, 'Second')
        painter.end(); del writer
        def fake_dialog(printer, parent):
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat); printer.setOutputFileName(str(output))
            printer.setPrintRange(QPrinter.PrintRange.PageRange); printer.setFromTo(2, 2)
            dialog = Mock(); dialog.exec.return_value = QDialog.DialogCode.Accepted
            return dialog
        with patch('companion.pdf_print.QPrintDialog', side_effect=fake_dialog) as dialog_type:
            dialog_type.PrintDialogOption = __import__('PySide6.QtPrintSupport', fromlist=['QPrintDialog']).QPrintDialog.PrintDialogOption
            self.assertTrue(print_pdf(source))
        document = QPdfDocument()
        try:
            self.assertEqual(document.load(str(output)), QPdfDocument.Error.None_)
            self.assertEqual(document.pageCount(), 1)
        finally: document.close()
