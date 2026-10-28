"""Independent editor and resident integration on disposable data only."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime,timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QSystemTrayIcon
from companion.core import Settings,save_json
from companion.content_editor import ContentEditor
from companion.costumes import CostumeRenderer
from companion.growth_content import atomic_json,load_catalog,read_json,seed_content
from companion.ui import Controller,character_frames,create_application

class GrowthUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=create_application()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.editors=[]
    def editor(self):
        editor=ContentEditor(self.root/'content');self.editors.append(editor);return editor
    def tearDown(self):
        for e in self.editors:e.hide();e.deleteLater()
        self.app.processEvents()
    def test_editor_changes_content_without_json_hand_editing_and_without_touching_progress(self):
        editor=self.editor();atomic_json(self.root/'growth.json',{'synthetic':'preserve'})
        before=(self.root/'growth.json').read_bytes();editor.fields['name'].setText('編集した追加セリフ')
        editor.text_fields['*'].setPlainText('追加した会話です。')
        self.assertTrue(editor.save(),editor.status.text());c=load_catalog(self.root/'content')
        self.assertEqual(c.items['lines']['base:company']['texts']['*'],'追加した会話です。')
        self.assertEqual((self.root/'growth.json').read_bytes(),before)
    def test_editor_supports_add_duplicate_delete_and_level_rewards(self):
        e=self.editor();n=e.items.count();e.add_item();self.assertEqual(e.items.count(),n+1)
        e.fields['name'].setText('新セリフ');e.duplicate();self.assertEqual(e.items.count(),n+2)
        e.delete_item();self.assertEqual(e.items.count(),n+1);self.assertTrue(e.save(),e.status.text())
        e.kind.setCurrentIndex(e.kind.findData('rewards'));self.assertEqual(e.fields['unlock'].toPlainText(),'base:welcome_pin')
    def test_two_editors_cannot_silently_overwrite_each_other(self):
        first=self.editor();second=self.editor();first.fields['name'].setText('先の変更');self.assertTrue(first.save())
        second.fields['name'].setText('後の変更');self.assertFalse(second.save());self.assertIn('別の編集',second.status.text())
        self.assertEqual(read_json(self.root/'content/base/pack.json')['lines'][0]['name'],'先の変更')
    def test_editor_rejects_duplicate_ids_and_bad_image_without_writing(self):
        e=self.editor();original=(e.folder/'pack.json').read_bytes();e.fields['id'].setText('small_sparkle');self.assertFalse(e.save())
        self.assertEqual((e.folder/'pack.json').read_bytes(),original)
    def test_editor_with_corrupt_base_reports_problem_and_does_not_save_over_it(self):
        seed_content(self.root/'content');path=self.root/'content/base/pack.json';path.write_text('{bad')
        e=self.editor();self.assertIsNone(e.document);self.assertFalse(e.save());e.add_item()
        self.assertEqual(path.read_text(),'{bad')
    def test_costumes_compose_supported_frames_only_and_keep_original_assets(self):
        seed_content(self.root/'content');c=load_catalog(self.root/'content');renderer=CostumeRenderer()
        renderer.configure(c,dict(equipped={'accessory':'base:welcome_pin'},unlocked=['base:welcome_pin']),'A')
        frames=character_frames('A');before=frames[24].toImage();dressed=renderer.compose(frames[24],'A',24)
        self.assertNotEqual(before,dressed.toImage());self.assertEqual(frames[24].toImage(),before)
        self.assertEqual(renderer.compose(frames[16],'A',16).toImage(),frames[16].toImage())
        self.assertEqual(renderer.compose(frames[24],'A',24).cacheKey(),dressed.cacheKey())
    def test_costume_editor_preview_can_select_all_characters(self):
        e=self.editor();e.kind.setCurrentIndex(e.kind.findData('costumes'))
        for character in ('A','B','E'):
            e.preview_character.setCurrentIndex(e.preview_character.findData(character));e.update_preview()
            self.assertEqual(e.preview.character,character);self.assertIsNotNone(e.preview.costumes)
            self.assertFalse(e.preview.grab().isNull())
    def test_resident_integration_keeps_forms_and_normal_notifications_priority(self):
        data=self.root/'Data';save_json(data/'settings.json',asdict(Settings(context_enabled=False,mail_enabled=False)))
        with patch.object(QSystemTrayIcon,'isSystemTrayAvailable',return_value=True),patch('companion.growth_ui.session_locked',return_value=False):
            host=Controller(self.app,data_path=data)
        try:
            host.panel.hide();service=host.growth_service;service.notifications=[dict(kind='level',level=2,character='A')]
            host.bubble.show_one_shot_form();self.assertIsNone(service.next_notice(datetime.now().astimezone()))
            host.bubble.hide();host.engine.paused_until=None
            with patch('companion.core.is_quiet',return_value=False):notice=service.next_notice(datetime.now().astimezone())
            self.assertIsNotNone(notice);self.assertIn('Lv.2',notice.text)
            self.assertTrue((data/'growth.json').exists());before=deepcopy(service.store.data);service.reload();self.assertEqual(service.store.data,before)
            service.show();self.assertTrue(service.window.isVisible());self.assertIn('EXP',service.window.summary.text())
        finally:
            for t in (host.tick_timer,host.poll_timer,host.animation_timer,host.activity_timer,host.context_timer):t.stop()
            host.shutdown();host.tray.hide()
            for w in (host.panel,host.resident,host.bubble,host.history_window):w.hide()
            host.deleteLater();self.app.processEvents()
