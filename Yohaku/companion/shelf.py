"""Local temporary launcher references. No operations on referenced data."""
from copy import deepcopy
from datetime import datetime,timedelta
import json
import ntpath
from pathlib import Path,PureWindowsPath
import re
from uuid import uuid4
from .context_options import ContextOptionsStore
from .file_drop import dropped_item

PERIODS={'day':'1日','week':'1週間','month':'1ヶ月','forever':'無期限'}
MAX_ITEMS=500

class ShelfError(ValueError):pass


def local_time(value):
    return value.astimezone().replace(tzinfo=None) if value.tzinfo is not None else value


def next_reset(added,period):
    value=local_time(added)
    if period=='forever':return None
    if period=='day':
        boundary=value.replace(hour=5,minute=0,second=0,microsecond=0)
        return boundary if value<boundary else boundary+timedelta(days=1)
    if period=='week':
        return value.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=7-value.weekday())
    if period=='month':
        year,month=(value.year+1,1) if value.month==12 else (value.year,value.month+1)
        return datetime(year,month,1)
    raise ShelfError('保持期間の指定が不正です。')


def validate(document):
    if (not isinstance(document,dict) or set(document)!={'schema_version','period','items'}
            or type(document['schema_version']) is not int or document['schema_version']!=1
            or not isinstance(document['period'],str) or document['period'] not in PERIODS
            or not isinstance(document['items'],list) or len(document['items'])>MAX_ITEMS):
        raise ShelfError('預けたものの設定形式が不正です。登録は500件までです。')
    ids=set();paths=set()
    for row in document['items']:
        if not isinstance(row,dict) or set(row)!={'id','path','kind','added_at'}:
            raise ShelfError('預けたものの形式が不正です。')
        if not isinstance(row['id'],str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',row['id']) or row['id'] in ids:
            raise ShelfError('登録IDが不正または重複しています。')
        path=row['path']
        if (not isinstance(path,str) or len(path)>2048 or any(ord(c)<32 for c in path)
                or not (Path(path).is_absolute() or PureWindowsPath(path).is_absolute())):
            raise ShelfError('登録先にはファイル・フォルダーのフルパスを指定してください。')
        key=ntpath.normcase(ntpath.normpath(path))
        if key in paths or row['kind'] not in ('file','folder'):raise ShelfError('登録先が重複しているか、種類が不正です。')
        try:
            if not isinstance(row['added_at'],str) or len(row['added_at'])>40:raise ValueError()
            if not 1970<=datetime.fromisoformat(row['added_at']).year<=9998:raise ValueError()
        except ValueError:raise ShelfError('預けた日時が不正です。') from None
        ids.add(row['id']);paths.add(key)
    if len(json.dumps(document,ensure_ascii=False,indent=2).encode('utf-8'))>2*1024*1024:
        raise ShelfError('一覧の保存サイズを超えています。登録を減らしてください。')
    return deepcopy(document)


class ShelfStore(ContextOptionsStore):
    validate=staticmethod(validate)
    def __init__(self,path):
        self.path=Path(path);self.error='';self.data=dict(schema_version=1,period='day',items=[])
        if self.path.exists():
            try:
                if self.path.stat().st_size>2*1024*1024:raise ValueError()
                self.data=validate(json.loads(self.path.read_text(encoding='utf-8-sig')))
            except (OSError,ValueError,TypeError,RecursionError):
                self.error='預けたもののJSONを読み込めません。元のファイルは保持しています。'
    def ready(self):
        if self.error:raise ShelfError(self.error)
    def current_items(self,now,period=None):
        self.ready();period=period or self.data['period'];value=local_time(now)
        return [deepcopy(row) for row in self.data['items'] if period=='forever'
                or value<next_reset(datetime.fromisoformat(row['added_at']),period)]
    def prune(self,now):
        items=self.current_items(now)
        if len(items)!=len(self.data['items']):self.save(dict(self.data,items=items))
        return deepcopy(items)
    def add(self,path,now):
        self.ready();path=dropped_item(path);kind='folder' if path.is_dir() else 'file'
        key=ntpath.normcase(ntpath.normpath(str(path)));items=self.current_items(now)
        existing=next((row for row in items if ntpath.normcase(ntpath.normpath(row['path']))==key),None)
        if existing:
            items.remove(existing);identifier=existing['id']
        else:identifier=uuid4().hex
        if len(items)>=MAX_ITEMS:raise ShelfError('預けられるのは500件までです。一覧から登録を削除してください。')
        items.insert(0,dict(id=identifier,path=str(path),kind=kind,added_at=now.isoformat(timespec='seconds')))
        self.save(dict(self.data,items=items));return identifier
    def remove(self,identifier):
        self.ready();self.save(dict(self.data,items=[row for row in self.data['items'] if row['id']!=identifier]))
    def set_period(self,period,now):
        self.ready()
        if not isinstance(period,str) or period not in PERIODS:raise ShelfError('保持期間の指定が不正です。')
        self.save(dict(self.data,period=period,items=self.current_items(now,period)))
