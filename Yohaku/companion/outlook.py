"""Classic Outlook read-only adapter. No Graph, authentication or network client."""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import sys

from .core import Event


def read_calendar(show_titles: bool = False) -> list[Event]:
    if sys.platform != "win32":
        raise RuntimeError("従来版Outlookとの接続はWindowsで利用できます。")
    import pythoncom
    import win32api
    import win32com.client

    pythoncom.CoInitialize()
    try:
        try:
            outlook = win32com.client.GetActiveObject("Outlook.Application")
        except Exception:
            raise RuntimeError("従来版Outlookを開いてから、再接続してください。") from None
        now = datetime.now().astimezone()
        lower = now.replace(hour=0, minute=0, second=0, microsecond=0)
        upper = lower + timedelta(days=1)

        def outlook_date(value):
            # Outlook Jet filters use the Windows user's regional date/time format.
            local = value.replace(tzinfo=None)
            return (win32api.GetDateFormat(0, 0, local, None) + " " +
                    win32api.GetTimeFormat(0, 2, local, None))

        calendar = outlook.GetNamespace("MAPI").GetDefaultFolder(9)
        items = calendar.Items
        items.Sort("[Start]")
        items.IncludeRecurrences = True
        restriction = (f"[Start] < '{outlook_date(upper)}' AND "
                       f"[End] > '{outlook_date(lower)}'")
        bounded = items.Restrict(restriction)
        events = []
        item = bounded.GetFirst()
        scanned = 0
        while item is not None and scanned < 512:
            scanned += 1
            if not item.AllDayEvent and item.MeetingStatus not in (5, 7):
                # StartUTC/EndUTC avoid interpreting the COM datetime's TZ wrapper.
                from datetime import timezone
                start = item.StartUTC.replace(tzinfo=timezone.utc).astimezone()
                end = item.EndUTC.replace(tzinfo=timezone.utc).astimezone()
                if lower <= start < upper and end > start:
                    identity = f"{item.EntryID}/{start.isoformat()}"
                    key = hashlib.sha256(identity.encode()).hexdigest()
                    title = str(item.Subject) if show_titles else ""
                    events.append(Event(key, start, end, title))
            item = bounded.GetNext()
        return sorted(events, key=lambda event: event.start)
    except RuntimeError:
        raise
    except Exception:
        # Do not surface raw COM errors, profile names or appointment contents.
        raise RuntimeError("予定を取得できませんでした。Outlookの状態・社内設定をご確認ください。") from None
    finally:
        pythoncom.CoUninitialize()
