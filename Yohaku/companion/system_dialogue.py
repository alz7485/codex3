"""Editable personality-specific speech for functional interactions."""
from copy import deepcopy
import json
from pathlib import Path
import re

_DATA=json.loads((Path(__file__).parent/'assets/dialogue/system_phrases.json').read_text(encoding='utf-8'))
SYSTEM_LABELS=_DATA['labels']


def system_defaults():return deepcopy(_DATA['phrases'])


def system_fields(key):
    return set(re.findall(r'\{([a-z_]+)\}',_DATA['phrases']['冷静な案内役'][key][0]))


def validate_system_phrases(bank):
    if not isinstance(bank,dict) or set(bank)!=set(_DATA['phrases']):raise ValueError('操作案内には全7性格が必要です。')
    for voice,topics in bank.items():
        if not isinstance(topics,dict) or set(topics) not in (set(SYSTEM_LABELS),set(SYSTEM_LABELS)-{'extracted_only','extract_destination'}):raise ValueError(f'{voice}: 操作案内の項目が不足しています。')
        for key,lines in topics.items():
            if (not isinstance(lines,list) or not 1<=len(lines)<=200
                    or any(not isinstance(s,str) or not s.strip() or len(s)>1000 for s in lines)):
                raise ValueError(f'{voice} / {key}: セリフは1〜200件、1件1〜1000文字にしてください。')
            if any(set(re.findall(r'\{([a-z_]+)\}',line))!=system_fields(key) for line in lines):
                fields='・'.join('{'+s+'}' for s in sorted(system_fields(key))) or 'なし'
                raise ValueError(f'{voice} / {key}: この案内の差し込みは {fields} です。必要な情報を残してください。')


def render_system_phrase(voice,key,document=None,replacements=None,choose=lambda lines:lines[0]):
    bank=(document or {}).get('system_phrases',_DATA['phrases'])
    lines=bank[voice].get(key,_DATA['phrases'][voice][key]);template=lines[choose(list(range(len(lines))))]
    values={k:str(v) for k,v in (replacements or {}).items()}
    # Substitute once: braces in file names or user text stay literal.
    text=re.sub(r'\{([a-z_]+)\}',lambda m:values.get(m[1],m[0]),template)
    if voice=='寡黙な先輩':
        thought=re.search(r'\n（[\s\S]*）\s*$',text)
        if thought and text[:thought.start()].strip()!='…':text=text[:thought.start()].rstrip()
    return text
