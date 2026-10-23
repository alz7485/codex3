"""Read-only classic Outlook appointments and unaccepted Inbox meeting requests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import sys

from .core import Event

APPOINTMENT = '{00062002-0000-0000-C000-000000000046}'
MEETING = '{6ED8DA90-450B-101B-98DA-00AA003F1305}'


class CalendarEvents(list):
    def __init__(self, values, complete=True, warnings=()):
        super().__init__(values)
        self.complete = complete
        self.warnings = tuple(dict.fromkeys(warnings))


def named_property(item, group, identifier, default=None):
    try:
        return item.PropertyAccessor.GetProperty(f'http://schemas.microsoft.com/mapi/id/{group}/{identifier}')
    except Exception:
        return default


def optional(item, attribute, default=None):
    try:
        return getattr(item, attribute)
    except Exception:
        return default


def global_identity(item):
    value = optional(item, 'GlobalAppointmentID')
    if not value:
        value = named_property(item, MEETING, '00030102')
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex().upper()
    if isinstance(value, (tuple, list)):
        try:
            return bytes(value).hex().upper()
        except (ValueError, TypeError):
            return ''
    return str(value or '').strip().upper()


def utc_time(value):
    # StartUTC/EndUTC and PT_SYSTIME named properties contain literal UTC time.
    return value.replace(tzinfo=timezone.utc).astimezone()


def event_from(item, start, end, show_titles, response=''):
    legacy = f'{item.EntryID}/{start.isoformat()}'
    legacy_key = hashlib.sha256(legacy.encode()).hexdigest()
    identity = global_identity(item)
    key = hashlib.sha256(f'{identity}/{start.astimezone(timezone.utc).isoformat()}'.encode()).hexdigest() if identity else legacy_key
    return Event(key, start, end, str(optional(item, 'Subject', '') or '') if show_titles else '', response, legacy_key)


def merge_events(appointments, requests, excluded):
    # Calendar is authoritative when a request has already become an appointment.
    merged = {event.key: event for event in appointments if event.key not in excluded}
    for event in requests:
        if event.key not in excluded:
            merged.setdefault(event.key, event)
    return sorted(merged.values(), key=lambda event: event.start)


def read_calendar(show_titles: bool = False, whole_week: bool = False) -> list[Event]:
    if sys.platform != 'win32':
        raise RuntimeError('従来版Outlookとの接続はWindowsで利用できます。')
    import pythoncom
    import win32api
    import win32com.client

    pythoncom.CoInitialize()
    try:
        try:
            outlook = win32com.client.GetActiveObject('Outlook.Application')
        except Exception:
            raise RuntimeError('従来版Outlookを開いてから、再接続してください。') from None
        now = datetime.now().astimezone()
        lower = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if whole_week:
            lower -= timedelta(days=lower.weekday())
        upper = lower + timedelta(days=7 if whole_week else 1)
        namespace = outlook.GetNamespace('MAPI')
        warnings, appointments, requests, excluded = [], [], [], set()
        sources = 0

        def outlook_date(value):
            local = value.replace(tzinfo=None)
            return win32api.GetDateFormat(0, 0, local, None) + ' ' + win32api.GetTimeFormat(0, 2, local, None)

        try:
            items = namespace.GetDefaultFolder(9).Items
            items.Sort('[Start]')
            items.IncludeRecurrences = True
            try:
                bounded = items.Restrict(f"[Start] < '{outlook_date(upper)}' AND [End] > '{outlook_date(lower)}'")
            except Exception:
                # Some regional/profile settings reject the Jet date syntax.
                begin = lower.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                finish = upper.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                bounded = items.Restrict('@SQL="urn:schemas:calendar:dtstart" < '\
                                         f"'{finish}' AND \"urn:schemas:calendar:dtend\" > '{begin}'")
            item, scanned = bounded.GetFirst(), 0
            sources += 1
            while item is not None and scanned < 512:
                scanned += 1
                try:
                    if not item.AllDayEvent:
                        start, end = utc_time(item.StartUTC), utc_time(item.EndUTC)
                        if lower <= start < upper and end > start:
                            response = optional(item, 'ResponseStatus', 0)
                            status = optional(item, 'MeetingStatus', 0)
                            event = event_from(item, start, end, show_titles,
                                               '未承諾' if status in (1, 3) and response in (0, 5)
                                               else '仮承諾' if response == 2 else '')
                            if status in (5, 7) or response == 4:
                                excluded.add(event.key)
                            else:
                                appointments.append(event)
                except Exception:
                    warnings.append('読み取れない予定を除いて表示しています。')
                item = bounded.GetNext()
            if item is not None:
                warnings.append('予定表の確認上限に達したため、一部の予定を確認できていません。')
        except Exception:
            warnings.append('予定表を読み取れません。取得できた会議案内のみ表示しています。')

        try:
            inbox = namespace.GetDefaultFolder(6).Items
            # Restrict by class before scanning; ordinary mail is never inspected.
            invitations = inbox.Restrict("[MessageClass] = 'IPM.Schedule.Meeting.Request' OR [MessageClass] = 'IPM.Schedule.Meeting.Canceled'")
            invitations.Sort('[ReceivedTime]', True)
            item, scanned = invitations.GetFirst(), 0
            sources += 1
            seen_requests = set()
            while item is not None and scanned < 2048:
                scanned += 1
                try:
                    message_class = str(item.MessageClass).casefold()
                    if message_class in ('ipm.schedule.meeting.request', 'ipm.schedule.meeting.canceled'):
                        start = named_property(item, APPOINTMENT, '820D0040')
                        end = named_property(item, APPOINTMENT, '820E0040')
                        if start is None or end is None:
                            warnings.append('開催日時を読み取れない会議案内があります。')
                        elif not named_property(item, APPOINTMENT, '8215000B', False):
                            start, end = utc_time(start), utc_time(end)
                            if lower <= start < upper and end > start:
                                event = event_from(item, start, end, show_titles, '未承諾')
                                if event.key not in seen_requests:
                                    seen_requests.add(event.key)  # Most recent request wins.
                                    if message_class.endswith('.canceled'):
                                        excluded.add(event.key)
                                    response = named_property(item, APPOINTMENT, '82180003', 5)
                                    request_type = optional(item, 'MeetingRequestType', 0) or 0
                                    if (not message_class.endswith('.canceled') and response not in (3, 4)
                                            and not (int(request_type) & 524288)):
                                        requests.append(event)
                except Exception:
                    warnings.append('読み取れない会議案内を除いて表示しています。')
                item = invitations.GetNext()
            if item is not None:
                warnings.append('会議案内の確認上限に達したため、一部を確認できていません。')
        except Exception:
            warnings.append('未承諾の会議案内を確認できません。取得できた予定表のみ表示しています。')
        if not sources:
            raise RuntimeError('予定表と会議案内を読み取れませんでした。Outlookの状態・社内設定をご確認ください。')
        return CalendarEvents(merge_events(appointments, requests, excluded), complete=not warnings, warnings=warnings)
    except RuntimeError:
        raise
    except Exception:
        raise RuntimeError('予定を取得できませんでした。Outlookの状態・社内設定をご確認ください。') from None
    finally:
        pythoncom.CoUninitialize()
