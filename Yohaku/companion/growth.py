"""Character-local progress, bounded awake-time accounting and one-time grants."""
from copy import deepcopy
from datetime import date, datetime, timedelta
import ctypes
import math
from pathlib import Path
import random
import sys
import time

from .characters import CHARACTERS
from .growth_content import atomic_json, number, read_json, require


def awake_clock():
    if sys.platform == 'win32':
        result = ctypes.c_ulonglong()
        if ctypes.windll.kernel32.QueryUnbiasedInterruptTime(ctypes.byref(result)):
            return result.value / 10_000_000
    return time.monotonic()


def session_locked():
    """Read session availability without collecting input or desktop content."""
    if sys.platform != 'win32': return False
    from ctypes import wintypes
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user.OpenInputDesktop.restype = wintypes.HANDLE
    user.SwitchDesktop.argtypes = [wintypes.HANDLE]; user.SwitchDesktop.restype = wintypes.BOOL
    user.CloseDesktop.argtypes = [wintypes.HANDLE]
    handle = user.OpenInputDesktop(0, False, 0x0100)
    if not handle: return True
    try: return not bool(user.SwitchDesktop(handle))
    finally: user.CloseDesktop(handle)


def visible_app_count():
    """Count distinct executable paths with visible, non-tool top-level windows.

    No window titles, document names or executable paths are persisted.
    Permission failures yield an unknown value rather than a misleading count.
    """
    if sys.platform != 'win32': return None
    import win32gui, win32process, win32con, win32api
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    paths = set(); failed = False
    def callback(hwnd, _):
        nonlocal failed
        try:
            if not win32gui.IsWindowVisible(hwnd) or win32gui.GetWindow(hwnd, win32con.GW_OWNER): return
            if win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOOLWINDOW: return
            if win32gui.GetClassName(hwnd) in ('Shell_TrayWnd', 'Shell_SecondaryTrayWnd', 'Progman', 'WorkerW'): return
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            handle = kernel.OpenProcess(0x1000, False, pid)
            if not handle: failed = True; return
            try:
                buffer = ctypes.create_unicode_buffer(32768); length = wintypes.DWORD(len(buffer))
                if kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)):
                    path = buffer.value.casefold()
                    if Path(path).name not in ('applicationframehost.exe', 'shellexperiencehost.exe', 'searchhost.exe', 'startmenuexperiencehost.exe'):
                        paths.add(path)
                else: failed = True
            finally: kernel.CloseHandle(handle)
        except Exception: failed = True
    win32gui.EnumWindows(callback, None)
    return None if failed else len(paths)


def fresh_progress():
    return dict(exp=0., exp_seconds=0., level=1, seconds=0., days=[], trophies={}, best={},
                unlocked=[], equipped={}, events={}, sequence=0)


def validate_state(document):
    require(isinstance(document, dict) and type(document.get('schema_version')) is int and document['schema_version'] == 1,
            '成長データのバージョンに対応していません。')
    chars = document.get('characters')
    require(isinstance(chars, dict) and set(chars) <= set(CHARACTERS), '成長データのキャラIDが不正です。')
    for p in chars.values():
        require(isinstance(p, dict), '成長データが不正です。')
        require(number(p.get('exp'), 0, 1e15) and number(p.get('seconds'), 0, 1e15) and number(p.get('exp_seconds'),0,1e15)
                and type(p.get('level')) is int and 1 <= p['level'] <= 100
                and type(p.get('sequence')) is int and 0 <= p['sequence'] <= 10**15, '経験値・累計時間が不正です。')
        require(isinstance(p.get('days'), list) and len(p['days']) <= 370, '起動日数が不正です。')
        for day in p['days']: require(date.fromisoformat(day).isoformat() == day, '起動日が不正です。')
        require(isinstance(p.get('unlocked'), list) and len(p['unlocked']) <= 10000 and all(isinstance(s,str) for s in p['unlocked']), '解放記録が不正です。')
        require(isinstance(p.get('equipped'), dict) and set(p['equipped']) <= {'head','body','accessory'}
                and all(isinstance(s, str) for s in p['equipped'].values()), '装着記録が不正です。')
        for key in ('trophies', 'events', 'best'):
            require(isinstance(p.get(key), dict) and len(p[key]) <= 10000, '獲得記録が不正です。')
        for value in p['best'].values(): require(number(value, 0, 1e15), '最高値が不正です。')
        for value in p['trophies'].values():
            require(isinstance(value, dict) and number(value.get('exp'),0,100000), 'トロフィー記録が不正です。')
            require(datetime.fromisoformat(value['at']).tzinfo is not None, '取得日時にタイムゾーンがありません。')
        for value in p['events'].values():
            require(isinstance(value, dict) and type(value.get('count')) is int and value['count'] >= 0
                    and type(value.get('daily')) is int and value['daily'] >= 0, '演出記録が不正です。')
            require(datetime.fromisoformat(value['last']).tzinfo is not None, '演出日時にタイムゾーンがありません。'); date.fromisoformat(value['day'])
    return deepcopy(document)


