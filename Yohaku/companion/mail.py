"""Classic Outlook receive events with a one-second Inbox polling fallback.

Never starts Outlook, reads subjects/bodies, changes read flags, or persists IDs.
"""
from __future__ import annotations
from datetime import datetime, timedelta
import hashlib
import sys
import threading
import time


class MailDeduplicator:
    def __init__(self, capacity=2048):
        self.capacity = capacity
        self.seen = set()
        self.order = []

    def accept(self, identity):
        key = hashlib.sha256(str(identity).encode('utf-8')).hexdigest()
        if key in self.seen:
            return False
        self.seen.add(key)
        self.order.append(key)
        if self.capacity is not None and len(self.order) > self.capacity:
            self.seen.discard(self.order.pop(0))
        return True


def mail_identity(item):
    """Use a stable transport ID when rules move mail and change its EntryID."""
    try:
        store = str(item.Parent.StoreID)
    except Exception:
        store = ''
    for tag in ('0x1035001F', '0x1035001E'):
        try:
            identity = str(item.PropertyAccessor.GetProperty(
                'http://schemas.microsoft.com/mapi/proptag/' + tag)).strip()
            if identity:
                return (store, int(item.Class), 'internet', identity)
        except Exception:
            pass
    return (store, int(item.Class), 'entry', str(item.EntryID))


def sender_name(item):
    for attribute in ('SenderName', 'SenderEmailAddress'):
        try:
            value = str(getattr(item, attribute) or '').replace('\r', ' ').replace('\n', ' ').strip()
            if value:
                return value[:160]
        except Exception:
            pass
    return '送信者を取得できませんでした'


class OutlookMailWatcher:
    def __init__(self, received, status, show_senders=True):
        self.received = received
        self.status = status
        self.show_senders = show_senders
        self.stop_event = threading.Event()
        self.thread = None
        # Keep all hashes during this watcher session: an Inbox burst larger
        # than the LRU must not be counted again at the next poll.
        self.dedup = MailDeduplicator(capacity=None)
        self.started = datetime.now().astimezone()
        self.poll_since = self.started

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def stop(self):
        self.stop_event.set()

    def collect(self, items):
        messages = []
        for item in items:
            if self.stop_event.is_set():
                break
            try:
                kind = int(item.Class)
                if kind not in (43, 53) or item.ReceivedTime.astimezone() < self.started:
                    continue
                if not self.dedup.accept(mail_identity(item)):
                    continue
            except Exception:
                continue
            messages.append({'kind': 'mail' if kind == 43 else 'meeting',
                             'sender': sender_name(item) if self.show_senders else ''})
        if messages and not self.stop_event.is_set():
            self.received({'messages': messages})

    def run(self):
        if sys.platform != 'win32':
            self.status('受信通知はWindowsの従来版Outlookで利用できます。')
            return
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            while not self.stop_event.is_set():
                try:
                    application = win32com.client.GetActiveObject('Outlook.Application')
                    namespace = application.GetNamespace('MAPI')
                    watcher = self

                    def handle_ids(ids):
                        def incoming():
                            for identity in str(ids).split(','):
                                if not identity or watcher.stop_event.is_set():
                                    continue
                                try:
                                    yield namespace.GetItemFromID(identity)
                                except Exception:
                                    continue
                        watcher.collect(incoming())

                    class Events:
                        def OnNewMailEx(self, entry_ids):
                            handle_ids(entry_ids)

                    try:
                        sink = win32com.client.WithEvents(application, Events)
                        self.status('Outlook受信イベント＋1秒間隔の受信トレイ確認')
                    except Exception:
                        sink = None
                        self.status('Outlook受信トレイを1秒間隔で確認中（イベント接続は利用不可）')
                    inbox = namespace.GetDefaultFolder(6)
                    next_poll = time.monotonic()
                    while not self.stop_event.is_set():
                        pythoncom.PumpWaitingMessages()
                        if time.monotonic() >= next_poll:
                            next_poll = time.monotonic() + 1
                            items = inbox.Items
                            items.Sort('[ReceivedTime]', True)
                            try:
                                unread = int(inbox.UnReadItemCount)
                                if unread < 0:
                                    unread = None
                            except Exception:
                                unread = None
                            self.received({'unread_count': unread})
                            latest = [self.poll_since]

                            def recent_items():
                                # Do not truncate a burst to the first 100 messages.
                                for index in range(1, int(items.Count) + 1):
                                    if self.stop_event.is_set():
                                        return
                                    try:
                                        item = items.Item(index)
                                        received = item.ReceivedTime.astimezone()
                                        if received < self.poll_since:
                                            break
                                        latest[0] = max(latest[0], received)
                                        yield item
                                    except Exception:
                                        continue
                            self.collect(recent_items())
                            # Rescan a small overlap for timestamp ties and sync
                            # delays, rather than the whole monitoring session.
                            self.poll_since = max(self.started, latest[0] - timedelta(minutes=2))
                        self.stop_event.wait(0.1)
                    sink = None
                except Exception:
                    self.status('受信通知は再接続待ちです。従来版Outlookを開いてください。')
                    self.stop_event.wait(2)
        finally:
            pythoncom.CoUninitialize()
