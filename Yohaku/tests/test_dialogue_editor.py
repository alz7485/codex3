import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QFileDialog, QMessageBox
from companion.dialogue import DialogueStore, read_document
from companion.ui import create_application
from companion.dialogue_editor import DialogueEditor


class DialogueEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = DialogueStore(Path(self.temp.name) / 'dialogue.json')
        self.editor = DialogueEditor(self.store)
        self.editor.show()
        self.app.processEvents()

    def tearDown(self):
        self.editor.dirty = False
        self.editor.close()
        self.editor.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def test_editing_text_and_rules_does_not_apply_until_save_then_reloads(self):
        e = self.editor
        original = deepcopy(self.store.data)
        e.line_edit.setPlainText('編集した日本語\n改行も保存します。')
        e.rule_label.setText('編集した呼びかけ')
        e.expression.setCurrentIndex(e.expression.findData('wink'))
        e.options['bubble_seconds'].setValue(85)
        e.options['interval_minutes'].setValue(17)
        self.assertTrue(e.dirty)
        self.assertEqual(self.store.data, original)
        self.assertTrue(e.save())
        data = read_document(self.store.path)
        self.assertEqual(data['phrases']['控えめな皮肉屋']['call'][0], '編集した日本語\n改行も保存します。')
        self.assertEqual(data['rules'][0]['label'], '編集した呼びかけ')
        self.assertEqual(data['rules'][0]['expression'], 'wink')
        self.assertEqual(data['options']['interval_minutes'], 17)
        self.assertEqual(data['options']['bubble_seconds'], 85)
        self.assertFalse(e.dirty)

    def test_add_delete_phrase_topic_and_edit_new_condition(self):
        e = self.editor
        initial_count = len(e.bank())
        e.add_line()
        e.line_edit.setPlainText('追加したセリフ')
        self.assertEqual(len(e.bank()), initial_count + 1)
        e.remove_line()
        self.assertEqual(len(e.bank()), initial_count)
        e.add_rule()
        key = e.draft['rules'][-1]['id']
        self.assertTrue(all(key in bank for bank in e.draft['phrases'].values()))
        e.kind.setCurrentIndex(e.kind.findData('weekday'))
        e.days[2].setChecked(True)
        self.assertTrue(e.save())
        self.assertEqual(self.store.rule(key)['condition'], {'kind': 'weekday', 'days': [2]})
        e.remove_rule()
        self.assertTrue(e.save())
        self.assertIsNone(self.store.rule(key))

    def test_blank_text_and_failed_write_preserve_active_data(self):
        e = self.editor
        original = deepcopy(self.store.data)
        e.line_edit.setPlainText('')
        self.assertFalse(e.save())
        self.assertEqual(self.store.data, original)
        self.assertTrue(e.dirty)
        e.line_edit.setPlainText('保存できない変更')
        with patch.object(self.store, 'save', side_effect=OSError('denied')):
            self.assertFalse(e.save())
        self.assertEqual(self.store.data, original)
        self.assertIn('反映していません', e.status.text())

    def test_metric_and_compound_conditions_are_editable_and_validated(self):
        e=self.editor
        e.add_rule()
        e.kind.setCurrentIndex(e.kind.findData('metric_range'))
        e.metric_selector.setCurrentIndex(e.metric_selector.findData('desktop_files'))
        e.metric_minimum.setValue(50)
        e.no_maximum.setChecked(True)
        self.assertTrue(e.save())
        self.assertEqual(self.store.data['rules'][-1]['condition'],{'kind':'metric_range','metric':'desktop_files','minimum':50,'maximum':None})
        e.kind.setCurrentIndex(e.kind.findData('all'))
        e.details.setPlainText('[{"kind":"weekday","days":[0,1,2,3,4]},{"kind":"metric_range","metric":"until_work_end_minutes","minimum":0,"maximum":60}]')
        self.assertTrue(e.save())
        before=self.store.data
        e.details.setPlainText('{broken')
        self.assertFalse(e.save())
        self.assertIs(self.store.data,before)

    def test_reset_is_staged_and_revert_recovers_saved_custom_content(self):
        e = self.editor
        e.line_edit.setPlainText('保存済みのカスタム')
        e.save()
        e.reset_defaults()
        self.assertTrue(e.dirty)
        self.assertEqual(self.store.data['phrases']['控えめな皮肉屋']['call'][0], '保存済みのカスタム')
        e.revert()
        self.assertEqual(e.line_edit.toPlainText(), '保存済みのカスタム')
        self.assertFalse(e.dirty)

    def test_close_cancel_keeps_draft_discard_restores_saved_data(self):
        e = self.editor
        original = e.line_edit.toPlainText()
        e.line_edit.setPlainText('保存しない変更')
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Cancel):
            self.assertFalse(e.close())
        self.assertTrue(e.isVisible())
        self.assertEqual(e.line_edit.toPlainText(), '保存しない変更')
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Discard):
            self.assertTrue(e.close())
        self.assertEqual(e.line_edit.toPlainText(), original)

    def test_import_export_roundtrip_and_invalid_import_is_non_destructive(self):
        e = self.editor
        exported = Path(self.temp.name) / 'export.json'
        e.line_edit.setPlainText('書き出す内容')
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(exported), '')):
            e.export_json()
        self.assertTrue(exported.exists())
        e.revert()
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(exported), '')):
            e.import_json()
        self.assertTrue(e.dirty)
        self.assertEqual(e.line_edit.toPlainText(), '書き出す内容')
        before = deepcopy(e.draft)
        exported.write_text('{broken')
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(exported), '')):
            e.import_json()
        self.assertEqual(e.draft, before)
