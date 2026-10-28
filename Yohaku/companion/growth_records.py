"""Read-only views of growth definitions and earned records."""
from .growth import condition_matches,condition_value
from .growth_content import CONDITIONS,NUMERIC,number
from .metrics import METRICS

KIND_LABELS={'lines':'会話','events':'演出','costumes':'衣装','rewards':'レベル報酬'}
SLOT_LABELS={'head':'頭','body':'体','accessory':'アクセサリー'}


def collection_rows(catalog,progress,character):
    levels={key:item['level'] for kind in KIND_LABELS for key,item in catalog.items[kind].items() if character in item['characters']}
    for reward in catalog.items['rewards'].values():
        if character not in reward['characters']:continue
        for key in reward['unlock']:
            if key in levels:levels[key]=min(levels[key],reward['level'])
    rows=[];known=set()
    limit=max(progress['level'],len(catalog.config['level_thresholds'])) if catalog.config else 0
    for kind in KIND_LABELS:
        for key,item in catalog.items[kind].items():
            if character not in item['characters']:continue
            known.add(key);unlocked=key in progress['unlocked']
            rows.append(dict(key=key,kind=kind,name=item['name'],level=levels[key],unlocked=unlocked,item=item,reachable=levels[key]<=limit,
                state='解放済み' if unlocked else '反映待ち' if levels[key]<=progress['level'] else '現在の上限を超えています' if levels[key]>limit else '未解放'))
    for key in sorted((set(progress['unlocked'])|set(progress['equipped'].values()))-known):
        # A definition for another character is unavailable to this record too.
        rows.append(dict(key=key,kind='missing',name=key,level=None,unlocked=True,item=None,state='パック未読込・記録保持'))
    return sorted(rows,key=lambda row:(row['level'] if row['level'] is not None else 101,row['name'],row['key']))


def next_unlocks(catalog,progress,character):
    if not catalog.config:return []
    limit=max(progress['level'],len(catalog.config['level_thresholds']))
    rows=[row for row in collection_rows(catalog,progress,character)
          if row['kind'] in ('lines','events','costumes') and not row['unlocked'] and progress['level']<row['level']<=limit]
    if not rows:return []
    first=min(row['level'] for row in rows)
    return [row for row in rows if row['level']==first]


def condition_title(condition,catalog):
    kind=condition['type'];title=METRICS[condition['metric']] if kind=='metric' else CONDITIONS[kind]
    if kind in NUMERIC:
        if kind=='event_count':title+='：'+catalog.items['events'].get(condition['event_id'],{}).get('name','未読込の演出')
        op={'>=':'以上','<=':'以下','==':'と等しい'}[condition['op']]
        return f'{title}  {condition["value"]:g}{op}'
    if kind in ('time_range','date_range'):return title+'：'+condition['start']+'〜'+condition['end']
    if kind=='day_kind':return '会社カレンダーの'+('営業日' if condition['value']=='business' else '休日')
    return title


def condition_rows(item,progress,now,metrics,calendar,catalog,work):
    rows=[]
    metrics=dict(metrics,_growth_costumes=catalog.items['costumes']) if '_growth_character' in metrics else metrics
    for condition in item['conditions']:
        kind=condition['type'];value=None;known=catalog.config is not None
        if known and kind in NUMERIC:
            value=condition_value(condition,progress,now,metrics,calendar,catalog.config,work)
            known=number(value,-1e15,1e15)
        elif kind=='day_kind':known=known and calendar is not None
        elif kind=='outside_hours':known=known and calendar is not None and number(metrics.get('idle_minutes'),0,1e9)
        met=condition_matches(condition,progress,now,metrics,calendar,catalog.config,work) if known else None
        rows.append(dict(title=condition_title(condition,catalog),value=value if known else None,met=met,
                         status='未取得・確認できません' if met is None else '条件を満たしています' if met else 'まだ条件を満たしていません'))
    return rows


def trophy_text(key,catalog,progress,character,now,metrics,calendar,work,active):
    if not active:metrics={}
    metrics=dict(metrics,_growth_character=character)
    item=catalog.items['trophies'].get(key);record=progress['trophies'].get(key)
    if item is None:
        return key+'\n\n取得済みの記録を保持しています。パックを再読み込みすると名前や説明を確認できます。'+('\n取得日時：'+record['at'] if record else '')
    if item['hidden'] and not record:return '？？？\n\n秘密のトロフィーです。取得すると名前・条件・報酬を確認できます。'
    lines=[item['name'],item['description'],'',f'獲得時のEXP：{record["exp"] if record else item["exp"]:g}']
    if record:lines+=['取得日時：'+record['at'],'以下は現在の条件です。取得記録は取り消しません。']
    elif progress['level']<item['level']:lines+=[f'Lv.{item["level"]}から判定します。']
    if not active:lines+=['現在の常駐キャラとは別のキャラです。PC状態の現在値は表示しません。']
    rows=condition_rows(item,progress,now,metrics,calendar,catalog,work)
    if not rows:lines+=['条件の追加指定はありません。対象レベルで表示中に判定します。']
    for row in rows:
        lines+=['',row['title'],('現在値：'+f'{row["value"]:g}'+' / ' if row['value'] is not None else '')+row['status']]
    if key in progress['best']:lines+=['',f'保存済みの観測最高値：{progress["best"][key]:g}（最初の数値条件）']
    lines+=['','未取得の実績は、すべての条件を同じ確認時点で満たすと記録します。']
    return '\n'.join(lines)


def collection_text(row,catalog,progress,character,voice):
    if row['item'] is None:return row['key']+'\n\nパックを無効・削除しても取得記録を保持します。未読込の内容は表示・試着できません。'
    item=row['item'];lines=[row['name'],KIND_LABELS[row['kind']]+' / '+row['state'],f'解放レベル：Lv.{row["level"]}']
    if not row['unlocked'] and not row['reachable']:lines+=['現在のレベル上限を超えています。パックの設定を確認してください。']
    if row['kind']=='rewards':
        lines+=['','解放するもの：']
        for key in item['unlock']:
            target=catalog.all_items.get(key)
            if target and character in target['characters']:lines+=['・'+target['name']]
    if row['kind']=='costumes':
        frames=sorted({frame for variant in item['variants'] if variant['character']==character for frame in variant['frames']})
        poses=[]
        if any(frame<16 for frame in frames):poses.append('通常・表情')
        if any(16<=frame<24 for frame in frames):poses.append('歩行')
        if any(frame>=24 for frame in frames):poses.append('正面')
        lines+=['装備枠：'+SLOT_LABELS[item['slot']],'対応する動作：'+'・'.join(poses),'未対応フレーム・小道具の動作中は非表示です。']
    if row['kind'] in ('lines','events'):
        if row['unlocked']:
            text=item['texts'].get(voice,item['texts'].get('*','この性格のセリフは未登録です。'))
            lines+=['','現在の性格：'+voice,text]
            record=progress['events'].get(row['key'])
            if record:lines+=['',f'表示した回数：{record["count"]}','最後の表示：'+record['last']]
            lines+=['','解放後も条件・抽選・表示状況に従って話します。']
        else:lines+=['','セリフの本文は解放後に表示します。']
        for condition in item['conditions']:lines+=['・'+condition_title(condition,catalog)]
    return '\n'.join(lines)
