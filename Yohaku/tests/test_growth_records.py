"""Growth views are read-only, and trial equipment commits all slots together."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from PySide6.QtCore import Qt
from companion.business_calendar import BusinessCalendar
from companion.core import Settings
from companion.dialogue import DialogueStore
from companion.growth import GrowthEngine,GrowthStore,fresh_progress
from companion.growth_content import load_catalog,seed_content
from companion.growth_records import collection_rows,collection_text,condition_rows,next_unlocks,trophy_text
from companion.growth_ui import GrowthWindow
from companion.ui import create_application


class GrowthRecordsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=create_application()
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        seed_content(self.root/'content');self.catalog=load_catalog(self.root/'content');self.store=GrowthStore(self.root/'growth.json')
        self.engine=GrowthEngine(self.store,self.catalog,lambda:1000.);self.p=fresh_progress()
        self.engine.data['characters']['A']=self.p;self.settings=Settings(context_enabled=False)
        self.service=SimpleNamespace(engine=self.engine,store=self.store,host=SimpleNamespace(settings=self.settings,
            dialogue=DialogueStore(self.root/'dialogue.json'),engine=SimpleNamespace(context={})),
            error_text=lambda:'',calendar=lambda:BusinessCalendar(),work=lambda:('08:30','17:30'),reload=Mock(),open_editor=Mock(),apply_costumes=Mock())
        self.window=None;self.now=datetime(2026,10,28,10,tzinfo=timezone.utc)
    def tearDown(self):
        if self.window:self.window.hide();self.window.deleteLater();self.app.processEvents()
    def show_window(self):
        self.window=GrowthWindow(self.service);self.window.show();self.app.processEvents();return self.window
    def unlock(self):
        self.p.update(level=2,exp=65.);self.engine.update_unlocks(self.p,'A')
    def extra_costume(self,key='base:cap',slot='head'):
        item=deepcopy(self.catalog.items['costumes']['base:welcome_pin']);item.update(key=key,id=key.split(':')[1],slot=slot,name='テストの帽子')
        self.catalog.items['costumes'][key]=item;self.p['unlocked'].append(key);return key
    def test_next_unlock_uses_earlier_reward_level_and_does_not_repeat_reward_targets(self):
        self.catalog.items['costumes']['base:welcome_pin']['level']=8
        rows=next_unlocks(self.catalog,self.p,'A')
        self.assertEqual([(row['key'],row['level']) for row in rows],[('base:welcome_pin',2)])
        self.catalog.items['rewards']['base:level2']['characters']=['B']
        self.assertEqual(next_unlocks(self.catalog,self.p,'A')[0]['level'],8)
        self.catalog.config['level_thresholds']=[0,60];self.assertEqual(next_unlocks(self.catalog,self.p,'A'),[])
        row=next(row for row in collection_rows(self.catalog,self.p,'A') if row['key']=='base:welcome_pin')
        self.assertIn('上限',row['state'])
    def test_secret_trophies_do_not_disclose_name_description_conditions_or_exp_before_award(self):
        item=self.catalog.items['trophies']['base:first_hour'];item.update(hidden=True,name='秘密の名前',description='秘密の説明',exp=987)
        text=trophy_text(item['key'],self.catalog,self.p,'A',self.now,{},BusinessCalendar(),('08:30','17:30'),True)
        for secret in ('秘密の名前','秘密の説明','987','累計'):self.assertNotIn(secret,text)
        self.p['trophies'][item['key']]={'at':self.now.isoformat(),'exp':987}
        self.assertIn('秘密の名前',trophy_text(item['key'],self.catalog,self.p,'A',self.now,{},BusinessCalendar(),('08:30','17:30'),True))
    def test_missing_metrics_are_unknown_and_inactive_characters_do_not_borrow_current_pc_values(self):
        item=deepcopy(self.catalog.items['trophies']['base:first_hour']);item['conditions']=[dict(type='metric',metric='cpu_percent',op='>=',value=80)]
        rows=condition_rows(item,self.p,self.now,{},BusinessCalendar(),self.catalog,('08:30','17:30'))
        self.assertIsNone(rows[0]['met']);self.assertIsNone(rows[0]['value'])
        self.catalog.items['trophies'][item['key']]=item
        text=trophy_text(item['key'],self.catalog,self.p,'A',self.now,{'cpu_percent':99},BusinessCalendar(),('08:30','17:30'),False)
        self.assertNotIn('99',text);self.assertIn('未取得',text)
        self.assertTrue(condition_rows(item,self.p,self.now,{'cpu_percent':99},BusinessCalendar(),self.catalog,('08:30','17:30'))[0]['met'])
    def test_collection_hides_locked_speech_uses_selected_voice_and_keeps_orphan_records(self):
        key='base:company';row=next(row for row in collection_rows(self.catalog,self.p,'A') if row['key']==key)
        stock=self.catalog.items['lines'][key]['texts']['馴れ馴れしい関西弁']
        self.assertNotIn(stock,collection_text(row,self.catalog,self.p,'A','馴れ馴れしい関西弁'))
        self.p['unlocked']=[key,'removed:old'];rows=collection_rows(self.catalog,self.p,'A')
        row=next(row for row in rows if row['key']==key);self.assertIn(stock,collection_text(row,self.catalog,self.p,'A','馴れ馴れしい関西弁'))
        self.assertEqual(next(row for row in rows if row['key']=='removed:old')['kind'],'missing')
    def test_viewing_filtering_and_trial_refresh_do_not_save_or_modify_progress_or_active_character(self):
        self.unlock();before=deepcopy(self.engine.data)
        with patch.object(self.store,'save',side_effect=AssertionError('A view must not write')):
            window=self.show_window();combo=window.slots['accessory'];combo.setCurrentIndex(combo.findData('base:welcome_pin'))
            renderer=window.preview.costumes;window.frame.setCurrentIndex(16)
            window.collection.search.setText('リボン');window.refresh()
            self.assertEqual(combo.currentData(),'base:welcome_pin');self.assertIs(window.preview.costumes,renderer)
            self.assertEqual(window.preview.frame_index,16);self.assertTrue(window.apply_equipment.isEnabled())
            window.character.setCurrentIndex(window.character.findData('B'));window.refresh()
            self.assertEqual(self.settings.character,'A');self.assertFalse(window.apply_equipment.isEnabled())
        self.assertEqual(self.engine.data,before);self.assertFalse(self.store.path.exists())
    def test_collection_search_filter_and_personality_follow_selected_character_without_running_events(self):
        self.unlock();self.service.host.dialogue.data['profiles']['A']['voice']='馴れ馴れしい関西弁';window=self.show_window();collection=window.collection
        collection.search.setText('一緒の時間');self.assertIn('一緒やな',collection.detail.toPlainText())
        selection=collection.items.currentItem().data(0,Qt.ItemDataRole.UserRole);window.refresh()
        self.assertEqual(collection.items.currentItem().data(0,Qt.ItemDataRole.UserRole),selection)
        collection.search.setText('存在しない名前');self.assertIn('ありません',collection.detail.toPlainText());self.assertFalse(collection.try_button.isEnabled())
        collection.search.setText('リボン');collection.kind.setCurrentIndex(collection.kind.findData('costumes'));collection.try_button.click()
        self.assertIs(window.tabs.currentWidget(),window.costume_page);self.assertTrue(window.apply_equipment.isEnabled());self.assertEqual(self.p['equipped'],{})
    def test_all_equipment_slots_commit_once_and_failure_keeps_entire_previous_state(self):
        self.unlock();cap=self.extra_costume();candidate={'head':cap,'accessory':'base:welcome_pin'};before=deepcopy(self.engine.data)
        with patch.object(self.store,'save',side_effect=OSError('synthetic')):
            with self.assertRaises(OSError):self.engine.equip_set('A',candidate)
        self.assertEqual(self.engine.data,before)
        with patch.object(self.store,'save',wraps=self.store.save) as save:self.engine.equip_set('A',candidate);self.assertEqual(save.call_count,1)
        self.assertEqual(self.engine.progress('A')['equipped'],candidate);self.assertEqual(GrowthStore(self.store.path).data,self.store.data)
        with self.assertRaises(ValueError):self.engine.equip_set('A',dict(candidate,body='missing:new'))
        self.assertEqual(self.engine.progress('A')['equipped'],candidate)
    def test_unloaded_equipment_can_be_kept_while_another_slot_changes_but_cannot_be_newly_equipped(self):
        self.unlock();cap=self.extra_costume();self.p['equipped']={'accessory':'removed:old'}
        self.engine.equip_set('A',{'accessory':'removed:old','head':cap})
        self.assertEqual(self.engine.progress('A')['equipped']['accessory'],'removed:old')
        self.engine.equip_set('A',{'head':cap})
        with self.assertRaises(ValueError):self.engine.equip_set('A',{'accessory':'removed:old','head':cap})
    def test_failed_equipment_save_keeps_trial_for_retry_and_character_inspection_is_independent(self):
        self.unlock();window=self.show_window();combo=window.slots['accessory'];combo.setCurrentIndex(combo.findData('base:welcome_pin'))
        with patch.object(self.store,'save',side_effect=OSError('synthetic')):window.save_equipment()
        self.assertIn('保存できません',window.trial_status.text());self.assertEqual(self.engine.progress('A')['equipped'],{})
        window.refresh();self.assertEqual(combo.currentData(),'base:welcome_pin');window.save_equipment()
        self.assertEqual(self.engine.progress('A')['equipped'],{'accessory':'base:welcome_pin'})
        self.assertEqual(self.engine.progress('B')['equipped'],{});self.service.apply_costumes.assert_called_once()
