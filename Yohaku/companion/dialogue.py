"""Validated JSON conversation documents and declarative condition evaluation."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import shutil

from .motion import EXPRESSION_FRAMES
from .metrics import METRICS
from .advanced_context import condition_key, TEMPORAL_KINDS, EVENT_KINDS
import math

AUTO_PERSONALITY = "キャラクターに合わせる"
LEGACY_DEBTOR_VOICE = '倒置法の使い手'
DEBTOR_VOICE = '孤高の債務者'
INTERVALS = (10, 20, 30, 60, 90, 120)  # Legacy UI/import compatibility.
DEFAULT_PATH = Path(__file__).parent / 'assets/dialogue/default_dialogue.json'
PERSONALITY_WORDING_PATH = DEFAULT_PATH.with_name('personality_wording_v1.json')
KINDS = {'always': 'いつでも', 'time_range': '時間帯', 'weekday': '曜日',
         'session_range': '起動からの経過', 'before_meeting': '予定の前', 'after_meeting': '予定のあと', 'metric_range': 'PC・ファイル・予定の集計値', 'all': 'すべての条件（AND）', 'any': 'いずれかの条件（OR）',
         'metric_sustained':'集計値が一定時間続く', 'metric_transition':'集計値の変化・回復',
         'idle_return':'操作なしから戻った', 'watched_file':'指定ファイル・フォルダーの記録', 'business_day':'営業日・休日'}
ACTION_IDS = ('calendar_intro', 'calendar_unavailable', 'calendar_empty', 'activity_open', 'settings_open', 'no_conversation', 'reminder_disabled', 'click_concern', 'click_angry')
NEW_RULE_IDS = ('idle_short', 'idle_long', 'active_long', 'daily_busy', 'daily_light', 'many_open_files', 'few_open_files', 'desktop_busy', 'desktop_tidy', 'before_start', 'before_end', 'ending_soon', 'after_hours', 'repeat_file', 'missed_yesterday', 'week_busy', 'week_light', 'today_busy', 'today_light')
RESOURCE_RULE_IDS = ('cpu_high', 'cpu_low', 'memory_high', 'memory_low')
ADVANCED_RULE_IDS = ('cpu_recovered','memory_recovered','idle_returned','meetings_long','meetings_consecutive',
                     'meeting_short_break','battery_low','power_connected','target_unopened','target_reopened')
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
    _require(type(options.get('click_reactions')) is bool, '連打への反応はtrue/falseにしてください。')
    for key, bounds in {'click_window_seconds': (1, 30), 'click_concern_count': (2, 30),
                        'click_angry_count': (3, 60), 'click_recovery_seconds': (1, 120),
                        'click_repeat_seconds': (1, 600)}.items():
        _require(_integer(options.get(key), *bounds), f'{key} は{bounds[0]}〜{bounds[1]}の整数にしてください。')
    _require(options['click_angry_count'] > options['click_concern_count'], '怒る回数は困る回数より多くしてください。')
    _require(options['click_recovery_seconds'] >= options['click_window_seconds'], '連打のリセット時間は判定期間以上にしてください。')
    phrases = document.get('phrases')
    _require(isinstance(phrases, dict) and set(phrases) == set(VOICE_NAMES), f'{len(VOICE_NAMES)}種の性格のセリフを指定してください。')
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
    elif kind in ('metric_range','metric_sustained','metric_transition'):
        _require(isinstance(condition.get('metric'), str) and condition['metric'] in METRICS, f'{key}: 集計値の種類が不正です。')
        minimum, maximum = condition.get('minimum'), condition.get('maximum')
        numeric = lambda v: type(v) in (int, float) and math.isfinite(v) and -43200 <= v <= 100000
        _require(numeric(minimum) and (maximum is None or numeric(maximum) and maximum >= minimum), f'{key}: 集計値の下限・上限が不正です。')
        if kind in ('metric_sustained','metric_transition'):
            _require(_integer(condition.get('duration_minutes'),0,1440), f'{key}: 継続時間は0〜1440分です。')
        if kind=='metric_transition':
            lower,upper=condition.get('to_minimum'),condition.get('to_maximum')
            _require(numeric(lower) and (upper is None or numeric(upper) and upper>=lower),f'{key}: 変化後の範囲が不正です。')
            _require((maximum is not None and maximum<lower) or (upper is not None and upper<minimum),f'{key}: 変化前と変化後の範囲は重ねないでください。')
            _require(_integer(condition.get('window_minutes'),1,60),f'{key}: 変化後に話す期間は1〜60分です。')
    elif kind=='idle_return':
        _require(_integer(condition.get('idle_minutes'),1,1440) and _integer(condition.get('window_minutes'),1,60),f'{key}: 操作なし時間・発言期間が不正です。')
    elif kind=='watched_file':
        _require(isinstance(condition.get('target_id'),str) and (condition['target_id']=='' or re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',condition['target_id'])),f'{key}: 対象IDが不正です。')
        _require(condition.get('state') in ('opened_today','not_opened_today','count_range'),f'{key}: ファイルの記録条件が不正です。')
        _require(_integer(condition.get('minimum'),0,15000) and (condition.get('maximum') is None or _integer(condition['maximum'],condition['minimum'],15000)),f'{key}: 記録回数の範囲が不正です。')
    elif kind=='business_day':
        _require(type(condition.get('expected')) is bool,f'{key}: 営業日・休日を指定してください。')
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
    document = upgrade_voice_names(document)
    if document['schema_version'] == 2:
        return upgrade_personalities(upgrade_advanced(upgrade_resources(upgrade_names(upgrade_comfort(upgrade_click_reactions(upgrade_mail(document)))))))
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
    return upgrade_personalities(upgrade_advanced(upgrade_resources(upgrade_names(upgrade_comfort(upgrade_click_reactions(upgrade_mail(result)))))))


def canonical_voice(voice):
    return DEBTOR_VOICE if voice == LEGACY_DEBTOR_VOICE else voice


def upgrade_voice_names(document):
    result = deepcopy(document)
    phrases = result.get('phrases')
    if isinstance(phrases, dict) and LEGACY_DEBTOR_VOICE in phrases and DEBTOR_VOICE not in phrases:
        result['phrases'] = {canonical_voice(key): value for key, value in phrases.items()}
    profiles = result.get('profiles')
    if isinstance(profiles, dict):
        for profile in profiles.values():
            if isinstance(profile, dict) and profile.get('voice') == LEGACY_DEBTOR_VOICE:
                profile['voice'] = DEBTOR_VOICE
    return result


def upgrade_personalities(document):
    """Add missing voice banks once, matching only the user's existing topics."""
    if document.get('personality_expansion_version') == 1:
        return upgrade_personality_wording(document)
    phrases, rules = document.get('phrases'), document.get('rules')
    if (not isinstance(phrases, dict) or not isinstance(rules, list)
            or not all(isinstance(phrases.get(voice), dict) for voice in ORIGINAL_VOICE_NAMES)
            or not all(isinstance(rule, dict) and isinstance(rule.get('id'), str) for rule in rules)):
        return document  # Validation reports malformed input without inventing content.
    result = deepcopy(document)
    base = json.loads(DEFAULT_PATH.read_text(encoding='utf-8'))
    fallback = phrases[ORIGINAL_VOICE_NAMES[0]]
    for voice in ADDED_VOICE_NAMES:
        if voice in phrases:
            continue
        bank = {}
        for rule in rules:
            key = rule['id']
            if key in base['phrases'][voice]:
                bank[key] = deepcopy(base['phrases'][voice][key])
            elif key in fallback:
                # User-authored topics have no bundled text. Keep their words
                # intact as an editable starting point for each new voice.
                bank[key] = deepcopy(fallback[key])
        result['phrases'][voice] = bank
    result['personality_expansion_version'] = 1
    return upgrade_personality_wording(result)


