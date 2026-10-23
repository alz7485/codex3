"""Classic Outlook receive events with a one-second Inbox polling fallback.

Never starts Outlook, reads bodies, changes read flags, or persists message IDs.
"""
from __future__ import annotations
from datetime import datetime
import hashlib
import sys
import threading
import time


class MailDeduplicator:
    def __init__(self):
        self.seen = set()
        self.order = []

    def accept(self, identity):
        key = hashlib.sha256(str(identity).encode('utf-8')).hexdigest()
        if key in self.seen:
            return False
        self.seen.add(key)
        self.order.append(key)
        if len(self.order) > 2048:
            self.seen.discard(self.order.pop(0))
        return True


class OutlookMailWatcher:
    def __init__(self, received, status, show_details=False):
        self.received = received
        self.status = status
        self.show_details = show_details
        self.stop_event = threading.Event()
        self.thread = None
        self.dedup = MailDeduplicator()

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def stop(self):
        self.stop_event.set()

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
                    started = datetime.now().astimezone()
                    watcher = self

                    def handle_ids(ids):
                        count, subjects = 0, []
                        for identity in str(ids).split(',')[:100]:
                            if not identity or watcher.stop_event.is_set():
                                continue
                            try:
                                item = namespace.GetItemFromID(identity)
                                if int(item.Class) not in (43, 53):
                                    continue
                                if not watcher.dedup.accept(identity):
                                    continue
                                count += 1
                                if watcher.show_details:
                                    subjects.append(str(item.Subject)[:120])
                            except Exception:
                                continue
                        if count and not watcher.stop_event.is_set():
                            watcher.received({'count': count, 'subjects': subjects})

                    class Events:
                        def OnNewMailEx(self, entry_ids):
                            handle_ids(entry_ids)

                    try:
                        sink = win32com.client.WithEvents(application, Events)
                        self.status('Outlook受信イベント＋1秒間隔の受信トレイ確認')
                    except Exception:
                        sink = None
                        self.status('Outlook受信トレイを1秒間隔で確認中（イベント接続は利用不可）')
                    # Seed existing mail without reading subjects or producing alerts.
                    inbox = namespace.GetDefaultFolder(6)
                    items = inbox.Items
                    items.Sort('[ReceivedTime]', True)
                    for index in range(1, min(int(items.Count), 100) + 1):
                        try:
                            old = items.Item(index)
                            if old.ReceivedTime.astimezone() < started:
                                self.dedup.accept(old.EntryID)
                        except Exception:
                            pass
                    next_poll = time.monotonic()
                    while not self.stop_event.is_set():
                        pythoncom.PumpWaitingMessages()
                        if time.monotonic() >= next_poll:
                            next_poll = time.monotonic() + 1
                            items = inbox.Items
                            items.Sort('[ReceivedTime]', True)
                            ids = []
                            for index in range(1, min(int(items.Count), 100) + 1):
                                item = items.Item(index)
                                try:
                                    received = item.ReceivedTime.astimezone()
                                    if received < started:
                                        break
                                    ids.append(str(item.EntryID))
                                except Exception:
                                    continue
                            if ids:
                                handle_ids(','.join(ids))
                        self.stop_event.wait(0.1)
                    sink = None
                except Exception:
                    self.status('受信通知は再接続待ちです。従来版Outlookを開いてください。')
                    self.stop_event.wait(2)
        finally:
            pythoncom.CoUninitialize()
