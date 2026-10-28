"""Versioned, declarative content packs. No scripts or expressions are executed."""
from copy import deepcopy
from datetime import date
import json
import hashlib
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile

from .characters import CHARACTERS
from .dialogue import VOICE_NAMES
from .metrics import METRICS

MAX_JSON = 2 * 1024 * 1024
KINDS = ('lines', 'events', 'trophies', 'costumes', 'rewards')
EXPRESSIONS = ('happy', 'think', 'notice', 'front', 'sleepy', 'angry', 'troubled')
CONDITIONS = {
    'metric': 'PC状態の集計値', 'continuous_input': '操作が続いた推定時間（分）',
    'app_count': '表示中のアプリ数', 'streak_days': '連続起動日数',
    'total_minutes': '一緒に過ごした累計（分）', 'time_range': '時刻の範囲',
    'day_kind': '営業日・休日', 'outside_hours': '所定時間外のPC利用',
    'date_range': '日付の範囲', 'event_count': '演出との遭遇回数',
}
METRIC_CONDITIONS = {
    'idle_minutes':'idle_minutes','daily_active_minutes':'daily_active_minutes','daily_idle_minutes':'daily_idle_minutes',
    'observed_minutes':'observed_minutes','office_files':'open_office_files','desktop_files':'desktop_files',
    'repeat_file':'file_open_count','weekly_events':'weekly_events','daily_events':'daily_events',
    'unread_mail':'unread_mail_count','cpu_percent':'cpu_percent','memory_percent':'memory_percent',
    'battery_percent':'battery_percent','remaining_meetings':'remaining_meetings','completed_meetings':'completed_meetings',
    'meeting_minutes':'daily_meeting_minutes','meeting_gap':'next_meeting_gap_minutes','until_work_end':'until_work_end_minutes',
}
CONDITIONS.update({key:METRICS[metric] for key,metric in METRIC_CONDITIONS.items()})
CONDITIONS.update(total_days='記録に残っている起動日数',level='キャラのレベル',trophy_count='取得した実績数',costume_count='解放した衣装数',weekday='曜日（0=月曜〜6=日曜）',month='月（1〜12月）')
NUMERIC = ('metric', 'continuous_input', 'app_count', 'streak_days', 'total_minutes', 'event_count')+tuple(METRIC_CONDITIONS)+('total_days','level','trophy_count','costume_count','weekday','month')


class ContentError(ValueError): pass


def require(ok, message):
    if not ok: raise ContentError(message)


def number(value, low, high):
    return type(value) in (int, float) and low <= value <= high and math.isfinite(value)


def identifier(value): return isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9_.-]{0,63}', value)


def text(value, limit=1000): return isinstance(value, str) and 0 < len(value.strip()) <= limit


