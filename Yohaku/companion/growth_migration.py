"""Upgrade unchanged bundled pacing only; preserve edits and earned progress."""
from copy import deepcopy
from pathlib import Path
import os

from .growth_content import ContentError,atomic_json,inspect_pack,read_json,read_json_snapshot


def upgrade_pacing(root):
    assets=Path(__file__).parent/'assets'
    legacy=read_json(assets/'growth_migrations/v0350.json')
    for name,old in legacy.items():
        folder=Path(root)/name;path=folder/'pack.json';marker=folder/'.pacing-v0360'
        if marker.exists() or not path.is_file():continue
        try:
            document,digest=read_json_snapshot(path)
            _,errors=inspect_pack(document,folder)
            if errors or document['id']!=name:continue
        except (ContentError,ValueError):
            # A broken pack is reported by load_catalog; never replace it.
            continue
        current=read_json(assets/'growth'/name/'pack.json')
        updated=deepcopy(document)
        if name=='base' and updated.get('config',{}).get('level_thresholds')==old['config']['level_thresholds']:
            updated['config']['level_thresholds']=current['config']['level_thresholds']
        old_items={x['id']:x for x in old['trophies']};new_items={x['id']:x for x in current['trophies']}
        trophies=[]
        for item in updated['trophies']:
            if item==old_items.get(item['id']):
                replacement=new_items.get(item['id'])
                if replacement is not None:trophies.append(deepcopy(replacement))
            else:trophies.append(item)
        updated['trophies']=trophies
        if updated!=document:
            _,errors=inspect_pack(updated,folder)
            if errors:continue
            # Snapshot check also catches an editor saving during startup.
            if read_json_snapshot(path)[1]!=digest:continue
            backup=folder/'pack.pre-v0360.json'
            try:
                with backup.open('x',encoding='utf-8') as stream:
                    import json
                    stream.write(json.dumps(document,ensure_ascii=False,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
            except FileExistsError:pass
            if read_json_snapshot(path)[1]!=digest:continue
            atomic_json(path,updated)
        marker.touch(exist_ok=True)
