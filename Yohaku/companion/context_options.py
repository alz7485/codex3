"""Local context configuration and reversible topic preferences, with atomic saves."""
from copy import deepcopy
from datetime import date
import json
import ntpath
from pathlib import Path
import re
import shutil

from .business_calendar import BusinessCalendar


class ContextOptionsError(ValueError): pass


def defaults():
    return {'schema_version':1, 'calendar':{'japanese_holidays':True,'weekdays':[0,1,2,3,4],
            'holidays':[], 'workdays':[]}, 'targets':[], 'consecutive_gap_minutes':10}


def validate(document):
    if not isinstance(document,dict) or type(document.get('schema_version')) is not int or document['schema_version'] != 1:
        raise ContextOptionsError('設定JSONのschema_versionは1です。')
    calendar = document.get('calendar', {})
    if not isinstance(calendar,dict) or type(calendar.get('japanese_holidays')) is not bool:
        raise ContextOptionsError('日本の祝日の設定が不正です。')
    weekdays = calendar.get('weekdays')
    if not isinstance(weekdays,list) or not weekdays or any(type(n) is not int or n not in range(7) for n in weekdays) or len(set(weekdays)) != len(weekdays):
        raise ContextOptionsError('営業曜日を1つ以上指定してください。')
    for key in ('holidays','workdays'):
        values = calendar.get(key)
        if not isinstance(values,list) or len(values)>2000: raise ContextOptionsError('休日・営業日は各2000件までです。')
        for value in values:
            try:
                if not isinstance(value,str) or date.fromisoformat(value).isoformat()!=value: raise ValueError()
            except ValueError: raise ContextOptionsError('日付はYYYY-MM-DDで入力してください。') from None
    if type(document.get('consecutive_gap_minutes')) is not int or not 0<=document['consecutive_gap_minutes']<=120:
        raise ContextOptionsError('連続会議の間隔は0〜120分です。')
    targets = document.get('targets')
    if not isinstance(targets,list) or len(targets)>30: raise ContextOptionsError('対象ファイル・フォルダーは30件までです。')
    seen = set()
    for target in targets:
        if not isinstance(target,dict): raise ContextOptionsError('対象の形式が不正です。')
        key = target.get('id')
        if not isinstance(key,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',key) or key in seen:
            raise ContextOptionsError('対象IDが不正または重複しています。')
        seen.add(key)
        if target.get('kind') not in ('file','folder'): raise ContextOptionsError('ファイルかフォルダーを選んでください。')
        if not isinstance(target.get('label'),str) or not 1<=len(target['label'].strip())<=80:
            raise ContextOptionsError('対象の名前は1〜80文字です。')
        path = target.get('path')
        if not isinstance(path,str) or not 1<=len(path)<=2048 or '\0' in path or not ntpath.isabs(path):
            raise ContextOptionsError('対象には絶対パスを指定してください。')
    return deepcopy(document)


class ContextOptionsStore:
    def __init__(self, path):
        self.path = Path(path); self.data = defaults(); self.error = ''
        if self.path.exists():
            try:
                if self.path.stat().st_size>1024*1024: raise ContextOptionsError('設定JSONが大きすぎます。')
                self.data = self.validate(json.loads(self.path.read_text(encoding='utf-8-sig')))
            except (OSError,ValueError,TypeError,RecursionError) as error:
                self.error = f'設定を読めないため初期値を使用しています。元のファイルは保持しています。{error}'

    validate = staticmethod(validate)

    def save(self, document):
        candidate = self.validate(document)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary = self.path.with_suffix('.json.tmp')
        try:
            temporary.write_text(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            if self.path.exists(): shutil.copy2(self.path,self.path.with_suffix('.json.bak'))
            temporary.replace(self.path)
        finally: temporary.unlink(missing_ok=True)
        self.data = candidate; self.error = ''

    def calendar(self): return BusinessCalendar(self.data['calendar'])


class TopicPreferences(ContextOptionsStore):
    @staticmethod
    def validate(document):
        if not isinstance(document,dict) or type(document.get('schema_version')) is not int or document['schema_version'] != 1 or not isinstance(document.get('topics'),dict) or len(document['topics'])>200:
            raise ContextOptionsError('話題の表示設定が不正です。')
        for key,value in document['topics'].items():
            if not isinstance(key,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,39}',key) or not isinstance(value,dict) or type(value.get('reduced')) is not bool:
                raise ContextOptionsError('話題の表示設定が不正です。')
            try:
                day=value.get('muted_date','')
                if not isinstance(day,str) or (day and date.fromisoformat(day).isoformat()!=day): raise ValueError()
            except ValueError: raise ContextOptionsError('話題の休止日が不正です。') from None
        return deepcopy(document)

    def __init__(self,path):
        super().__init__(path)
        if not self.path.exists() or self.error: self.data={'schema_version':1,'topics':{}}

    def preference(self,key): return self.data['topics'].get(key,{'muted_date':'','reduced':False})

    def update(self,key,*,muted_date='',reduced=False):
        candidate=deepcopy(self.data)
        candidate['topics'][key]={'muted_date':muted_date,'reduced':reduced}
        self.save(candidate)