def upgrade_personality_wording(document):
    """Replace exact bundled v0.18 lines once; retain edits, order and removals."""
    if document.get('personality_wording_version') == 1 or not isinstance(document.get('phrases'), dict):
        return upgrade_senior_silence(document)
    result = deepcopy(document)
    changes = json.loads(PERSONALITY_WORDING_PATH.read_text(encoding='utf-8'))
    for voice, topics in changes['voices'].items():
        bank = result['phrases'].get(canonical_voice(voice))
        if not isinstance(bank, dict):
            continue
        for topic, rows in topics.items():
            lines = bank.get(topic)
            if not isinstance(lines, list):
                continue
            replacements = {row['before']: row['after'] for row in rows}
            bank[topic] = [replacements.get(line, line) if isinstance(line, str) else line for line in lines]
    result['personality_wording_version'] = 1
    return upgrade_senior_silence(result)


def upgrade_senior_silence(document):
    """Move only known bundled inner-thought variants to a silent reply."""
    if document.get('senior_silence_version') == 1 or not isinstance(document.get('phrases'), dict):
        return upgrade_debtor_wording(document)
    result = deepcopy(document)
    bank = result['phrases'].get('寡黙な先輩')
    changes = json.loads(PERSONALITY_WORDING_PATH.read_text(encoding='utf-8'))
    if isinstance(bank, dict):
        for topic, rows in changes['voices']['寡黙な先輩'].items():
            if not isinstance(bank.get(topic), list):
                continue
            replacements = {row['after']: '…\n（' + row['after'].split('\n（', 1)[1] for row in rows}
            bank[topic] = [replacements.get(line, line) if isinstance(line, str) else line for line in bank[topic]]
    result['senior_silence_version'] = 1
    return upgrade_debtor_wording(result)


