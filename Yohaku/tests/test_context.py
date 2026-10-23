from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from companion.context import UsageLedger, work_metrics
from companion.core import Engine, Settings
from companion.dialogue import DialogueError, DialogueStore, NEW_RULE_IDS, defaults, matches, read_document, validate
from companion.activity import FileHistory, FileObservation


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.now = datetime(2026, 10, 23, 14, 30, tzinfo=timezone.utc)

    def test_idle_active_totals_restart_and_sleep_gap(self):
        usage = UsageLedger(self.path/'usage.json', self.now)
        for i in range(120):
            usage.sample(self.now + timedelta(seconds=i * 5), 5, 2)
        usage.sample(self.now + timedelta(minutes=10), 5, 130)
        self.assertEqual(usage.metrics(self.now)['daily_active_minutes'], 10)
        self.assertEqual(usage.metrics(self.now)['active_streak_minutes'], 0)
        before = usage.metrics(self.now)['observed_minutes']
        usage.sample(self.now + timedelta(hours=2), 7200, 7200)
        self.assertEqual(usage.metrics(self.now)['observed_minutes'], before)
        usage.persist()
        restored = UsageLedger(usage.path, self.now + timedelta(hours=3))
        self.assertEqual(restored.days[usage.day]['active'], 600)
        self.assertEqual(set(json.loads(usage.path.read_text())['days'][usage.day]), {'active', 'idle', 'observed'})

    def test_midnight_splits_sample_and_app_use_yesterday(self):
        beginning = self.now.replace(hour=0, minute=0, second=2)
        usage = UsageLedger(self.path/'usage.json', beginning - timedelta(seconds=5))
        usage.sample(beginning, 5, 2)
        self.assertEqual(usage.days[beginning.date().isoformat()]['active'], 2)
        yesterday = (beginning.date() - timedelta(days=1)).isoformat()
        self.assertEqual(usage.days[yesterday]['active'], 3)
        self.assertEqual(usage.metrics(beginning)['missed_yesterday'], 0)
        usage.persist()
        later = UsageLedger(usage.path, beginning + timedelta(days=3))
        self.assertEqual(later.metrics(beginning + timedelta(days=3))['missed_yesterday'], 1)
        self.assertEqual(later.metrics(beginning + timedelta(days=3))['days_since_last_use'], 3)

    def test_first_install_unknown_input_and_retention(self):
        usage = UsageLedger(self.path/'usage.json', self.now)
        usage.sample(self.now, 5, None)
        self.assertIsNone(usage.metrics(self.now)['daily_active_minutes'])
        self.assertIsNone(usage.metrics(self.now)['missed_yesterday'])
        usage.days['2025-01-01'] = dict(active=1, idle=2, observed=3)
        usage.prune(self.now)
        self.assertNotIn('2025-01-01', usage.days)

    def test_working_hours_0830_1730(self):
        values = work_metrics(self.now)
        self.assertEqual(values['until_work_end_minutes'], 180)
        self.assertEqual(work_metrics(self.now.replace(hour=8, minute=0))['until_work_start_minutes'], 30)
        self.assertEqual(work_metrics(self.now.replace(hour=18, minute=0))['after_work_end_minutes'], 30)

    def test_metric_and_or_unknown_and_numeric_validation(self):
        c = {'kind':'metric_range','metric':'idle_minutes','minimum':5,'maximum':10}
        rule = {'condition':c}
        args = (self.now,self.now,False,[],False)
        self.assertFalse(matches(rule,*args,{}))
        self.assertFalse(matches(rule,*args,{'idle_minutes':None}))
        self.assertTrue(matches(rule,*args,{'idle_minutes':5}))
        self.assertFalse(matches(rule,*args,{'idle_minutes':11}))
        condition = {'kind':'all','conditions':[c,{'kind':'weekday','days':[4]}]}
        self.assertTrue(matches({'condition':condition},*args,{'idle_minutes':7}))
        condition['kind']='any'
        self.assertTrue(matches({'condition':condition},*args,{}))
        draft=defaults(); draft['rules'][2]['condition']={'kind':'metric_range','metric':'idle_minutes','minimum':float('nan'),'maximum':None}
        with self.assertRaises(DialogueError):validate(draft)

    def test_legacy_json_upgrade_preserves_custom_text_and_adds_conditions(self):
        old=defaults();old['schema_version']=1
        old['rules']=[r for r in old['rules'] if r['id'] not in (*NEW_RULE_IDS,'mail_received')]
        for bank in old['phrases'].values():
            for key in (*NEW_RULE_IDS,'mail_received'):bank.pop(key,None)
        old['phrases']['控えめな皮肉屋']['call']=['以前に編集したセリフ']
        for key in ('work_start','work_end','active_threshold_seconds'):old['options'].pop(key)
        path=self.path/'old.json';path.write_text(json.dumps(old,ensure_ascii=False))
        upgraded=read_document(path)
        self.assertEqual(upgraded['schema_version'],2)
        self.assertEqual(upgraded['phrases']['控えめな皮肉屋']['call'],['以前に編集したセリフ'])
        self.assertTrue(set(NEW_RULE_IDS)<={r['id'] for r in upgraded['rules']})
        self.assertEqual(json.loads(path.read_text())['schema_version'],1)
        old['rules'][0]['id']=[]
        path.write_text(json.dumps(old))
        with self.assertRaises(DialogueError):read_document(path)

    def test_context_rule_template_and_no_file_name_without_history(self):
        settings=Settings();store=DialogueStore(self.path/'dialogue.json')
        engine=Engine(settings,self.path/'history.json',choose=lambda xs:xs[0],dialogue=store)
        engine.started=self.now-timedelta(hours=3);engine.session_spoken=True
        for rule in store.data['rules']:rule['enabled']=rule['id']=='repeat_file'
        self.assertIsNone(engine.conversation(self.now))
        engine.context={'file_name':'予算.xlsx','file_open_count':4}
        notice=engine.conversation(self.now)
        self.assertIn('予算.xlsx',notice.text)
        self.assertIn('4回',notice.text)

    def test_repeated_file_summary_uses_all_rows_of_today_and_separates_paths(self):
        history=FileHistory(self.path/'files.sqlite3')
        observations=[FileObservation('C:/a/予算.xlsx','予算.xlsx','Excel',self.now-timedelta(minutes=i)) for i in (1,2,3,4)]
        observations.append(FileObservation('C:/b/予算.xlsx','予算.xlsx','Excel',self.now))
        history.append(observations,self.now)
        self.assertEqual(history.repeat_summary(self.now),{'file_name':'予算.xlsx','file_open_count':4})
        history.clear()
        self.assertIsNone(history.repeat_summary(self.now))
