"""Local aggregate context, with no input hooks, key contents or window titles."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta
import os
from pathlib import Path
import sys

from .core import load_json, save_json

from .metrics import METRICS


def input_idle_seconds():
    if sys.platform != 'win32':
        return None
    class LastInput(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.UINT), ('dwTime', wintypes.DWORD)]
    info = LastInput()
    info.cbSize = ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return None
    clock = ctypes.windll.kernel32.GetTickCount64
    clock.restype = ctypes.c_ulonglong
    return ((clock() - info.dwTime) & 0xFFFFFFFF) / 1000


def desktop_file_count():
    """Current user's redirected Desktop plus Public Desktop; names are not returned."""
    if sys.platform != 'win32':
        return None
    from win32com.shell import shell, shellcon
    roots = {Path(shell.SHGetFolderPath(0, key, 0, 0)) for key in
             (shellcon.CSIDL_DESKTOPDIRECTORY, shellcon.CSIDL_COMMON_DESKTOPDIRECTORY)}
    total = 0
    for root in roots:
        if not root.exists():
            continue
        with os.scandir(root) as entries:
            for item in entries:
                if total >= 10000:
                    return total
                if item.name.casefold() == 'desktop.ini' or item.name.startswith('.'):
                    continue
                try:
                    stat = item.stat(follow_symlinks=False)
                    if getattr(stat, 'st_file_attributes', 0) & 0x6:
                        continue  # Hidden/system; do not count directories or recurse.
                    if item.is_file(follow_symlinks=False):
                        total += 1
                except OSError:
                    continue
    return total


def office_file_count():
    if sys.platform != 'win32':
        return None
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    try:
        total, failed = 0, False
        for app, collection in (('Excel.Application', 'Workbooks'), ('Word.Application', 'Documents'), ('PowerPoint.Application', 'Presentations')):
            try:
                office = win32com.client.GetActiveObject(app)
            except Exception as error:
                if getattr(error, 'hresult', None) not in (-2147221021, -2147221005, -2147221164):
                    failed = True
                continue
            try:
                total += min(10000, int(getattr(office, collection).Count))
            except Exception:
                failed = True
        return None if failed else total
    finally:
        pythoncom.CoUninitialize()


class UsageLedger:
    """Only observed time is accumulated; sleep, app shutdown and unknown samples are gaps."""
    def __init__(self, path, now):
        self.path = Path(path)
        raw = load_json(self.path)
        self.days = {}
        for day, values in raw.get('days', {}).items() if isinstance(raw.get('days'), dict) else ():
            try:
                datetime.strptime(day, '%Y-%m-%d')
                if isinstance(values, dict) and all(type(values.get(k)) in (int, float) and 0 <= values[k] <= 90000
                                                   for k in ('active', 'idle', 'observed')):
                    self.days[day] = {k: float(values[k]) for k in ('active', 'idle', 'observed')}
            except (ValueError, TypeError):
                continue
        self.active_streak = 0.0
        self.idle = None
        self.day = now.date().isoformat()
        self.previous_days = set(self.days)
        self.days.setdefault(self.day, dict(active=0.0, idle=0.0, observed=0.0))
        self.prune(now)

    def touch(self, now):
        self.day = now.date().isoformat()
        self.days.setdefault(self.day, dict(active=0.0, idle=0.0, observed=0.0))
        self.prune(now)

    def prune(self, now):
        cutoff = (now.date() - timedelta(days=34)).isoformat()
        self.days = {day: values for day, values in self.days.items() if cutoff <= day <= now.date().isoformat()}

    def sample(self, now, dt, idle, threshold=60):
        self.day = now.date().isoformat()
        self.days.setdefault(self.day, dict(active=0.0, idle=0.0, observed=0.0))
        self.idle = idle if type(idle) in (float, int) and idle >= 0 else None
        if not 0 < dt <= 15 or self.idle is None:
            self.active_streak = 0
            return
        active = self.idle < threshold
        self.active_streak = self.active_streak + dt if active else 0
        # At most 15 seconds can cross a local midnight. Split the observed time.
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_dt = min(dt, max(0, (now - midnight).total_seconds()))
        portions = [(self.day, today_dt)]
        if dt > today_dt:
            portions.append(((now.date() - timedelta(days=1)).isoformat(), dt - today_dt))
        for day, duration in portions:
            bucket = self.days.setdefault(day, dict(active=0.0, idle=0.0, observed=0.0))
            bucket['active' if active else 'idle'] += duration
            bucket['observed'] += duration
        self.prune(now)

    def metrics(self, now):
        day = now.date().isoformat()
        bucket = self.days.get(day, dict(active=0, idle=0, observed=0))
        yesterday = (now.date() - timedelta(days=1)).isoformat()
        before = [d for d in (self.previous_days | set(self.days)) if d < day]
        last = max(before) if before else None
        result = {
            'idle_minutes': self.idle / 60 if self.idle is not None else None,
            'active_streak_minutes': self.active_streak / 60 if self.idle is not None else None,
            'daily_active_minutes': bucket['active'] / 60 if self.idle is not None else None,
            'daily_idle_minutes': bucket['idle'] / 60 if self.idle is not None else None,
            'observed_minutes': bucket['observed'] / 60,
            'missed_yesterday': int(yesterday not in self.previous_days | set(self.days)) if last else None,
            'days_since_last_use': (now.date() - datetime.fromisoformat(last).date()).days if last else None,
        }
        return result

    def persist(self):
        save_json(self.path, {'version': 1, 'days': self.days})


def work_metrics(now, start='08:30', end='17:30'):
    beginning = now.replace(hour=int(start[:2]), minute=int(start[3:]), second=0, microsecond=0)
    ending = now.replace(hour=int(end[:2]), minute=int(end[3:]), second=0, microsecond=0)
    return {'until_work_start_minutes': (beginning - now).total_seconds() / 60,
            'until_work_end_minutes': (ending - now).total_seconds() / 60,
            'after_work_end_minutes': (now - ending).total_seconds() / 60}
