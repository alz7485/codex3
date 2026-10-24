from copy import deepcopy
import ctypes
from datetime import date,datetime,timedelta,timezone
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from companion.advanced_context import ConditionTimeline,condition_key,meeting_metrics
from companion.business_calendar import BusinessCalendar,japanese_holidays
from companion.context import system_power_metrics
from companion.context_options import ContextOptionsStore,TopicPreferences,ContextOptionsError
from companion.core import Engine,Event,Settings
from companion.dialogue import ADVANCED_RULE_IDS,defaults,matches,validate,read_document,DialogueError
from companion.activity import FileHistory,FileObservation
from companion.reminders import monthly_date,next_occurrence,due_time,new_rule


class AdvancedContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name);self.now=datetime(2026,10,23,10,tzinfo=timezone.utc)
        self.engine=Engine(Settings(quiet_start='00:00',quiet_end='00:00'),self.path/'history.json',choose=lambda xs:xs[0])

    def rule(self,key):return self.engine.dialogue.rule(key)

    def only(self,key):
        for rule in self.engine.dialogue.data['rules']:rule['enabled']=rule['id']==key

    def test_sustained_condition_requires_continuous_valid_observations(self):
        rule=self.rule('cpu_high');key=condition_key(rule['condition']);timeline=ConditionTimeline()
        for second in range(0,180,5):self.assertFalse(timeline.update(second,{'cpu_percent':90},[rule])[key]['active'])
        self.assertTrue(timeline.update(180,{'cpu_percent':90},[rule])[key]['active'])
        self.assertFalse(timeline.update(185,{'cpu_percent':None},[rule])[key]['active'])
        self.assertFalse(timeline.update(190,{'cpu_percent':90},[rule])[key]['active'])
        self.assertFalse(timeline.update(500,{'cpu_percent':90},[rule])[key]['active'])

    def test_recovery_survives_intermediate_values_and_is_consumed_once(self):
        self.only('cpu_recovered');rule=self.rule('cpu_recovered');timeline=ConditionTimeline();key=condition_key(rule['condition'])
        for second in range(0,181,5):timeline.update(second,{'cpu_percent':90},[rule])
        self.assertFalse(timeline.update(185,{'cpu_percent':70},[rule])[key]['active'])
        state=timeline.update(190,{'cpu_percent':40},[rule]);self.assertTrue(state[key]['active'])
        self.engine.context={'cpu_percent':40,'_temporal':state}
        self.assertIn('40%',self.engine.conversation(self.now).text)
        self.assertIsNone(self.engine.conversation(self.now))
        for second in range(195,376,5):timeline.update(second,{'cpu_percent':90},[rule])
        new=timeline.update(380,{'cpu_percent':40},[rule]);self.assertNotEqual(new[key]['event'],state[key]['event'])
        self.engine.context={'cpu_percent':40,'_temporal':new}
        self.assertIsNotNone(self.engine.conversation(self.now+timedelta(minutes=3)))

    def test_return_event_initialization_expiry_unknown_and_sleep(self):
        rule=self.rule('idle_returned');key=condition_key(rule['condition']);timeline=ConditionTimeline()
        self.assertFalse(timeline.update(0,{'idle_minutes':0},[rule])[key]['active'])
        timeline.update(5,{'idle_minutes':35},[rule])
        self.assertTrue(timeline.update(10,{'idle_minutes':0},[rule])[key]['active'])
        for second in range(15,611,5):last=timeline.update(second,{'idle_minutes':0},[rule])
        self.assertFalse(last[key]['active'])
        timeline.update(615,{'idle_minutes':35},[rule])
        self.assertFalse(timeline.update(1000,{'idle_minutes':0},[rule])[key]['active'])
        timeline.update(1005,{'idle_minutes':35},[rule]);timeline.update(1010,{'idle_minutes':None},[rule])
        self.assertFalse(timeline.update(1015,{'idle_minutes':0},[rule])[key]['active'])

    def test_automatic_event_is_not_consumed_if_history_save_fails(self):
        self.only('idle_returned');rule=self.rule('idle_returned');timeline=ConditionTimeline()
        timeline.update(0,{'idle_minutes':35},[rule])
        self.engine.context={'_temporal':timeline.update(5,{'idle_minutes':0},[rule])}
        self.engine.last_display=self.now-timedelta(hours=1)
        with patch.object(Path,'replace',side_effect=OSError('locked')):
            with self.assertRaises(OSError):self.engine.next_notice(self.now,[])
        self.assertFalse(self.engine.consumed_events)
        self.assertIsNotNone(self.engine.next_notice(self.now+timedelta(seconds=15),[]))
        self.assertIsNone(self.engine.next_notice(self.now+timedelta(minutes=11),[]))

    def test_temporal_state_is_pruned_when_rules_are_removed(self):
        rule=self.rule('cpu_high');timeline=ConditionTimeline();timeline.update(0,{'cpu_percent':90},[rule])
        self.assertTrue(timeline.states);self.assertEqual(timeline.update(5,{},[]),{});self.assertFalse(timeline.states)

    def test_transition_ranges_and_duration_validation(self):
        for mutation in (lambda c:c.update(to_minimum=50,to_maximum=90),lambda c:c.update(duration_minutes=-1),lambda c:c.update(window_minutes=0)):
            draft=defaults();condition=next(r for r in draft['rules'] if r['id']=='cpu_recovered')['condition'];mutation(condition)
            with self.assertRaises(DialogueError):validate(draft)

    def test_meeting_union_clusters_and_available_gap(self):
        def event(key,start,end):return Event(key,self.now+timedelta(minutes=start),self.now+timedelta(minutes=end))
        values=meeting_metrics([event('a',-10,20),event('b',10,30),event('c',35,65),event('d',100,130)],self.now,10)
        self.assertEqual(values,{'daily_meeting_minutes':100,'consecutive_meetings':3,'next_meeting_gap_minutes':0})
        empty=meeting_metrics([],self.now);self.assertEqual(empty['consecutive_meetings'],0);self.assertIsNone(empty['next_meeting_gap_minutes'])

    def test_meeting_cluster_gap_is_configurable_and_boundary_inclusive(self):
        events=[Event('a',self.now,self.now+timedelta(minutes=30)),Event('b',self.now+timedelta(minutes=40),self.now+timedelta(minutes=60))]
        self.assertEqual(meeting_metrics(events,self.now,10)['consecutive_meetings'],2)
        self.assertEqual(meeting_metrics(events,self.now,9)['consecutive_meetings'],1)
        self.assertEqual(meeting_metrics(events,self.now,10)['next_meeting_gap_minutes'],10)
        between=self.now+timedelta(minutes=32)
        self.assertEqual(meeting_metrics(events,between,10)['consecutive_meetings'],2)
        self.assertEqual(meeting_metrics(events,between,10)['next_meeting_gap_minutes'],8)

    def test_power_api_battery_ac_charging_unknown_and_desktop(self):
        state={'flags':1,'ac':0,'percent':20}
        def read(pointer):
            self.assertEqual(ctypes.sizeof(pointer._obj),12)
            for key,value in state.items():setattr(pointer._obj,key,value)
            return 1
        with patch('companion.context.sys.platform','win32'),patch.object(ctypes,'windll',SimpleNamespace(kernel32=SimpleNamespace(GetSystemPowerStatus=read)),create=True):
            self.assertEqual(system_power_metrics(),{'battery_percent':20,'ac_connected':0,'battery_charging':0})
            state.update(flags=8,ac=1,percent=50);self.assertEqual(system_power_metrics()['battery_charging'],1)
            for flag in (128,255):
                state['flags']=flag;self.assertTrue(all(x is None for x in system_power_metrics().values()))
            state.update(flags=1,percent=255);self.assertIsNone(system_power_metrics()['battery_percent'])

    def test_power_connection_does_not_fire_at_startup(self):
        rule=self.rule('power_connected');key=condition_key(rule['condition']);timeline=ConditionTimeline()
        self.assertFalse(timeline.update(0,{'ac_connected':1},[rule])[key]['active'])
        timeline.update(5,{'ac_connected':0},[rule]);self.assertTrue(timeline.update(10,{'ac_connected':1},[rule])[key]['active'])

    def test_japanese_public_substitute_citizen_and_special_holidays(self):
        for day in ('2026-01-12','2026-03-20','2026-05-06','2026-09-22','2019-04-30','2019-05-02','2019-10-22','2020-07-23','2020-07-24','2021-08-09'):
            value=date.fromisoformat(day);self.assertIn(value,japanese_holidays(value.year),day)
        self.assertNotIn(date(2020,10,12),japanese_holidays(2020))
        self.assertNotIn(date(2021,10,11),japanese_holidays(2021))

    def test_company_holidays_and_workday_override(self):
        calendar=BusinessCalendar({'japanese_holidays':True,'weekdays':[0,1,2,3,4],'holidays':['2026-10-23'],'workdays':['2026-10-24','2026-01-12']})
        self.assertFalse(calendar.is_business_day(date(2026,10,23)))
        self.assertTrue(calendar.is_business_day(date(2026,10,24)))
        self.assertTrue(calendar.is_business_day(date(2026,1,12)))
        self.assertFalse(calendar.is_business_day(date(2026,10,25)))

    def test_departure_weekday_setting_uses_company_business_calendar(self):
        self.engine.settings.departure_enabled=True
        self.engine.context_options.data['calendar']['holidays']=['2026-10-23']
        when=self.now.replace(hour=17)
        self.assertIsNone(self.engine.departure_notice(when))
        self.engine.context_options.data['calendar']['workdays']=['2026-10-23']
        self.assertIsNotNone(self.engine.departure_notice(when))

    def test_business_notification_dates_keep_legacy_weekdays_separate(self):
        calendar=BusinessCalendar({'holidays':['2026-01-30'],'weekdays':range(5),'japanese_holidays':True})
        self.assertEqual(monthly_date(2026,1,{'kind':'month_end_business_day'},calendar),date(2026,1,29))
        self.assertEqual(monthly_date(2026,1,{'kind':'month_end_weekday'},calendar),date(2026,1,30))
        rule=new_rule();rule['condition']={'kind':'month_end_business_day'}
        now=datetime(2026,1,29,17,tzinfo=timezone.utc)
        self.assertEqual(due_time(rule,now,calendar),now)
        self.assertEqual(next_occurrence(rule,now,calendar),now)

    def test_business_cutoff_rolls_across_year_and_multiple_months(self):
        calendar=BusinessCalendar({'holidays':[f'2026-01-{i:02d}' for i in range(1,32)],'weekdays':range(5),'japanese_holidays':True})
        condition={'kind':'monthly_business_day_before','day':1}
        expected=date(2025,12,31)
        self.assertEqual(monthly_date(2026,2,condition,calendar),expected)
        rule=new_rule();rule['condition']=condition
        now=datetime(2025,12,31,17,tzinfo=timezone.utc)
        self.assertEqual(due_time(rule,now,calendar),now)

    def test_target_counts_use_history_and_folder_boundaries_without_scanning(self):
        history=FileHistory(self.path/'files.sqlite3')
        for i,path in enumerate(('C:/work/a/report.xlsx','c:/WORK/a/report.xlsx','C:/work/a/sub/a.docx','C:/work/ab/other.xlsx')):
            history.append([FileObservation(path,'file','Excel',self.now+timedelta(seconds=i))],self.now)
        targets=[{'id':'file','kind':'file','path':'C:\\work\\a\\report.xlsx'}, {'id':'folder','kind':'folder','path':'C:/work/a'}, {'id':'missing','kind':'file','path':'C:/none.xlsx'}]
        self.assertEqual(history.target_counts(targets,self.now),{'file':2,'folder':3,'missing':0})

    def test_target_unknown_never_means_not_opened_and_labels_are_substituted(self):
        self.only('target_unopened');rule=self.rule('target_unopened');rule['condition']['target_id']='daily'
        self.assertIsNone(self.engine.conversation(self.now))
        self.engine.context_options.data['targets']=[{'id':'daily','label':'日報','path':'C:/daily.xlsx','kind':'file'}]
        self.engine.context={'_target_counts':{'daily':0}}
        self.assertIn('日報',self.engine.conversation(self.now).text)
        self.engine.context={'_target_counts':{'daily':1}};self.assertIsNone(self.engine.conversation(self.now))
        self.engine.context_options.data['targets'].append({'id':'memo','label':'メモ','path':'C:/memo.xlsx','kind':'file'})
        first=deepcopy(rule['condition']);first.update(state='opened_today')
        second=deepcopy(first);second['target_id']='memo'
        rule['condition']={'kind':'any','conditions':[first,second]}
        self.engine.context={'_target_counts':{'daily':0,'memo':1}}
        self.assertIn('メモ',self.engine.conversation(self.now).text)

    def test_topic_mute_survives_restart_and_expires_next_day(self):
        self.only('chat');self.engine.topic_preferences.update('chat',muted_date=self.now.date().isoformat())
        self.assertIsNone(self.engine.conversation(self.now))
        reloaded=TopicPreferences(self.path/'topic_preferences.json');self.assertEqual(reloaded.preference('chat')['muted_date'],'2026-10-23')
        self.assertIsNotNone(self.engine.conversation(self.now+timedelta(days=1)))
        self.engine.topic_preferences.update('chat');self.assertIsNotNone(self.engine.conversation(self.now))

    def test_reduced_topic_enforces_double_cooldown_even_for_manual_clicks(self):
        self.only('chat');self.rule('chat')['cooldown_minutes']=10
        self.engine.topic_preferences.update('chat',reduced=True)
        self.assertIsNotNone(self.engine.conversation(self.now))
        self.assertIsNone(self.engine.conversation(self.now+timedelta(minutes=19)))
        self.assertIsNotNone(self.engine.conversation(self.now+timedelta(minutes=20)))

    def test_options_atomic_failure_backup_and_invalid_file_preservation(self):
        store=self.engine.context_options;store.save(store.data);before=store.path.read_bytes();candidate=deepcopy(store.data)
        candidate['calendar']['holidays']=['2026-10-23']
        with patch.object(Path,'replace',side_effect=OSError('locked')):
            with self.assertRaises(OSError):store.save(candidate)
        self.assertEqual(store.path.read_bytes(),before);self.assertNotEqual(store.data,candidate)
        store.save(candidate);self.assertEqual(store.path.with_suffix('.json.bak').read_bytes(),before)
        store.path.write_text('{broken');bad=ContextOptionsStore(store.path);self.assertTrue(bad.error);self.assertEqual(store.path.read_text(),'{broken')

    def test_invalid_calendar_and_preferences_do_not_silently_enable_messages(self):
        self.only('chat');self.engine.topic_preferences.error='unreadable'
        self.assertIsNone(self.engine.conversation(self.now))
        self.engine.topic_preferences.error='';self.engine.context_options.error='unreadable'
        self.engine.conversation(self.now);self.assertIsNone(self.engine.context['business_day'])
        self.engine.settings.departure_enabled=True
        self.assertIsNone(self.engine.departure_notice(self.now.replace(hour=17)))

    def test_old_json_upgrade_preserves_custom_conditions_and_adds_topics_once(self):
        old=defaults();old.pop('advanced_context_version')
        old['rules']=[r for r in old['rules'] if r['id'] not in ADVANCED_RULE_IDS]
        for bank in old['phrases'].values():
            for key in ADVANCED_RULE_IDS:bank.pop(key)
        cpu=next(r for r in old['rules'] if r['id']=='cpu_high');cpu['condition'].update(kind='metric_range',minimum=90);cpu['condition'].pop('duration_minutes')
        old['phrases']['控えめな皮肉屋']['chat']=['独自の一言']
        path=self.path/'old.json';path.write_text(json.dumps(old,ensure_ascii=False));before=path.read_bytes()
        migrated=read_document(path);self.assertEqual(path.read_bytes(),before)
        self.assertEqual(next(r for r in migrated['rules'] if r['id']=='cpu_high')['condition'],cpu['condition'])
        self.assertEqual(migrated['phrases']['控えめな皮肉屋']['chat'],['独自の一言'])
        self.assertTrue(set(ADVANCED_RULE_IDS)<={r['id'] for r in migrated['rules']})
        path.write_text(json.dumps(migrated));self.assertEqual(read_document(path),migrated)

    def test_private_context_files_and_backups_are_excluded_from_source(self):
        module_path=Path(__file__).parents[1]/'scripts/package_source.py'
        spec=importlib.util.spec_from_file_location('advanced_package',module_path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for name in ('context_options','topic_preferences'):
            for suffix in ('.json','.json.bak','.json.tmp'):(self.path/(name+suffix)).write_text('private')
        self.assertEqual(module.source_files(self.path),[])
