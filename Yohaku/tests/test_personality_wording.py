"""Non-destructive wording upgrades and occasional inline inner thoughts."""
from copy import deepcopy
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from companion.core import Engine, Settings
from companion.dialogue import (DialogueError, DialogueStore, PERSONALITY_WORDING_PATH,
    defaults, read_document, upgrade, validate)


def v018_document():
    document=defaults();document.pop('personality_wording_version')
    changes=json.loads(PERSONALITY_WORDING_PATH.read_text())
    for voice,topics in changes['voices'].items():
        for topic,rows in topics.items():
            before={row['after']:row['before'] for row in rows}
            document['phrases'][voice][topic]=[before.get(line,line) for line in document['phrases'][voice][topic]]
    return document


class PersonalityWordingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'dialogue.json'

    def test_bundled_versioned_changes_upgrade_previous_default_without_changing_other_voices(self):
        old=v018_document();original=deepcopy(old)
        self.assertEqual(old['phrases']['寡黙な先輩']['call'][0],'呼んだか。')
        self.assertEqual(old['phrases']['倒置法の使い手']['chat'][0],'小さくていい……次の一歩は。')
        updated=validate(upgrade(old))
        self.assertEqual(updated,defaults());self.assertEqual(old,original)
        for field in ('options','profiles','rules'):self.assertEqual(updated[field],old[field])
        for voice in ('控えめな皮肉屋','冷静な案内役','元気な応援係','のんびりした同僚','馴れ馴れしい関西弁'):
            self.assertEqual(updated['phrases'][voice],old['phrases'][voice])

    def test_mixed_stock_custom_reordered_and_deleted_lines_keep_their_order_and_length(self):
        old=v018_document()
        old['phrases']['寡黙な先輩']['call']=['独自の返事','ここにいる。','呼んだか。']
        old['phrases']['倒置法の使い手']['chat']=['独自の語り。','小さくていい……次の一歩は。']
        old['options']['interval_minutes']=17
        old['rules'][2]['enabled']=False
        updated=validate(upgrade(old))
        self.assertEqual(updated['phrases']['寡黙な先輩']['call'],[
            '独自の返事','ここにいる。','呼んだか。\n（呼ばれると、少しうれしい。）'])
        self.assertEqual(updated['phrases']['倒置法の使い手']['chat'],[
            '独自の語り。','次の一手を決めよう。\n小さくていい……進める一手なら。'])
        self.assertEqual(updated['rules'],old['rules']);self.assertEqual(updated['options'],old['options'])

    def test_custom_topic_with_stock_like_text_and_deleted_topic_are_not_rewritten_or_restored(self):
        old=v018_document();old['rules']=[row for row in old['rules'] if row['id']!='water']
        custom=deepcopy(next(row for row in old['rules'] if row['id']=='chat'))
        custom.update(id='my_topic',label='独自の話題');old['rules'].append(custom)
        for voice,bank in old['phrases'].items():
            bank.pop('water');bank['my_topic']=['呼んだか。','小さくていい……次の一歩は。']
        updated=validate(upgrade(old))
        self.assertEqual(updated['rules'],old['rules'])
        for voice,bank in updated['phrases'].items():
            self.assertNotIn('water',bank);self.assertEqual(bank['my_topic'],old['phrases'][voice]['my_topic'])

    def test_reading_keeps_file_until_save_and_failed_save_preserves_original(self):
        old=v018_document();self.path.write_text(json.dumps(old,ensure_ascii=False))
        raw=self.path.read_bytes();store=DialogueStore(self.path)
        self.assertFalse(store.error);self.assertEqual(self.path.read_bytes(),raw)
        self.assertEqual(store.data['phrases']['寡黙な先輩']['call'][0],
                         '呼んだか。\n（呼ばれると、少しうれしい。）')
        with patch('pathlib.Path.replace',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):store.save(store.data)
        self.assertEqual(self.path.read_bytes(),raw)
        self.assertFalse(self.path.with_suffix('.json.tmp').exists())
        store.save(store.data)
        self.assertEqual(self.path.with_suffix('.json.bak').read_bytes(),raw)
        self.assertEqual(read_document(self.path),store.data)

    def test_revision_marker_preserves_user_removal_of_thoughts_and_reversion_to_old_wording(self):
        document=defaults()
        document['phrases']['寡黙な先輩']['call'][0]='呼んだか。'
        document['phrases']['倒置法の使い手']['chat'][0]='小さくていい……次の一歩は。'
        self.path.write_text(json.dumps(document,ensure_ascii=False))
        self.assertEqual(read_document(self.path),document)
        self.assertEqual(upgrade(upgrade(document)),document)

    def test_malformed_phrase_is_rejected_and_corrupt_input_remains_intact(self):
        old=v018_document();old['phrases']['寡黙な先輩']['call']=[{'text':'不正'}]
        with self.assertRaises(DialogueError):validate(upgrade(old))
        self.path.write_text(json.dumps(old,ensure_ascii=False));raw=self.path.read_bytes()
        self.assertTrue(DialogueStore(self.path).error);self.assertEqual(self.path.read_bytes(),raw)

    def test_engine_selects_plain_or_thought_variant_as_one_message_and_retains_line_break(self):
        store=DialogueStore(self.path);settings=Settings(personality='寡黙な先輩')
        engine=Engine(settings,self.path.with_name('history.json'),dialogue=store,choose=lambda values:values[0])
        text=engine.phrase('call')
        self.assertEqual(text,'呼んだか。\n（呼ばれると、少しうれしい。）')
        engine.choose=lambda values:1
        self.assertEqual(engine.phrase('call'),'どうした。')
        lines=[line for phrases in store.data['phrases']['寡黙な先輩'].values() for line in phrases]
        thoughts=[line for line in lines if '\n（' in line]
        self.assertEqual(len(thoughts),32);self.assertEqual(len(lines),181)
        for line in thoughts:self.assertRegex(line,r'^[^\n]+\n（[^（）\n]+）$')


class PersonalityWordingInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from companion.ui import create_application
        cls.app=create_application()

    def test_thought_and_narration_share_bubble_and_fit_their_content_height(self):
        from companion.ui import InteractionBubble
        from companion.core import Notice
        bubble=InteractionBubble();self.addCleanup(bubble.hide)
        bank=defaults()['phrases']
        for voice,topic in (('寡黙な先輩','call'),('倒置法の使い手','chat'),('倒置法の使い手','cpu_high')):
            text=bank[voice][topic][0]
            bubble.display(Notice('',text));self.app.processEvents()
            self.assertEqual(bubble.text.text(),text)
            self.assertFalse(bubble.heading.isVisible())
            self.assertFalse(bubble.choice_row.isVisible())
            self.assertEqual(bubble.content_scroll.verticalScrollBar().maximum(),0)
        bubble.display(Notice('',bank['寡黙な先輩']['call'][0]));self.app.processEvents()
        height=bubble.height()
        bubble.display(Notice('','呼んだか。'));self.app.processEvents()
        self.assertLess(bubble.height(),height)

    def test_editor_round_trips_and_removes_inline_thought_without_readding_it(self):
        from companion.dialogue_editor import DialogueEditor
        with tempfile.TemporaryDirectory() as temporary:
            store=DialogueStore(Path(temporary)/'dialogue.json')
            editor=DialogueEditor(store)
            try:
                editor.voice.setCurrentText('寡黙な先輩');editor.phrase_topics.setCurrentRow(0)
                self.assertEqual(editor.line_edit.toPlainText(),'呼んだか。\n（呼ばれると、少しうれしい。）')
                editor.line_edit.setPlainText('了解。\n（お茶も忘れずに。）')
                self.assertTrue(editor.save())
                self.assertEqual(read_document(store.path)['phrases']['寡黙な先輩']['call'][0],
                                 '了解。\n（お茶も忘れずに。）')
                editor.line_edit.setPlainText('呼んだか。');self.assertTrue(editor.save())
                self.assertEqual(read_document(store.path)['phrases']['寡黙な先輩']['call'][0],'呼んだか。')
            finally:
                editor.dirty=False;editor.hide();editor.deleteLater();self.app.processEvents()


if __name__=='__main__':unittest.main()
