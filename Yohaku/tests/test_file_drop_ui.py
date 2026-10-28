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
            self.c = Controller(self.app,data_path=Path(os.environ["LOCALAPPDATA"])/"Yohaku")
        self.addCleanup(self.cleanup)
        for timer in (self.c.tick_timer, self.c.poll_timer, self.c.animation_timer, self.c.activity_timer, self.c.context_timer):
            timer.stop()
        self.output = self.root/'out'; self.output.mkdir()
        document = defaults()
        for rule in document['rules']: rule['destination'] = str(self.output)
        self.c.file_drop_service.store.save(document)
        self.c.file_drop_service.destinations.save({'schema_version':1,'destinations':[{'id':'out','name':'保管用','path':str(self.output)}]})
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

    def test_zip_choices_extract_to_selected_destination_and_keep_source_with_month_password(self):
        import pyzipper
        source=self.root/'archive.zip';password='prefix'+datetime.now().astimezone().strftime('%m')
        with pyzipper.AESZipFile(source,'w',encryption=pyzipper.WZ_AES) as archive:
            archive.setpassword(password.encode());archive.writestr('note.txt',b'content')
        doc=self.c.file_drop_service.store.data
        for row in doc['rules']:
            if '.zip' in row['extensions']:row['password_template']='prefix{month}'
        self.c.file_drop_service.store.save(doc);self.c.file_drop_service.drop(source)
        self.assertTrue(self.c.bubble.drop_buttons['extract'].isVisible());self.assertFalse(self.c.bubble.drop_buttons['shelve'].isVisible())
        self.assertTrue(self.c.bubble.drop_buttons['move'].isVisible())
        self.c.bubble.drop_buttons['extract'].click();self.assertIn('解凍',self.c.bubble.text.text())
        self.c.bubble.drop_extra_buttons['destination:out'].click();self.wait_worker()
        self.assertTrue(source.exists());self.assertEqual((self.output/'archive/note.txt').read_bytes(),b'content')
        self.assertFalse((self.output/'archive.zip').exists());self.assertIn('ZIP',self.c.bubble.text.text())

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
        self.c.bubble.drop_buttons['move'].click(); self.assertTrue(source.exists())
        self.c.bubble.drop_extra_buttons['destination:out'].click(); self.c.file_drop_service.run('destination:out')
        self.wait_worker()
        self.assertFalse(source.exists()); self.assertEqual((self.output/source.name).read_bytes(), b'content')
        self.assertIn('移動しました', self.c.bubble.text.text())

    def test_cancel_changed_file_and_print_paper_selection(self):
        source=self.file('資料.pdf');self.c.file_drop_service.drop(source)
        self.assertTrue(self.c.bubble.drop_buttons['move'].isVisible())
        self.assertTrue(self.c.bubble.drop_buttons['print_pdf'].isVisible())
        self.assertFalse(self.c.bubble.drop_settings_button.isVisible())
        self.c.bubble.drop_cancel.click();self.c.file_drop_service.run('move');self.assertTrue(source.exists())
        self.c.file_drop_service.drop(source);source.write_bytes(b'edited')
        self.c.file_drop_service.run('move');self.assertIn('変更',self.c.bubble.text.text());self.assertTrue(source.exists())
        self.c.file_drop_service.drop(source)
        with patch('companion.pdf_print.print_pdf',return_value=True) as printing:
            self.c.bubble.drop_buttons['print_pdf'].click();printing.assert_not_called()
            self.assertEqual(set(self.c.bubble.drop_extra_buttons),{'paper:a4','paper:a3','paper:auto'})
            self.c.bubble.drop_extra_buttons['paper:a3'].click();self.wait_worker()
            printing.assert_called_once_with(source,'a3')
        self.assertIn('送信しました',self.c.bubble.text.text());self.assertTrue(source.exists())

    def test_paper_button_prints_real_pdf_in_worker_without_native_printer(self):
        source=self.root/'thread-input.pdf';output=self.root/'thread-output.pdf'
        writer=QPdfWriter(str(source));painter=QPainter(writer)
        painter.drawText(100,200,'Synthetic background print');painter.end();del writer
        def factory():
            printer=QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat);printer.setOutputFileName(str(output));printer.setResolution(300)
            return printer,[]
        self.c.file_drop_service.drop(source);self.c.bubble.drop_buttons['print_pdf'].click()
        with patch('companion.pdf_print.default_printer',side_effect=factory):
            self.c.bubble.drop_extra_buttons['paper:auto'].click();self.wait_worker()
        self.assertIn('送信しました',self.c.bubble.text.text());self.assertTrue(source.exists())
        from PySide6.QtCore import QFile,QIODevice
        device=QFile(str(output));document=QPdfDocument()
        try:
            self.assertTrue(device.open(QIODevice.OpenModeFlag.ReadOnly));document.load(device)
            self.assertEqual(document.status(),QPdfDocument.Status.Ready);self.assertEqual(document.pageCount(),1)
        finally:document.close();device.close()

    def test_remote_urls_and_multiple_files_do_not_run_but_folders_offer_only_move(self):
        one = self.file('one.txt'); two = self.file('two.txt')
        for urls in ([QUrl('https://example.invalid/a.zip')], [QUrl('file:relative.txt')], [QUrl.fromLocalFile(str(one)), QUrl.fromLocalFile(str(two))]):
            enter, drop = self.gesture(urls)
            self.assertFalse(enter.isAccepted()); self.assertFalse(drop.isAccepted())
        self.c.file_drop_service.drop(self.output)
        self.assertEqual(self.c.bubble.current, 'file_drop')
        self.assertTrue(self.c.bubble.drop_buttons['move'].isVisible())
        self.assertFalse(self.c.bubble.drop_buttons['move_extract'].isVisible())
        self.assertTrue(one.exists()); self.assertTrue(two.exists())

    def test_folder_drop_holds_icon_moves_after_choice_and_releases_after_completion(self):
        source = self.root/'資料フォルダ'; source.mkdir(); (source/'資料.txt').write_bytes(b'original')
        enter, drop = self.gesture([QUrl.fromLocalFile(str(source))])
        self.assertTrue(enter.isAccepted()); self.assertTrue(drop.isAccepted())
        self.assertIsNotNone(self.c.resident.held_frame)
        self.c.bubble.drop_buttons['move'].click(); self.c.bubble.drop_extra_buttons['destination:out'].click(); self.wait_worker()
        self.assertFalse(source.exists()); self.assertEqual((self.output/source.name/'資料.txt').read_bytes(), b'original')
        self.assertIsNone(self.c.resident.held_frame)

    def test_cancel_and_replacing_choices_clear_the_held_item(self):
        source = self.file('資料.pdf'); self.c.file_drop_service.drop(source)
        self.assertIsNotNone(self.c.resident.held_icon)
        self.c.bubble.dismiss(); self.assertIsNone(self.c.resident.held_icon)
        self.c.file_drop_service.drop(source); self.c.bubble.open_choices()
        self.assertIsNone(self.c.resident.held_icon); self.assertTrue(source.exists())

    def test_mail_raises_envelope_and_returns_to_held_file_without_losing_choices(self):
        self.c.settings.outlook_enabled = self.c.settings.mail_enabled = True
        self.c.file_drop_service.drop(self.file('資料.txt'))
        held = self.c.resident.held_frame
        self.c.mail_result(self.c.mail_generation, {'messages': [{'kind': 'mail'}]}, '')
        self.assertTrue(self.c.resident.mail_raised); self.assertIsNotNone(self.c.resident.mail_frame)
        self.assertEqual(self.c.bubble.current, 'file_drop')
        self.c.resident.lower_mail(); self.assertFalse(self.c.resident.mail_raised)
        self.assertIs(self.c.resident.held_frame, held)
        self.c.bubble.dismiss(); self.assertIsNone(self.c.resident.held_frame)

    def test_unread_counts_do_not_raise_envelope_and_dismiss_clears_mail_pose(self):
        self.c.settings.outlook_enabled = self.c.settings.mail_enabled = True
        self.c.mail_result(self.c.mail_generation, {'unread_count': 10}, '')
        self.assertFalse(self.c.resident.mail_raised)
        self.c.mail_result(self.c.mail_generation, {'messages': [{'kind': 'mail'}]}, '')
        self.assertTrue(self.c.resident.mail_raised)
        self.c.bubble.dismiss(); self.assertFalse(self.c.resident.mail_raised)
        self.assertFalse(self.c.resident.mail_timer.isActive())

    def test_calendar_requests_and_reminders_check_planner_and_other_messages_do_not(self):
        self.c.select_content('calendar')
        self.assertTrue(self.c.resident.calendar_checking)
        self.assertIsNotNone(self.c.resident.calendar_frame)
        self.c.bubble.dismiss(); self.assertFalse(self.c.resident.calendar_checking)
        for kind in ('calendar', 'reminder', 'departure'):
            self.c.bubble.display(Notice('', '予定のお知らせ', True, kind=kind))
            self.assertTrue(self.c.resident.calendar_checking)
        self.c.bubble.display(Notice('', '普通のひとこと'))
        self.assertFalse(self.c.resident.calendar_checking)
        self.assertFalse(self.c.resident.calendar_timer.isActive())

    def test_character_switch_keeps_held_icon_and_all_three_added_poses_render(self):
        self.c.file_drop_service.drop(self.file('a.txt'))
        icon = self.c.resident.held_icon
        for character in 'ABE':
            self.c.resident.set_character(character)
            self.assertIs(self.c.resident.held_icon, icon)
            self.assertFalse(self.c.resident.grab().isNull())
            self.c.resident.raise_mail(); self.assertFalse(self.c.resident.grab().isNull())
            self.c.resident.lower_mail(); self.c.resident.check_calendar()
            self.assertFalse(self.c.resident.grab().isNull()); self.c.resident.lower_calendar()
        with patch.object(QSystemTrayIcon, 'isSystemTrayAvailable', return_value=True):
            self.c.hide_character()
        self.assertIsNone(self.c.resident.held_icon)
        self.assertFalse(self.c.resident.mail_raised); self.assertFalse(self.c.resident.calendar_checking)

    def test_notification_editors_save_the_selected_bold_color_ranges(self):
        from companion.reminder_editor import ReminderEditor
        from companion.reminders import ReminderStore
        from PySide6.QtGui import QTextCursor
        store=ReminderStore(self.root/'editor-reminders.json');editor=ReminderEditor(store)
        try:
            editor.add_rule();editor.message.setPlainText('提出してください')
            cursor=editor.message.textCursor();cursor.setPosition(0);cursor.setPosition(2,QTextCursor.MoveMode.KeepAnchor)
            editor.message.setTextCursor(cursor);editor.message.bold_button.click()
            editor.message.color_box.activated.emit(editor.message.color_box.findData('#7650a3'))
            editor.save()
            styles=[dict(start=0,length=2,bold=True,color='#7650a3')]
            self.assertEqual(ReminderStore(store.path).data['notifications'][0]['message_styles'],styles)
            self.c.bubble.show_one_shot_form();self.c.bubble.reminder_message.set_message('提出してください',styles)
            self.c.save_one_shot()
            self.assertEqual(self.c.engine.one_shots.data['notifications'][0]['message_styles'],styles)
        finally:editor.dirty=False;editor.close();editor.deleteLater()

    def test_named_destinations_editor_closes_speech_and_plus_adds_json_rows(self):
        from companion.destination_editor import DestinationEditor
        service=self.c.file_drop_service
        service.destinations.save({'schema_version':1,'destinations':[]})
        source=self.file('data.zip');service.drop(source)
        self.assertFalse(self.c.bubble.drop_buttons['move_extract'].isVisible())
        self.c.bubble.drop_buttons['move'].click()
        self.assertEqual(service.stage,'destination');self.assertFalse(self.c.bubble.drop_extra_buttons)
        self.c.bubble.drop_settings_button.click()
        self.assertFalse(self.c.bubble.isVisible());self.assertIsNone(service.pending)
        editor=service.destination_editor;self.assertIsInstance(editor,DestinationEditor)
        editor.add_button.click();editor.rows[0]['name'].setText('提出用');editor.rows[0]['path'].setText(str(self.output));editor.save()
        saved=json.loads((self.root/'Yohaku/file_destinations.json').read_text())
        self.assertEqual(saved['destinations'][0]['name'],'提出用');self.assertEqual(saved['destinations'][0]['path'],str(self.output))
        self.assertTrue(source.exists());self.assertFalse(self.c.bubble.isVisible());editor.hide()
        service.drop(source);self.c.bubble.drop_buttons['move'].click()
        self.assertEqual([b.text() for b in self.c.bubble.drop_extra_buttons.values()],['提出用'])

    def test_destination_snapshot_does_not_change_when_json_is_edited_and_cancel_is_safe(self):
        service=self.c.file_drop_service;source=self.file('a.txt');service.drop(source)
        service.run('destination:out');self.assertTrue(source.exists())
        service.run('move');second=self.root/'changed'
        document={'schema_version':1,'destinations':[{'id':'out','name':'変更後','path':str(second)}]}
        (self.root/'Yohaku/file_destinations.json').write_text(json.dumps(document))
        self.c.bubble.drop_cancel.click();service.run('destination:out');self.assertTrue(source.exists())
        service.drop(source);service.run('move')
        self.assertEqual(self.c.bubble.drop_extra_buttons['destination:out'].text(),'変更後')
        service.run('destination:out');self.wait_worker();self.assertTrue((second/source.name).exists())

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

    def test_print_menu_cancel_never_submits_a_job(self):
        source=self.file('資料.pdf');self.c.file_drop_service.drop(source)
        with patch('companion.pdf_print.print_pdf') as printing:
            self.c.bubble.drop_buttons['print_pdf'].click();self.c.bubble.drop_cancel.click()
            self.c.file_drop_service.run('paper:a4');printing.assert_not_called()
        self.assertTrue(source.exists())

    def test_closed_application_does_not_redisplay_a_late_result(self):
        self.c.file_drop_service.closed = True; self.c.bubble.hide()
        self.c.file_drop_service.finished({'path': str(self.output/'a.txt')}, '')
        self.assertFalse(self.c.bubble.isVisible())

    def test_sharing_hides_both_general_and_destination_editors(self):
        service=self.c.file_drop_service;service.show_editor();service.show_destination_editor()
        self.assertTrue(service.destination_editor.isVisible())
        self.c.share()
        self.assertFalse(service.editor.isVisible());self.assertFalse(service.destination_editor.isVisible())
        if self.c.hidden:self.c.share()

    def test_deposit_is_first_choice_and_only_saves_a_reference(self):
        self.c.panel.shelf_period.setCurrentIndex(self.c.panel.shelf_period.findData('forever'))
        service=self.c.shelf_service
        file=self.file('預ける.pdf');folder=self.root/'預けるフォルダ';folder.mkdir();(folder/'inside.txt').write_bytes(b'keep')
        for path,title in [(file,'ファイルを預ける'),(folder,'フォルダを預ける')]:
            self.c.file_drop_service.drop(path)
            self.assertEqual(next(iter(self.c.bubble.drop_buttons)),'shelve')
            self.assertEqual(self.c.bubble.drop_buttons['shelve'].text(),title)
            self.c.bubble.drop_buttons['shelve'].click();self.assertTrue(path.exists())
            self.assertIn('預かりました',self.c.bubble.text.text())
        self.assertEqual(len(service.store.data['items']),2)
        self.assertEqual((folder/'inside.txt').read_bytes(),b'keep');self.assertEqual(list(self.output.iterdir()),[])
        self.c.file_drop_service.drop(file);self.c.bubble.drop_buttons['shelve'].click()
        self.assertEqual(len(service.store.data['items']),2)

    def test_shelf_single_click_does_not_open_but_double_click_does(self):
        self.c.panel.shelf_period.setCurrentIndex(self.c.panel.shelf_period.findData('forever'))
        from PySide6.QtGui import QDesktopServices
        path=self.file('launcher.txt');service=self.c.shelf_service;service.deposit(path)
        self.c.select_content('shelf');self.app.processEvents()
        self.assertEqual(self.c.bubble.current,'shelf');self.assertFalse(self.c.bubble.timer.isActive())
        widget=self.c.bubble.file_links;item=widget.item(0);self.assertFalse(item.icon().isNull())
        point=widget.visualItemRect(item).center()
        with patch.object(QDesktopServices,'openUrl',return_value=True) as opened:
            QTest.mouseClick(widget.viewport(),Qt.MouseButton.LeftButton,pos=point);opened.assert_not_called()
            QTest.mouseDClick(widget.viewport(),Qt.MouseButton.LeftButton,pos=point)
            opened.assert_called_once_with(QUrl.fromLocalFile(str(path)))

    def test_deposit_accepts_updates_while_move_and_print_keep_snapshot_checks(self):
        self.c.panel.shelf_period.setCurrentIndex(self.c.panel.shelf_period.findData('forever'))
        source=self.file('autosaved.pdf');service=self.c.file_drop_service
        with patch('companion.file_drop_ui.execute') as moving,patch('companion.pdf_print.print_pdf') as printing:
            for action in ('move','print_pdf','shelve'):
                service.drop(source);source.write_bytes(source.read_bytes()+b' saved')
                self.c.bubble.drop_buttons[action].click()
                if action=='shelve':self.assertIn('預かりました',self.c.bubble.text.text())
                else:self.assertIn('変更',self.c.bubble.text.text())
            moving.assert_not_called();printing.assert_not_called()
        folder=self.root/'live-folder';folder.mkdir();service.drop(folder)
        (folder/'new.txt').write_bytes(b'keep')
        info=folder.stat();os.utime(folder,ns=(info.st_atime_ns,info.st_mtime_ns+2_000_000_000))
        self.c.bubble.drop_buttons['shelve'].click()
        self.assertIn('預かりました',self.c.bubble.text.text())
        self.assertEqual(len(self.c.shelf_service.store.data['items']),2)
        self.assertEqual(source.read_bytes(),b'content saved saved saved')
        self.assertEqual((folder/'new.txt').read_bytes(),b'keep')

    def test_deposit_still_rejects_missing_retyped_and_link_targets(self):
        service=self.c.file_drop_service
        for name in ('missing','retyped','linked'):
            source=self.file(name);service.drop(source)
            if name=='missing':source.unlink()
            elif name=='retyped':source.unlink();source.mkdir()
            with patch('companion.file_drop.is_link',return_value=name=='linked'):
                self.c.bubble.drop_buttons['shelve'].click()
            self.assertIn('確認できないか、変更',self.c.bubble.text.text())
            self.assertFalse(self.c.shelf_service.store.data['items'])

    def test_shelf_right_click_menu_and_delete_touch_only_registry(self):
        self.c.panel.shelf_period.setCurrentIndex(self.c.panel.shelf_period.findData('forever'))
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtWidgets import QMenu
        service=self.c.shelf_service;path=self.file('launcher.txt');folder=self.root/'launcher-folder';folder.mkdir()
        service.deposit(path);service.deposit(folder);self.c.select_content('shelf');self.app.processEvents()
        rows={row['kind']:row for row in service.store.data['items']}
        file_menu=service.menu_for(rows['file']);folder_menu=service.menu_for(rows['folder'])
        try:
            self.assertEqual([a.text() for a in file_menu.actions()],['フォルダを開く','削除'])
            self.assertEqual([a.text() for a in folder_menu.actions()],['削除'])
            with patch.object(QDesktopServices,'openUrl',return_value=True) as opened:
                file_menu.actions()[0].trigger();opened.assert_called_once_with(QUrl.fromLocalFile(str(path.parent)))
            widget=self.c.bubble.file_links;point=widget.visualItemRect(widget.item(0)).center()
            QTest.mouseClick(widget.viewport(),Qt.MouseButton.RightButton,pos=point)
            self.assertIsNotNone(service.popup);self.assertTrue(service.popup.isVisible())
            service.close_popup()
            self.assertEqual(self.c.bubble.current,'shelf');self.assertFalse(self.c.bubble.choice_row.isVisible())
            file_menu.actions()[1].trigger();folder_menu.actions()[0].trigger()
            self.assertFalse(service.store.data['items']);self.assertEqual(path.read_bytes(),b'content');self.assertTrue(folder.is_dir())
        finally:file_menu.deleteLater();folder_menu.deleteLater()

    def test_shelf_setting_persists_and_expiry_refreshes_visible_list(self):
        from companion.shelf import ShelfStore
        service=self.c.shelf_service;before=datetime(2026,10,25,23,59)
        with patch.object(service,'now',return_value=before):
            field=self.c.panel.shelf_period;field.setCurrentIndex(field.findData('week'))
            self.assertEqual(ShelfStore(service.store.path).data['period'],'week')
            service.deposit(self.file('expires.txt'));self.c.select_content('shelf')
            self.assertEqual(self.c.bubble.file_links.count(),1)
        with patch.object(service,'now',return_value=datetime(2026,10,26)):
            service.expire();self.assertFalse(service.store.data['items'])
            self.assertEqual(self.c.bubble.file_links.count(),0);self.assertIn('何も',self.c.bubble.text.text())
        self.assertTrue((self.root/'expires.txt').exists())

    def test_shelf_new_mail_is_inline_and_does_not_replace_the_list(self):
        self.c.panel.shelf_period.setCurrentIndex(self.c.panel.shelf_period.findData('forever'))
        self.c.shelf_service.deposit(self.file('safe.txt'));self.c.select_content('shelf')
        self.c.settings.outlook_enabled=self.c.settings.mail_enabled=True
        self.c.mail_result(self.c.mail_generation,{'messages':[{'kind':'mail'}]},'')
        self.assertEqual(self.c.bubble.current,'shelf');self.assertEqual(self.c.bubble.file_links.count(),1)
        self.assertIn('メール',self.c.bubble.shelf_mail.text());self.assertTrue(self.c.bubble.shelf_mail.isVisible())
        self.assertTrue(self.c.shelf_service.mail_timer.isActive())
        self.assertEqual(self.c.shelf_service.mail_timer.interval(),60000)
        self.assertFalse(self.c.bubble.timer.isActive())

    def test_shelf_mail_expires_without_resetting_the_list_or_its_message(self):
        self.c.panel.shelf_period.setCurrentIndex(self.c.panel.shelf_period.findData('forever'))
        service=self.c.shelf_service;bubble=self.c.bubble
        service.deposit(self.file('first.txt'));service.deposit(self.file('second.txt'))
        self.c.select_content('shelf');bubble.file_links.setCurrentRow(1)
        service.report('開けませんでした。登録は残しています。');original=bubble.text.text()
        ids=[bubble.file_links.item(n).data(Qt.ItemDataRole.UserRole) for n in range(2)]
        service.show_mail(Notice('','メールが届きました。',True,kind='notification'))
        self.assertEqual(bubble.text.text(),original)
        # Shorten only the test wait; production's 60000ms is checked above.
        service.mail_timer.start(1);QTest.qWait(100)
        self.assertFalse(service.mail_timer.isActive());self.assertFalse(bubble.shelf_mail.isVisible())
        self.assertTrue(bubble.isVisible());self.assertEqual(bubble.current,'shelf')
        self.assertEqual(bubble.text.text(),original);self.assertEqual(bubble.file_links.currentRow(),1)
        self.assertEqual([bubble.file_links.item(n).data(Qt.ItemDataRole.UserRole) for n in range(2)],ids)

    def test_shelf_mail_timeout_cannot_overwrite_new_content_or_reopen_a_hidden_bubble(self):
        service=self.c.shelf_service;bubble=self.c.bubble
        for next_view in ('notification','hidden'):
            self.c.select_content('shelf')
            service.show_mail(Notice('','メールが届きました。',True,kind='notification'))
            self.assertTrue(service.mail_timer.isActive())
            notice=Notice('','次の通知です。',True,kind='reminder')
            if next_view=='notification':bubble.display(notice)
            else:QTest.mouseClick(bubble.shelf_mail,Qt.MouseButton.LeftButton)
            self.assertFalse(service.mail_timer.isActive());self.assertFalse(bubble.shelf_mail.isVisible())
            service.mail_timer.timeout.emit()
            if next_view=='notification':self.assertIs(bubble.notice,notice);self.assertEqual(bubble.text.raw_text,notice.text)
            else:self.assertFalse(bubble.isVisible())
        self.c.select_content('shelf');self.assertFalse(bubble.shelf_mail.isVisible())

    def test_shelf_browsing_does_not_block_due_notifications(self):
        self.c.panel.shelf_period.setCurrentIndex(self.c.panel.shelf_period.findData('forever'))
        self.c.shelf_service.deposit(self.file('notification-safe.txt'));self.c.select_content('shelf')
        notice=Notice('','期限のお知らせ',True,kind='reminder')
        with patch.object(self.c.engine,'departure_notice',return_value=None),patch.object(self.c.engine,'next_notice',return_value=notice) as next_notice:
            self.c.tick();self.assertTrue(next_notice.call_args.kwargs['allow_reminders'])
        self.assertIs(self.c.bubble.notice,notice);self.assertEqual(len(self.c.shelf_service.store.data['items']),1)
        self.c.shelf_service.expire();self.assertIs(self.c.bubble.notice,notice)
