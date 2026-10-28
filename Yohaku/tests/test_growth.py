"""Synthetic awake-time and durable, character-local progress contracts."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from companion.business_calendar import BusinessCalendar
from companion.growth import GrowthEngine,GrowthStore,condition_matches,fresh_progress,streak_days
from companion.growth_content import load_catalog,seed_content

class GrowthTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        seed_content(self.root/'content');self.catalog=load_catalog(self.root/'content');self.assertFalse(self.catalog.errors)
        self.catalog.config['exp_interval_seconds']=5
        self.store=GrowthStore(self.root/'growth.json');self.clock=1000.;self.now=datetime(2026,10,27,9,tzinfo=timezone(timedelta(hours=9)))
        self.calendar=BusinessCalendar(dict(japanese_holidays=False));self.engine=GrowthEngine(self.store,self.catalog,lambda:self.clock,lambda:0.)
    def step(self,seconds=5,character='A',metrics=None,locked=False):
        self.clock+=seconds;self.now+=timedelta(seconds=seconds)
        return self.engine.step(character,self.now,metrics or {},self.calendar,locked=locked)
    def test_exp_and_seconds_persist_per_character_and_do_not_backfill_restart(self):
        self.step(10);self.assertAlmostEqual(self.engine.progress('A')['exp'],1/6)
        self.step(5,character='B');self.step(10,character='B')
        restored=GrowthStore(self.store.path);self.assertEqual(restored.data,self.store.data)
        restarted=GrowthEngine(restored,self.catalog,lambda:self.clock)
        self.assertEqual(restarted.progress('B')['seconds'],10);self.assertEqual(restarted.progress('A')['seconds'],10)
        restarted.step('A',self.now+timedelta(days=2),{},self.calendar)
        self.assertEqual(restarted.progress('A')['seconds'],10)
    def test_default_five_minute_grant_saves_once_and_exit_carries_remainder(self):
        self.catalog.config['exp_interval_seconds']=300
        self.step(5);initial=self.store.path.read_bytes()
        for _ in range(58):self.step(5)
        self.assertEqual(self.engine.progress('A')['exp'],0)
        self.assertEqual(self.store.path.read_bytes(),initial)
        self.step(5);self.assertEqual(self.engine.progress('A')['exp'],5)
        self.assertEqual(GrowthStore(self.store.path).data['characters']['A']['exp'],5)
        self.step(10);self.engine.flush()
        restored=GrowthStore(self.store.path);self.assertEqual(restored.data['characters']['A']['exp_seconds'],10)
        self.assertEqual(restored.data['characters']['A']['exp'],5)
    def test_unsaved_fraction_survives_restart_without_early_or_double_exp_grant(self):
        self.catalog.config['exp_interval_seconds']=300
        for _ in range(29):self.step(10)
        self.engine.flush();self.assertEqual(self.engine.progress('A')['exp'],0)
        self.engine=GrowthEngine(GrowthStore(self.store.path),self.catalog,lambda:self.clock)
        self.step(10);self.assertEqual(self.engine.progress('A')['exp'],5)
        self.assertEqual(self.engine.progress('A')['exp_seconds'],0)
    def test_sleep_gaps_clock_jumps_and_locked_time_are_not_counted(self):
        self.step(10);self.step(3600);self.step(5,locked=True)
        self.now+=timedelta(hours=2);self.step(5)
        self.assertEqual(self.engine.progress('A')['seconds'],10)
        self.catalog.config['count_locked']=True;self.step(5,locked=True)
        self.assertEqual(self.engine.progress('A')['seconds'],15)
    def test_query_unbiased_clock_sleep_exclusion_with_wall_gap(self):
        self.step(5);self.now+=timedelta(minutes=30);self.step(5)
        self.assertEqual(self.engine.progress('A')['seconds'],5)
    def test_level_unlocks_are_persistent_never_auto_equipped_and_not_revoked(self):
        self.catalog.config['exp_per_hour']=3600;self.catalog.config['level_thresholds']=[0,5,30]
        notices=self.step(5);p=self.engine.progress('A')
        self.assertEqual(p['level'],2);self.assertIn('base:welcome_pin',p['unlocked']);self.assertFalse(p['equipped'])
        self.engine.equip('A','accessory','base:welcome_pin')
        restored=GrowthEngine(GrowthStore(self.store.path),self.catalog,lambda:self.clock)
        self.assertEqual(restored.progress('A')['equipped']['accessory'],'base:welcome_pin')
        self.catalog.config['level_thresholds']=[0,500,3000];self.step(5)
        self.assertEqual(self.engine.progress('A')['level'],2);self.assertTrue(any(n['kind']=='level' for n in notices))
        self.engine.equip('A','accessory','');self.assertFalse(self.engine.progress('A')['equipped'])
    def test_unearned_and_wrong_slot_costumes_cannot_be_equipped(self):
        self.step();self.assertRaises(ValueError,self.engine.equip,'A','accessory','base:welcome_pin')
        self.catalog.config['level_thresholds']=[0,.01];self.step()
        self.assertRaises(ValueError,self.engine.equip,'A','head','base:welcome_pin')
    def test_trophy_and_reward_exp_are_one_time_even_after_restart_and_reload(self):
        item=self.catalog.items['trophies']['base:first_hour'];item['conditions'][0]['value']=.01
        self.step();self.assertEqual(self.engine.progress('A')['trophies']['base:first_hour']['exp'],5)
        before=self.engine.progress('A')['exp'];self.step()
        self.assertAlmostEqual(self.engine.progress('A')['exp']-before,5/60)
        self.engine=GrowthEngine(GrowthStore(self.store.path),self.catalog,lambda:self.clock,lambda:0)
        self.step();self.assertEqual(len(self.engine.progress('A')['trophies']),1)
    def test_failed_transaction_does_not_advance_memory_or_grant_again(self):
        item=self.catalog.items['trophies']['base:first_hour'];item['conditions'][0]['value']=.01
        with patch('companion.growth.atomic_json',side_effect=OSError('full')):
            self.assertRaises(OSError,self.step)
        self.assertFalse(self.store.data['characters']);self.step()
        self.assertEqual(len(self.engine.progress('A')['trophies']),1)
    def test_backup_is_previous_committed_state_and_corruption_is_read_only(self):
        self.step();old=deepcopy(self.store.data);self.step()
        self.assertEqual(json.loads(self.store.path.with_suffix('.json.bak').read_text()),old)
        self.store.path.write_text('{broken',encoding='utf-8');store=GrowthStore(self.store.path)
        self.assertEqual(store.data,old);self.assertFalse(store.writable)
        engine=GrowthEngine(store,self.catalog,lambda:self.clock);self.clock+=10;engine.step('A',self.now,{},self.calendar)
        self.assertEqual(self.store.path.read_text(),'{broken')
    def test_corrupt_without_backup_does_not_overwrite_original(self):
        self.store.path.write_text('{bad');s=GrowthStore(self.store.path)
        self.assertTrue(s.error);self.assertFalse(s.writable);self.assertRaises(OSError,s.save,s.data)
    def test_event_probability_cooldown_daily_limit_and_durable_count(self):
        self.catalog.items['lines'].clear();self.step();voice=next(iter(self.catalog.items['events']['base:small_sparkle']['texts']))
        self.clock+=61;self.now+=timedelta(seconds=61)
        item=self.engine.choose_event('A',voice,self.now,{},self.calendar);self.assertIsNotNone(item)
        p=self.engine.progress('A');self.assertEqual(p['events'][item['key']]['count'],1)
        self.clock+=40000;self.now+=timedelta(seconds=40000)
        self.assertIsNone(self.engine.choose_event('A',voice,self.now,{},self.calendar))
        self.clock+=86400;self.now+=timedelta(days=1)
        self.assertIsNotNone(self.engine.choose_event('A',voice,self.now,{},self.calendar))
        self.assertEqual(self.engine.progress('A')['events'][item['key']]['count'],2)
    def test_zero_probability_stays_zero_at_high_level(self):
        self.step();self.catalog.items['lines'].clear();self.catalog.items['events']['base:small_sparkle']['probability']=0
        self.clock+=61;self.assertIsNone(self.engine.choose_event('A','孤高のギャンブラー',self.now,{},self.calendar))
    def test_missing_pack_keeps_earned_history_and_equipment_but_disables_render_definition(self):
        self.catalog.config['level_thresholds']=[0,.01];self.step();self.engine.equip('A','accessory','base:welcome_pin')
        before=deepcopy(self.store.data);self.catalog.items['costumes'].clear();self.catalog.items['rewards'].clear();self.engine.reload(self.catalog)
        self.assertEqual(self.store.data,before)
    def test_continuous_input_uses_configurable_idle_and_resets_on_gap(self):
        item=self.catalog.items['trophies']['base:first_hour'];item['conditions']=[dict(type='continuous_input',op='>=',value=.15)]
        self.step(metrics={'idle_minutes':0});self.assertFalse(self.engine.progress('A')['trophies'])
        self.step(metrics={'idle_minutes':0});self.assertTrue(self.engine.progress('A')['trophies'])
        self.step(metrics={'idle_minutes':2});self.assertEqual(self.engine.active_seconds,0)
    def test_calendar_and_business_streaks_are_distinct_and_holiday_use_is_not_work(self):
        now=self.now.replace(year=2026,month=10,day=26)
        days=['2026-10-23','2026-10-26']
        self.assertEqual(streak_days(days,now,self.calendar,'business'),2)
        self.assertEqual(streak_days(days,now,self.calendar,'calendar'),1)
        c=dict(type='outside_hours');p=fresh_progress()
        self.assertFalse(condition_matches(c,p,now.replace(hour=19),{},self.calendar,self.catalog.config,('08:30','17:30')))
        self.assertTrue(condition_matches(c,p,now.replace(hour=19),{'idle_minutes':0},self.calendar,self.catalog.config,('08:30','17:30')))
    def test_unknown_metrics_do_not_satisfy_zero_threshold_and_negative_metrics_work(self):
        p=fresh_progress();c=dict(type='app_count',op='<=',value=0)
        self.assertFalse(condition_matches(c,p,self.now,{},self.calendar,self.catalog.config,('08:30','17:30')))
        c=dict(type='metric',metric='until_work_end_minutes',op='<=',value=-5)
        self.assertTrue(condition_matches(c,p,self.now,{'until_work_end_minutes':-10},self.calendar,self.catalog.config,('08:30','17:30')))
    def test_missing_calendar_never_awards_holiday_outside_hours_or_business_streak(self):
        p=fresh_progress();p['days']=[self.now.date().isoformat()];config=dict(self.catalog.config,streak_mode='business')
        for c in (dict(type='day_kind',value='business'),dict(type='day_kind',value='holiday'),dict(type='outside_hours'),dict(type='streak_days',op='>=',value=0)):
            self.assertFalse(condition_matches(c,p,self.now.replace(hour=22),{'idle_minutes':0},None,config,('08:30','17:30')))
        config['streak_mode']='calendar'
        self.assertTrue(condition_matches(dict(type='streak_days',op='>=',value=1),p,self.now,{},None,config,('08:30','17:30')))
    def test_overnight_date_range_day_kind_and_event_count_conditions(self):
        p=fresh_progress();cases=[dict(type='time_range',start='22:00',end='06:00'),dict(type='date_range',start='2026-10-01',end='2026-10-31'),dict(type='day_kind',value='business'),dict(type='event_count',event_id='base:small_sparkle',op='>=',value=1)]
        p['events']['base:small_sparkle']={'count':1}
        for c in cases:self.assertTrue(condition_matches(c,p,self.now.replace(hour=23),{},self.calendar,self.catalog.config,('08:30','17:30')))
    def test_reload_unlocks_new_content_for_created_characters_without_granting_exp_or_time(self):
        self.catalog.config['exp_interval_seconds']=300
        self.step(10);self.step(5,character='B');self.step(10,character='B')
        before=deepcopy(self.engine.data);catalog=load_catalog(self.root/'content')
        item=deepcopy(catalog.items['costumes']['base:welcome_pin']);item.update(id='added',key='base:added',level=1)
        catalog.items['costumes']['base:added']=item
        self.assertEqual(self.engine.reload(catalog),[])
        for char in ('A','B'):
            after=self.engine.progress(char)
            self.assertIn('base:added',after['unlocked'])
            for key in ('exp','exp_seconds','seconds','days','trophies','equipped'):self.assertEqual(after[key],before['characters'][char][key])
        self.assertNotIn('E',self.engine.data['characters'])
        self.assertEqual(GrowthStore(self.store.path).data,self.engine.data)
        with patch.object(self.store,'save',wraps=self.store.save) as save:self.engine.reload(catalog);save.assert_not_called()
    def test_reload_recalculates_level_once_and_retains_progress_on_save_failure(self):
        self.step(10);before=deepcopy(self.engine.data);catalog=deepcopy(self.catalog);catalog.config['level_thresholds']=[0,.1]
        with patch.object(self.store,'save',side_effect=OSError('locked')):self.assertRaises(OSError,self.engine.reload,catalog)
        self.assertEqual(self.engine.data,before)
        notices=self.engine.reload(catalog);self.assertEqual(notices,[dict(kind='level',level=2,character='A')])
        self.assertEqual(self.engine.progress('A')['exp'],before['characters']['A']['exp'])
        self.assertEqual(self.engine.reload(catalog),[])
    def test_reload_with_invalid_base_preserves_saved_progress(self):
        self.step();before=deepcopy(self.engine.data);catalog=deepcopy(self.catalog);catalog.config=None
        self.assertEqual(self.engine.reload(catalog),[]);self.assertEqual(self.engine.data,before)
    def test_configured_event_interval_applies_at_startup_and_after_reload_without_extra_roll(self):
        self.catalog.items['lines'].clear();self.catalog.config['event_interval_seconds']=30
        event=self.catalog.items['events']['base:small_sparkle'];event.update(probability=1,daily_limit=10,cooldown_minutes=1)
        self.step();self.engine=GrowthEngine(self.store,self.catalog,lambda:self.clock,lambda:0)
        self.clock+=29;self.now+=timedelta(seconds=29)
        self.assertIsNone(self.engine.choose_event('A','冷静な案内役',self.now,{},self.calendar))
        self.clock+=1;self.now+=timedelta(seconds=1)
        self.assertIsNotNone(self.engine.choose_event('A','冷静な案内役',self.now,{},self.calendar))
        catalog=deepcopy(self.catalog);catalog.config['event_interval_seconds']=3600;self.engine.reload(catalog)
        self.clock+=60;self.now+=timedelta(seconds=60)
        self.assertIsNone(self.engine.choose_event('A','冷静な案内役',self.now,{},self.calendar))
        catalog.config['event_interval_seconds']=30;self.engine.reload(catalog)
        self.assertIsNotNone(self.engine.choose_event('A','冷静な案内役',self.now,{},self.calendar))
        self.engine.reload(catalog)
        self.assertIsNone(self.engine.choose_event('A','冷静な案内役',self.now,{},self.calendar))
    def test_committed_time_and_trophy_exp_produce_one_combined_gain_signal(self):
        self.catalog.config['exp_interval_seconds']=300
        p=fresh_progress();p.update(exp=55.,seconds=3595.,exp_seconds=295.,days=[self.now.date().isoformat()])
        self.engine.data['characters']['A']=p;self.engine.last_character='A'
        notices=self.step(5);gains=[n for n in notices if n['kind']=='exp']
        self.assertEqual(gains,[dict(kind='exp',amount=10.,character='A')])
        self.assertEqual(GrowthStore(self.store.path).data['characters']['A']['exp'],65.)
        self.assertFalse(any(n['kind']=='exp' for n in self.step(5)))
    def test_failed_exp_save_cannot_return_a_gain_signal_or_advance_saved_balance(self):
        self.catalog.config['exp_interval_seconds']=300
        p=fresh_progress();p.update(exp_seconds=295.,seconds=295.,days=[self.now.date().isoformat()]);self.engine.data['characters']['A']=p
        with patch.object(self.store,'save',side_effect=OSError('synthetic')):self.assertRaises(OSError,self.step,5)
        self.assertEqual(self.engine.progress('A')['exp'],0);self.assertEqual(self.engine.progress('A')['exp_seconds'],295.)
