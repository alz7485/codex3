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
        locked=patch('companion.growth_ui.session_locked',return_value=False);locked.start();self.addCleanup(locked.stop)
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
            host.engine.context_options.error='synthetic corrupt calendar'
            self.assertIsNone(service.calendar());host.engine.context_options.error=''
            self.assertTrue((data/'growth.json').exists());before=deepcopy(service.store.data);service.reload();self.assertEqual(service.store.data,before)
            service.show();self.assertTrue(service.window.isVisible());self.assertIn('EXP',service.window.summary.text())
        finally:
            for t in (host.tick_timer,host.poll_timer,host.animation_timer,host.activity_timer,host.context_timer):t.stop()
            host.shutdown();host.tray.hide()
            for w in (host.panel,host.resident,host.bubble,host.history_window):w.hide()
            host.deleteLater();self.app.processEvents()
    def test_same_pack_reload_recovers_a_conflict_and_cancel_preserves_draft(self):
        from PySide6.QtWidgets import QMessageBox
        first=self.editor();second=self.editor();first.fields['name'].setText('先に保存');self.assertTrue(first.save())
        second.fields['name'].setText('残したい編集');self.assertFalse(second.save())
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No):second.reload_pack()
        self.assertEqual(second.fields['name'].text(),'残したい編集')
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):second.reload_pack()
        self.assertEqual(second.fields['name'].text(),'先に保存')
        second.fields['name'].setText('再読み込み後に保存');self.assertTrue(second.save(),second.status.text())
    def test_opening_uses_one_snapshot_so_a_concurrent_update_is_not_silently_overwritten(self):
        from companion.growth_content import read_json_snapshot
        e=self.editor()
        def racing_read(path):
            doc,digest=read_json_snapshot(path);new=deepcopy(doc);new['name']='同時に更新されたパック'
            atomic_json(path,new);return doc,digest
        with patch('companion.content_editor.read_json_snapshot',side_effect=racing_read):e.reload_pack()
        e.fields['name'].setText('古い内容からの編集');self.assertFalse(e.save())
        self.assertEqual(read_json(e.folder/'pack.json')['name'],'同時に更新されたパック')
    def test_frame_picker_and_reward_picker_use_visual_selections_and_keep_hidden_checks(self):
        from companion.growth_editor_widgets import FramePicker,RewardPicker
        from PySide6.QtCore import Qt
        frames=FramePicker([24,25]);frames.set_selected(range(16,24));self.assertEqual(frames.selected(),list(range(16,24)))
        frames.set_selected([]);frames.accept();self.assertNotEqual(frames.result(),frames.DialogCode.Accepted)
        picker=RewardPicker({'base:a':'衣装A','base:b':'会話B'},['base:a'])
        picker.search.setText('会話B');self.assertTrue(picker.items.item(0).isHidden());self.assertEqual(picker.selected(),['base:a'])
        picker.items.item(1).setCheckState(Qt.CheckState.Checked);self.assertEqual(picker.selected(),['base:a','base:b'])
        frames.deleteLater();picker.deleteLater()
    def test_reward_selection_includes_unsaved_content_and_saves_valid_references(self):
        from companion.growth_editor_widgets import RewardPicker,FramePicker
        e=self.editor();e.add_item();key=e.document['id']+':'+e.fields['id'].text()
        e.kind.setCurrentIndex(e.kind.findData('rewards'));self.assertIn(key,e.reward_options())
        with patch.object(RewardPicker,'exec',return_value=RewardPicker.DialogCode.Accepted),patch.object(RewardPicker,'selected',return_value=[key]):e.choose_rewards()
        self.assertEqual(e.fields['unlock'].toPlainText(),key);self.assertTrue(e.save(),e.status.text())
        self.assertEqual(load_catalog(self.root/'content').items['rewards']['base:level2']['unlock'],[key])
        e.kind.setCurrentIndex(e.kind.findData('costumes'));field=e.variant_widgets[0]['frames']
        with patch.object(FramePicker,'exec',return_value=FramePicker.DialogCode.Accepted),patch.object(FramePicker,'selected',return_value=list(range(16,24))):e.choose_frames(field)
        self.assertEqual(field.text(),'16,17,18,19,20,21,22,23')
    def test_costume_preview_animates_walk_and_stops_before_changing_or_hiding_forms(self):
        e=self.editor();e.kind.setCurrentIndex(e.kind.findData('costumes'));e.show();self.app.processEvents();clock=[100.]
        with patch('companion.content_editor.time.monotonic',side_effect=lambda:clock[0]):
            e.toggle_preview();self.assertTrue(e.preview_timer.isActive());self.assertEqual(e.preview.frame_index,16)
            clock[0]+=.14;e.advance_preview();self.assertEqual(e.preview.frame_index,17)
            e.preview_flipped.setChecked(True);self.assertTrue(e.preview.flipped);self.assertFalse(e.preview.grab().isNull())
            e.hide();self.assertFalse(e.preview_timer.isActive())
            e.toggle_preview();e.kind.setCurrentIndex(e.kind.findData('lines'));self.assertFalse(e.preview_timer.isActive())
            e.advance_preview()  # A queued callback must not use deleted form widgets.
    def test_growth_refresh_keeps_selection_and_renderer_and_defers_notifications_during_other_editors(self):
        from PySide6.QtWidgets import QWidget
        from PySide6.QtCore import Qt
        data=self.root/'Data';save_json(data/'settings.json',asdict(Settings(context_enabled=False,mail_enabled=False)))
        with patch.object(QSystemTrayIcon,'isSystemTrayAvailable',return_value=True):host=Controller(self.app,data_path=data)
        def cleanup():
            host.shutdown();host.tray.hide()
            for w in (host.panel,host.resident,host.bubble,host.history_window):w.hide()
            host.deleteLater();self.app.processEvents()
        self.addCleanup(cleanup)
        for timer in (host.tick_timer,host.poll_timer,host.animation_timer,host.activity_timer,host.context_timer,host.growth_service.timer):timer.stop()
        host.panel.hide();host.bubble.hide();service=host.growth_service
        service.show();window=service.window;window.frame.setCurrentIndex(16)
        renderer=window.preview.costumes;window.trophies.setCurrentItem(window.trophies.topLevelItem(0))
        selected=window.trophies.currentItem().data(0,Qt.ItemDataRole.UserRole)
        p=service.engine.data['characters']['A'];p['exp_seconds']=100;p['seconds']=100
        window.refresh();self.assertIs(window.preview.costumes,renderer);self.assertEqual(window.preview.frame_index,16)
        self.assertEqual(window.trophies.currentItem().data(0,Qt.ItemDataRole.UserRole),selected)
        self.assertIn('3分20秒',window.summary.text());window.hide()
        service.notifications=[dict(kind='level',level=2,character='A')]
        host.file_drop_service.show_destination_editor()
        with patch('companion.core.is_quiet',return_value=False):
            self.assertIsNone(service.next_notice(datetime.now().astimezone()))
            host.file_drop_service.destination_editor.hide()
            with patch('companion.growth_ui.session_locked',return_value=True):self.assertIsNone(service.next_notice(datetime.now().astimezone()))
            with patch('companion.growth_ui.QApplication.activeModalWidget',return_value=QWidget()):self.assertIsNone(service.next_notice(datetime.now().astimezone()))
            self.assertEqual(len(service.notifications),1)
            self.assertIsNotNone(service.next_notice(datetime.now().astimezone()))
        doc=read_json(service.content_root/'base/pack.json');doc['costumes'][0]['level']=1;atomic_json(service.content_root/'base/pack.json',doc)
        before=deepcopy(service.engine.data)
        with patch.object(service.store,'save',side_effect=OSError('synthetic')):service.reload()
        self.assertTrue(service.error);self.assertEqual(service.engine.data,before)
        service.reload();self.assertFalse(service.error);self.assertIn('base:welcome_pin',service.engine.progress('A')['unlocked'])
        self.assertEqual(service.engine.progress('A')['exp'],before['characters']['A']['exp'])
