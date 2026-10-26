"""Named local move destinations; old per-extension paths remain readable."""
from copy import deepcopy
import json
import ntpath
from pathlib import Path, PureWindowsPath
import re
from uuid import uuid4
from .context_options import ContextOptionsStore
from .file_drop import FileDropError


def validate(document):
    if (not isinstance(document, dict) or set(document) != {'schema_version','destinations'}
            or type(document['schema_version']) is not int or document['schema_version'] != 1
            or not isinstance(document['destinations'], list) or len(document['destinations']) > 100):
        raise FileDropError('移動先は100件まで登録できます。')
    ids=set(); names=set()
    for row in document['destinations']:
        if not isinstance(row,dict) or set(row) != {'id','name','path'}:
            raise FileDropError('移動先の設定形式が不正です。')
        if not isinstance(row['id'],str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',row['id']) or row['id'] in ids:
            raise FileDropError('移動先IDが不正または重複しています。')
        name=row['name'];path=row['path']
        if not isinstance(name,str) or not name.strip() or len(name)>60 or any(ord(c)<32 for c in name) or name.strip().casefold() in names:
            raise FileDropError('表示名は重複しない1〜60文字にしてください。')
        if (not isinstance(path,str) or len(path)>2048 or any(ord(c)<32 for c in path)
                or not (Path(path).is_absolute() or PureWindowsPath(path).is_absolute())):
            raise FileDropError('移動先にはフォルダーのフルパスを入力してください。')
        ids.add(row['id']);names.add(name.strip().casefold())
    return deepcopy(document)


class DestinationStore(ContextOptionsStore):
    validate=staticmethod(validate)

    def __init__(self,path,legacy=None):
        self.path=Path(path);self.error='';self.data={'schema_version':1,'destinations':[]}
        if self.path.exists():
            try:
                if self.path.stat().st_size>1024*1024:raise ValueError()
                self.data=validate(json.loads(self.path.read_text(encoding='utf-8-sig')))
            except (OSError,ValueError,TypeError,RecursionError):
                self.error='移動先JSONを読み込めません。元のファイルは保持しています。'
        elif legacy and not legacy.error:
            seen=set(); names=set()
            for rule in legacy.data['rules']:
                folder=rule['destination'];key=ntpath.normcase(ntpath.normpath(folder))
                if not folder or key in seen:continue
                label=(PureWindowsPath(folder).name if PureWindowsPath(folder).is_absolute() else Path(folder).name) or rule['label']
                name=label[:55];i=2
                while name.casefold() in names:name=f'{label[:50]} ({i})';i+=1
                names.add(name.casefold());seen.add(key)
                self.data['destinations'].append(dict(id=uuid4().hex,name=name,path=folder))
