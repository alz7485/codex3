from datetime import datetime, timedelta, timezone
import sys
import types
import unittest
from unittest.mock import patch
from companion.mail import MailDeduplicator, OutlookMailWatcher, sender_with_honorific


class MailWatcherTests(unittest.TestCase):
    def test_sender_honorific_is_added_once_and_not_added_to_unknown_sender(self):
        for value, expected in [('山田 太郎', '山田 太郎さん'), ('佐藤さん', '佐藤さん'),
                                ('鈴木様', '鈴木さん'), ('田中さま', '田中さん'),
                                ('送信者不明', '送信者不明'), ('   ', '送信者不明'),
                                ('送信者を取得できませんでした', '送信者を取得できませんでした')]:
            self.assertEqual(sender_with_honorific(value), expected)
    def message(self, identity, sender='山田 太郎', transport=None):
        class Message:
            Class = 43
            ReceivedTime = datetime.now(timezone.utc) + timedelta(seconds=3)
            EntryID = identity
            SenderName = sender
            Parent = types.SimpleNamespace(StoreID='inbox-store')
            @property
            def Subject(self): raise AssertionError('Subject must never be read')
            @property
            def Body(self): raise AssertionError('Body must never be read')
        item = Message()
        if transport:
            item.PropertyAccessor = types.SimpleNamespace(GetProperty=lambda _: transport)
        return item

    def test_sender_is_display_only_and_moved_mail_is_not_delivered_twice(self):
        delivered = []
        watcher = OutlookMailWatcher(delivered.append, lambda _: None)
        watcher.collect([self.message('entry-1', transport='stable-message'),
                         self.message('entry-2', transport='stable-message')])
        self.assertEqual(delivered, [{'messages': [{'kind': 'mail', 'sender': '山田 太郎'}]}])
        self.assertNotIn('stable-message', watcher.dedup.seen)

    def test_large_burst_is_not_truncated_or_repeated_when_dedup_cache_would_overflow(self):
        delivered = []
        watcher = OutlookMailWatcher(delivered.append, lambda _: None)
        items = [self.message(str(i)) for i in range(2100)]
        watcher.collect(items)
        watcher.collect(items)
        self.assertEqual(len(delivered), 1)
        self.assertEqual(len(delivered[0]['messages']), 2100)

    def test_missing_sender_keeps_mail_and_preexisting_mail_is_ignored(self):
        delivered = []
        watcher = OutlookMailWatcher(delivered.append, lambda _: None)
        old = self.message('old')
        old.ReceivedTime -= timedelta(days=1)
        watcher.collect([old, self.message('new', sender='')])
        self.assertEqual(delivered, [{'messages': [{'kind': 'mail', 'sender': '送信者を取得できませんでした'}]}])

    def test_deduplication_is_bounded_and_no_raw_ids_are_persisted(self):
        cache=MailDeduplicator()
        self.assertTrue(cache.accept('private-id'))
        self.assertFalse(cache.accept('private-id'))
        self.assertNotIn('private-id',cache.seen)
        for i in range(2100):cache.accept(f'id-{i}')
        self.assertEqual(len(cache.seen),2048)

    def exercise_watcher(self, events=True):
        delivered=[];status=[];state={}
        now=datetime.now(timezone.utc)
        class Message:
            Class=43
            def __init__(self, identity, received):self.EntryID=identity;self.ReceivedTime=received;self.subject_reads=0
            @property
            def Subject(self):self.subject_reads+=1;return 'PRIVATE SUBJECT'
            @property
            def Body(self):raise AssertionError('Body must not be read')
            @property
            def SenderName(self):raise AssertionError('Sender must not be read')
        old=Message('old',now-timedelta(days=1));new=Message('new',now+timedelta(seconds=3))
        class Items:
            Count=1
            def Sort(self,*_):pass
            def Item(self,_):return state.get('item',old)
        items=Items()
        namespace=types.SimpleNamespace(GetDefaultFolder=lambda _:types.SimpleNamespace(Items=items,UnReadItemCount=7),GetItemFromID=lambda _:new)
        app=types.SimpleNamespace(GetNamespace=lambda _:namespace)
        package=types.ModuleType('win32com');client=types.ModuleType('win32com.client');package.client=client
        activations=[]
        client.GetActiveObject=lambda name:activations.append(name) or app
        def with_events(app, handler):
            if not events:raise RuntimeError('no event cache')
            state['handler']=handler();return state['handler']
        client.WithEvents=with_events
        pythoncom=types.ModuleType('pythoncom');pythoncom.CoInitialize=lambda:None;pythoncom.CoUninitialize=lambda:None
        def received(payload):
            delivered.append(payload)
            if 'messages' in payload: watcher.stop()
        watcher=OutlookMailWatcher(received,status.append,False)
        def pump():
            if events:
                state['handler'].OnNewMailEx('new')
                # A second report from the event/poll channels must not alert again.
                state['handler'].OnNewMailEx('new')
            else:state['item']=new
        pythoncom.PumpWaitingMessages=pump
        with patch.dict(sys.modules,{'pythoncom':pythoncom,'win32com':package,'win32com.client':client}),patch('companion.mail.sys.platform','win32'):
            watcher.run()
        self.assertEqual(activations,['Outlook.Application'])
        self.assertEqual([p for p in delivered if 'messages' in p],[{'messages':[{'kind':'mail','sender':''}]}])
        if not events: self.assertIn({'unread_count':7},delivered)
        self.assertEqual(new.subject_reads,0)
        self.assertTrue(status)

    def test_new_mail_event_is_immediate_without_subject_body_or_sender_reads(self):
        self.exercise_watcher(events=True)

    def test_polling_fallback_ignores_existing_mail_and_detects_new_mail(self):
        self.exercise_watcher(events=False)
