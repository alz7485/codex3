"""Validated JSON conversation documents and declarative condition evaluation."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import shutil

from .motion import EXPRESSION_FRAMES
from .metrics import METRICS
import math

AUTO_PERSONALITY = "キャラクターに合わせる"
INTERVALS = (10, 20, 30, 60, 90, 120)  # Legacy UI/import compatibility.
DEFAULT_PATH = Path(__file__).parent / 'assets/dialogue/default_dialogue.json'
KINDS = {'always': 'いつでも', 'time_range': '時間帯', 'weekday': '曜日',
         'session_range': '起動からの経過', 'before_meeting': '予定の前', 'after_meeting': '予定のあと', 'metric_range': 'PC・ファイル・予定の集計値', 'all': 'すべての条件（AND）', 'any': 'いずれかの条件（OR）'}
ACTION_IDS = ('calendar_intro', 'calendar_unavailable', 'calendar_empty', 'activity_open', 'settings_open', 'no_conversation', 'reminder_disabled')
NEW_RULE_IDS = ('idle_short', 'idle_long', 'active_long', 'daily_busy', 'daily_light', 'many_open_files', 'few_open_files', 'desktop_busy', 'desktop_tidy', 'before_start', 'before_end', 'ending_soon', 'after_hours', 'repeat_file', 'missed_yesterday', 'week_busy', 'week_light', 'today_busy', 'today_light')
MAX_BYTES = 2 * 1024 * 1024


class DialogueError(ValueError):
    pass


def _require(ok, message):
    if not ok:
        raise DialogueError(message)


def _integer(value, minimum, maximum):
    return type(value) is int and minimum <= value <= maximum


def _text(value, limit=1000):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def validate(document):
    """Reject incomplete, invalid or excessively large documents before any mutation."""
    _require(isinstance(document, dict), 'JSONの最上位はオブジェクトにしてください。')
    _require(document.get('schema_version') == 2 and type(document.get('schema_version')) is int, '対応していないJSON形式です。schema_versionは2です。')
    options = document.get('options')
    _require(isinstance(options, dict), '全体設定 options がありません。')
    for key, bounds in {'interval_minutes': (1, 1440), 'bubble_seconds': (5, 300),
                        'meeting_lead_minutes': (1, 120), 'repeat_window': (0, 64)}.items():
        _require(_integer(options.get(key), *bounds), f'{key} は{bounds[0]}〜{bounds[1]}の整数にしてください。')
    for key in ('suppress_during_meetings', 'avoid_consecutive_topic'):
        _require(type(options.get(key)) is bool, f'{key} はtrue/falseにしてください。')
    _require(options.get('selection_policy') in ('least_recent', 'weighted'), '話題の選択方式が不正です。')
    for name in ('work_start', 'work_end'):
        value = options.get(name)
        _require(isinstance(value, str) and re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', value), '勤務時間はHH:mmで指定してください。')
    _require(options['work_start'] < options['work_end'], '始業は終業より前にしてください。')
    _require(_integer(options.get('active_threshold_seconds'), 5, 600), '操作あり判定は5〜600秒にしてください。')
    phrases = document.get('phrases')
    _require(isinstance(phrases, dict) and set(phrases) == set(VOICE_NAMES), '4種の性格のセリフを指定してください。')
    profiles = document.get('profiles')
    _require(isinstance(profiles, dict) and set(profiles) == set('ABEF'), 'A/B/E/Fのキャラ設定が必要です。')
    for key, profile in profiles.items():
        _require(isinstance(profile, dict) and profile.get('voice') in VOICE_NAMES, f'{key}の性格が不正です。')
        _require(_text(profile.get('description'), 300) and _text(profile.get('tagline'), 1000), f'{key}の説明と代表的な一言を入力してください。')
    rules = document.get('rules')
    _require(isinstance(rules, list) and 3 <= len(rules) <= 200, '発生ルールは3〜200件にしてください。')
    ids = []
    for rule in rules:
        _require(isinstance(rule, dict), '発生ルールの形式が不正です。')
        key = rule.get('id')
        _require(isinstance(key, str) and re.fullmatch(r'[a-z][a-z0-9_]{0,39}', key), 'ルールIDは小文字英数字と_で40文字以内にしてください。')
        _require(key not in ids, f'ルールID {key} が重複しています。')
        ids.append(key)
        _require(_text(rule.get('label'), 60), f'{key}: 話題名を入力してください。')
        _require(type(rule.get('enabled')) is bool, f'{key}: 有効・無効の値が不正です。')
        trigger = 'click' if key == 'call' else 'reminder' if key == 'meeting' else 'notification' if key == 'mail_received' else 'action' if key in ACTION_IDS else 'auto'
        _require(rule.get('trigger') == trigger, f'{key}: 発生方法は{trigger}にしてください。')
        _require(isinstance(rule.get('expression'), str) and rule['expression'] in EXPRESSION_FRAMES, f'{key}: 表情が不正です。')
        _require(_integer(rule.get('weight'), 1, 100) and _integer(rule.get('cooldown_minutes'), 0, 1440), f'{key}: 出現しやすさまたは再発言の間隔が不正です。')
        _require(_integer(rule.get('priority', 0), 0, 5), f'{key}: 優先度は0〜5にしてください。')
        condition = rule.get('condition')
        _require(isinstance(condition, dict) and isinstance(condition.get('kind'), str) and condition['kind'] in KINDS, f'{key}: 発生条件が不正です。')
        kind = condition['kind']
        _require(trigger == 'auto' or kind == 'always', f'{key}: 呼びかけ・予定通知の条件は「いつでも」です。')
        validate_condition(condition, key)
    _require({'call', 'meeting', 'chat', 'mail_received', *ACTION_IDS} <= set(ids), '基本の呼びかけ・案内・普段の一言のルールは削除できません。')
    for voice, bank in phrases.items():
        _require(isinstance(bank, dict) and set(bank) == set(ids), f'{voice}: すべての話題のセリフが必要です。')
        for key, lines in bank.items():
            _require(isinstance(lines, list) and 1 <= len(lines) <= 200 and all(_text(line) for line in lines), f'{voice} / {key}: セリフは1〜200件、1件1〜1000文字にしてください。')
    _require(len(json.dumps(document, ensure_ascii=False).encode('utf-8')) <= MAX_BYTES, 'JSONは2MB以内にしてください。')
    return deepcopy(document)


def validate_condition(condition, key='', depth=0):
    _require(depth <= 4 and isinstance(condition, dict) and isinstance(condition.get('kind'), str) and condition['kind'] in KINDS, f'{key}: 条件の種類・深さが不正です。')
    kind = condition['kind']
    if kind in ('all', 'any'):
        children = condition.get('conditions')
        _require(isinstance(children, list) and 1 <= len(children) <= 8, f'{key}: 詳細条件は1〜8件の配列にしてください。')
        for child in children:
            validate_condition(child, key, depth + 1)
    elif kind == 'metric_range':
        _require(isinstance(condition.get('metric'), str) and condition['metric'] in METRICS, f'{key}: 集計値の種類が不正です。')
        minimum, maximum = condition.get('minimum'), condition.get('maximum')
        numeric = lambda v: type(v) in (int, float) and math.isfinite(v) and -43200 <= v <= 100000
        _require(numeric(minimum) and (maximum is None or numeric(maximum) and maximum >= minimum), f'{key}: 集計値の下限・上限が不正です。')
    elif kind == 'time_range':
        for name in ('start', 'end'):
            value = condition.get(name)
            _require(isinstance(value, str) and re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', value), f'{key}: 時刻はHH:mm形式にしてください。')
    elif kind == 'weekday':
        days = condition.get('days')
        _require(isinstance(days, list) and 1 <= len(days) <= 7 and all(_integer(d, 0, 6) for d in days) and len(set(days)) == len(days), f'{key}: 曜日を1つ以上選んでください。')
    elif kind in ('session_range', 'before_meeting', 'after_meeting'):
        minimum, maximum = condition.get('minimum_minutes'), condition.get('maximum_minutes')
        _require(_integer(minimum, 0, 43200), f'{key}: 開始までの分数が不正です。')
        _require((maximum is None and kind == 'session_range') or (_integer(maximum, 0, 43200) and maximum >= minimum), f'{key}: 上限は下限以上にしてください。')
        if kind == 'session_range':
            _require(type(condition.get('first_only')) is bool, f'{key}: 初回のみの値が不正です。')


def upgrade(document):
    if not isinstance(document, dict) or type(document.get('schema_version')) is not int or document.get('schema_version') not in (1, 2):
        return document
    if document['schema_version'] == 2:
        return upgrade_mail(document)
    result = deepcopy(document)
    base = json.loads(DEFAULT_PATH.read_text(encoding='utf-8'))
    result['schema_version'] = 2
    if isinstance(result.get('options'), dict):
        for key in ('work_start', 'work_end', 'active_threshold_seconds'):
            result['options'].setdefault(key, base['options'][key])
    if isinstance(result.get('rules'), list) and isinstance(result.get('phrases'), dict):
        existing = {r['id'] for r in result['rules'] if isinstance(r, dict) and isinstance(r.get('id'), str)}
        for rule in base['rules']:
            if rule['id'] not in existing:
                if rule['id'] != 'mail_received' and rule['id'] not in NEW_RULE_IDS:
                    continue
                result['rules'].append(deepcopy(rule))
                for voice, bank in result['phrases'].items():
                    if isinstance(bank, dict) and voice in base['phrases']:
                        bank[rule['id']] = deepcopy(base['phrases'][voice][rule['id']])
    return upgrade_mail(result)


def upgrade_mail(document):
    """Add the new topic once; later user deletions stay deleted."""
    if document.get('content_revision', 0) == 3:
        return document
    result = deepcopy(document)
    base = json.loads(DEFAULT_PATH.read_text(encoding='utf-8'))
    if isinstance(result.get('rules'), list) and isinstance(result.get('phrases'), dict):
        existing = {r.get('id') for r in result['rules'] if isinstance(r, dict) and isinstance(r.get('id'), str)}
        if 'mail_unread' not in existing:
            result['rules'].append(deepcopy(next(r for r in base['rules'] if r['id'] == 'mail_unread')))
            for voice, bank in result['phrases'].items():
                if isinstance(bank, dict) and voice in base['phrases']:
                    bank['mail_unread'] = deepcopy(base['phrases'][voice]['mail_unread'])
        for voice, bank in result['phrases'].items():
            if isinstance(bank, dict) and voice in base['phrases'] and isinstance(bank.get('mail_received'), list):
                # Old templates count new mail; retain unrelated custom wording.
                bank['mail_received'] = [base['phrases'][voice]['mail_received'][i % 2]
                                         if isinstance(line, str) and '{mail_count}' in line else line
                                         for i, line in enumerate(bank['mail_received'])]
    result['content_revision'] = 3
    return result


def read_document(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise DialogueError('JSONは2MB以内にしてください。')
    try:
        return validate(upgrade(json.loads(path.read_text(encoding='utf-8-sig'))))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise DialogueError('JSONを読み込めません。書式とUTF-8の文字コードを確認してください。') from error


def defaults():
    return read_document(DEFAULT_PATH)


# Voice identifiers stay stable so existing personality overrides keep working.
VOICE_NAMES = ('控えめな皮肉屋', '冷静な案内役', '元気な応援係', 'のんびりした同僚')
_DEFAULT = defaults()
PHRASES = _DEFAULT['phrases']
PROFILES = {key: (p['voice'], p['description'], p['tagline']) for key, p in _DEFAULT['profiles'].items()}
EXPRESSIONS = {r['id']: r['expression'] for r in _DEFAULT['rules']}
BUBBLE_MS = _DEFAULT['options']['bubble_seconds'] * 1000


def voice_for(settings, document=None):
    profiles = (document or _DEFAULT)['profiles']
    return profiles[settings.character]['voice'] if settings.personality == AUTO_PERSONALITY else settings.personality


class DialogueStore:
    def __init__(self, path, legacy_interval=10):
        self.path = Path(path)
        self.error = ''
        self.data = defaults()
        if self.path.exists():
            try:
                self.data = read_document(self.path)
            except (OSError, DialogueError) as error:
                self.error = f'会話JSONを読み込めないため初期値を使用中です。元のファイルは変更していません。{error}'
        else:
            self.data['options']['interval_minutes'] = legacy_interval

    def save(self, document):
        candidate = validate(document)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.json.tmp')
        try:
            temporary.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            if self.path.exists():
                shutil.copy2(self.path, self.path.with_suffix('.json.bak'))
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)
        self.data = candidate
        self.error = ''

    def rule(self, key):
        return next((r for r in self.data['rules'] if r['id'] == key), None)


def matches(rule, now, started, session_spoken, events, connected, context=None):
    c = rule['condition']
    kind = c['kind']
    if kind in ('all', 'any'):
        values = [matches({'condition': child}, now, started, session_spoken, events, connected, context) for child in c['conditions']]
        return all(values) if kind == 'all' else any(values)
    if kind == 'metric_range':
        value = (context or {}).get(c['metric'])
        return type(value) in (int, float) and math.isfinite(value) and value >= c['minimum'] and (c['maximum'] is None or value <= c['maximum'])
    if kind == 'always':
        return True
    if kind == 'time_range':
        current, start, end = now.strftime('%H:%M'), c['start'], c['end']
        return True if start == end else start <= current < end if start < end else current >= start or current < end
    if kind == 'weekday':
        return now.weekday() in c['days']
    if kind == 'session_range':
        elapsed = (now - started).total_seconds() / 60
        return (not c['first_only'] or not session_spoken) and elapsed >= c['minimum_minutes'] and (c['maximum_minutes'] is None or elapsed <= c['maximum_minutes'])
    if not connected:
        return False
    if kind == 'before_meeting':
        return any(c['minimum_minutes'] < (e.start - now).total_seconds() / 60 <= c['maximum_minutes'] for e in events)
    if kind == 'after_meeting':
        return any(c['minimum_minutes'] <= (now - e.end).total_seconds() / 60 <= c['maximum_minutes'] for e in events)
    return False
