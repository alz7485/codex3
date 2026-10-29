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
    def test_example_pack_adds_13_valid_trophies_and_never_replaces_edited_pack(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);seed_content(root);seed_examples(root);catalog=load_catalog(root)
            self.assertFalse(catalog.errors);self.assertEqual(len(catalog.items['trophies']),13)
            file=root/'daily_trophies/pack.json';file.write_text('{user edit}',encoding='utf-8');seed_examples(root)
            self.assertEqual(file.read_text(),'{user edit}')
    def test_character_records_and_calendar_conditions_grant_once_without_bonus_exp(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);seed_content(root/'content');seed_examples(root/'content');catalog=load_catalog(root/'content')
            catalog.items['trophies']={k:v for k,v in catalog.items['trophies'].items() if k in ('daily_trophies:friday','daily_trophies:december')}
            engine=GrowthEngine(GrowthStore(root/'growth.json'),catalog,lambda:1000.)
            now=datetime(2026,12,4,10,tzinfo=timezone.utc)
            p=fresh_progress();p.update(seconds=960*60,days=[f'2026-11-{d:02}' for d in range(1,29)])
            engine.data['characters']['A']=p
            engine.step('A',now,{},BusinessCalendar());p=deepcopy(engine.progress('A'))
            self.assertIn('daily_trophies:friday',p['trophies']);self.assertIn('daily_trophies:december',p['trophies']);self.assertEqual(p['exp'],0)
            engine.step('A',now,{},BusinessCalendar());self.assertEqual(engine.progress('A')['trophies'],p['trophies']);self.assertEqual(engine.progress('A')['exp'],p['exp'])
            self.assertFalse(engine.progress('B')['trophies'])

class GrowthPacingTests(unittest.TestCase):
    def test_first_level_requires_eight_hours_and_early_levels_are_spaced(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);seed_content(root/'content');catalog=load_catalog(root/'content')
            engine=GrowthEngine(GrowthStore(root/'growth.json'),catalog,lambda:1000.)
            p=fresh_progress();p['exp']=475;engine.update_unlocks(p,'A');self.assertEqual(p['level'],1)
            p['exp']=480;engine.update_unlocks(p,'A');self.assertEqual(p['level'],2)
            p['exp']=955;engine.update_unlocks(p,'A');self.assertEqual(p['level'],2)
            p['exp']=960;engine.update_unlocks(p,'A');self.assertEqual(p['level'],3)
            values=catalog.config['level_thresholds'];self.assertTrue(all(b-a>=480 for a,b in zip(values,values[1:])))
            p['level']=8;p['exp']=180;engine.update_unlocks(p,'A');self.assertEqual(p['level'],8)
            self.assertEqual(catalog.config['exp_interval_seconds'],300)
            self.assertFalse(catalog.items['trophies'])

    def test_earliest_trophy_needs_three_days_and_sixteen_hours_and_does_not_cluster(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);seed_content(root/'content');seed_examples(root/'content');catalog=load_catalog(root/'content')
            catalog.items['trophies']={k:v for k,v in catalog.items['trophies'].items() if k in ('daily_trophies:friday','daily_trophies:december')}
            engine=GrowthEngine(GrowthStore(root/'growth.json'),catalog,lambda:1000.)
            now=datetime(2026,12,4,10,tzinfo=timezone.utc)
            p=fresh_progress();p.update(seconds=960*60,days=['2026-12-04'])
            engine.data['characters']['A']=p
            metrics=dict(cpu_percent=0,memory_percent=0,desktop_files=0,open_office_files=0,unread_mail_count=0,completed_meetings=10,weekly_events=50)
            engine.step('A',now,metrics,BusinessCalendar());self.assertFalse(engine.progress('A')['trophies'])
            p=engine.data['characters']['A'];p['days']=['2026-12-03','2026-12-04']
            engine.step('A',now,metrics,BusinessCalendar());self.assertFalse(engine.progress('A')['trophies'])
            p=engine.data['characters']['A'];p['days']=['2026-12-02','2026-12-03','2026-12-04'];p['seconds']=959*60
            engine.step('A',now,metrics,BusinessCalendar());self.assertFalse(engine.progress('A')['trophies'])
            p=engine.data['characters']['A'];p['seconds']=960*60
            engine.step('A',now,metrics,BusinessCalendar());self.assertEqual(set(engine.progress('A')['trophies']),{'daily_trophies:three_days'})
            engine.step('A',now,metrics,BusinessCalendar());self.assertEqual(len(engine.progress('A')['trophies']),1)

    def test_existing_stock_packs_upgrade_with_backup_but_progress_and_customizations_survive(self):
        from companion.growth_content import atomic_json,read_json
        from companion.growth_migration import upgrade_pacing
        with TemporaryDirectory() as temp:
            root=Path(temp)/'content';seed_content(root);seed_examples(root)
            old=read_json(Path(__file__).parents[1]/'companion/assets/growth_migrations/v0350.json')
            for name,doc in old.items():
                folder=root/name;(folder/'.pacing-v0360').unlink();atomic_json(folder/'pack.json',doc)
            before=b'{"record":"must stay byte identical"}';(root.parent/'growth.json').write_bytes(before)
            base=root/'base/pack.json';doc=read_json(base);doc['lines'][0]['texts']['*']='私のセリフ';atomic_json(base,doc)
            daily=root/'daily_trophies/pack.json';custom=read_json(daily);custom['trophies'][0]['texts']['*']='自作の条件';atomic_json(daily,custom)
            upgrade_pacing(root);catalog=load_catalog(root)
            self.assertFalse(catalog.errors);self.assertEqual(catalog.config['level_thresholds'][1],480)
            self.assertEqual(read_json(base)['lines'][0]['texts']['*'],'私のセリフ')
            self.assertFalse(read_json(base)['trophies'])
            self.assertEqual(read_json(base.with_name('pack.pre-v0360.json')),doc)
            self.assertEqual(read_json(daily)['trophies'][0],custom['trophies'][0])
            self.assertEqual((root.parent/'growth.json').read_bytes(),before)
            # An intentional later edit must not be migrated again.
            doc=read_json(base);doc['config']['level_thresholds']=[0,60];atomic_json(base,doc);upgrade_pacing(root)
            self.assertEqual(read_json(base)['config']['level_thresholds'],[0,60])

    def test_migration_preserves_custom_curve_and_broken_pack_and_does_not_reinstall_deleted_samples(self):
        from companion.growth_content import atomic_json,read_json
        from companion.growth_migration import upgrade_pacing
        import shutil
        with TemporaryDirectory() as temp:
            root=Path(temp);seed_content(root);seed_examples(root)
            folder=root/'base';(folder/'.pacing-v0360').unlink();doc=read_json(folder/'pack.json')
            doc['config']['level_thresholds']=[0,1000];atomic_json(folder/'pack.json',doc);upgrade_pacing(root)
            self.assertEqual(read_json(folder/'pack.json')['config']['level_thresholds'],[0,1000])
            (folder/'.pacing-v0360').unlink();(folder/'pack.json').write_text('{broken');upgrade_pacing(root)
            self.assertEqual((folder/'pack.json').read_text(),'{broken')
            shutil.rmtree(root/'daily_trophies');seed_examples(root);self.assertFalse((root/'daily_trophies').exists())
