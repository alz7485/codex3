"""Local, declarative recurring notifications. Weekdays mean Monday–Friday."""
from copy import deepcopy
from datetime import date, timedelta
import calendar
import json
from pathlib import Path
import re
from uuid import uuid4
from .message_format import validate_styles


KINDS = {
    'daily': '毎日',
    'weekly': '毎週・曜日を指定',
    'monthly_day': '毎月・日付を指定',
    'month_end_weekday': '月末の最終平日',
    'monthly_weekday_before': '毎月○日までの最終平日',
    'month_end_business_day':'月末の最終営業日（祝日・会社休日を除く）',
    'monthly_business_day_before':'毎月○日までの最終営業日',
}
WEEKDAYS = ('月', '火', '水', '木', '金', '土', '日')
WINDOW_SECONDS = 600


class ReminderError(ValueError):
    pass


def new_rule():
    return {'id': uuid4().hex, 'name': '新しい通知', 'enabled': True, 'time': '17:00',
            'message': '締め作業の確認をお願いします。',
            'condition': {'kind': 'month_end_weekday'}}


def validate(document):
    if not isinstance(document, dict) or type(document.get('schema_version')) is not int or document['schema_version'] != 1:
        raise ReminderError('通知JSONの schema_version は1にしてください。')
    rows = document.get('notifications')
    if not isinstance(rows, list) or len(rows) > 100:
        raise ReminderError('通知は100件まで登録できます。')
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ReminderError('通知はオブジェクトで指定してください。')
        identifier = row.get('id')
        if not isinstance(identifier, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', identifier) or identifier in seen:
            raise ReminderError('通知IDは重複しない英数字・ハイフン・下線にしてください（64文字まで）。')
        seen.add(identifier)
        for key, maximum, title in (('name', 80, '管理用の名前'), ('message', 1000, 'メッセージ')):
            if not isinstance(row.get(key), str) or not row[key].strip() or len(row[key]) > maximum:
                raise ReminderError(f'{title}は1〜{maximum}文字で入力してください。')
        try:validate_styles(row['message'], row.get('message_styles', []))
        except ValueError as error:raise ReminderError(str(error)) from None
        if type(row.get('enabled')) is not bool:
            raise ReminderError('有効・無効はtrueかfalseで指定してください。')
        if not isinstance(row.get('time'), str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', row['time']):
            raise ReminderError('通知時刻はHH:mm（00:00〜23:59）で指定してください。')
        condition = row.get('condition')
        if (not isinstance(condition, dict) or not isinstance(condition.get('kind'), str)
                or condition['kind'] not in KINDS):
            raise ReminderError('通知条件を選んでください。')
        kind = condition['kind']
        if kind in ('monthly_day', 'monthly_weekday_before','monthly_business_day_before'):
            if type(condition.get('day')) is not int or not 1 <= condition['day'] <= 31:
                raise ReminderError('毎月の日付は1〜31日で指定してください。')
        if kind == 'weekly':
            days = condition.get('weekdays')
            if (not isinstance(days, list) or not days or len(days) > 7 or
                    any(type(day) is not int or not 0 <= day <= 6 for day in days) or len(set(days)) != len(days)):
                raise ReminderError('毎週の通知は曜日を1つ以上選んでください。')
    return deepcopy(document)


def monthly_date(year, month, condition, business_calendar=None):
    """Clamp an absent day to month end, then move backwards over weekends."""
    last = calendar.monthrange(year, month)[1]
    kind = condition['kind']
    target = date(year, month, last if kind in ('month_end_weekday','month_end_business_day') else min(condition['day'], last))
    if kind in ('month_end_business_day','monthly_business_day_before'):
        if business_calendar is None:
            from .business_calendar import BusinessCalendar
            business_calendar=BusinessCalendar()
        for _ in range(370):
            if business_calendar.is_business_day(target): return target
            target-=timedelta(days=1)
        return None
    if kind in ('month_end_weekday', 'monthly_weekday_before'):
        while target.weekday() >= 5:
            target -= timedelta(days=1)
    return target


def matches_date(day, condition, business_calendar=None):
    kind = condition['kind']
    if kind == 'daily':
        return True
    if kind == 'weekly':
        return day.weekday() in condition['weekdays']
    # With a cutoff of the 1st, the last weekday may be in the previous month.
    candidates = [(day.year, day.month)]
    if kind in ('month_end_business_day','monthly_business_day_before'):
        month=day.year*12+day.month-1
        candidates=[(n//12,n%12+1) for n in range(month,month+14)]
    if kind in ('monthly_weekday_before','monthly_business_day_before'):
        candidates.append((day.year + (day.month == 12), day.month % 12 + 1))
    return any(day == monthly_date(year, month, condition, business_calendar) for year, month in candidates)


def due_time(rule, now, business_calendar=None):
    if not rule['enabled'] or not matches_date(now.date(), rule['condition'],business_calendar):
        return None
    hour, minute = map(int, rule['time'].split(':'))
    due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return due if 0 <= (now - due).total_seconds() < WINDOW_SECONDS else None


def next_occurrence(rule, now, business_calendar=None):
    """The next calendar occurrence, independent of delivery/quiet-hour state."""
    hour, minute = map(int, rule['time'].split(':'))
    for offset in range(370):
        candidate = now + timedelta(days=offset)
        candidate = candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate >= now and matches_date(candidate.date(), rule['condition'],business_calendar):
            return candidate
    return None


class ReminderStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = {'schema_version': 1, 'notifications': []}
        self.error = ''
        if self.path.exists():
            try:
                if self.path.stat().st_size > 512_000:
                    raise ReminderError('通知JSONが大きすぎます。')
                self.data = validate(json.loads(self.path.read_text(encoding='utf-8-sig')))
            except (OSError, ValueError, RecursionError) as error:
                self.error = f'通知設定を読み込めません。元のJSONは保持しています。{error}'

    def save(self, document):
        candidate = validate(document)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.path.with_suffix('.json.bak').write_bytes(self.path.read_bytes())
        temporary = self.path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(self.path)
        self.data = candidate
        self.error = ''
