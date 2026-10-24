"""Read-only classic Outlook appointments and unaccepted Inbox meeting requests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import hashlib
import sys

from .core import Event

APPOINTMENT = '{00062002-0000-0000-C000-000000000046}'
MEETING = '{6ED8DA90-450B-101B-98DA-00AA003F1305}'


def show_calendar():
    """Explicit user navigation only. Never save, respond to or add an item."""
    if sys.platform!='win32':raise RuntimeError('Outlookの予定表はWindowsで開けます。')
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    try:
        try:app=win32com.client.GetActiveObject('Outlook.Application')
        except Exception:app=win32com.client.Dispatch('Outlook.Application')
        folder=app.GetNamespace('MAPI').GetDefaultFolder(9)
        explorer=app.ActiveExplorer()
        if explorer is None:explorer=folder.GetExplorer()
        else:explorer.CurrentFolder=folder
        explorer.Display();explorer.Activate()
    except Exception:
        raise RuntimeError('Outlookの予定表を開けませんでした。従来版Outlookの起動・設定をご確認ください。') from None
    finally:pythoncom.CoUninitialize()


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


@dataclass
class Meeting:
    event: Event
    identity: str
    occurrence: str
    recurring: bool | None
    cancelled: bool = False
    eligible: bool = True
    sequence: int | None = None


def meeting_from(item, event, cancelled=False, eligible=True):
    identity = global_identity(item)
    occurrence = ''
    # GlobalObjectId embeds the original occurrence date. Clean only its date
    # bytes so an exception moved to another day still matches its old request.
    if identity.startswith('040000008200E00074C5B7101A82E008') and len(identity) >= 40:
        raw = bytes.fromhex(identity)
        if any(raw[16:20]):
            occurrence = f'{int.from_bytes(raw[16:18], "big"):04d}-{raw[18]:02d}-{raw[19]:02d}'
        identity = (raw[:16] + b'\0' * 4 + raw[20:]).hex().upper()
    original = named_property(item, APPOINTMENT, '82280040')
    if original is not None:
        occurrence = utc_time(original).date().isoformat()
    recurring = optional(item, 'IsRecurring', named_property(item, APPOINTMENT, '8223000B'))
    sequence = named_property(item, APPOINTMENT, '82010003')
    return Meeting(event, identity or event.key, occurrence, recurring, cancelled, eligible,
                   sequence if isinstance(sequence, int) else None)


def merge_events(appointments, requests, lower, upper):
    # Resolve revisions before the date filter: a move outside this view also
    # supersedes the old in-range invitation. Inbox is already newest first.
    starts = {}
    for meeting in appointments:
        if meeting.recurring is None:
            starts.setdefault(meeting.identity, set()).add(meeting.event.start)
    repeated = {identity for identity, values in starts.items() if len(values) > 1}

    def key(meeting):
        occurrence = meeting.occurrence
        if not occurrence and (meeting.recurring or meeting.identity in repeated):
            occurrence = meeting.event.start.date().isoformat()
        return meeting.identity, occurrence

    latest = {}
    cancelled_series = {}
    for index, meeting in enumerate(requests):
        logical = key(meeting)
        if logical not in latest:
            latest[logical] = (meeting, index)
            if meeting.cancelled and meeting.recurring and not meeting.occurrence:
                cancelled_series.setdefault(meeting.identity, (meeting, index))
    merged = {}
    calendar = {}
    blocked = set()
    for meeting in appointments:
        logical = key(meeting)
        if meeting.cancelled:
            blocked.add(logical)
        else:
            merged[logical] = meeting.event
            calendar[logical] = meeting
    for logical, (meeting, index) in latest.items():
        saved = calendar.get(logical)
        if (saved and saved.sequence is not None and meeting.sequence is not None
                and meeting.sequence < saved.sequence):
            continue  # A stale Inbox revision must not cancel a newer Calendar copy.
        if meeting.cancelled:
            blocked.add(logical)
        elif meeting.eligible:
            if (saved and saved.sequence is not None and meeting.sequence is not None
                    and meeting.sequence > saved.sequence):
                merged[logical] = meeting.event
            else:
                # Without comparable revisions the existing Calendar is authoritative.
                merged.setdefault(logical, meeting.event)

    def series_active(logical):
        cancellation = cancelled_series.get(logical[0])
        if cancellation is None:
            return True
        cancelled, cancelled_at = cancellation
        saved = calendar.get(logical)
        if (saved and saved.sequence is not None and cancelled.sequence is not None
                and saved.sequence > cancelled.sequence):
            return True
        meeting, index = latest.get(logical, (None, cancelled_at))
        return index < cancelled_at and meeting.eligible and not meeting.cancelled

    return sorted((event for logical, event in merged.items()
                   if logical not in blocked and series_active(logical)
                   and lower <= event.start < upper), key=lambda event: event.start)


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
        warnings, appointments, requests = [], [], []
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
                            appointments.append(meeting_from(item, event, status in (5, 7) or response == 4))
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
            while item is not None and scanned < 2048:
                scanned += 1
                try:
                    message_class = str(item.MessageClass).casefold()
                    if message_class in ('ipm.schedule.meeting.request', 'ipm.schedule.meeting.canceled'):
                        start = named_property(item, APPOINTMENT, '820D0040')
                        end = named_property(item, APPOINTMENT, '820E0040')
                        if start is None or end is None:
                            warnings.append('開催日時を読み取れない会議案内があります。')
                        else:
                            start, end = utc_time(start), utc_time(end)
                            if end > start:
                                event = event_from(item, start, end, show_titles, '未承諾')
                                response = named_property(item, APPOINTMENT, '82180003', 5)
                                request_type = optional(item, 'MeetingRequestType', 0) or 0
                                requests.append(meeting_from(item, event, message_class.endswith('.canceled'),
                                                             response not in (3, 4) and not (int(request_type) & 524288)
                                                             and not named_property(item, APPOINTMENT, '8215000B', False)))
                except Exception:
                    warnings.append('読み取れない会議案内を除いて表示しています。')
                item = invitations.GetNext()
            if item is not None:
                warnings.append('会議案内の確認上限に達したため、一部を確認できていません。')
        except Exception:
            warnings.append('未承諾の会議案内を確認できません。取得できた予定表のみ表示しています。')
        if not sources:
            raise RuntimeError('予定表と会議案内を読み取れませんでした。Outlookの状態・社内設定をご確認ください。')
        return CalendarEvents(merge_events(appointments, requests, lower, upper), complete=not warnings, warnings=warnings)
    except RuntimeError:
        raise
    except Exception:
        raise RuntimeError('予定を取得できませんでした。Outlookの状態・社内設定をご確認ください。') from None
    finally:
        pythoncom.CoUninitialize()