class GrowthStore:
    def __init__(self, path):
        self.path = Path(path); self.data = dict(schema_version=1, characters={})
        self.error = ''; self.writable = True
        if self.path.exists():
            try: self.data = validate_state(read_json(self.path))
            except (OSError, ValueError, TypeError, KeyError, RecursionError) as e:
                self.writable = False
                self.error = '成長データを読めません。原本を上書きせず成長を停止しています。Data/growth.jsonをバックアップから復元してください。'
                try: self.data = validate_state(read_json(self.path.with_suffix('.json.bak')))
                except (OSError, ValueError, TypeError, KeyError, RecursionError): pass

    def save(self, candidate):
        if not self.writable: raise OSError(self.error)
        candidate = validate_state(candidate)
        # Backup represents the previous complete transaction. State is advanced
        # in memory only after the primary replacement has succeeded.
        if self.path.exists(): atomic_json(self.path.with_suffix('.json.bak'), self.data)
        atomic_json(self.path, candidate); self.data = candidate; self.error = ''


def streak_days(days, now, calendar, mode):
    recorded = set(days); current = now.date(); count = 0
    for _ in range(370):
        if mode == 'business' and not calendar.is_business_day(current):
            current -= timedelta(days=1); continue
        if current.isoformat() not in recorded: break
        count += 1; current -= timedelta(days=1)
    return count


def condition_value(c, progress, now, metrics, calendar, config, work):
    kind = c['type']
    if kind == 'metric': return metrics.get(c['metric'])
    if kind == 'continuous_input': return metrics.get('growth_active_minutes')
    if kind == 'app_count': return metrics.get('visible_apps')
    if kind == 'total_minutes': return progress['seconds']/60
    if kind == 'streak_days':
        if config['streak_mode']=='business' and calendar is None:return None
        return streak_days(progress['days'], now, calendar, config['streak_mode'])
    if kind == 'event_count': return progress['events'].get(c['event_id'], {}).get('count', 0)
    return None


def condition_matches(c, progress, now, metrics, calendar, config, work):
    kind = c['type']
    if kind in ('metric', 'continuous_input', 'app_count', 'total_minutes', 'streak_days', 'event_count'):
        value = condition_value(c, progress, now, metrics, calendar, config, work)
        if not number(value, -1e15, 1e15): return False
        return {'>=': value >= c['value'], '<=': value <= c['value'], '==': value == c['value']}[c['op']]
    if kind == 'time_range':
        clock = now.strftime('%H:%M'); start, end = c['start'], c['end']
        return start <= clock <= end if start <= end else clock >= start or clock <= end
    if kind == 'date_range': return c['start'] <= now.date().isoformat() <= c['end']
    if kind == 'day_kind': return calendar is not None and calendar.is_business_day(now.date()) == (c['value'] == 'business')
    if kind == 'outside_hours':
        return (calendar is not None and number(metrics.get('idle_minutes'),0,1e9) and metrics['idle_minutes']*60 < config['idle_threshold_seconds']
                and (not calendar.is_business_day(now.date()) or not work[0] <= now.strftime('%H:%M') < work[1]))
    return False