def upgrade_debtor_wording(document):
    if document.get('debtor_voice_version') == 1 or not isinstance(document.get('phrases'), dict):
        return document
    result = deepcopy(document)
    bank = result['phrases'].get(DEBTOR_VOICE)
    changes = json.loads(DEFAULT_PATH.with_name('debtor_wording_v1.json').read_text(encoding='utf-8'))
    if isinstance(bank, dict):
        for topic, rows in changes.items():
            if isinstance(bank.get(topic), list):
                replacements = {row['before']: row['after'] for row in rows}
                bank[topic] = [replacements.get(line, line) if isinstance(line, str) else line for line in bank[topic]]
    result['debtor_voice_version'] = 1
    return result


def upgrade_advanced(document):
    if document.get('advanced_context_version')==1: return upgrade_conversation_flow(document)
    result=deepcopy(document); base=json.loads(DEFAULT_PATH.read_text(encoding='utf-8'))
    if isinstance(result.get('rules'),list) and isinstance(result.get('phrases'),dict):
        existing={r.get('id') for r in result['rules'] if isinstance(r,dict) and isinstance(r.get('id'),str)}
        for key in ADVANCED_RULE_IDS:
            if len(result['rules'])>=200: break
            if key not in existing:
                result['rules'].append(deepcopy(next(r for r in base['rules'] if r['id']==key)))
                for voice,bank in result['phrases'].items():
                    if isinstance(bank,dict) and voice in base['phrases']: bank[key]=deepcopy(base['phrases'][voice][key])
        for rule in result['rules']:
            if rule.get('id') in ('cpu_high','memory_high'):
                stock=next(r for r in base['rules'] if r['id']==rule['id'])
                legacy=deepcopy(stock['condition']); legacy.pop('duration_minutes',None); legacy['kind']='metric_range'
                if rule.get('condition')==legacy: rule['condition']=deepcopy(stock['condition'])
            if rule.get('id') in ('before_start','before_end','ending_soon','after_hours'):
                stock=next(r for r in base['rules'] if r['id']==rule['id'])
                legacy=deepcopy(stock['condition'])
                for i,c in enumerate(legacy.get('conditions',[])):
                    if c['kind']=='business_day': legacy['conditions'][i]={'kind':'weekday','days':[0,1,2,3,4]}
                if rule.get('condition')==legacy: rule['condition']=deepcopy(stock['condition'])
    result['advanced_context_version']=1
    return upgrade_conversation_flow(result)


