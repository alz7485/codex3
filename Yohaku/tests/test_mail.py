from datetime import datetime, timedelta, timezone
import sys
import types
import unittest
from unittest.mock import patch
from companion.mail import MailDeduplicator, OutlookMailWatcher


class MailWatcherTests(unittest.TestCase):
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
        namespace=types.SimpleNamespace(GetDefaultFolder=lambda _:types.SimpleNamespace(Items=items),GetItemFromID=lambda _:new)
        app=types.SimpleNamespace(GetNamespace=lambda _:namespace)
        package=types.ModuleType('win32com');client=types.ModuleType('win32com.client');package.client=client
        activations=[]
        client.GetActiveObject=lambda name:activations.append(name) or app
        def with_events(app, handler):
            if not events:raise RuntimeError('no event cache')
            state['handler']=handler();return state['handler']
        client.WithEvents=with_events
        pythoncom=types.ModuleType('pythoncom');pythoncom.CoInitialize=lambda:None;pythoncom.CoUninitialize=lambda:None
        def received(payload):delivered.append(payload);watcher.stop()
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
        self.assertEqual(delivered,[{'count':1,'subjects':[]}])
        self.assertEqual(new.subject_reads,0)
        self.assertTrue(status)

    def test_new_mail_event_is_immediate_without_subject_body_or_sender_reads(self):
        self.exercise_watcher(events=True)

    def test_polling_fallback_ignores_existing_mail_and_detects_new_mail(self):
        self.exercise_watcher(events=False)