class GrowthEngine:
    def __init__(self, store, catalog, clock=awake_clock, chooser=random.random):
        self.store = store; self.catalog = catalog; self.clock = clock; self.random = chooser
        self.last_clock = clock(); self.last_wall = None; self.last_character = None
        self.data=deepcopy(store.data);self.last_save=self.last_clock
        self.active_seconds = 0.; self.last_event_check=self.last_clock
        self.next_event = self.last_clock + (catalog.config['event_interval_seconds'] if catalog.config else 60)
        self.pending = []

    def progress(self, character): return self.data['characters'].get(character, fresh_progress())

    def commit(self,candidate):
        self.store.save(candidate);self.data=deepcopy(candidate);self.last_save=self.clock()

    def flush(self):
        if self.data!=self.store.data:self.commit(self.data)

    def update_unlocks(self, p, character):
        config = self.catalog.config; previous = p['level']
        p['level'] = max(previous, sum(p['exp'] >= n for n in config['level_thresholds']))
        unlocked = set(p['unlocked'])
        for kind in ('lines', 'events', 'costumes', 'rewards'):
            for key, item in self.catalog.items[kind].items():
                if character in item['characters'] and p['level'] >= item['level']:
                    unlocked.add(key)
                    if kind == 'rewards':
                        unlocked.update(ref for ref in item['unlock'] if character in self.catalog.all_items[ref]['characters'])
        p['unlocked'] = sorted(unlocked)
        return p['level'] > previous

    def step(self, character, now, metrics, calendar, work=('08:30','17:30'), locked=False):
        clock = self.clock(); dt = clock-self.last_clock; self.last_clock = clock
        wall_dt = (now-self.last_wall).total_seconds() if self.last_wall else dt
        self.last_wall = now
        if not self.catalog.config or not self.store.writable: return []
        config = self.catalog.config
        # Gaps are not backfilled, even after a crash/restart, resume or clock jump.
        if not 0 <= dt <= 20 or wall_dt < 0 or abs(wall_dt-dt) > 3: dt = 0
        if locked and not config['count_locked']: dt = 0
        # The UI settles the old character before switching. Never attribute a
        # preceding interval to a newly selected character.
        if self.last_character is not None and character != self.last_character: dt = 0
        self.last_character = character
        idle = metrics.get('idle_minutes')
        if dt and number(idle, 0, 1e9) and idle*60 < config['idle_threshold_seconds']:
            self.active_seconds += dt
        else: self.active_seconds = 0.
        metrics = dict(metrics, growth_active_minutes=self.active_seconds/60)
        candidate = deepcopy(self.data); p = candidate['characters'].setdefault(character, fresh_progress())
        previous_exp=p['exp']
        new_day=now.date().isoformat() not in p['days']
        p['seconds'] += dt;p['exp_seconds'] += dt
        interval=config['exp_interval_seconds'];grants=int((p['exp_seconds']+1e-7)//interval)
        p['exp_seconds']=max(0.,p['exp_seconds']-grants*interval)
        p['exp']+=grants*interval*config['exp_per_hour']/3600
        p['days'] = sorted(set(p['days']) | {now.date().isoformat()})[-370:]
        notifications = []
        for key, item in self.catalog.items['trophies'].items():
            if character not in item['characters'] or p['level'] < item['level']: continue
            values = [condition_value(c,p,now,metrics,calendar,config,work) for c in item['conditions']]
            numeric = [v for v in values if number(v, 0, 1e15)]
            if numeric: p['best'][key] = max(p['best'].get(key,0), numeric[0])
            if key not in p['trophies'] and all(condition_matches(c,p,now,metrics,calendar,config,work) for c in item['conditions']):
                p['trophies'][key] = dict(at=now.isoformat(), exp=item['exp'])
                p['exp'] += item['exp']; notifications.append(dict(kind='trophy', key=key, character=character))
        if self.update_unlocks(p,character): notifications.insert(0, dict(kind='level', level=p['level'], character=character))
        if candidate != self.data:
            if grants or notifications or new_day or clock-self.last_save>=interval:self.commit(candidate)
            else:self.data=candidate
        earned=p['exp']-previous_exp
        if earned>0:notifications.append(dict(kind='exp',amount=earned,character=character))
        return notifications

    def choose_event(self, character, voice, now, metrics, calendar, work=('08:30','17:30')):
        clock = self.clock()
        if not self.catalog.config or not self.store.writable or clock < self.next_event: return None
        self.last_event_check=clock
        self.next_event = clock + self.catalog.config['event_interval_seconds']
        p = self.progress(character); candidates = []
        for kind in ('lines', 'events'):
            for key, item in self.catalog.items[kind].items():
                if character not in item['characters'] or key not in p['unlocked']: continue
                if voice not in item['texts'] and '*' not in item['texts']: continue
                old = p['events'].get(key)
                if old:
                    if (now-datetime.fromisoformat(old['last'])).total_seconds() < item['cooldown_minutes']*60: continue
                    if old['day'] == now.date().isoformat() and old['daily'] >= item['daily_limit']: continue
                if all(condition_matches(c,p,now,metrics,calendar,self.catalog.config,work) for c in item['conditions']) and self.random() < item['probability']:
                    candidates.append((kind,item))
        if not candidates: return None
        # Chance does not grow with level. Only one candidate wins an opportunity.
        _, item = max(candidates, key=lambda pair:(pair[1]['priority'], self.random()))
        candidate = deepcopy(self.data); p = candidate['characters'].setdefault(character,fresh_progress())
        old = p['events'].get(item['key'],{})
        p['sequence'] += 1
        p['events'][item['key']] = dict(count=old.get('count',0)+1, last=now.isoformat(), day=now.date().isoformat(),
                                       daily=(old.get('daily',0) if old.get('day') == now.date().isoformat() else 0)+1,
                                       occurrence=p['sequence'])
        p['exp'] += item['exp'];leveled=self.update_unlocks(p,character)
        self.commit(candidate)
        if leveled:self.pending.append(dict(kind='level',level=p['level'],character=character))
        return item

    def equip(self, character, slot, key):
        if slot not in ('head','body','accessory'):raise ValueError('不正な装備枠です。')
        equipped=dict(self.progress(character)['equipped'])
        if key:equipped[slot]=key
        else:equipped.pop(slot,None)
        self.equip_set(character,equipped)

    def equip_set(self,character,equipped):
        if (not isinstance(character,str) or character not in CHARACTERS or not isinstance(equipped,dict) or not set(equipped)<={'head','body','accessory'}
                or not all(isinstance(key,str) and key for key in equipped.values())):raise ValueError('装備の組み合わせが不正です。')
        candidate = deepcopy(self.data); p = candidate['characters'].setdefault(character,fresh_progress())
        for slot,key in equipped.items():
            if p['equipped'].get(slot)==key:continue
            item = self.catalog.items['costumes'].get(key)
            if not item or key not in p['unlocked'] or item['slot'] != slot or character not in item['characters']:
                raise ValueError('未解放か対象外の衣装です。')
        if p['equipped']==equipped:return
        p['equipped']=dict(equipped)
        self.commit(candidate)

    def reload(self, catalog):
        self.catalog=catalog
        if catalog.config:
            self.next_event=max(self.clock(),self.last_event_check+catalog.config['event_interval_seconds'])
        if not catalog.config or not self.store.writable:return []
        candidate=deepcopy(self.data);notifications=[]
        # Existing EXP/seconds and uncredited time are unchanged. New content
        # becomes available immediately for every already-created character.
        for character,progress in candidate['characters'].items():
            if self.update_unlocks(progress,character):notifications.append(dict(kind='level',level=progress['level'],character=character))
        if candidate!=self.data:self.commit(candidate)
        return notifications
