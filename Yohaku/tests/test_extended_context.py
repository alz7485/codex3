"""Ratio conditions, remaining schedule, seven voices and non-destructive upgrade."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
import math
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from companion.advanced_context import remaining_meeting_metrics
from companion.core import Engine,Event,Settings
from companion.dialogue import DialogueStore,DialogueError,EXTENDED_RULE_IDS,defaults,matches,read_document,upgrade,validate


class ExtendedContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'dialogue.json'
        self.now=datetime(2026,10,26,10,tzinfo=timezone(timedelta(hours=9)))
        self.condition={'kind':'metric_ratio','numerator':'daily_active_minutes','denominator':'observed_minutes',
                        'minimum_total':120,'minimum':85,'maximum':100}

    def match_ratio(self,active,total):
        return matches({'condition':self.condition},self.now,self.now,True,[],False,
                       {'daily_active_minutes':active,'observed_minutes':total})

    def test_ratio_boundaries_and_minimum_observation_prevent_early_claims(self):
        for active,total,expected in ((102,120,True),(101.99,120,False),(120,120,True),(119,119,False),(170,200,True)):
            with self.subTest(active=active,total=total):self.assertEqual(self.match_ratio(active,total),expected)
        self.condition.update(minimum=0,maximum=25)
        self.assertTrue(self.match_ratio(30,120));self.assertFalse(self.match_ratio(31,120))

    def test_unknown_nonfinite_negative_zero_and_inconsistent_values_do_not_match(self):
        for active,total in ((None,120),(100,None),(True,120),(1,False),(100,0),(-1,120),(121,120),
                             (float('nan'),120),(100,float('inf')),(float('inf'),120)):
            with self.subTest(active=active,total=total):self.assertFalse(self.match_ratio(active,total))
        self.condition.update(minimum=0,maximum=100)
        self.assertTrue(self.match_ratio(1e308,1e308))

    def test_ratio_validation_rejects_invalid_metric_percent_and_floor(self):
        for changes in ({'numerator':'unknown'},{'denominator':[]},{'minimum_total':0},{'minimum_total':True},
                        {'minimum':-1},{'minimum':101},{'maximum':84},{'maximum':float('inf')}):
            document=defaults();document['rules'][-1]['condition']={**self.condition,**changes}
            with self.subTest(changes=changes),self.assertRaises(DialogueError):validate(document)

    def event(self,key,start,end):return Event(key,self.now+timedelta(minutes=start),self.now+timedelta(minutes=end))

    def test_remaining_union_overlap_and_next_duration_have_independent_expectations(self):
        events=[self.event('done',-60,-30),self.event('active',-10,30),self.event('nested',10,20),
                self.event('adjacent',30,60),self.event('long',120,240)]
        values=remaining_meeting_metrics(events,self.now)
        self.assertEqual(values,{'remaining_meetings':4,'completed_meetings':1,'remaining_meeting_minutes':180,
            'overlapping_meetings':2,'next_meeting_duration_minutes':10})
        self.assertEqual(remaining_meeting_metrics([self.event('a',0,30),self.event('b',30,60)],self.now)['overlapping_meetings'],1)

    def test_remaining_schedule_clips_midnight_and_excludes_other_days_and_zero_length(self):
        start=self.now.replace(hour=0,minute=0)
        events=[Event('overnight',start-timedelta(hours=1),start+timedelta(minutes=30)),
                Event('late',start+timedelta(hours=23),start+timedelta(days=1,hours=1)),
                Event('tomorrow',start+timedelta(days=1),start+timedelta(days=1,hours=1)),
                Event('zero',self.now,self.now),Event('invalid',self.now,self.now-timedelta(minutes=1))]
        values=remaining_meeting_metrics(events,self.now)
        self.assertEqual(values['completed_meetings'],1);self.assertEqual(values['remaining_meetings'],1)
        self.assertEqual(values['remaining_meeting_minutes'],60);self.assertEqual(values['next_meeting_duration_minutes'],120)
        self.assertEqual(values['overlapping_meetings'],1)

    def test_empty_and_all_finished_are_distinct_from_unknown_next_duration(self):
        empty=remaining_meeting_metrics([],self.now)
        self.assertEqual(empty['remaining_meetings'],0);self.assertEqual(empty['completed_meetings'],0)
        self.assertIsNone(empty['next_meeting_duration_minutes']);self.assertEqual(empty['overlapping_meetings'],0)
        done=remaining_meeting_metrics([self.event('a',-20,0)],self.now)
        self.assertEqual(done['remaining_meetings'],0);self.assertEqual(done['completed_meetings'],1)

    def legacy(self):
        document=defaults();document.pop('extended_context_version')
        document['rules']=[row for row in document['rules'] if row['id'] not in EXTENDED_RULE_IDS]
        for bank in document['phrases'].values():
            for key in EXTENDED_RULE_IDS:bank.pop(key)
        return document

    def test_upgrade_adds_twelve_topics_once_and_preserves_existing_edits_and_source(self):
        document=self.legacy();document['phrases']['孤高のギャンブラー']['chat']=['独自の語り。']
        document['options']['interval_minutes']=23;document['rules'][2]['enabled']=False
        self.path.write_text(json.dumps(document,ensure_ascii=False));raw=self.path.read_bytes()
        store=DialogueStore(self.path)
        self.assertFalse(store.error);self.assertEqual(self.path.read_bytes(),raw)
        self.assertEqual(store.data['rules'][:len(document['rules'])],document['rules'])
        self.assertEqual(store.data['options'],document['options'])
        self.assertEqual(store.data['phrases']['孤高のギャンブラー']['chat'],['独自の語り。'])
        self.assertEqual(len(store.data['rules']),76)
        store.save(store.data);self.assertEqual(self.path.with_suffix('.json.bak').read_bytes(),raw)
        self.assertEqual(read_document(self.path),store.data)
        changed=deepcopy(store.data);changed['rules']=[r for r in changed['rules'] if r['id']!='active_ratio_high']
        for bank in changed['phrases'].values():bank.pop('active_ratio_high')
        self.assertEqual(upgrade(changed),changed)

    def test_upgrade_at_rule_limit_retains_custom_topic_and_does_not_exceed_cap(self):
        document=self.legacy()
        while len(document['rules'])<200:
            key='custom_'+str(len(document['rules']));row=deepcopy(document['rules'][2]);row.update(id=key,label='独自の話題')
            document['rules'].append(row)
            for bank in document['phrases'].values():bank[key]=['独自の文章']
        upgraded=validate(upgrade(document));self.assertEqual(len(upgraded['rules']),200)
        self.assertEqual(upgraded['rules'],document['rules'])
        self.assertEqual(upgraded['phrases'],document['phrases'])

    def test_failed_upgrade_save_retains_disk_and_can_retry(self):
        self.path.write_text(json.dumps(self.legacy(),ensure_ascii=False));raw=self.path.read_bytes();store=DialogueStore(self.path)
        with patch('pathlib.Path.replace',side_effect=OSError('locked')):
            with self.assertRaises(OSError):store.save(store.data)
        self.assertEqual(self.path.read_bytes(),raw);self.assertFalse(self.path.with_suffix('.json.tmp').exists())
        store.save(store.data);self.assertEqual(len(read_document(self.path)['rules']),76)

    def test_all_new_voice_lines_resolve_tokens_and_senior_thoughts_only_accompany_silence(self):
        store=DialogueStore(self.path);settings=Settings();engine=Engine(settings,self.path.with_name('history.json'),dialogue=store)
        engine.context.update(daily_active_minutes=160,overlapping_meetings=2,next_meeting_duration_minutes=90,
            remaining_meeting_minutes=240,open_office_files=9,memory_percent=89,battery_percent=25,desktop_files=120)
        for voice in store.data['phrases']:
            settings.personality=voice
            for key in EXTENDED_RULE_IDS:
                lines=store.data['phrases'][voice][key];self.assertEqual(len(lines),3)
                for index in range(3):
                    engine.choose=lambda values,i=index:i
                    text=engine.phrase(key);self.assertNotRegex(text,r'\{[a-z_]+\}')
                    if voice=='寡黙な先輩' and '\n（' in text:self.assertEqual(text.split('\n',1)[0],'…')

    def test_ratio_conversation_retains_cadence_quiet_and_new_topics_are_not_notifications(self):
        settings=Settings(quiet_start='00:00',quiet_end='00:00');store=DialogueStore(self.path)
        for row in store.data['rules']:row['enabled']=row['id']=='active_ratio_high'
        engine=Engine(settings,self.path.with_name('history.json'),dialogue=store,choose=lambda values:values[0])
        engine.context={'daily_active_minutes':110,'observed_minutes':120};engine.last_display=self.now-timedelta(minutes=10)
        notice=engine.next_notice(self.now,[]);self.assertEqual(notice.kind,'message');self.assertFalse(notice.important)
        self.assertIsNone(engine.next_notice(self.now+timedelta(minutes=9),[]))
        self.assertIsNone(engine.next_notice(self.now+timedelta(minutes=11),[],hidden=True))
        engine.category_last.clear();settings.quiet_start='09:00';settings.quiet_end='11:00'
        self.assertIsNone(engine.next_notice(self.now+timedelta(minutes=11),[]))


class ExtendedContextInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from companion.ui import create_application
        cls.app=create_application()

    def test_ratio_form_saves_selected_metrics_floor_and_percentage_without_touching_runtime_first(self):
        from companion.dialogue_editor import DialogueEditor
        with tempfile.TemporaryDirectory() as temporary:
            store=DialogueStore(Path(temporary)/'dialogue.json');editor=DialogueEditor(store)
            try:
                row=next(i for i,r in enumerate(editor.draft['rules']) if r['id']=='active_ratio_high')
                editor.rule_list.setCurrentRow(row)
                self.assertEqual(editor.kind.currentData(),'metric_ratio')
                self.assertEqual(editor.metric_selector.currentData(),'daily_active_minutes')
                self.assertEqual(editor.ratio_denominator.currentData(),'observed_minutes')
                editor.ratio_total.setValue(180);editor.metric_minimum.setValue(90)
                self.assertEqual(store.rule('active_ratio_high')['condition']['minimum'],85)
                self.assertTrue(editor.save())
                condition=read_document(store.path)['rules'][row]['condition']
                self.assertEqual(condition['minimum'],90);self.assertEqual(condition['minimum_total'],180)
                editor.metric_minimum.setValue(101);self.assertFalse(editor.save())
                self.assertEqual(store.rule('active_ratio_high')['condition']['minimum'],90)
            finally:editor.dirty=False;editor.hide();editor.deleteLater();self.app.processEvents()

    def test_controller_uses_only_fresh_complete_calendar_and_enabled_activity_collection(self):
        from companion.ui import Controller
        with tempfile.TemporaryDirectory() as temporary,patch.dict(os.environ,{'LOCALAPPDATA':temporary}):
            controller=Controller(self.app,data_path=Path(os.environ["LOCALAPPDATA"])/"Yohaku")
            try:
                for timer in (controller.tick_timer,controller.poll_timer,controller.animation_timer,controller.activity_timer,controller.context_timer):timer.stop()
                now=datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
                controller.events=[Event('a',now+timedelta(minutes=10),now+timedelta(minutes=100))]
                controller.connected=True;controller.connected_at=now;controller.daily_events=1
                controller.settings.context_enabled=False
                controller.refresh_context_metrics(now)
                self.assertEqual(controller.engine.context['remaining_meetings'],1)
                self.assertEqual(controller.engine.context['next_meeting_duration_minutes'],90)
                self.assertNotIn('observed_minutes',controller.engine.context)
                controller.daily_events=None;controller.refresh_context_metrics(now)
                self.assertNotIn('remaining_meetings',controller.engine.context)
                controller.daily_events=1;controller.connected_at=now-timedelta(minutes=6);controller.refresh_context_metrics(now)
                self.assertNotIn('remaining_meetings',controller.engine.context)
            finally:
                controller.shutdown();controller.tray.hide()
                for widget in (controller.panel,controller.resident,controller.bubble,controller.history_window):widget.hide()
                controller.deleteLater();self.app.processEvents()


if __name__=='__main__':unittest.main()
