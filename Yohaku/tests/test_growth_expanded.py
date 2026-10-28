from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from companion.ui import create_application
from companion.business_calendar import BusinessCalendar
from companion.growth import GrowthEngine,GrowthStore,condition_value,fresh_progress
from companion.growth_content import METRIC_CONDITIONS,NUMERIC,ContentError,load_catalog,seed_content,seed_examples,validate_condition
from companion.content_editor import ConditionDialog

class ExpandedGrowthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=create_application()
    def test_all_new_metric_conditions_use_existing_values_and_unknown_stays_unknown(self):
        p=fresh_progress();now=datetime(2026,10,28,tzinfo=timezone.utc)
        for kind,metric in METRIC_CONDITIONS.items():
            c=validate_condition(dict(type=kind,op='>=',value=1))
            self.assertEqual(condition_value(c,p,now,{metric:3},None,{},('08:30','17:30')),3)
            self.assertIsNone(condition_value(c,p,now,{},None,{},('08:30','17:30')))
    def test_editor_roundtrips_all_numeric_condition_types(self):
        for kind in NUMERIC:
            c=dict(type=kind,op='>=',value=1)
            if kind=='metric':c['metric']='cpu_percent'
            if kind=='event_count':c['event_id']='base:small_sparkle'
            dialog=ConditionDialog(condition=c)
            try:self.assertEqual(dialog.value()['type'],kind)
            finally:dialog.hide();dialog.deleteLater()
        with self.assertRaises(ContentError):validate_condition(dict(type='month',op='==',value=13))
        with self.assertRaises(ContentError):validate_condition(dict(type='weekday',op='==',value=2.5))
    def test_example_pack_adds_16_valid_trophies_and_never_replaces_edited_pack(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);seed_content(root);seed_examples(root);catalog=load_catalog(root)
            self.assertFalse(catalog.errors);self.assertEqual(len(catalog.items['trophies']),17)
            file=root/'daily_trophies/pack.json';file.write_text('{user edit}',encoding='utf-8');seed_examples(root)
            self.assertEqual(file.read_text(),'{user edit}')
    def test_character_records_and_calendar_conditions_grant_once_without_bonus_exp(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);seed_content(root/'content');seed_examples(root/'content');catalog=load_catalog(root/'content')
            engine=GrowthEngine(GrowthStore(root/'growth.json'),catalog,lambda:1000.)
            now=datetime(2026,12,4,10,tzinfo=timezone.utc)
            engine.step('A',now,{},BusinessCalendar());p=deepcopy(engine.progress('A'))
            self.assertIn('daily_trophies:friday',p['trophies']);self.assertIn('daily_trophies:december',p['trophies']);self.assertEqual(p['exp'],0)
            engine.step('A',now,{},BusinessCalendar());self.assertEqual(engine.progress('A')['trophies'],p['trophies']);self.assertEqual(engine.progress('A')['exp'],p['exp'])
            self.assertFalse(engine.progress('B')['trophies'])