def atomic_json(path, value):
    """Unique temp files allow the editor and reader to coexist safely."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    require(len(payload.encode('utf-8'))<=MAX_JSON,'JSONは2MBまでです。')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=path.parent,
                                         prefix='.'+path.name+'-', suffix='.tmp', delete=False) as f:
            temporary = Path(f.name); f.write(payload); f.flush()
            import os
            os.fsync(f.fileno())
        temporary.replace(path)
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def read_json(path):
    return read_json_snapshot(path)[0]


def read_json_snapshot(path):
    with Path(path).open('rb') as stream:payload=stream.read(MAX_JSON+1)
    require(len(payload)<=MAX_JSON,'JSONは2MBまでです。')
    document=json.loads(payload.decode('utf-8-sig'),parse_constant=lambda _: (_ for _ in ()).throw(ContentError('有限の数値を指定してください。')))
    return document,hashlib.sha256(payload).hexdigest()


def asset_path(root, value):
    require(isinstance(value, str) and len(value) <= 240 and '\\' not in value, '画像はパック内の相対パスで指定してください。')
    parts = PurePosixPath(value)
    require(value and not parts.is_absolute() and all(p not in ('..', '.') for p in parts.parts)
            and ':' not in value and '\0' not in value, '画像パスがパックの外を参照しています。')
    candidate = Path(root).joinpath(*parts.parts)
    require(candidate.resolve().is_relative_to(Path(root).resolve()), '画像パスがパックの外を参照しています。')
    require(candidate.is_file() and candidate.suffix.lower() == '.png' and candidate.stat().st_size <= 8*1024*1024,
            '画像は実在する8MB以下のPNGにしてください。')
    # Inspect headers before Qt decodes a potentially enormous image.
    import struct
    with candidate.open('rb') as f: header = f.read(24)
    require(len(header) == 24 and header[:8] == b'\x89PNG\r\n\x1a\n' and header[12:16] == b'IHDR', 'PNGのヘッダーが不正です。')
    w, h = struct.unpack('>II', header[16:24])
    require(1 <= w <= 2048 and 1 <= h <= 2048, '画像寸法は1〜2048pxです。')
    from PySide6.QtGui import QImageReader
    reader = QImageReader(str(candidate))
    require(reader.canRead() and not reader.read().isNull(), 'PNGを読み込めません。')
    return candidate


def validate_condition(c):
    require(isinstance(c, dict) and c.get('type') in CONDITIONS, '未知の条件タイプです。')
    kind = c['type']
    if kind in NUMERIC:
        require(c.get('op') in ('>=', '<=', '==') and number(c.get('value'), -1e9 if kind=='metric' else 0, 1e9), '条件の比較・値が不正です。')
    if kind in ('weekday','month'):
        require(number(c.get('value'),0 if kind=='weekday' else 1,6 if kind=='weekday' else 12) and c['value']==int(c['value']),'曜日は0〜6、月は1〜12の整数です。')
    if kind == 'metric': require(c.get('metric') in METRICS, '未知のPC状態項目です。')
    if kind == 'event_count': require(text(c.get('event_id'), 130), '演出IDが必要です。')
    if kind == 'time_range':
        for key in ('start', 'end'):
            require(isinstance(c.get(key), str) and re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', c[key]), '時刻はHH:mmです。')
    if kind == 'date_range':
        try:
            require(date.fromisoformat(c['start']).isoformat() == c['start'] and
                    date.fromisoformat(c['end']).isoformat() == c['end'] and c['start'] <= c['end'], '日付の範囲が不正です。')
        except (ValueError, TypeError, KeyError): raise ContentError('日付はYYYY-MM-DDです。') from None
    if kind == 'day_kind': require(c.get('value') in ('business', 'holiday'), '営業日か休日を選んでください。')
    return deepcopy(c)


def validate_config(c):
    require(isinstance(c, dict), '成長の全体設定が必要です。')
    for key, low, high in (('exp_per_hour', 0, 10000), ('exp_interval_seconds',5,3600), ('event_interval_seconds', 30, 3600),
                           ('idle_threshold_seconds', 5, 600)):
        require(number(c.get(key), low, high), key+'が範囲外です。')
    thresholds = c.get('level_thresholds')
    require(isinstance(thresholds, list) and 2 <= len(thresholds) <= 100 and thresholds[0] == 0
            and all(number(n, 0, 1e12) for n in thresholds)
            and all(a < b for a, b in zip(thresholds, thresholds[1:])), 'レベル累計EXPは0から始まる昇順の2〜100個です。')
    require(c.get('streak_mode') in ('calendar', 'business'), '連続起動は暦日か営業日です。')
    require(type(c.get('count_locked')) is bool, 'ロック中の計時はオン／オフです。')
    return deepcopy(c)


def validate_item(kind, item, root):
    require(kind in KINDS and isinstance(item, dict) and identifier(item.get('id')), '項目IDが不正です。')
    require(text(item.get('name'), 80), '表示名は1〜80文字です。')
    require(type(item.get('enabled')) is bool and type(item.get('level')) is int and 1 <= item['level'] <= 100, '有効状態またはレベルが不正です。')
    chars = item.get('characters')
    require(isinstance(chars, list) and chars and len(chars) == len(set(chars)) and all(c in CHARACTERS for c in chars), '対象キャラを選んでください。')
    if kind in ('lines', 'events', 'trophies'):
        conditions = item.get('conditions')
        require(isinstance(conditions, list) and len(conditions) <= 12, '条件は12個までです。')
        for c in conditions: validate_condition(c)
        require(item.get('expression') in EXPRESSIONS, '表情が不正です。')
        texts = item.get('texts')
        require(isinstance(texts, dict) and texts and all(k in (*VOICE_NAMES, '*') and text(v) for k, v in texts.items()), '性格別のセリフを入力してください。')
        require(number(item.get('exp'), 0, 100000), '報酬EXPは0〜100000です。')
    if kind in ('lines', 'events'):
        for key, low, high in (('probability', 0, 1), ('cooldown_minutes', 1, 525600)):
            require(number(item.get(key), low, high), key+'が範囲外です。')
        require(type(item.get('daily_limit')) is int and 1 <= item['daily_limit'] <= 100
                and type(item.get('priority')) is int and 0 <= item['priority'] <= 100, '回数上限・優先度が不正です。')
        if kind == 'lines': require(item['exp'] == 0, '追加セリフのEXPは0です。演出を使用してください。')
        if kind == 'events': require(item.get('effect') in ('pose', 'sparkle'), '演出方式が不正です。')
    if kind == 'trophies':
        require(type(item.get('hidden')) is bool and text(item.get('description'), 500), '実績の説明・秘密設定が不正です。')
        if item.get('icon'): asset_path(root, item['icon'])
    if kind == 'rewards':
        require(isinstance(item.get('unlock'), list) and 1 <= len(item['unlock']) <= 30
                and all(text(s, 130) for s in item['unlock']), '解放する項目IDを指定してください。')
    if kind == 'costumes':
        require(item.get('slot') in ('head', 'body', 'accessory') and item.get('layer') in ('back', 'front', 'accessory'), '衣装の枠・レイヤーが不正です。')
        variants = item.get('variants')
        require(isinstance(variants, list) and 1 <= len(variants) <= 100, '衣装の対応フレームを1〜100件指定してください。')
        for v in variants:
            require(isinstance(v, dict) and v.get('character') in chars, '衣装の対象キャラが不正です。')
            frames = v.get('frames')
            require(isinstance(frames, list) and frames and len(frames) <= 28 and
                    all(type(f) is int and 0 <= f <= 27 for f in frames), '通常・歩行・正面のフレームは0〜27です。')
            for key in ('x', 'y'): require(number(v.get(key), -2048, 2048), '画像位置は±2048pxです。')
            require(number(v.get('scale'), .05, 8), '画像倍率は0.05〜8です。')
            asset_path(root, v.get('image'))
    return deepcopy(item)


class Catalog:
    def __init__(self):
        self.items = {kind: {} for kind in KINDS}; self.packs = {}; self.errors = []; self.config = None

    @property
    def all_items(self): return {key: item for values in self.items.values() for key, item in values.items()}


def inspect_pack(document, root):
    """Return individual valid entries plus errors; malformed entries are isolated."""
    require(isinstance(document, dict) and type(document.get('schema_version')) is int and document['schema_version'] == 1,
            'パックのschema_versionは1です。')
    require(len(json.dumps(document,ensure_ascii=False,allow_nan=False).encode('utf-8'))<=MAX_JSON,'JSONは2MBまでです。')
    require(identifier(document.get('id')) and text(document.get('name'), 80) and type(document.get('enabled')) is bool, 'パックのID・表示名・有効状態が不正です。')
    valid = {k: [] for k in KINDS}; errors = []; seen = set()
    # Duplicate IDs invalidate ALL conflicting entries, not just the last one.
    from collections import Counter
    counts = Counter(item.get('id') for k in KINDS for item in document.get(k, []) if isinstance(item, dict) and isinstance(item.get('id'), str))
    for kind in KINDS:
        entries = document.get(kind)
        require(isinstance(entries, list) and len(entries) <= 300, kind+'は300件までの配列です。')
        for index, item in enumerate(entries):
            try:
                require(not isinstance(item, dict) or counts.get(item.get('id'), 0) <= 1, '同じ項目IDが重複しています。')
                valid[kind].append(validate_item(kind, item, root))
            except (ValueError, TypeError, OSError, RecursionError) as e:
                errors.append(f'{kind}[{index+1}]: {e}')
    if document.get('id') == 'base': validate_config(document.get('config'))
    return valid, errors


def load_catalog(content_root):
    catalog = Catalog(); candidates = []
    root = Path(content_root)
    if root.is_dir():
        try:folders = sorted(root.iterdir())
        except OSError:
            catalog.errors.append('コンテンツ保存先の一覧を読み込めません。保存先の権限をご確認ください。');folders=[]
        if len(folders) > 100: catalog.errors.append('パックは100個までです。超過分は読み込みません。')
        for folder in folders[:100]:
            if not folder.is_dir() or folder.is_symlink() or folder.name.startswith('.'): continue
            path = folder/'pack.json'
            try:
                document = read_json(path); valid, errors = inspect_pack(document, folder)
                catalog.errors.extend(f'{folder.name}: {s}' for s in errors)
                candidates.append((folder, document, valid))
            except (OSError, ValueError, TypeError, RecursionError) as e: catalog.errors.append(f'{folder.name}: {e}')
    from collections import Counter
    counts = Counter(doc['id'] for _, doc, _ in candidates)
    for folder, doc, valid in candidates:
        if counts[doc['id']] > 1:
            catalog.errors.append(f'{folder.name}: パックID {doc["id"]} が重複しているため無効です。'); continue
        catalog.packs[doc['id']] = dict(path=folder, document=doc)
        if not doc['enabled']: continue
        if doc['id'] == 'base': catalog.config = validate_config(doc['config'])
        for kind, entries in valid.items():
            for item in entries:
                if not item['enabled']: continue
                key = doc['id']+':'+item['id']
                catalog.items[kind][key] = dict(item, key=key, root=folder)
    # References to disabled/deleted/invalid entries must not partially award.
    changed=True
    while changed:
        changed=False
        for kind in ('events','lines','trophies','rewards'):
            for key,item in list(catalog.items[kind].items()):
                unlocked={**catalog.items['costumes'],**catalog.items['lines'],**catalog.items['events']}
                invalid=(any(ref not in unlocked for ref in item.get('unlock',[])) or
                         any(c['event_id'] not in catalog.items['events'] for c in item.get('conditions',[]) if c['type']=='event_count'))
                if invalid:
                    catalog.errors.append(key+': 参照先が存在しないか、無効です。');del catalog.items[kind][key];changed=True
    if catalog.config is None: catalog.errors.append('有効なbaseパックがありません。成長を停止しています。')
    return catalog


def seed_content(root):
    """Install a sample once. Never overwrite an existing user-edited base pack."""
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    _seed_packs(root,('base',))


def seed_examples(root):
    root=Path(root);marker=root/'.daily-trophies-installed'
    if marker.exists():return
    _seed_packs(root,('daily_trophies',))
    marker.touch(exist_ok=True)


def _seed_packs(root,names):
    root.mkdir(parents=True,exist_ok=True)
    for name in names:
        if (root/name).exists():continue
        source=Path(__file__).parent/'assets/growth'/name
        with tempfile.TemporaryDirectory(prefix='.'+name+'-',dir=root) as temp:
            staged=Path(temp)/name;shutil.copytree(source,staged)
            if not (root/name).exists():
                try:staged.rename(root/name)
                except OSError:
                    if not (root/name).is_dir():raise
