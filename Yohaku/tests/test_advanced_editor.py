import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from companion.ui import create_application
from companion.context_options import ContextOptionsStore,TopicPreferences
from companion.context_editor import ContextOptionsEditor
from companion.dialogue import DialogueStore,read_document
from companion.dialogue_editor import DialogueEditor
from companion.reminder_editor import ReminderEditor
from companion.reminders import ReminderStore
from PySide6.QtWidgets import QFileDialog,QMessageBox


class AdvancedEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=create_application()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
        self.options=ContextOptionsStore(self.path/'context_options.json')
        self.prefs=TopicPreferences(self.path/'topic_preferences.json')
        self.dialogue=DialogueStore(self.path/'dialogue.json')
        self.editor=ContextOptionsEditor(self.options,self.prefs,self.dialogue);self.editor.show();self.app.processEvents()

    def tearDown(self):
        self.editor.dirty=False;self.editor.close();self.editor.deleteLater();self.app.processEvents();self.temp.cleanup()

    def test_calendar_and_meeting_fields_validate_save_and_restore(self):
        e=self.editor;before=deepcopy(self.options.data)
        e.holidays.setPlainText('2026-10-30\n2026-12-31');e.workdays.setPlainText('2026-10-24');e.gap.setValue(15)
        self.assertEqual(self.options.data,before);self.assertTrue(e.dirty);self.assertTrue(e.save())
        self.assertEqual(self.options.data['calendar']['holidays'],['2026-10-30','2026-12-31'])
        self.assertTrue(self.options.calendar().is_business_day(datetime(2026,10,24).date()))
        self.assertEqual(ContextOptionsStore(self.options.path).data['consecutive_gap_minutes'],15)
        e.holidays.setPlainText('2026-99-99');self.assertFalse(e.save());self.assertTrue(e.dirty)
        e.revert();self.assertEqual(e.holidays.toPlainText(),'2026-10-30\n2026-12-31')

    def test_file_and_folder_registration_preserves_ids_and_allows_cancelled_close(self):
        e=self.editor
        with patch.object(QFileDialog,'getOpenFileName',return_value=('C:/work/daily.xlsx','')):e.add_target('file')
        with patch.object(QFileDialog,'getExistingDirectory',return_value='C:/work/project'):e.add_target('folder')
        self.assertTrue(e.save());first=deepcopy(self.options.data['targets']);self.assertEqual(len(first),2)
        e.revert();self.assertEqual(e.candidate()['targets'],first)
        e.targets.topLevelItem(0).setText(0,'日報');self.assertTrue(e.dirty)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Cancel):self.assertFalse(e.close())
        self.assertEqual(self.options.data['targets'],first)
        self.assertTrue(e.save());self.assertEqual(self.options.data['targets'][0]['id'],first[0]['id'])

    def test_topic_preferences_apply_immediately_and_rollback_on_save_failure(self):
        e=self.editor;e.topic.setCurrentIndex(e.topic.findData('chat'));e.muted.setChecked(True);e.reduced.setChecked(True)
        self.assertEqual(self.prefs.preference('chat'),{'muted_date':datetime.now().astimezone().date().isoformat(),'reduced':True})
        self.assertFalse(e.dirty)
        with patch.object(Path,'replace',side_effect=OSError('locked')):e.muted.setChecked(False)
        self.assertTrue(e.muted.isChecked());self.assertIn('保存できません',e.topic_status.text())
        e.reset_topic();self.assertEqual(self.prefs.preference('chat'),{'muted_date':'','reduced':False})

    def test_new_condition_forms_save_durations_recovery_targets_and_business_days(self):
        candidate=deepcopy(self.options.data);candidate['targets']=[{'id':'daily','label':'日報','path':'C:/work/daily.xlsx','kind':'file'}];self.options.save(candidate)
        e=DialogueEditor(self.dialogue,self.options);e.show();self.app.processEvents()
        try:
            def select(key):e.rule_list.setCurrentRow(next(i for i,r in enumerate(e.draft['rules']) if r['id']==key))
            select('cpu_high');e.duration.setValue(4)
            select('cpu_recovered');e.to_maximum.setValue(40);e.event_window.setValue(15)
            select('idle_returned');e.idle_length.setValue(45)
            select('target_unopened');e.target_selector.setCurrentIndex(e.target_selector.findData('daily'));e.rule_enabled.setChecked(True)
            e.add_rule();key=e.draft['rules'][-1]['id'];e.kind.setCurrentIndex(e.kind.findData('business_day'));e.business_expected.setCurrentIndex(1)
            self.assertTrue(e.save());saved=read_document(self.dialogue.path);rules={r['id']:r for r in saved['rules']}
            self.assertEqual(rules['cpu_high']['condition']['duration_minutes'],4)
            self.assertEqual(rules['cpu_recovered']['condition']['to_maximum'],40)
            self.assertEqual(rules['idle_returned']['condition']['idle_minutes'],45)
            self.assertEqual(rules['target_unopened']['condition']['target_id'],'daily')
            self.assertEqual(rules[key]['condition'],{'kind':'business_day','expected':False})
        finally:e.dirty=False;e.close();e.deleteLater();self.app.processEvents()

    def test_business_notification_editor_uses_company_calendar_for_preview(self):
        candidate=deepcopy(self.options.data);candidate['calendar']['holidays']=['2026-10-30'];self.options.save(candidate)
        store=ReminderStore(self.path/'reminders.json');e=ReminderEditor(store,self.options)
        try:
            e.add_rule();e.kind.setCurrentIndex(e.kind.findData('monthly_business_day_before'));e.day.setValue(15)
            self.assertTrue(e.save());self.assertEqual(store.data['notifications'][0]['condition'],{'kind':'monthly_business_day_before','day':15})
            self.assertTrue(e.day.isEnabled());self.assertIn('基準日',e.description.text())
        finally:e.dirty=False;e.close();e.deleteLater();self.app.processEvents()
