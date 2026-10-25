"""Regression coverage for the seven v0.19.0 audit findings."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from companion.advanced_context import ConditionTimeline
from companion.dialogue import (DialogueError, DialogueStore, EXTENDED_RULE_IDS, KINDS,
                               MAX_BYTES, defaults, read_document, upgrade, validate)


class AuditInputRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'dialogue.json'

    def write(self, document):
        self.path.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')
        return self.path.read_bytes()

    def test_huge_ratio_and_existing_numeric_fields_reject_with_fallback_without_changing_source(self):
        for topic, fields in [('active_ratio_high', ('minimum_total', 'minimum', 'maximum')),
                              ('cpu_high', ('minimum', 'maximum')),
                              ('cpu_recovered', ('to_minimum', 'to_maximum'))]:
            for field in fields:
                with self.subTest(topic=topic, field=field):
                    document = defaults()
                    rule = next(r for r in document['rules'] if r['id'] == topic)
                    rule['condition'][field] = 10**400
                    original = self.write(document)
                    with self.assertRaises(DialogueError):
                        read_document(self.path)
                    store = DialogueStore(self.path)
                    self.assertTrue(store.error)
                    self.assertEqual(store.data, defaults())
                    self.assertEqual(self.path.read_bytes(), original)

    def test_malformed_legacy_rule_is_rejected_before_migration(self):
        document = defaults()
        document.pop('advanced_context_version')
        document['rules'][2] = 7
        original = self.write(document)
        with self.assertRaises(DialogueError):
            upgrade(document)
        self.assertTrue(DialogueStore(self.path).error)
        self.assertEqual(self.path.read_bytes(), original)

    def test_extra_children_are_rejected_before_save_and_not_executed_as_metadata(self):
        store = DialogueStore(self.path)
        store.save(store.data)
        original = self.path.read_bytes()
        for topic in ('chat', 'active_ratio_high'):
            with self.subTest(topic=topic):
                document = deepcopy(store.data)
                rule = next(r for r in document['rules'] if r['id'] == topic)
                rule['condition']['conditions'] = [7]
                with self.assertRaises(DialogueError):
                    store.save(document)
                self.assertEqual(self.path.read_bytes(), original)
                self.assertEqual(store.data, defaults())
                # Even an unvalidated non-composite condition has no child rules.
                self.assertEqual(ConditionTimeline().update(100, {}, [rule]), {})

    def test_near_limit_valid_legacy_configuration_keeps_edits_instead_of_using_defaults(self):
        document = defaults()
        document.pop('extended_context_version')
        document['rules'] = [r for r in document['rules'] if r['id'] not in EXTENDED_RULE_IDS]
        for bank in document['phrases'].values():
            for key in EXTENDED_RULE_IDS:
                bank.pop(key)
        document['phrases']['孤高のギャンブラー']['chat'][0] = 'KEEP_CUSTOM_EDIT'
        document['rules'][2]['enabled'] = False
        target = MAX_BYTES - 512
        for bank in document['phrases'].values():
            for lines in bank.values():
                while len(lines) < 200:
                    available = target - len(json.dumps(document, ensure_ascii=False).encode('utf-8')) - 4
                    if available < 1:
                        break
                    lines.append('x' * min(1000, available))
                if available < 1:
                    break
            if available < 1:
                break
        validate(document)
        original = self.write(document)
        store = DialogueStore(self.path)
        self.assertFalse(store.error)
        self.assertEqual(store.data['rules'], document['rules'])
        self.assertEqual(store.data['phrases'], document['phrases'])
        self.assertEqual(store.data['options'], document['options'])
        self.assertEqual(self.path.read_bytes(), original)
        store.save(store.data)
        self.assertEqual(self.path.with_suffix('.json.bak').read_bytes(), original)
        self.assertEqual(read_document(self.path), store.data)

    def test_condition_documentation_covers_every_supported_kind(self):
        path = Path(__file__).resolve().parents[1] / 'docs/DIALOGUE_JSON.md'
        text = path.read_text(encoding='utf-8')
        self.assertIn(f'次の{len(KINDS)}種', text)
        table = text.split('次の15種', 1)[1].split('`weight`', 1)[0]
        for kind in KINDS:
            self.assertIn(f'`{kind}`', table)


class AuditAccessibilityRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from companion.ui import create_application
        cls.app = create_application()

    def test_accessible_names_follow_ratio_and_regular_metric_labels(self):
        from PySide6.QtGui import QAccessible
        from companion.dialogue_editor import DialogueEditor
        with tempfile.TemporaryDirectory() as temporary:
            editor = DialogueEditor(DialogueStore(Path(temporary) / 'dialogue.json'))
            try:
                for topic, expected in [('active_ratio_high', '割合'), ('memory_low', '集計値')]:
                    row = next(i for i, r in enumerate(editor.draft['rules']) if r['id'] == topic)
                    editor.rule_list.setCurrentRow(row)
                    for field, bound in [(editor.metric_minimum, '下限'), (editor.metric_maximum, '上限')]:
                        name = QAccessible.queryAccessibleInterface(field).text(QAccessible.Text.Name)
                        self.assertEqual(name, f'{expected}の{bound}' + ('（%）' if expected == '割合' else ''))
            finally:
                editor.dirty = False
                editor.hide(); editor.deleteLater(); self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