def upgrade_conversation_flow(document):
    if document.get('conversation_flow_version')==1:return document
    result=deepcopy(document);base=json.loads(DEFAULT_PATH.read_text(encoding='utf-8'))
    previous={
        '履歴を開きました。\\n日付を選んで、振り返ってみましょう。',
        'ファイル履歴を表示しました。\\nカレンダーから日付を選んでください。',
        '履歴を開きました！\\n日付を選んで確認しましょう。',
        '履歴を開いたよ。\\n見たい日を選んでみてね。'}
    for voice,bank in result.get('phrases',{}).items() if isinstance(result.get('phrases'),dict) else ():
        if isinstance(bank,dict) and voice in base['phrases'] and isinstance(bank.get('activity_open'),list):
            bank['activity_open']=[base['phrases'][voice]['activity_open'][0] if isinstance(line,str) and line in previous else line for line in bank['activity_open']]
    result['conversation_flow_version']=1
    return result


def upgrade_resources(document):
    """Add resource topics once; preserve edits and subsequent topic deletions."""
    if document.get('resource_context_version') == 1:
        return document
    result = deepcopy(document)
    base = json.loads(DEFAULT_PATH.read_text(encoding='utf-8'))
    if isinstance(result.get('rules'), list) and isinstance(result.get('phrases'), dict):
        existing = {r.get('id') for r in result['rules'] if isinstance(r, dict) and isinstance(r.get('id'), str)}
        for key in RESOURCE_RULE_IDS:
            if len(result['rules']) >= 200:
                break
            if key not in existing:
                result['rules'].append(deepcopy(next(r for r in base['rules'] if r['id'] == key)))
                for voice, bank in result['phrases'].items():
                    if isinstance(bank, dict) and voice in base['phrases']:
                        bank[key] = deepcopy(base['phrases'][voice][key])
    result['resource_context_version'] = 1
    return result


LEGACY_SELF_REFERENCES = {
    'はい、余白の出番ですか？': 'はい、私の出番ですか？',
    'ご用件を、余白にどうぞ。': 'ご用件は、私にどうぞ。',
    '余白の準備はできています。予定は詰めすぎずに。': 'こちらの準備はできています。予定は詰めすぎずに。',
    '月曜の余白です。今週も、適度によろしく。': '月曜日ですね。今週も、適度によろしく。',
    '余白という名前なので、少し黙っていても仕事のうちです。': '少し黙っていても、見守るのは仕事のうちです。',
    'しばらく静かですね。余白の出番、と受け取っておきます。': 'しばらく静かですね。私の出番、と受け取っておきます。',
    '余白にも、心の余白が必要なんです。': '私にも、心の余白が必要なんです。',
}


def upgrade_names(document):
    """Replace only exact stock self-references; retain user-authored text and rules."""
    if document.get('naming_version') == 1:
        return document
    result = deepcopy(document)
    if isinstance(result.get('phrases'), dict):
        for bank in result['phrases'].values():
            if not isinstance(bank, dict):
                continue
            for key, lines in bank.items():
                if isinstance(lines, list):
                    bank[key] = [LEGACY_SELF_REFERENCES.get(line, line) if isinstance(line, str) else line for line in lines]
    result['naming_version'] = 1
    return result


def upgrade_comfort(document):
    result = deepcopy(document)
    if isinstance(result.get('options'), dict):
        result['options'].setdefault('click_repeat_seconds', 30)
    if result.get('anonymous_mail_version') != 1:
        base = json.loads(DEFAULT_PATH.read_text(encoding='utf-8'))
        if isinstance(result.get('phrases'), dict):
            for voice, bank in result['phrases'].items():
                if isinstance(bank, dict) and voice in base['phrases']:
                    bank['mail_received'] = deepcopy(base['phrases'][voice]['mail_received'])
        result['anonymous_mail_version'] = 1
    return result


def upgrade_click_reactions(document):
    """Extend old documents once, preserving all existing edits and switches."""
    if document.get('click_reactions_version') == 1:
        return document
    result = deepcopy(document)
    base = json.loads(DEFAULT_PATH.read_text(encoding='utf-8'))
    if isinstance(result.get('options'), dict):
        for key, value in base['options'].items():
            if key.startswith('click_'):
                result['options'].setdefault(key, value)
    if isinstance(result.get('rules'), list) and isinstance(result.get('phrases'), dict):
        existing = {r.get('id') for r in result['rules'] if isinstance(r, dict) and isinstance(r.get('id'), str)}
        for key in ('click_concern', 'click_angry'):
            if key not in existing:
                result['rules'].append(deepcopy(next(r for r in base['rules'] if r['id'] == key)))
                for voice, bank in result['phrases'].items():
                    if isinstance(bank, dict) and voice in base['phrases']:
                        bank[key] = deepcopy(base['phrases'][voice][key])
    result['click_reactions_version'] = 1
    return result


LEGACY_MAIL_WORDING = {
    'Outlookで新着メールを検知しました。',
    'メールが届いたみたい。お知らせしておくね。',
    'メールが届きました。お時間のあるときにご確認ください。',
    'メールが届きました。読む時間にも余白をどうぞ。',
    'メールが届きました！ 必要なときに確認しましょう。',
    '新しいメールが届きました。まずはお知らせまで。',
    '新しいメールが来ています！ まずはお知らせです。',
    '新しいメールが来てるよ。手が空いたら見てみてね。',
}


def upgrade_mail(document):
    """Add the new topic once; later user deletions stay deleted."""
    if document.get('content_revision', 0) == 3:
        return upgrade_mail_wording(document)
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
    return upgrade_mail_wording(result)


def upgrade_mail_wording(document):
    if document.get('mail_wording_version') == 1:
        return document
    result = deepcopy(document)
    base = json.loads(DEFAULT_PATH.read_text(encoding='utf-8'))
    if isinstance(result.get('phrases'), dict):
        for voice, bank in result['phrases'].items():
            if isinstance(bank, dict) and voice in base['phrases'] and isinstance(bank.get('mail_received'), list):
                bank['mail_received'] = [base['phrases'][voice]['mail_received'][i % 2]
                    if isinstance(line, str) and line in LEGACY_MAIL_WORDING else line
                    for i, line in enumerate(bank['mail_received'])]
    result['mail_wording_version'] = 1
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
ORIGINAL_VOICE_NAMES = ('控えめな皮肉屋', '冷静な案内役', '元気な応援係', 'のんびりした同僚')
ADDED_VOICE_NAMES = ('馴れ馴れしい関西弁', '寡黙な先輩', DEBTOR_VOICE)
VOICE_NAMES = (*ORIGINAL_VOICE_NAMES, *ADDED_VOICE_NAMES)
_DEFAULT = defaults()
PHRASES = _DEFAULT['phrases']
PROFILES = {key: (p['voice'], p['description'], p['tagline']) for key, p in _DEFAULT['profiles'].items()}
EXPRESSIONS = {r['id']: r['expression'] for r in _DEFAULT['rules']}
BUBBLE_MS = _DEFAULT['options']['bubble_seconds'] * 1000


def voice_for(settings, document=None):
    profiles = (document or _DEFAULT)['profiles']
    return canonical_voice(profiles[settings.character]['voice'] if settings.personality == AUTO_PERSONALITY else settings.personality)


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
    context=context or {}
    if kind in TEMPORAL_KINDS:
        key=condition_key(c); state=context.get('_temporal',{}).get(key,{})
        return bool(state.get('active')) and (kind not in EVENT_KINDS or state.get('event')!=context.get('_consumed_events',{}).get(key))
    if kind=='business_day': return context.get('business_day')==int(c['expected'])
    if kind=='watched_file':
        value=context.get('_target_counts',{}).get(c['target_id'])
        if type(value) is not int: return False
        return value>0 if c['state']=='opened_today' else value==0 if c['state']=='not_opened_today' else c['minimum']<=value and (c['maximum'] is None or value<=c['maximum'])
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
